"""Automatically refresh source receipts through the already enrolled Windows app.

No source SQL writes, no changes to submitted ERP invoice amounts or GL entries.
Only an explicit VPS configuration enables this for an exact device.
"""
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

import frappe
from frappe.utils import now_datetime, get_datetime

from cafe_app.payment_truth import decode_report, normalize_payment, money

PURPOSE = "source_payments_v1"
SOURCE = re.compile(r"\[Sepand:(\d{4}):(\d+)\]")
YEAR = "1405"
INTERVAL_SECONDS = 300
MAX_FACTORS = 500


def source_key(remarks):
    match = SOURCE.search(remarks or "")
    return f"{match[1]}-{match[2]}" if match else None


def snapshots(keys):
    keys = list(set(key for key in keys if key))
    if not keys:
        return {}
    result = {}
    for row in frappe.get_all("Cafe Source Payment", filters={"name": ["in", keys]}, fields=["name", "methods_json", "checked_at"]):
        value = json.loads(row.methods_json)
        value["checked_at"] = row.checked_at
        value["is_stale"] = (now_datetime() - get_datetime(row.checked_at)).total_seconds() > 900
        result[row.name] = value
    return result


def unknown_snapshot():
    return {"status": "Unknown", "total": None, "received": None, "outstanding": None,
            "methods": [], "credit": None, "basis": "Invoice", "account_balance": None, "checked_at": None}


def for_invoice(invoice):
    key = source_key(invoice.remarks)
    if not key or invoice.is_return:
        return None
    return snapshots([key]).get(key, unknown_snapshot())


def payment_overview(orders):
    source = snapshots(source_key(order.remarks) for order in orders if not order.is_return)
    result = {"received": 0, "outstanding": 0, "credit_count": 0, "unpaid_count": 0,
              "partial_count": 0, "unknown_count": 0, "unallocated_count": 0, "review_count": 0,
              "paid_count": 0, "cancelled_count": 0, "stale_debt_count": 0}
    for order in orders:
        key = source_key(order.remarks)
        if not key or order.is_return:
            continue
        payment = source.get(key, unknown_snapshot())
        result["received"] += payment["received"] or 0
        result["outstanding"] += payment["outstanding"] or 0
        field = {"Credit": "credit_count", "Partial": "partial_count", "Unpaid": "unpaid_count",
                 "Unknown": "unknown_count", "Paid": "paid_count", "Cancelled": "cancelled_count"}.get(payment["status"])
        if payment["basis"] == "Unallocated" and payment["status"] != "Unknown":
            field = "review_count"
        if field:
            result[field] += 1
        if payment["basis"] == "Unallocated" and payment["status"] not in ("Unknown", "Cancelled"):
            result["unallocated_count"] += 1
        if payment.get("is_stale") and payment["status"] not in ("Paid", "Cancelled"):
            result["stale_debt_count"] += 1
    return result


def _configured_device(device):
    if device != frappe.conf.get("source_payment_device"):
        return False
    if not frappe.db.get_value("Cafe Desktop Device", device, "enabled"):
        return False
    user = frappe.db.get_value("Cafe Desktop Device", device, "enrolled_by")
    return bool(user and frappe.db.get_value("User", user, "enabled") and (
        user == "Administrator" or "System Manager" in frappe.get_roles(user)))


def _factor_ids():
    # Refresh the least recently checked invoices first, including old debts.
    # No date cutoff can cause an old credit invoice to stop being checked.
    invoices = frappe.db.sql("""SELECT remarks,posting_date FROM `tabSales Invoice`
        WHERE docstatus=1 AND is_return=0 AND remarks LIKE %s""", (f"%[Sepand:{YEAR}:%",), as_dict=True)
    keys = {source_key(row.remarks) for row in invoices}
    keys.discard(None)
    stored = frappe.get_all("Cafe Source Payment", filters={"name": ["in", list(keys) or [""]]},
        fields=["name", "checked_at", "status"])
    checked = {row.name: get_datetime(row.checked_at) for row in stored}
    pending = {row.name for row in stored if row.status in ("Credit", "Partial", "Unpaid", "Unknown")}
    oldest = get_datetime("2000-01-01")
    ranked = sorted(keys, key=lambda key: (checked.get(key, oldest), -int(key.split("-")[1])))
    # Debts and today's receipts are refreshed each round. Remaining capacity
    # rotates through older receipts so historical edits are also picked up.
    from frappe.utils import getdate, nowdate
    recent = {source_key(row.remarks) for row in invoices if getdate(row.posting_date) == getdate(nowdate())}
    priority = [key for key in ranked if key in pending or key in recent][:350]
    selected = priority + [key for key in ranked if key not in set(priority)][:MAX_FACTORS - len(priority)]
    return [int(key.split("-")[1]) for key in selected]


