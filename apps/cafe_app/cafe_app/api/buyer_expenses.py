"""Purchase desk expenses and staff advances, each backed by a posted Journal Entry."""

import math

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate

from cafe_app.access import SCOPE_LABELS, buyer_scopes, is_manager
from cafe_app.api import buyer_activity, purchasing
from cafe_app.utils import get_cafe_settings, get_mode_of_payment_account

ADVANCE_ACCOUNT_NAME = "مساعده کارکنان"
MODES = ("Cash", "Credit Card")
EXCLUDED_EXPENSE_TYPES = ("Cost of Goods Sold", "Stock Adjustment", "Depreciation", "Round Off")


def _require_access():
	if not buyer_scopes() and not is_manager():
		frappe.throw(_("دسترسی به این بخش فقط برای مسئول خرید و مدیر است"), frappe.PermissionError)


def _expense_accounts(company):
	return frappe.get_all(
		"Account",
		filters={"company": company, "root_type": "Expense", "is_group": 0,
			"disabled": 0, "account_type": ["not in", EXCLUDED_EXPENSE_TYPES]},
		fields=["name", "account_name"], order_by="account_name",
	)


@frappe.whitelist()
def options():
	_require_access()
	company = get_cafe_settings().company
	allowed = buyer_scopes()
	return {
		"scopes": [{"value": scope, "label": label} for scope, label in SCOPE_LABELS.items()
			if is_manager() or scope in allowed],
		"accounts": _expense_accounts(company),
		"employees": frappe.get_all("Cafe Employee", filters={"status": "Active"},
			fields=["name", "full_name"], order_by="full_name"),
		"modes": [{"value": "Cash", "label": "نقدی"}, {"value": "Credit Card", "label": "کارتخوان"}],
	}


@frappe.whitelist()
def list_entries(scope=None, kind=None, limit=100):
	_require_access()
	allowed = buyer_scopes()
	if scope and scope not in SCOPE_LABELS:
		frappe.throw(_("بخش نامعتبر است"))
	if scope and allowed and scope not in allowed:
		frappe.throw(_("به این بخش دسترسی نداری"), frappe.PermissionError)
	if kind and kind not in ("Expense", "Advance"):
		frappe.throw(_("نوع ثبت نامعتبر است"))
	filters = {}
	if scope:
		filters["scope"] = scope
	elif allowed:
		filters["scope"] = ["in", allowed]
	if kind:
		filters["kind"] = kind
	rows = frappe.get_all(
		"Cafe Buyer Expense", filters=filters,
		fields=["name", "creation", "owner", "scope", "kind", "posting_date", "amount",
			"mode_of_payment", "expense_account", "employee", "employee_name", "note", "journal_entry"],
		order_by="creation desc", limit=max(1, min(int(limit), 200)),
	)
	owners = {
		r.name: r.full_name for r in frappe.get_all("User",
			filters={"name": ["in", list({r.owner for r in rows}) or [""]]},
			fields=["name", "full_name"])
	}
	for row in rows:
		row.owner_name = owners.get(row.owner, row.owner)
	return rows


def _payment_account(mode, company):
	if mode not in MODES:
		frappe.throw(_("روش پرداخت نامعتبر است"))
	name = get_mode_of_payment_account(mode, company)
	info = frappe.db.get_value("Account", name, ["company", "root_type", "is_group", "disabled", "account_type"], as_dict=True) if name else None
	if not info or info.company != company or info.root_type != "Asset" or info.is_group or info.disabled or info.account_type not in ("Cash", "Bank"):
		frappe.throw(_("حساب صندوق یا کارتخوان برای این روش پرداخت آماده نیست"))
	return name


def _debit_account(kind, account, employee, company):
	if kind == "Expense":
		allowed = {row.name for row in _expense_accounts(company)}
		if account not in allowed:
			frappe.throw(_("حساب هزینه نامعتبر است"), frappe.PermissionError)
		return account, None
	if kind == "Advance":
		name = frappe.db.get_value("Account", {"company": company, "account_name": ADVANCE_ACCOUNT_NAME,
			"root_type": "Asset", "is_group": 0, "disabled": 0}, "name")
		if not name:
			frappe.throw(_("حساب مساعده کارکنان هنوز آماده نیست"))
		employee_name = frappe.db.get_value("Cafe Employee", {"name": employee, "status": "Active"}, "full_name")
		if not employee_name:
			frappe.throw(_("کارمند فعال را انتخاب کن"))
		return name, employee_name
	frappe.throw(_("نوع ثبت نامعتبر است"))


@frappe.whitelist()
def record_entry(scope, kind, amount, mode_of_payment="Cash", posting_date=None, account=None, employee=None, note=None):
	"""Post one balanced entry and save the purchase desk register in one transaction."""
	_require_access()
	scope = purchasing._scope_for_write(scope)
	settings = get_cafe_settings()
	amount = flt(amount)
	if not math.isfinite(amount) or amount <= 0 or amount > 10_000_000_000_000:
		frappe.throw(_("مبلغ معتبر وارد کن"))
	date = getdate(posting_date or nowdate())
	if date > getdate(nowdate()):
		frappe.throw(_("تاریخ ثبت نمی‌تواند در آینده باشد"))
	note = (note or "").strip()
	if len(note) > 500:
		frappe.throw(_("توضیح حداکثر ۵۰۰ نویسه باشد"))
	credit_account = _payment_account(mode_of_payment, settings.company)
	debit_account, employee_name = _debit_account(kind, account, employee, settings.company)
	if debit_account == credit_account:
		frappe.throw(_("حساب هزینه و پرداخت نمی‌توانند یکسان باشند"))

	doc = frappe.get_doc({
		"doctype": "Cafe Buyer Expense", "scope": scope, "kind": kind,
		"posting_date": date, "amount": amount, "mode_of_payment": mode_of_payment,
		"expense_account": account if kind == "Expense" else None,
		"employee": employee if kind == "Advance" else None,
		"employee_name": employee_name, "note": note or None,
	}).insert(ignore_permissions=True)
	cost_center = frappe.get_cached_value("Company", settings.company, "cost_center")
	debit_line = {"account": debit_account, "debit_in_account_currency": amount}
	if kind == "Expense":
		debit_line["cost_center"] = cost_center
	entry = frappe.get_doc({
		"doctype": "Journal Entry", "voucher_type": "Journal Entry", "company": settings.company,
		"posting_date": date,
		"user_remark": f"{('هزینه' if kind == 'Expense' else 'مساعده')} {SCOPE_LABELS[scope]} · {employee_name or account or ''} · {doc.name}" + (f" · {note}" if note else ""),
		"accounts": [
			debit_line,
			{"account": credit_account, "credit_in_account_currency": amount},
		],
	})
	entry.flags.ignore_permissions = True
	entry.insert(ignore_permissions=True)
	entry.submit()
	doc.journal_entry = entry.name
	doc.save(ignore_permissions=True)
	buyer_activity.log("expense.create" if kind == "Expense" else "advance.create",
		"Cafe Buyer Expense", doc.name, scope,
		f"{'هزینه' if kind == 'Expense' else 'مساعده'} {employee_name or account or ''} · {amount:g} ریال",
		after={"scope": scope, "kind": kind, "posting_date": str(date), "amount": amount,
			"mode_of_payment": mode_of_payment, "expense_account": doc.expense_account,
			"employee": doc.employee, "employee_name": employee_name, "note": note,
			"journal_entry": entry.name})
	return {"name": doc.name, "journal_entry": entry.name}
