import frappe
from frappe.desk.page.setup_wizard.setup_wizard import setup_complete

# Iranian defaults shared by every café tenant.
# Fiscal year 1405: 1 Farvardin 1405 (2026-03-21) to 29 Esfand 1405 (2027-03-20).
IRAN_DEFAULTS = {
	"country": "Iran",
	"currency": "IRR",
	"timezone": "Asia/Tehran",
	"language": "فارسی",
	"lang": "فارسی",
	"chart_of_accounts": "Standard",
	"fy_start_date": "2026-03-21",
	"fy_end_date": "2027-03-20",
}

ONE_CAFE = {
	"company_name": "One Cafe",
	"company_abbr": "ONE",
}


def provision_cafe(company_name, company_abbr, **overrides):
	"""Run the ERPNext setup wizard headlessly for a café site.

	No email/password is passed, so no user account is created or changed.
	"""
	if frappe.db.exists("Company", company_name):
		return {"status": "exists", "company": company_name}

	args = {**IRAN_DEFAULTS, **overrides, "company_name": company_name, "company_abbr": company_abbr}
	return setup_complete(args)


def provision_one_cafe():
	return provision_cafe(**ONE_CAFE)
