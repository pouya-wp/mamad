import frappe
from frappe.utils import add_days, getdate, nowdate

MENU_ROOT = "منوی کافه"
INGREDIENT_GROUPS = ("مواد اولیه", "بسته‌بندی و مصرفی")
WALK_IN_CUSTOMER = "مشتری حضوری"


def get_company():
	return frappe.defaults.get_user_default("Company") or frappe.db.get_single_value(
		"Global Defaults", "default_company"
	)


def get_cafe_settings(company=None):
	"""Everything the panel needs to transact for the current company, resolved from its POS Profile."""
	company = company or get_company()
	profile = frappe.db.get_value(
		"POS Profile",
		{"company": company, "disabled": 0},
		["name", "warehouse", "customer", "selling_price_list", "currency", "write_off_cost_center"],
		as_dict=True,
	)
	if not profile:
		return frappe._dict(company=company)

	return frappe._dict(
		company=company,
		pos_profile=profile.name,
		warehouse=profile.warehouse,
		customer=profile.customer,
		price_list=profile.selling_price_list,
		currency=profile.currency,
		cost_center=profile.write_off_cost_center,
	)


def menu_groups():
	return [MENU_ROOT, *frappe.get_all("Item Group", filters={"parent_item_group": MENU_ROOT}, pluck="name")]


def ingredient_groups():
	return list(INGREDIENT_GROUPS)


def get_mode_of_payment_account(mode_of_payment, company):
	return frappe.db.get_value(
		"Mode of Payment Account", {"parent": mode_of_payment, "company": company}, "default_account"
	)


def period_range(period="today", from_date=None, to_date=None):
	"""Return (from_date, to_date, previous_from, previous_to) for a named period or explicit dates."""
	today = getdate(nowdate())
	if from_date and to_date:
		start, end = getdate(from_date), getdate(to_date)
	elif period == "week":
		start, end = add_days(today, -6), today
	elif period == "month":
		start, end = add_days(today, -29), today
	elif period == "year":
		start, end = add_days(today, -364), today
	else:
		start, end = today, today

	length = (end - start).days + 1
	return start, end, add_days(start, -length), add_days(start, -1)
