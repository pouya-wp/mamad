"""Staff and their employment contracts (manager only)."""

import frappe
from frappe import _
from frappe.utils import cint, date_diff, flt, getdate, nowdate

from cafe_app.access import require_manager

CONTRACT_FIELDS = (
	"position", "start_date", "end_date", "shift_start", "shift_end",
	"working_days", "monthly_salary", "payment_day", "sign_date", "note",
)


def _contract_state(contract, today):
	"""active / expiring (<= 30 days left) / expired / upcoming / open (no end date)."""
	start = getdate(contract.start_date) if contract.start_date else None
	end = getdate(contract.end_date) if contract.end_date else None
	if start and start > today:
		return "upcoming", None
	if not end:
		return "open", None
	left = date_diff(end, today)
	if left < 0:
		return "expired", left
	return ("expiring" if left <= 30 else "active"), left


def _serialize(doc, today):
	contracts = []
	for c in sorted(doc.contracts, key=lambda c: str(c.start_date or c.sign_date or ""), reverse=True):
		state, days_left = _contract_state(c, today)
		contracts.append({**{f: c.get(f) for f in CONTRACT_FIELDS}, "name": c.name, "state": state, "days_left": days_left})

	current = [c for c in contracts if c["state"] in ("active", "expiring", "open")]
	return {
		"name": doc.name,
		"full_name": doc.full_name,
		"national_id": doc.national_id,
		"phone": doc.phone,
		"address": doc.address,
		"birth_date": doc.birth_date,
		"status": doc.status,
		"notes": doc.notes,
		"contracts": contracts,
		"current": current,
		"monthly_salary": sum(flt(c["monthly_salary"]) for c in current),
	}


@frappe.whitelist()
def list_staff():
	require_manager()
	today = getdate(nowdate())
	names = frappe.get_all("Cafe Employee", order_by="full_name asc", pluck="name")
	return [_serialize(frappe.get_doc("Cafe Employee", n), today) for n in names]


@frappe.whitelist()
def save_employee(data):
	require_manager()
	data = frappe._dict(frappe.parse_json(data))
	if not (data.full_name or "").strip():
		frappe.throw(_("نام کارمند لازم است"))

	doc = frappe.get_doc("Cafe Employee", data.name) if data.name else frappe.new_doc("Cafe Employee")
	doc.update({
		"full_name": data.full_name.strip(),
		"national_id": (data.national_id or "").strip() or None,
		"phone": (data.phone or "").strip() or None,
		"address": data.address,
		"birth_date": data.birth_date or None,
		"status": data.status or "Active",
		"notes": data.notes,
	})
	doc.set("contracts", [])
	for row in data.contracts or []:
		row = frappe._dict(row)
		doc.append("contracts", {
			"position": row.position,
			"start_date": row.start_date or None,
			"end_date": row.end_date or None,
			"shift_start": row.shift_start,
			"shift_end": row.shift_end,
			"working_days": row.working_days,
			"monthly_salary": flt(row.monthly_salary),
			"payment_day": cint(row.payment_day) or None,
			"sign_date": row.sign_date or None,
			"note": row.note,
		})
	doc.save(ignore_permissions=True)
	return _serialize(doc, getdate(nowdate()))


@frappe.whitelist()
def delete_employee(name):
	require_manager()
	frappe.delete_doc("Cafe Employee", name, ignore_permissions=True)
