"""CLI-only live acceptance checks; reports remain in the private site folder."""
import json
import traceback
from pathlib import Path

import frappe
from cafe_app.api.orders import list_orders, order_totals, get_order
from cafe_app.maintenance.verify_source_payments import verify


def run():
    try:
        frappe.set_user("Administrator")
        baseline = verify()
        example = get_order("ACC-SINV-2026-01240")
        payment = example["source_payment"]
        assert payment["customer"]["id"] == 175 and payment["customer"]["name"] == "تیام"
        assert payment["basis"] == "Unallocated" and payment["outstanding"] is None
        assert payment["source_factor"] == 23702
        card = next(row for row in payment["methods"] if row["method_id"] == 3)
        assert card["account_name"] == "صادرات پوز" and card["amount"] == 3740000
        totals = order_totals()
        credit = totals["credit_report"]
        assert credit["account_debt"] == sum(max(row["account_balance"], 0) for row in credit["customers"] if row["account_balance"] is not None)
        assert all(row["customer_id"] and row["customer_name"] for row in credit["customers"])
        assert credit["unverified_customers"] == 0, "Some source customer accounts remain unverified"
        assert any(row["customer_id"] == 10 and row["account_key"].startswith('110:4:') for row in credit["customers"])
        assert any(row["customer_id"] == 192 and row["account_balance"] is not None for row in credit["customers"])
        matches = list_orders(search="تیام", limit=2000)
        assert any(row.name == example["name"] for row in matches)
        assert all(row.source_payment["customer"]["name"] == "تیام" for row in matches)
        filters = {}
        for state in ("paid", "credit", "partial", "unpaid", "review", "unknown", "cancelled"):
            rows = list_orders(payment_state=state, limit=2000)
            summary = order_totals(payment_state=state)
            filters[state] = len(rows)
            assert summary["count"] == (0 if state == "cancelled" else len(rows))
            if state == "review":
                assert all(row.source_payment["basis"] == "Unallocated" for row in rows)
            if state in ("credit", "partial", "unpaid"):
                assert all(row.source_payment["basis"] != "Unallocated" for row in rows)
        assert sum(filters.values()) == baseline["orders"]
        result = {"verified": True, "orders": baseline["orders"], "financial_changes": baseline["financial_changes"],
            "today_sales_match": baseline["today_sales_match"], "filters": filters,
            "credit_customers": len(credit["customers"]), "verified_accounts": credit["verified_accounts"],
            "unverified_customers": credit["unverified_customers"], "account_debt": credit["account_debt"],
            "invoice_1240": {"customer": payment["customer"], "credit": payment["credit"],
                "total": payment["total"], "received": payment["received"], "outstanding": payment["outstanding"]},
            "payment_catalog": totals["payment_catalog"], "jobs": baseline["jobs"]}
        target = Path(frappe.get_site_path("private", "files", "source-reconciliation", "payment-clarity-20260929.json"))
        target.write_text(json.dumps(result, ensure_ascii=False, default=str), encoding="utf-8")
        target.chmod(0o600)
        return result
    except Exception as error:
        frame = traceback.extract_tb(error.__traceback__)[-1]
        return {"verified": False, "error_type": type(error).__name__, "check": Path(frame.filename).name,
            "line": frame.lineno, "reason": str(error)[:200] if isinstance(error, AssertionError) else "Live payment checks failed"}