def maybe_queue(device):
    """Called inside the poll's device-row lock; no concurrent duplicate jobs."""
    if not _configured_device(device):
        return None
    now = now_datetime()
    last = frappe.db.sql("""SELECT name,status,creation,started_at FROM `tabCafe Desktop Job`
        WHERE device=%s AND purpose=%s ORDER BY creation DESC LIMIT 1""", (device, PURPOSE), as_dict=True)
    if last:
        previous = last[0]
        age = (now - get_datetime(previous.creation)).total_seconds()
        if previous.status in ("Queued", "Running"):
            if age < 600:
                return None
            frappe.db.set_value("Cafe Desktop Job", previous.name, {
                "status": "Timed Out", "finished_at": now, "processing_error": "Device did not finish the payment read within 10 minutes"}, update_modified=False)
        elif age < INTERVAL_SECONDS:
            return None
    ids = _factor_ids()
    if not ids:
        return None
    return queue_factors(device, ids)


def queue_factors(device, ids):
    if not _configured_device(device) or not ids or len(ids) > MAX_FACTORS:
        raise ValueError("Invalid payment source or batch size")
    ids = [int(factor) for factor in ids]
    if any(factor <= 0 for factor in ids) or len(ids) != len(set(ids)):
        raise ValueError("Invalid source invoice IDs")
    script = (Path(__file__).parent / "maintenance" / "sync-source-payments.ps1").read_text(encoding="utf-8-sig")
    script = script.replace("__FACTOR_IDS__", ",".join(str(factor) for factor in ids))
    if len(script.encode("utf-8")) > 32768:
        raise ValueError("Payment read exceeds script size limit")
    job = frappe.get_doc({"doctype": "Cafe Desktop Job", "device": device, "purpose": PURPOSE,
        "status": "Queued", "timeout_seconds": 90, "script": script,
        "script_sha256": hashlib.sha256(script.encode("utf-8")).hexdigest()}).insert(ignore_permissions=True)
    return job.name


def bootstrap():
    """VPS CLI only: initial reads for the complete already imported history."""
    device = frappe.conf.get("source_payment_device")
    if not _configured_device(device):
        raise ValueError("Configure an enabled source payment device first")
    # Same serialization as poll: never enqueue duplicate bootstrap batches.
    frappe.db.sql("SELECT name FROM `tabCafe Desktop Device` WHERE name=%s FOR UPDATE", (device,))
    if frappe.db.exists("Cafe Desktop Job", {"device": device, "purpose": PURPOSE, "status": ["in", ["Queued", "Running"]]}):
        return {"queued": [], "already_pending": True}
    rows = frappe.db.sql("SELECT remarks FROM `tabSales Invoice` WHERE docstatus=1 AND is_return=0 AND remarks LIKE %s",
        (f"%[Sepand:{YEAR}:%",), as_dict=True)
    ids = sorted({int(source_key(row.remarks).split("-")[1]) for row in rows if source_key(row.remarks)}, reverse=True)
    jobs = [queue_factors(device, ids[offset:offset + MAX_FACTORS]) for offset in range(0, len(ids), MAX_FACTORS)]
    frappe.db.commit()
    return {"queued": jobs, "invoices": len(ids)}


