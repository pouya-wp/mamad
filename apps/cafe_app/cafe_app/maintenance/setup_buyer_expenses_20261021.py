"""Create the dedicated current-asset account used for employee advances."""

import frappe

from cafe_app.api.buyer_expenses import ADVANCE_ACCOUNT_NAME
from cafe_app.utils import get_cafe_settings


def inspect():
	company = get_cafe_settings().company
	return {
		"company": company,
		"account": frappe.db.get_value("Account", {"company": company, "account_name": ADVANCE_ACCOUNT_NAME}, "name"),
		"parent": frappe.db.get_value("Account", {"company": company, "account_name": "Prepaid Expenses", "is_group": 0}, "parent_account"),
	}


def run():
	state = inspect()
	if state["account"]:
		return state
	if not state["parent"]:
		frappe.throw("Current Assets parent for employee advances was not found")
	frappe.get_doc({
		"doctype": "Account", "account_name": ADVANCE_ACCOUNT_NAME,
		"company": state["company"], "parent_account": state["parent"],
		"root_type": "Asset", "is_group": 0,
	}).insert(ignore_permissions=True)
	frappe.db.commit()
	return inspect()
