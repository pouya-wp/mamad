"""Read-only deployment planning for buyer expenses and employee advances."""

import frappe

from cafe_app.utils import get_cafe_settings, get_mode_of_payment_account


def inspect():
	company = get_cafe_settings().company
	return {
		"company": company,
		"payment_accounts": {
			mode: get_mode_of_payment_account(mode, company)
			for mode in ("Cash", "Credit Card")
		},
		"assets": frappe.get_all(
			"Account", filters={"company": company, "root_type": "Asset"},
			fields=["name", "account_name", "is_group", "account_type", "parent_account"],
			order_by="account_name", limit=100,
		),
		"expense_account_count": frappe.db.count("Account", {"company": company, "root_type": "Expense", "is_group": 0}),
		"active_staff_count": frappe.db.count("Cafe Employee", {"status": "Active"}),
	}
