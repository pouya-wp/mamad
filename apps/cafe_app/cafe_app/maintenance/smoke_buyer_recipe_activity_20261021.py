"""Re-save one existing recipe as a buyer and roll back the whole transaction."""

import frappe

from cafe_app import recipes
from cafe_app.api import menu


def run():
	previous = frappe.session.user
	result = None
	try:
		frappe.set_user("cafe.buyer@onecafe.beyondex.one")
		candidate = frappe.get_all("Cafe Recipe", fields=["item"], limit=1)
		if not candidate:
			frappe.throw("No recipe available for smoke check")
		item_code = candidate[0].item
		before = recipes.get_recipe(item_code)
		menu.save_recipe(item_code, before["rows"], before["notes"])
		entry = frappe.get_all("Cafe Buyer Activity",
			filters={"actor": frappe.session.user, "action": "recipe.update", "reference_name": item_code},
			fields=["name", "before_json", "after_json"], order_by="creation desc", limit=1)
		if not entry or not entry[0].before_json or not entry[0].after_json:
			frappe.throw("Recipe audit was not recorded")
		result = {"item": item_code, "activity": entry[0].name}
	finally:
		frappe.db.rollback()
		frappe.set_user(previous)
	if frappe.db.exists("Cafe Buyer Activity", result["activity"]):
		frappe.throw("Recipe smoke activity was not rolled back")
	return {**result, "rolled_back": True}
