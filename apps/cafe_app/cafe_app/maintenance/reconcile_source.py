"""Audited CLI-only catalog repair and idempotent historic sales backfill."""
import json
import re
from collections import Counter, defaultdict
from datetime import date, time
from decimal import Decimal
from pathlib import Path

import frappe

from cafe_app.api.sepehryar import import_sales
from cafe_app.product_name_repair import _clean_name


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def _write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, default=str), encoding="utf-8")
    temp.chmod(0o600)
    temp.replace(path)


def _load(catalog_path, week_path, extras_path):
    catalog, week, extras = map(_read, (catalog_path, week_path, extras_path))
    for export in (catalog, week, extras):
        if export["machine"] != "DESKTOP-GCTP2FH" or export["database"] != "Sepand_One_1405":
            raise ValueError("Unexpected source device or database")
    names = {}
    for row in catalog["sets"][0]:
        key = (int(row["w"]), int(row["id"]))
        name = _clean_name(row["n"])
        if key in names or not name:
            raise ValueError("Invalid or duplicate warehouse/item name")
        names[key] = name
    invoice_ids = set()
    source_names = defaultdict(lambda: defaultdict(set))
    totals = {int(row["f"]): row for row in week["totals"]}
    for invoice in week["invoices"]:
        factor = int(invoice["sourceInvoiceId"])
        if factor in invoice_ids or factor <= 0:
            raise ValueError("Duplicate or invalid source invoice")
        invoice_ids.add(factor)
        posting_date = date.fromisoformat(invoice["postingDate"])
        time.fromisoformat(invoice["postingTime"])
        if not date(2026, 9, 19) <= posting_date < date(2026, 9, 28):
            raise ValueError("Invoice outside the audited date range")
        if not invoice["items"]:
            raise ValueError("Empty source invoice")
        total = Decimal(0)
        for row in invoice["items"]:
            key = (int(row["warehouseId"]), int(row["sourceItemId"]))
            if names.get(key) != _clean_name(row["name"]):
                raise ValueError("Invoice name does not match warehouse catalog")
            row["name"] = names[key]
            if Decimal(str(row["quantity"])) <= 0 or Decimal(str(row["amount"])) <= 0:
                raise ValueError("Nonpositive source quantity or amount")
            if Decimal(str(row.get("discount") or 0)):
                raise ValueError("Unmapped source discount")
            total += Decimal(str(row["amount"]))
            source_names[factor][key[1]].add(names[key])
        if total != Decimal(str(totals[factor]["products"])):
            raise ValueError("Source product total mismatch")
    for row in extras["sets"][1]:
        key = (int(row["w"]), int(row["k"]))
        if names.get(key) != _clean_name(row["n"]):
            raise ValueError("Exception invoice name mismatch")
        source_names[int(row["f"])][key[1]].add(names[key])
    return names, week, source_names


def _existing():
    result = {}
    for row in frappe.get_all("Sales Invoice", filters={"remarks": ["like", "%[Sepand:1405:%"]},
                              fields=["name", "remarks", "grand_total", "docstatus", "posting_date"]):
        match = re.search(r"\[Sepand:1405:(\d+)\]", row.remarks or "")
        if match:
            factor = int(match.group(1))
            if factor in result:
                raise ValueError(f"Duplicate server invoice marker: {factor}")
            result[factor] = row
    return result


def reconcile(catalog_path, week_path, extras_path, report_path, apply=False):
    names, week, source_names = _load(catalog_path, week_path, extras_path)
    existing = _existing()
    item_plan, row_plan, unresolved = [], [], []
    for item in frappe.get_all("Item", filters={"item_code": ["like", "SEPAND-%"]}, fields=["name", "item_code", "item_name"]):
        parts = item.item_code.split("-")
        key = (3, int(parts[1])) if len(parts) == 2 else (int(parts[1]), int(parts[2]))
        expected = names.get(key)
        if expected and expected != item.item_name:
            item_plan.append({"name": item.name, "old": item.item_name, "new": expected})
    parents = {row.name: factor for factor, row in existing.items()}
    for row in frappe.get_all("Sales Invoice Item", filters={"item_code": ["like", "SEPAND-%"]},
                              fields=["name", "parent", "item_code", "item_name", "qty", "base_amount"]):
        parts = row.item_code.split("-")
        expected = None
        if len(parts) == 3:
            expected = names.get((int(parts[1]), int(parts[2])))
        else:
            candidates = source_names.get(parents.get(row.parent), {}).get(int(parts[1]), set())
            if len(candidates) == 1:
                expected = next(iter(candidates))
        if not expected:
            unresolved.append(dict(row))
        elif expected != row.item_name:
            row_plan.append({"name": row.name, "parent": row.parent, "old": row.item_name, "new": expected})
    differences, missing = [], []
    for invoice in week["invoices"]:
        factor = int(invoice["sourceInvoiceId"])
        source_total = sum(Decimal(str(row["amount"])) for row in invoice["items"])
        if factor not in existing:
            if invoice["sourceState"] != "archive":
                raise ValueError("Backfill must only add finalized archived invoices")
            missing.append(factor)
        elif source_total != Decimal(str(existing[factor].grand_total)):
            differences.append({"factor": factor, "invoice": existing[factor].name,
                                "server_total": existing[factor].grand_total, "source_total": source_total})
    report = {"catalog_changes": item_plan, "invoice_name_changes": row_plan,
              "unresolved_names": unresolved, "existing_amount_differences": differences,
              "missing_factors": missing, "already_present": len(week["invoices"]) - len(missing),
              "apply": bool(apply)}
    # Save every old label and discrepancy before touching names.
    _write(report_path, report)
    if apply:
        for row in item_plan:
            frappe.db.set_value("Item", row["name"], "item_name", row["new"], update_modified=False)
        for row in row_plan:
            frappe.db.set_value("Sales Invoice Item", row["name"], "item_name", row["new"], update_modified=False)
        frappe.db.commit()
        frappe.clear_cache(doctype="Item")
    return {"catalog_changes": len(item_plan), "invoice_name_changes": len(row_plan),
            "unresolved_names": len(unresolved), "existing_amount_differences": len(differences),
            "missing": len(missing), "already_present": report["already_present"], "applied": bool(apply)}


