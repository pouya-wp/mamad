"""Cheques and promissory notes the café receives or issues (manager only)."""

import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate, nowdate

from cafe_app.access import require_manager

DIRECTIONS = ("Received", "Issued")
KINDS = ("Regular", "Guarantee", "Promissory")
STATUSES = ("Pending", "Cleared", "Bounced", "Transferred", "Returned", "Cancelled")
FIELDS = ["name", "direction", "kind", "party", "amount", "due_date", "status", "issue_date", "bank", "cheque_no", "sayad_id", "status_date", "journal_entry", "note"]


@frappe.whitelist()
def list_cheques(direction=None, status=None):
	require_manager()
	filters = {}
	if direction in DIRECTIONS:
		filters["direction"] = direction
	if status in STATUSES:
		filters["status"] = status
	rows = frappe.get_all("Cafe Cheque", filters=filters, fields=FIELDS, order_by="due_date asc, creation asc", limit=1000)
	vouchers = {r.journal_entry for r in rows if r.journal_entry}
	posted = {r.name for r in frappe.get_all("Journal Entry", filters={"name": ["in", list(vouchers) or [""]], "docstatus": 1}, fields=["name"])}
	for row in rows:
		row.settled = row.status == "Cleared" and row.journal_entry in posted

	today = getdate(nowdate())
	week = add_days(today, 7)
	summary = {d: {"pending": 0, "pending_count": 0, "due_week": 0, "overdue": 0, "bounced": 0} for d in DIRECTIONS}
	all_rows = frappe.get_all("Cafe Cheque", fields=["direction", "amount", "due_date", "status", "journal_entry"], limit=5000)
	all_vouchers = {r.journal_entry for r in all_rows if r.journal_entry}
	all_posted = {r.name for r in frappe.get_all("Journal Entry", filters={"name": ["in", list(all_vouchers) or [""]], "docstatus": 1}, fields=["name"])}
	for r in all_rows:
		s = summary[r.direction]
		if r.status == "Pending" or (r.status == "Cleared" and r.journal_entry not in all_posted):
			s["pending"] += flt(r.amount)
			s["pending_count"] += 1
			if r.due_date and getdate(r.due_date) < today:
				s["overdue"] += 1
			elif r.due_date and getdate(r.due_date) <= week:
				s["due_week"] += flt(r.amount)
		elif r.status == "Bounced":
			s["bounced"] += 1
	return {"rows": rows, "summary": summary}


@frappe.whitelist()
def save_cheque(data):
	require_manager()
	data = frappe._dict(frappe.parse_json(data))
	if data.direction not in DIRECTIONS:
		frappe.throw(_("مشخص کن چک دریافتی است یا پرداختی"))
	if not (data.party or "").strip():
		frappe.throw(_("طرف حساب لازم است"))
	if flt(data.amount) <= 0:
		frappe.throw(_("مبلغ را وارد کن"))
	kind = data.kind if data.kind in KINDS else "Regular"
	if kind == "Regular" and not data.due_date:
		frappe.throw(_("تاریخ سررسید را وارد کن"))

	doc = frappe.get_doc("Cafe Cheque", data.name) if data.name else frappe.new_doc("Cafe Cheque")
	if doc.get("journal_entry"):
		frappe.throw(_("چک تسویه‌شده سند حسابداری دارد و قابل ویرایش نیست"))
	status = data.status if data.status in STATUSES else "Pending"
	if status == "Cleared":
		frappe.throw(_("برای تسویه چک از «ثبت تسویه و سند» استفاده کن"))
	if status != doc.status:
		doc.status_date = getdate(nowdate())
	doc.update({
		"direction": data.direction,
		"kind": kind,
		"party": data.party.strip(),
		"amount": flt(data.amount),
		"due_date": data.due_date or None,
		"status": status,
		"issue_date": data.issue_date or None,
		"bank": (data.bank or "").strip() or None,
		"cheque_no": (data.cheque_no or "").strip() or None,
		"sayad_id": (data.sayad_id or "").strip() or None,
		"note": data.note,
	})
	doc.save(ignore_permissions=True)
	return doc.name


