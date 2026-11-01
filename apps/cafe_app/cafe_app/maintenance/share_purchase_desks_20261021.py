"""Grant both existing purchase managers both purchase desks without touching passwords."""

import frappe

from cafe_app.access import CAFE_BUYER, RESTAURANT_BUYER, ensure_roles

BUYERS = (
	"restaurant.buyer@onecafe.beyondex.one",
	"cafe.buyer@onecafe.beyondex.one",
)
ROLES = (RESTAURANT_BUYER, CAFE_BUYER)


def inspect():
	return [
		{"user": email, "exists": bool(frappe.db.exists("User", email)), "roles": frappe.get_roles(email) if frappe.db.exists("User", email) else []}
		for email in BUYERS
	]


def grant_both():
	missing = [email for email in BUYERS if not frappe.db.exists("User", email)]
	if missing:
		frappe.throw(f"Missing purchase manager accounts: {', '.join(missing)}")
	ensure_roles()
	for email in BUYERS:
		user = frappe.get_doc("User", email)
		current = {row.role for row in user.roles}
		for role in ROLES:
			if role not in current:
				user.append("roles", {"role": role})
		user.save(ignore_permissions=True)
		frappe.clear_cache(user=email)
	frappe.db.commit()
	return inspect()


def smoke():
	"""Read-only checks as each account; report counts only, no business rows."""
	from cafe_app.access import can_edit_recipes, require_manager
	from cafe_app.api import purchasing
	from frappe.utils import nowdate

	previous = frappe.session.user
	results = []
	try:
		for email in BUYERS:
			frappe.set_user(email)
			access = purchasing.me()
			counts = {
				scope: len(purchasing.list_purchases(scope=scope, limit=1)["rows"])
				for scope in ("Restaurant", "Cafe")
			}
			calendar = purchasing.calendar_month(nowdate(), nowdate())
			try:
				require_manager()
			except frappe.PermissionError:
				manager_denied = True
			else:
				manager_denied = False
			results.append({
				"user": email,
				"scopes": [s["value"] for s in access["scopes"]],
				"is_manager": access["is_manager"],
				"can_edit_recipes": can_edit_recipes(),
				"manager_denied": manager_denied,
				"query_rows": counts,
				"calendar_days": len(calendar),
			})
	finally:
		frappe.set_user(previous)
	return results
