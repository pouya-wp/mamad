"""Append-only business activity trail for purchase managers (manager read only)."""

import json

import frappe
from frappe.utils import getdate

from cafe_app.access import buyer_scopes, require_manager


def log(action, reference_doctype, reference_name, scope, summary, before=None, after=None):
	"""Write in the same transaction as the change; a failed log aborts that change."""
	if not buyer_scopes():
		return
	actor = frappe.session.user
	frappe.get_doc({
		"doctype": "Cafe Buyer Activity",
		"actor": actor,
		"actor_name": frappe.db.get_value("User", actor, "full_name") or actor,
		"action": action,
		"reference_doctype": reference_doctype,
		"reference_name": reference_name,
		"scope": scope,
		"summary": summary,
		"before_json": json.dumps(before, ensure_ascii=False, default=str) if before is not None else None,
		"after_json": json.dumps(after, ensure_ascii=False, default=str) if after is not None else None,
	}).insert(ignore_permissions=True)


def purchase_snapshot(doc):
	return {
		"scope": doc.scope,
		"purchase_date": str(doc.purchase_date),
		"supplier": doc.supplier,
		"payment": doc.payment,
		"total": doc.total,
		"note": doc.note,
		"source": doc.source,
		"items": [
			{"item_name": r.item_name, "ingredient": r.ingredient, "qty": r.qty,
			 "unit": r.unit, "unit_price": r.unit_price, "amount": r.amount}
			for r in doc.items
		],
	}


@frappe.whitelist()
def actors():
	require_manager()
	return frappe.db.sql(
		"select distinct actor, actor_name from `tabCafe Buyer Activity` order by actor_name",
		as_dict=True,
	)


@frappe.whitelist()
def list_activity(actor=None, action=None, scope=None, from_date=None, to_date=None, limit=100, start=0):
	require_manager()
	filters = {}
	if actor:
		filters["actor"] = actor
	if action:
		filters["action"] = action
	if scope:
		filters["scope"] = scope
	if from_date and to_date:
		start, end = getdate(from_date), getdate(to_date)
		if end < start:
			frappe.throw("بازه تاریخ نامعتبر است")
		filters["creation"] = ["between", [f"{start} 00:00:00", f"{end} 23:59:59"]]
	rows = frappe.get_all(
		"Cafe Buyer Activity", filters=filters,
		fields=["name", "creation", "actor", "actor_name", "action", "reference_doctype",
			"reference_name", "scope", "summary", "before_json", "after_json"],
		order_by="creation desc", start=max(0, int(start)), limit=max(1, min(int(limit), 200)),
	)
	for row in rows:
		before_raw = row.pop("before_json", None)
		after_raw = row.pop("after_json", None)
		row.before = json.loads(before_raw) if before_raw else None
		row.after = json.loads(after_raw) if after_raw else None
	return rows
