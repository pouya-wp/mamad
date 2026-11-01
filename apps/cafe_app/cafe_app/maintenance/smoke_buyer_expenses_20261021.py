"""Exercise expense and advance posting as a buyer, then roll back every write."""

import frappe

from cafe_app.api import buyer_activity, buyer_expenses, purchasing


def run():
	previous = frappe.session.user
	result = None
	try:
		frappe.set_user("restaurant.buyer@onecafe.beyondex.one")
		choices = buyer_expenses.options()
		if not choices["accounts"] or not choices["employees"]:
			frappe.throw("Expense account or active employee missing")
		expense = buyer_expenses.record_entry(
			"Restaurant", "Expense", 10, "Cash",
			account=choices["accounts"][0].name, note="آزمون موقت؛ برگشت تراکنش",
		)
		advance = buyer_expenses.record_entry(
			"Cafe", "Advance", 10, "Cash",
			employee=choices["employees"][0].name, note="آزمون موقت؛ برگشت تراکنش",
		)
		purchase = purchasing.create_or_update(None, "Restaurant", [
			{"item_name": "آزمون موقت گزارش فعالیت", "qty": 1, "unit": "عدد", "amount": 10},
		], source="Manual")
		purchase_doc = frappe.get_doc("Cafe Purchase", purchase["name"])
		purchasing.create_or_update(purchase_doc, "Restaurant", [
			{"item_name": "آزمون موقت گزارش فعالیت", "qty": 1, "unit": "عدد", "amount": 20},
		], source="Manual")
		purchasing.delete_purchase(purchase["name"])
		activity_count = frappe.db.count("Cafe Buyer Activity", {"reference_name": ["in", [expense["name"], advance["name"], purchase["name"]]]})
		try:
			buyer_activity.list_activity(limit=1)
		except frappe.PermissionError:
			buyer_denied = True
		else:
			buyer_denied = False
		frappe.set_user("Administrator")
		manager_rows = buyer_activity.list_activity(limit=10)
		if activity_count != 5 or not buyer_denied or not any(r.reference_name == advance["name"] for r in manager_rows):
			frappe.throw("Buyer activity permissions or logging failed")
		result = {"expense": expense, "advance": advance, "activity_count": activity_count, "buyer_denied": buyer_denied}
	finally:
		frappe.db.rollback()
		frappe.set_user(previous)
	if frappe.db.exists("Cafe Buyer Expense", result["expense"]["name"]) or frappe.db.exists("Cafe Buyer Expense", result["advance"]["name"]):
		frappe.throw("Smoke records were not rolled back")
	if frappe.db.exists("Journal Entry", result["expense"]["journal_entry"]) or frappe.db.exists("Journal Entry", result["advance"]["journal_entry"]):
		frappe.throw("Smoke journal entries were not rolled back")
	return {**result, "rolled_back": True}
