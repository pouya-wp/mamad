"""Who may see what in the panel.

Managers (Administrator / System Manager) see everything. A purchase manager
sees the registers and purchase calendar of their granted desks, plus an
assistant limited to purchasing; other APIs are refused before they run.

Managers granted the restaurant purchase role also keep the recipes. They may
read and edit what goes into each dish, while the menu API strips price, cost
and margin, so profitability never leaves the server.
"""

import frappe
from frappe import _

RESTAURANT_BUYER = "Restaurant Purchase Manager"
CAFE_BUYER = "Cafe Purchase Manager"
BUYER_SCOPES = {RESTAURANT_BUYER: "Restaurant", CAFE_BUYER: "Cafe"}
SCOPE_LABELS = {"Restaurant": "رستوران", "Cafe": "کافه"}

# Exactly what a purchase manager's panel calls.
BUYER_METHODS = {
	"login",
	"logout",
	"ping",
	"cafe_app.api.session.boot",
	"cafe_app.api.agent.status",
	"cafe_app.api.agent.chat",
	"cafe_app.api.agent.confirm",
	"cafe_app.api.agent.cancel",
	"cafe_app.api.voice.transcribe",
	"cafe_app.api.voice.speak",
}
BUYER_PREFIXES = ("cafe_app.api.purchasing.", "cafe_app.api.buyer_expenses.")

# Additionally open to the restaurant's purchase manager, who keeps the recipes.
RECIPE_METHODS = {
	"cafe_app.api.menu.get_groups",
	"cafe_app.api.menu.list_menu",
	"cafe_app.api.menu.get_menu_item",
	"cafe_app.api.menu.list_ingredients",
	"cafe_app.api.menu.save_recipe",
}


def is_manager(user=None):
	user = user or frappe.session.user
	return user == "Administrator" or "System Manager" in frappe.get_roles(user)


def buyer_scopes(user=None):
	"""Purchase desks granted to this user, in a stable display order."""
	user = user or frappe.session.user
	if is_manager(user):
		return ()
	roles = set(frappe.get_roles(user))
	return tuple(scope for role, scope in BUYER_SCOPES.items() if role in roles)


def buyer_scope(user=None):
	"""Legacy primary desk; use buyer_scopes for authorization."""
	return next(iter(buyer_scopes(user)), None)


def require_manager():
	if not is_manager():
		frappe.throw(_("دسترسی به این بخش فقط برای مدیر است"), frappe.PermissionError)


def can_edit_recipes(user=None):
	"""Managers and purchase managers with the restaurant desk."""
	user = user or frappe.session.user
	return is_manager(user) or "Restaurant" in buyer_scopes(user)


def require_recipe_access():
	if not can_edit_recipes():
		frappe.throw(_("ویرایش رسپی فقط برای مدیر و مسئول خرید رستوران است"), frappe.PermissionError)


def restrict_buyers():
	"""before_request hook: a purchase manager can only reach the purchasing API."""
	user = frappe.session.user
	if user in ("Guest", "Administrator") or not buyer_scopes(user):
		return

	path = frappe.request.path or ""
	# Frappe also dispatches `?cmd=<method>` on any path.
	method = frappe.form_dict.get("cmd")
	if not method:
		if not path.startswith("/api/"):
			return
		method = path[len("/api/method/"):] if path.startswith("/api/method/") else None
	if method and (method in BUYER_METHODS or method.startswith(BUYER_PREFIXES)):
		return
	if method and method in RECIPE_METHODS and "Restaurant" in buyer_scopes(user):
		return
	frappe.throw(_("دسترسی به این بخش فقط برای مدیر است"), frappe.PermissionError)


def ensure_roles():
	for role in BUYER_SCOPES:
		if not frappe.db.exists("Role", role):
			# desk_access=0: these users live only in the panel, never in the ERPNext desk.
			frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 0}).insert(ignore_permissions=True)