@frappe.whitelist()
def set_status(name, status):
	require_manager()
	if status not in STATUSES:
		frappe.throw(_("وضعیت نامعتبر است"))
	if status == "Cleared":
		frappe.throw(_("برای تسویه چک از «ثبت تسویه و سند» استفاده کن"))
	doc = frappe.get_doc("Cafe Cheque", name)
	if doc.journal_entry:
		frappe.throw(_("چک تسویه‌شده سند حسابداری دارد و وضعیت آن قابل تغییر نیست"))
	doc.status = status
	doc.status_date = getdate(nowdate())
	doc.save(ignore_permissions=True)
	return doc.name


@frappe.whitelist()
def delete_cheque(name):
	require_manager()
	if frappe.db.get_value("Cafe Cheque", name, "journal_entry"):
		frappe.throw(_("چک دارای سند حسابداری را نمی‌توان حذف کرد"))
	frappe.delete_doc("Cafe Cheque", name, ignore_permissions=True)


@frappe.whitelist()
def settlement_accounts():
	"""Eligible leaf accounts for a manager-reviewed, balanced settlement entry."""
	require_manager()
	from cafe_app.utils import get_cafe_settings
	company = get_cafe_settings().company
	currency = frappe.get_cached_value("Company", company, "default_currency")
	rows = frappe.get_all("Account", filters={"company": company, "is_group": 0, "disabled": 0},
		fields=["name", "account_name", "account_type", "root_type", "account_currency"], order_by="account_name")
	rows = [r for r in rows if not r.account_currency or r.account_currency == currency]
	return {
		"bank": [r for r in rows if r.account_type in ("Bank", "Cash")],
		"counterpart": [r for r in rows if r.account_type not in ("Bank", "Cash", "Receivable", "Payable")
			and r.root_type in ("Asset", "Liability", "Income", "Expense")],
	}


@frappe.whitelist()
def settle_cheque(name, bank_account, counterpart_account, posting_date=None):
	"""Post one balanced Journal Entry, then mark the cheque paid in the same transaction."""
	require_manager()
	from cafe_app.utils import get_cafe_settings

	frappe.db.sql("select name from `tabCafe Cheque` where name=%s for update", (name,))
	doc = frappe.get_doc("Cafe Cheque", name)
	if doc.journal_entry and frappe.db.get_value("Journal Entry", doc.journal_entry, "docstatus") != 2:
		frappe.throw(_("این چک قبلاً تسویه شده یا سند آن نیازمند بررسی است"))
	if doc.status == "Cancelled":
		frappe.throw(_("چک باطل‌شده قابل تسویه نیست"))
	if doc.kind != "Regular":
		frappe.throw(_("تسویه خودکار فقط برای چک عادی فعال است"))
	accounts = settlement_accounts()
	if bank_account not in {r.name for r in accounts["bank"]}:
		frappe.throw(_("حساب بانکی یا صندوق معتبر نیست"))
	if counterpart_account not in {r.name for r in accounts["counterpart"]} or counterpart_account == bank_account:
		frappe.throw(_("حساب مقابل معتبر نیست"))
	settings = get_cafe_settings()
	cost_center = frappe.get_cached_value("Company", settings.company, "cost_center")
	amount = flt(doc.amount)
	if amount <= 0:
		frappe.throw(_("مبلغ چک معتبر نیست"))
	debit, credit = (bank_account, counterpart_account) if doc.direction == "Received" else (counterpart_account, bank_account)
	entry = frappe.get_doc({
		"doctype": "Journal Entry", "voucher_type": "Journal Entry", "company": settings.company,
		"posting_date": getdate(posting_date or nowdate()),
		"user_remark": f"تسویه چک {doc.name} · {doc.party}",
		"accounts": [
			{"account": debit, "debit_in_account_currency": amount, "cost_center": cost_center},
			{"account": credit, "credit_in_account_currency": amount, "cost_center": cost_center},
		],
	})
	entry.insert(ignore_permissions=True)
	entry.submit()
	doc.status = "Cleared"
	doc.status_date = getdate(posting_date or nowdate())
	doc.journal_entry = entry.name
	doc.save(ignore_permissions=True)
	return {"cheque": doc.name, "journal_entry": entry.name}
