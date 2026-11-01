"""CLI checks. Reports exclude credentials and preserve existing invoice money."""
import json
from pathlib import Path
from collections import Counter

import frappe


BASELINE = Path("/home/frappe/frappe-bench/sites/frontend/private/files/source-reconciliation/payment-financial-baseline-20260929.json")


def baseline():
    invoices = frappe.db.sql("""SELECT name,base_total,base_net_total,base_grand_total,base_discount_amount,docstatus
        FROM `tabSales Invoice` WHERE remarks LIKE %s""", ("%[Sepand:%",), as_dict=True)
    items = frappe.db.sql("""SELECT i.name,i.parent,i.item_code,i.qty,i.base_rate,i.base_amount,i.base_net_amount
        FROM `tabSales Invoice Item` i JOIN `tabSales Invoice` s ON s.name=i.parent WHERE s.remarks LIKE %s""", ("%[Sepand:%",), as_dict=True)
    payments = frappe.db.sql("""SELECT p.name,p.parent,p.mode_of_payment,p.base_amount
        FROM `tabSales Invoice Payment` p JOIN `tabSales Invoice` s ON s.name=p.parent WHERE s.remarks LIKE %s""", ("%[Sepand:%",), as_dict=True)
    data = {"invoices": invoices, "items": items, "payments": payments}
    if BASELINE.exists():
        raise ValueError("The financial baseline already exists; it will not be overwritten")
    BASELINE.parent.mkdir(parents=True, exist_ok=True)
    BASELINE.write_text(json.dumps(data, default=str, ensure_ascii=False), encoding="utf-8")
    BASELINE.chmod(0o600)
    return {key: len(rows) for key, rows in data.items()}


def verify():
    from cafe_app.api.orders import list_orders, get_order, order_totals
    from cafe_app.api.dashboard import summary
    from cafe_app.source_payments import source_key

    before = json.loads(BASELINE.read_text(encoding="utf-8"))
    changed = {}
    for key, doctype in (("invoices", "Sales Invoice"), ("items", "Sales Invoice Item"), ("payments", "Sales Invoice Payment")):
        changed[key] = []
        current_rows = frappe.get_all(doctype, filters={"name": ["in", [row["name"] for row in before[key]]]}, fields=list(before[key][0]))
        by_name = {row.name: json.loads(json.dumps(row, default=str)) for row in current_rows}
        for row in before[key]:
            if by_name.get(row["name"]) != row:
                changed[key].append(row["name"])
    assert not any(changed.values()), "Existing invoice financial data changed"
    frappe.set_user("Administrator")
    orders = list_orders(limit=5000)
    states = Counter(o.get("source_payment", {}).get("status", "Non-source") for o in orders)
    detail_checked = 0
    for order in orders:
        payment = order.get("source_payment")
        if not payment:
            continue
        if payment["status"] == "Paid":
            assert payment["outstanding"] == 0 and payment["received"] == payment["total"]
        if payment["basis"] == "Unallocated":
            assert payment["outstanding"] is None
        if payment["status"] == "Credit":
            assert payment["credit"] > 0 and payment["received"] != payment["total"]
        if detail_checked < 4 and payment["status"] in ("Credit", "Partial", "Paid"):
            detail = get_order(order.name)
            assert detail["source_payment"]["status"] == payment["status"]
            assert detail["payments"] == payment["methods"]
            detail_checked += 1
    dashboard = summary(period="today")
    totals = order_totals()
    today_totals = order_totals(from_date=str(frappe.utils.nowdate()), to_date=str(frappe.utils.nowdate()))
    assert today_totals["revenue"] == dashboard["kpis"]["revenue"], "Order and dashboard totals disagree"
    assert today_totals["count"] == dashboard["kpis"]["orders"], "Order and dashboard counts disagree"
    example = get_order("ACC-SINV-2026-01240")
    if example.get("source_items_current"):
        assert len(example["items"]) == 4 and sum(row["amount"] for row in example["items"]) == example["grand_total"]
        assert example["grand_total"] == 10230000 and example["source_payment"]["received"] == 3740000
    projected = frappe.db.sql("SELECT count(*) FROM `tabCafe Source Payment` WHERE JSON_CONTAINS_PATH(methods_json,'one','$.items')=1")[0][0]
    jobs = frappe.get_all("Cafe Desktop Job", filters={"purpose": "source_payments_v1"},
        fields=["name", "status", "processed_at", "processing_error", "creation"], order_by="creation desc", limit=4)
    return {"financial_changes": {key: len(rows) for key, rows in changed.items()}, "orders": len(orders),
        "source_statuses": dict(states), "details_checked": detail_checked, "all_period_payment_totals": totals["source_payments"],
        "today_methods": dashboard["payments"], "today_payment_totals": dashboard["source_payments"], "jobs": jobs,
        "today_sales_match": True, "source_item_snapshots": projected,
        "invoice_1240": {"source_items_current": example.get("source_items_current"), "items": example["items"],
            "grand_total": example["grand_total"], "initial_stored_total": example.get("original_grand_total"), "payments": example["payments"]}}


def safe_verify():
    try:
        result = verify()
    except Exception as error:
        return {"verified": False, "error_type": type(error).__name__}
    report = BASELINE.with_name("payment-sync-final-audit-20260929.json")
    report.write_text(json.dumps(result, ensure_ascii=False, default=str), encoding="utf-8")
    report.chmod(0o600)
    return {"verified": True, **result}