def backfill(catalog_path, week_path, extras_path, progress_path):
    """Commit one invoice at a time; retries skip every committed source marker."""
    _names, week, _source_names = _load(catalog_path, week_path, extras_path)
    frappe.set_user("Administrator")
    existing = _existing()
    progress = {"status": "running", "source_count": len(week["invoices"]), "existing_at_start": 0,
                "created": [], "skipped": [], "errors": []}
    pending = []
    for invoice in week["invoices"]:
        factor = int(invoice["sourceInvoiceId"])
        if factor in existing:
            progress["existing_at_start"] += 1
            progress["skipped"].append(factor)
        else:
            if invoice["sourceState"] != "archive":
                raise ValueError("Cannot backfill an active invoice")
            pending.append(invoice)
    _write(progress_path, progress)
    for invoice in pending:
        try:
            result = import_sales([invoice])
            frappe.db.commit()
            progress["created"].extend(result["created"])
            progress["skipped"].extend(result["skipped"])
        except Exception as error:
            frappe.db.rollback()
            progress["errors"].append({"factor": invoice["sourceInvoiceId"], "type": type(error).__name__, "message": str(error)[:400]})
        _write(progress_path, progress)
        if progress["errors"]:
            # Stop at the first failure, preserving all committed invoices.
            break
    progress["status"] = "failed" if progress["errors"] else "complete"
    _write(progress_path, progress)
    return {"status": progress["status"], "created": len(progress["created"]),
            "skipped": len(progress["skipped"]), "errors": progress["errors"]}


def audit(catalog_path, week_path, extras_path, before_path, progress_path, report_path):
    """Verify old financial values and exact new rows against the source export."""
    names, week, _source_names = _load(catalog_path, week_path, extras_path)
    before, progress = _read(before_path), _read(progress_path)
    current = _existing()
    old_financial_changes, new_errors = [], []
    for old in before["invoices"]:
        row = frappe.db.get_value("Sales Invoice", old["name"],
                                  ["grand_total", "docstatus", "posting_date", "posting_time", "remarks"], as_dict=True)
        if not row or any(str(row[field]) != str(old[field]) for field in ("grand_total", "docstatus", "posting_date", "posting_time", "remarks")):
            old_financial_changes.append({"invoice": old["name"], "kind": "header"})
    for old in before["invoice_rows"]:
        row = frappe.db.get_value("Sales Invoice Item", old["name"], ["item_code", "qty", "base_rate", "base_amount"], as_dict=True)
        if not row or row.item_code != old["item_code"] or any(Decimal(str(row[field])) != Decimal(str(old[field])) for field in ("qty", "base_rate", "base_amount")):
            old_financial_changes.append({"row": old["name"], "kind": "item"})
    by_factor = {int(invoice["sourceInvoiceId"]): invoice for invoice in week["invoices"]}
    for created in progress["created"]:
        source = by_factor[int(created["sourceInvoiceId"])]
        expected = Counter((f"SEPAND-{row['warehouseId']}-{row['sourceItemId']}", row["name"],
                            Decimal(str(row["quantity"])), Decimal(str(row["amount"]))) for row in source["items"])
        rows = frappe.get_all("Sales Invoice Item", filters={"parent": created["name"]},
                              fields=["item_code", "item_name", "qty", "base_amount"])
        actual = Counter((row.item_code, row.item_name, Decimal(str(row.qty)), Decimal(str(row.base_amount))) for row in rows)
        header = current.get(int(created["sourceInvoiceId"]))
        expected_total = sum(Decimal(str(row["amount"])) for row in source["items"])
        if expected != actual or not header or header.docstatus != 1 or Decimal(str(header.grand_total)) != expected_total or str(header.posting_date) != source["postingDate"]:
            new_errors.append(created)
    catalog_errors = []
    for row in frappe.get_all("Item", filters={"item_code": ["like", "SEPAND-%"]}, fields=["item_code", "item_name"]):
        parts = row.item_code.split("-")
        key = (3, int(parts[1])) if len(parts) == 2 else (int(parts[1]), int(parts[2]))
        if key in names and row.item_name != names[key]:
            catalog_errors.append(row.item_code)
    report = {"status": progress["status"], "created": len(progress["created"]), "skipped": len(progress["skipped"]),
              "missing": [factor for factor in by_factor if factor not in current],
              "old_financial_changes": old_financial_changes, "new_invoice_errors": new_errors,
              "catalog_name_errors": catalog_errors, "import_errors": progress["errors"],
              "source_cancelled_existing": [row["f"] for row in _read(extras_path)["sets"][0] if row["c"] and int(row["f"]) in current]}
    _write(report_path, report)
    return report
