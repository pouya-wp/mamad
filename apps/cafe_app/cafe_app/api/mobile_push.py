"""Manage opted-in mobile push devices and send batched sales notices."""

import hashlib
import re

import frappe
import requests
from frappe import _
from frappe.utils import now_datetime


PUSH_ENDPOINT = "https://exp.host/--/api/v2/push/send"
TOKEN_PATTERN = re.compile(r"^(?:Expo|Exponent)PushToken\[[A-Za-z0-9_-]+\]$")


def _require_user():
	if frappe.session.user == "Guest":
		frappe.throw(_("برای ثبت اعلان ابتدا وارد شوید"), frappe.AuthenticationError)


def _hash(token):
	return hashlib.sha256(token.encode("ascii")).hexdigest()


@frappe.whitelist(methods=["POST"])
def register_device(token, platform):
	"""Register only the current signed-in user's own phone."""
	_require_user()
	if not isinstance(token, str) or len(token) > 200 or not TOKEN_PATTERN.fullmatch(token):
		frappe.throw(_("شناسهٔ اعلان نامعتبر است"))
	if platform not in ("ios", "android"):
		frappe.throw(_("سیستم عامل نامعتبر است"))

	name = _hash(token)
	values = {"user": frappe.session.user, "platform": platform, "enabled": 1, "last_seen": now_datetime()}
	if frappe.db.exists("Cafe Mobile Device", name):
		frappe.db.set_value("Cafe Mobile Device", name, values)
	else:
		frappe.get_doc({"doctype": "Cafe Mobile Device", "token_hash": name, "push_token": token, **values}).insert(ignore_permissions=True)
	return {"registered": True}


@frappe.whitelist(methods=["POST"])
def unregister_device(token):
	_require_user()
	if not isinstance(token, str) or len(token) > 200 or not TOKEN_PATTERN.fullmatch(token):
		frappe.throw(_("شناسهٔ اعلان نامعتبر است"))
	name = _hash(token)
	if frappe.db.get_value("Cafe Mobile Device", name, "user") == frappe.session.user:
		frappe.db.set_value("Cafe Mobile Device", name, "enabled", 0)
	return {"registered": False}


def notify_sales_import(count):
	"""Worker task: one notification per import batch, never one per invoice."""
	if not count or count < 1:
		return
	devices = frappe.get_all(
		"Cafe Mobile Device",
		filters={"enabled": 1},
		fields=["name", "user", "push_token"],
		limit_page_length=100,
	)
	devices = [device for device in devices if frappe.db.get_value("User", device.user, "enabled")]
	if not devices:
		return
	message = {
		"title": "ONE CAFE",
		"body": f"{count} سفارش تازه از سپهریار ثبت شد.",
		"sound": "default",
		"channelId": "one-cafe-updates",
		"data": {"path": "/orders"},
	}
	try:
		response = requests.post(
			PUSH_ENDPOINT,
			json=[{"to": device.push_token, **message} for device in devices],
			timeout=10,
		)
		response.raise_for_status()
		outcomes = response.json().get("data", [])
		if isinstance(outcomes, dict):
			outcomes = [outcomes]
		for device, outcome in zip(devices, outcomes):
			if outcome.get("details", {}).get("error") == "DeviceNotRegistered":
				frappe.db.set_value("Cafe Mobile Device", device.name, "enabled", 0)
	except (requests.RequestException, ValueError) as exc:
		frappe.log_error(title="ONE CAFE mobile push failed", message=str(exc))
