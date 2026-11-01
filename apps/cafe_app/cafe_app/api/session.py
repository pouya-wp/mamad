import base64
import binascii
import hashlib
import hmac
import json
import secrets
import time

import frappe
from frappe import _
from frappe.sessions import get_csrf_token

from cafe_app.access import SCOPE_LABELS, buyer_scope, buyer_scopes
from cafe_app.cafe_setup import ensure_cafe_defaults
from cafe_app.utils import get_cafe_settings


DESKTOP_COOKIE = "one_cafe_device"
DESKTOP_LIFETIME = 90 * 24 * 60 * 60
DESKTOP_RENEW_BEFORE = 30 * 24 * 60 * 60


def _desktop_request():
	return "ONECAFE/" in (frappe.get_request_header("User-Agent") or "")


def _manager(user):
	return user == "Administrator" or "System Manager" in frappe.get_roles(user)


def _encode(value):
	return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode(value):
	return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _sign(value):
	secret = frappe.conf.get("cafe_desktop_signing_key")
	if not secret:
		return None
	return _encode(hmac.new(secret.encode("utf-8"), value.encode("ascii"), hashlib.sha256).digest())


def _device_claims(token):
	if not token or len(token) > 512:
		return None
	try:
		encoded, signature = token.split(".", 1)
		expected = _sign(encoded)
		if not expected or not hmac.compare_digest(signature, expected):
			return None
		claims = json.loads(_decode(encoded))
		if not isinstance(claims, dict) or not isinstance(claims.get("u"), str) or not isinstance(claims.get("e"), int):
			return None
		if claims["e"] <= time.time():
			return None
		return claims
	except (ValueError, TypeError, UnicodeError, binascii.Error):
		return None


def _remember_desktop(user):
	if not frappe.conf.get("cafe_desktop_signing_key"):
		return
	claims = _device_claims(frappe.request.cookies.get(DESKTOP_COOKIE))
	if claims and claims["u"] == user and claims["e"] - time.time() > DESKTOP_RENEW_BEFORE:
		return
	payload = _encode(json.dumps({
		"u": user,
		"e": int(time.time()) + DESKTOP_LIFETIME,
		"n": secrets.token_hex(12),
	}, separators=(",", ":")).encode("utf-8"))
	frappe.local.cookie_manager.set_cookie(
		DESKTOP_COOKIE, payload + "." + _sign(payload),
		max_age=DESKTOP_LIFETIME, secure=True, httponly=True, samesite="Lax",
	)


def _restore_desktop():
	claims = _device_claims(frappe.request.cookies.get(DESKTOP_COOKIE))
	if not claims:
		return
	user = claims["u"]
	if not frappe.db.get_value("User", user, "enabled") or not _manager(user):
		return
	frappe.local.login_manager.login_as(user)
	# An expired sid may already be queued for deletion in this response.
	# The newly issued login cookies must win over that stale deletion.
	reissued = {"sid", "full_name", "user_id", "user_image", "user_lang", "system_user"}
	frappe.local.cookie_manager.to_delete = [
		key for key in frappe.local.cookie_manager.to_delete if key not in reissued
	]


def forget_desktop(login_manager=None):
	"""Frappe on_logout hook: an explicit logout revokes this browser's device cookie."""
	if _desktop_request():
		frappe.local.cookie_manager.delete_cookie(DESKTOP_COOKIE)


def _log_desktop_auth_failure():
	"""Record cookie presence, never credentials, to diagnose unattended clients."""
	try:
		cookies = frappe.request.cookies
		frappe.logger("cafe_desktop_auth", allow_site=True).error(json.dumps({
			"event": "desktop_boot_unauthenticated",
			"ip": getattr(frappe.local, "request_ip", None),
			"user_agent": (frappe.get_request_header("User-Agent") or "")[:256],
			"sid_present": bool(cookies.get("sid")),
			"sid_is_guest": cookies.get("sid") == "Guest",
			"device_cookie_present": bool(cookies.get(DESKTOP_COOKIE)),
			"device_cookie_valid": bool(_device_claims(cookies.get(DESKTOP_COOKIE))),
			"signing_key_configured": bool(frappe.conf.get("cafe_desktop_signing_key")),
		}, sort_keys=True))
	except Exception:
		# Logging cannot interrupt or change authentication.
		pass


@frappe.whitelist(allow_guest=True)
def boot():
	"""Session bootstrap for the panel: who is logged in, their CSRF token and the café context."""
	if frappe.session.user == "Guest" and _desktop_request():
		_restore_desktop()
	if frappe.session.user == "Guest":
		if _desktop_request():
			_log_desktop_auth_failure()
		frappe.throw(_("Not logged in"), frappe.AuthenticationError)

	ensure_cafe_defaults()
	if _desktop_request() and _manager(frappe.session.user):
		_remember_desktop(frappe.session.user)
	user = frappe.get_cached_doc("User", frappe.session.user)

	return {
		"csrf_token": get_csrf_token(),
		"user": {
			"name": user.name,
			"full_name": user.full_name,
			"image": user.user_image,
			"roles": frappe.get_roles(),
			# Purchase managers only get their desk's purchase register.
			"buyer_scope": buyer_scope(),
			"buyer_scope_label": SCOPE_LABELS.get(buyer_scope()),
			"buyer_scopes": list(buyer_scopes()),
			"is_buyer": bool(buyer_scopes()),
		},
		"cafe": get_cafe_settings(),
	}