def process_job(job_id):
    job = frappe.get_doc("Cafe Desktop Job", job_id)
    if job.purpose != PURPOSE or job.status != "Succeeded" or job.processed_at:
        return {"applied": 0}
    if not _configured_device(job.device):
        raise ValueError("Payment source device is not authorized")
    report = decode_report(job.stdout)
    if report.get("version") not in (1, 2, 3) or report.get("machine") != "DESKTOP-GCTP2FH" or report.get("database") != "Sepand_One_1405":
        raise ValueError("Unexpected payment source")
    headers, allocations, catalog_rows = report["sets"][:3]
    item_rows = report["sets"][3] if report["version"] >= 2 else None
    if len(headers) > MAX_FACTORS or len(allocations) > MAX_FACTORS * 20:
        raise ValueError("Too many source payment records")
    match = re.search(r"FactorID IN \(([0-9,]+)\)", job.script)
    if not match:
        raise ValueError("Missing requested invoice IDs")
    requested = {int(value) for value in match[1].split(",")}
    catalog = {}
    catalog_accounts = {}
    for row in catalog_rows:
        label = str(row["name"] or "").strip()
        method = int(row["id"])
        if not label or len(label) > 140 or method in catalog or method == 99:
            raise ValueError("Invalid source payment catalog")
        catalog[method] = label.replace("ك", "ک").replace("ي", "ی")
        account_label = str(row.get("account_name") or "").strip()
        if len(account_label) > 280 or "?" in account_label:
            raise ValueError("Invalid payment account label")
        catalog_accounts[method] = account_label.replace("ك", "ک").replace("ي", "ی") or None
    by_factor = defaultdict(list)
    items_by_factor = defaultdict(list)
    if item_rows is not None:
        if len(item_rows) > MAX_FACTORS * 100:
            raise ValueError("Too many source invoice items")
        for row in item_rows:
            factor, warehouse, sku = int(row["f"]), int(row["w"]), int(row["k"])
            qty, amount = money(row["qty"]), money(row["amount"])
            if factor not in requested or warehouse <= 0 or sku <= 0 or qty <= 0 or amount <= 0:
                raise ValueError("Invalid source invoice item")
            code = f"SEPAND-{warehouse}-{sku}"
            label = str(row["name"] or f"کالای سپهریار {code}").strip()
            if len(label) > 140 or "?" in label:
                raise ValueError("Invalid source item name")
            items_by_factor[factor].append({"item_code": code, "item_name": label.replace("ك", "ک").replace("ي", "ی"),
                "qty": float(qty), "amount": float(amount), "rate": float(amount / qty)})
    for row in allocations:
        factor = int(row["f"])
        if factor not in requested:
            raise ValueError("Unrequested payment allocation")
        by_factor[factor].append(row)
    prepared = {}
    for header in headers:
        factor = int(header["f"])
        if factor not in requested or factor in prepared:
            raise ValueError("Duplicate or unrequested source invoice")
        prepared[factor] = normalize_payment(header, by_factor[factor], catalog)
        for method in prepared[factor]["methods"]:
            method["account_name"] = catalog_accounts.get(method.get("method_id"))
        if report["version"] >= 3:
            identity = int(header.get("customer_id") or 0)
            label = str(header.get("customer_name") or "").strip()
            account = str(header.get("account_key") or "")
            if identity < 0 or len(label) > 280 or "?" in label or (account and not re.fullmatch(r"\d+:\d+:\d+", account)):
                raise ValueError("Invalid source customer identity")
            prepared[factor]["customer"] = {"id": identity or None,
                "name": label.replace("ك", "ک").replace("ي", "ی") or None,
                "account_key": account or None, "account_verified": bool(header.get("account_verified"))}
            prepared[factor]["source_factor"] = factor
            prepared[factor]["payment_catalog"] = [{"method_id": method, "name": name,
                "account_name": catalog_accounts.get(method)} for method, name in catalog.items()]
        if item_rows is not None:
            prepared[factor]["items"] = items_by_factor[factor]
    # Missing source headers invalidate the prior snapshot instead of retaining
    # a stale Paid status after a source invoice was removed.
    for factor in requested - prepared.keys():
        prepared[factor] = unknown_snapshot()
    timestamp = job.started_at or job.creation
    now = now_datetime()
    for factor, payment in prepared.items():
        name = f"{YEAR}-{factor}"
        current = frappe.db.get_value("Cafe Source Payment", name, "checked_at")
        if current and get_datetime(current) > get_datetime(timestamp):
            continue
        values = {field: payment.get(field) for field in ("status", "total", "received", "outstanding", "credit", "basis", "account_balance")}
        # Frappe Currency columns are NOT NULL. JSON retains unknown amounts
        # as null for API consumers; numeric SQL fields use the required zero.
        for field in ("total", "received", "outstanding", "credit", "account_balance"):
            if values[field] is None:
                values[field] = 0
        values.update({"methods_json": json.dumps(payment, ensure_ascii=False), "device": job.device,
            "checked_at": timestamp, "job": job.name})
        if current:
            frappe.db.set_value("Cafe Source Payment", name, values, update_modified=False)
        else:
            frappe.get_doc({"doctype": "Cafe Source Payment", "source_key": name, **values}).insert(ignore_permissions=True)
    frappe.db.set_value("Cafe Desktop Job", job.name, {"processed_at": now, "processing_error": ""}, update_modified=False)
    return {"applied": len(prepared), "statuses": {state: sum(p["status"] == state for p in prepared.values())
        for state in ("Unknown", "Unpaid", "Credit", "Partial", "Paid", "Cancelled")}}


def accept_report(job_id):
    # Preserve the source result even if processing fails. A later predefined
    # read can recover; arbitrary maintenance commands are never auto-retried.
    frappe.db.savepoint("payment_snapshot")
    try:
        return process_job(job_id)
    except Exception as error:
        frappe.db.rollback(save_point="payment_snapshot")
        frappe.db.set_value("Cafe Desktop Job", job_id, "processing_error",
            f"{type(error).__name__}: payment report could not be validated or stored"[:200], update_modified=False)
        return {"applied": 0, "error": "Payment report processing failed"}
