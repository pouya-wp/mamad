"""Read projections of live POS invoices; submitted ERP documents are retained."""
import frappe
from frappe.utils import flt

from cafe_app.source_payments import source_key, snapshots
from cafe_app.source_categories import source_code_group
from cafe_app.source_catalog import display_item_name


def payment_join(alias="si"):
    return f"""LEFT JOIN `tabCafe Source Payment` sp ON {alias}.is_return=0
        AND {alias}.remarks LIKE '%%[Sepand:%%'
        AND sp.name=REPLACE(SUBSTRING_INDEX(SUBSTRING_INDEX({alias}.remarks,'[Sepand:',-1),']',1),':','-')"""


def total_sql(alias="si", field="base_grand_total"):
    return f"""CASE WHEN sp.status='Cancelled' THEN 0
        WHEN sp.name IS NOT NULL AND JSON_UNQUOTE(JSON_EXTRACT(sp.methods_json,'$.total')) IS NOT NULL
            AND JSON_UNQUOTE(JSON_EXTRACT(sp.methods_json,'$.total'))<>'null' THEN sp.total
        ELSE {alias}.{field} END"""


def invoice_items(company, start, end, until_time=None):
    cache = getattr(frappe.local, "source_reporting_items", None)
    if cache is None:
        cache = frappe.local.source_reporting_items = {}
    key = (company, str(start), str(end), str(until_time))
    if key in cache:
        return cache[key]
    rows = frappe.db.sql("""SELECT si.name,si.remarks,si.is_return,i.item_code,i.item_name,i.stock_qty AS qty,
        i.base_net_amount AS revenue,i.item_group FROM `tabSales Invoice` si
        JOIN `tabSales Invoice Item` i ON i.parent=si.name
        WHERE si.docstatus=1 AND si.company=%s AND si.posting_date BETWEEN %s AND %s
        AND (%s IS NULL OR si.posting_date<%s OR si.posting_time<=%s)""",
        (company, start, end, until_time, end, until_time), as_dict=True)
    source = snapshots(source_key(row.remarks) for row in rows if not row.is_return)
    result = []
    seen = set()
    for row in rows:
        payment = source.get(source_key(row.remarks)) if not row.is_return else None
        if payment and payment["status"] == "Cancelled":
            continue
        if payment and payment.get("items"):
            if row.name in seen:
                continue
            seen.add(row.name)
            result.extend({"item_code": item["item_code"], "item_name": item["item_name"], "qty": item["qty"],
                "revenue": item["amount"], "item_group": source_code_group(item["item_code"]) or row.item_group}
                for item in payment["items"])
        else:
            row.item_name = display_item_name(row.item_code, row.item_name)
            result.append(row)
    cache[key] = result
    return result


def top_items(company, start, end, limit=8):
    totals = {}
    for row in invoice_items(company, start, end):
        key = (row["item_code"], row["item_name"])
        item = totals.setdefault(key, {"item_code": key[0], "item_name": key[1], "qty": 0, "revenue": 0})
        item["qty"] += flt(row["qty"])
        item["revenue"] += flt(row["revenue"])
    return sorted(totals.values(), key=lambda row: -row["qty"])[:limit]


def by_group(company, start, end):
    totals = {}
    for row in invoice_items(company, start, end):
        item = totals.setdefault(row["item_group"], {"item_group": row["item_group"], "qty": 0, "revenue": 0})
        item["qty"] += flt(row["qty"])
        item["revenue"] += flt(row["revenue"])
    return sorted(totals.values(), key=lambda row: -row["revenue"])
