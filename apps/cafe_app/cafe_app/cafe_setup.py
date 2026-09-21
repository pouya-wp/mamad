import frappe
from frappe.utils.nestedset import get_root_of

from cafe_app.utils import WALK_IN_CUSTOMER, get_company, get_mode_of_payment_account

CARD_ACCOUNT_NAME = "کارتخوان"
CAFE_EXPENSE_ACCOUNTS = (
	"اجاره",
	"حقوق و دستمزد",
	"آب، برق و گاز",
	"اینترنت و تلفن",
	"تعمیرات و نگهداری",
	"تبلیغات و بازاریابی",
	"ملزومات و شوینده",
	"سایر هزینه‌ها",
)


def ensure_cafe_defaults(company=None):
	"""Idempotently create what a café needs to sell from the panel. Safe to call on every boot."""
	company = company or get_company()
	if not company:
		return

	if frappe.db.exists("POS Profile", {"company": company, "disabled": 0}):
		return

	customer = ensure_walk_in_customer()
	ensure_card_payment_account(company)
	ensure_expense_accounts(company)
	create_pos_profile(company, customer)
	frappe.db.commit()


def ensure_walk_in_customer():
	if not frappe.db.exists("Customer", WALK_IN_CUSTOMER):
		frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": WALK_IN_CUSTOMER,
				"customer_type": "Individual",
				"customer_group": frappe.db.get_single_value("Selling Settings", "customer_group")
				or _first_leaf("Customer Group"),
				"territory": frappe.db.get_single_value("Selling Settings", "territory") or _first_leaf("Territory"),
			}
		).insert(ignore_permissions=True)
	return WALK_IN_CUSTOMER


def _first_leaf(tree_doctype):
	"""Customers must link to a non-group node; fall back to the root only if the tree has no leaves."""
	return frappe.db.get_value(tree_doctype, {"is_group": 0}, "name", order_by="lft asc") or get_root_of(
		tree_doctype
	)


def ensure_card_payment_account(company):
	"""Card payments (کارتخوان) settle to a bank account; the wizard only wires up Cash."""
	if get_mode_of_payment_account("Credit Card", company):
		return

	abbr = frappe.get_cached_value("Company", company, "abbr")
	account = f"{CARD_ACCOUNT_NAME} - {abbr}"
	if not frappe.db.exists("Account", account):
		parent = frappe.db.get_value(
			"Account", {"company": company, "is_group": 1, "account_type": "Bank"}, "name"
		) or frappe.db.get_value("Account", {"company": company, "is_group": 1, "account_name": "Bank Accounts"}, "name")
		frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": CARD_ACCOUNT_NAME,
				"company": company,
				"parent_account": parent,
				"account_type": "Bank",
			}
		).insert(ignore_permissions=True)

	mode = frappe.get_doc("Mode of Payment", "Credit Card")
	mode.append("accounts", {"company": company, "default_account": account})
	mode.save(ignore_permissions=True)


def ensure_expense_accounts(company):
	parent = frappe.db.get_value(
		"Account", {"company": company, "is_group": 1, "account_name": "Indirect Expenses"}, "name"
	)
	if not parent:
		return

	for name in CAFE_EXPENSE_ACCOUNTS:
		if frappe.db.exists("Account", {"company": company, "account_name": name}):
			continue
		frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": name,
				"company": company,
				"parent_account": parent,
				"root_type": "Expense",
			}
		).insert(ignore_permissions=True)


def create_pos_profile(company, customer):
	company_doc = frappe.get_cached_doc("Company", company)
	warehouse = frappe.db.get_single_value("Stock Settings", "default_warehouse") or frappe.db.get_value(
		"Warehouse", {"company": company, "is_group": 0, "warehouse_name": "Stores"}, "name"
	)

	frappe.get_doc(
		{
			"doctype": "POS Profile",
			"name": f"صندوق {company}",
			"company": company,
			"customer": customer,
			"currency": company_doc.default_currency,
			"warehouse": warehouse,
			"update_stock": 1,
			"selling_price_list": frappe.db.get_single_value("Selling Settings", "selling_price_list")
			or "Standard Selling",
			"write_off_account": company_doc.write_off_account,
			"write_off_cost_center": company_doc.cost_center,
			"write_off_limit": 1,
			"payments": [
				{"mode_of_payment": "Cash", "default": 1},
				{"mode_of_payment": "Credit Card"},
			],
		}
	).insert(ignore_permissions=True)
