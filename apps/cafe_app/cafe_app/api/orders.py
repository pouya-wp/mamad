import frappe
from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_sales_return
from frappe import _
from frappe.utils import cint, flt

from cafe_app.source_catalog import display_item_name
from cafe_app.sales_source import order_payment_modes, order_payments
from cafe_app.source_payments import source_key, snapshots, unknown_snapshot, for_invoice, payment_overview
from cafe_app.utils import get_cafe_settings
from cafe_app.payment_truth import credit_customers
from cafe_app.source_reporting import payment_join


def _order_rows(from_date=None, to_date=None, search=None, payment_state=None, start=None, limit=50):
    if not frappe.has_permission("Sales Invoice", "read"):
        frappe.throw(_("دسترسی به سفارش‌ها مجاز نیست"), frappe.PermissionError)
    params = {"company": get_cafe_settings().company}
    conditions = ["si.docstatus=1", "si.company=%(company)s"]
    if from_date and to_date:
        conditions.append("si.posting_date BETWEEN %(from_date)s AND %(to_date)s")
        params.update(from_date=from_date, to_date=to_date)
    if search:
        conditions.append("""(si.name LIKE %(search)s OR si.remarks LIKE %(search)s
            OR JSON_UNQUOTE(JSON_EXTRACT(sp.methods_json,'$.customer.name')) LIKE %(search)s
            OR JSON_UNQUOTE(JSON_EXTRACT(sp.methods_json,'$.customer.id'))=%(customer_id)s)""")
        params.update(search=f"%{str(search).strip()}%", customer_id=str(search).strip())
    if payment_state and payment_state != "all":
        states = {"paid": "Paid", "credit": "Credit", "partial": "Partial", "unpaid": "Unpaid",
            "unknown": "Unknown", "cancelled": "Cancelled"}
        if payment_state == "review":
            conditions.append("sp.basis='Unallocated' AND sp.status NOT IN ('Unknown','Cancelled')")
        elif payment_state == "unknown":
            conditions.append("(sp.status='Unknown' OR (sp.name IS NULL AND si.remarks LIKE %(source_marker)s))")
            params["source_marker"] = "%[Sepand:%"
        elif payment_state in states:
            conditions.append("sp.status=%(payment_status)s")
            params["payment_status"] = states[payment_state]
            if payment_state in ("credit", "partial", "unpaid"):
                conditions.append("sp.basis<>'Unallocated'")
        else:
            frappe.throw(_("فیلتر پرداخت نامعتبر است"))
    pagination = ""
    if start is not None:
        params.update(start=max(0, cint(start)), limit=max(1, min(cint(limit), 2000)))
        pagination = "LIMIT %(limit)s OFFSET %(start)s"
    return frappe.db.sql(f"""SELECT si.name,si.posting_date,si.posting_time,si.base_grand_total,
        si.is_return,si.return_against,si.status,si.remarks,si.owner FROM `tabSales Invoice` si
        {payment_join()} WHERE {' AND '.join(conditions)}
        ORDER BY si.posting_date DESC,si.posting_time DESC,si.name DESC {pagination}""", params, as_dict=True)


@frappe.whitelist()
def list_orders(from_date=None, to_date=None, search=None, start=0, limit=50, payment_state=None):
    orders = _order_rows(from_date, to_date, search, payment_state, start, limit)

    names = [o.name for o in orders] or [""]
    modes = {}
    for parent, mode in frappe.get_all(
        "Sales Invoice Payment", filters={"parent": ["in", names]}, fields=["parent", "mode_of_payment"], as_list=True
    ):
        modes.setdefault(parent, []).append(mode)
    counts = dict(
        frappe.db.sql(
            "select parent, sum(qty) from `tabSales Invoice Item` where parent in %(names)s group by parent",
            {"names": names},
        )
    )
    source = snapshots(source_key(o.remarks) for o in orders if not o.is_return)
    for o in orders:
        o.payment_modes = order_payment_modes(o, modes.get(o.name, []))
        key = source_key(o.remarks)
        if key and not o.is_return:
            o.source_payment = source.get(key, unknown_snapshot())
            if o.source_payment.get("total") is not None:
                o.original_grand_total = o.base_grand_total
                o.base_grand_total = o.source_payment["total"]
            if o.source_payment.get("items"):
                o.items_count = sum(item["qty"] for item in o.source_payment["items"])
            o.payment_modes = [p["mode_of_payment"] + (" · " + p["account_name"]
                if p.get("account_name") and p["account_name"] != p["mode_of_payment"] else "")
                for p in o.source_payment["methods"]]
            if o.source_payment.get("credit") and o.source_payment["basis"] != "Customer Account":
                o.payment_modes.append("نسیه")
            if not o.payment_modes:
                o.payment_modes = ["سپهریار؛ روش نامشخص"]
        if not o.get("items_count"):
            o.items_count = counts.get(o.name, 0)
        o.owner_name = frappe.utils.get_fullname(o.owner)
    return orders


@frappe.whitelist()
def order_totals(from_date=None, to_date=None, search=None, payment_state=None):
    """Totals for the complete filtered set, independent of list pagination."""
    orders = _order_rows(from_date, to_date, search, payment_state)
    source = snapshots(source_key(order.remarks) for order in orders if not order.is_return)
    revenue = 0
    count = 0
    methods = {}
    direct_received = 0
    account_settled = 0
    catalog = []
    catalog_checked = ""
    for order in orders:
        payment = source.get(source_key(order.remarks)) if not order.is_return else None
        cancelled = payment and payment["status"] == "Cancelled"
        if not cancelled:
            revenue += payment["total"] if payment and payment["total"] is not None else order.base_grand_total
            count += not order.is_return
        order.source_payment = payment
        if payment and not cancelled:
            direct_received += payment.get("direct_received") or 0
            if payment.get("basis") == "Customer Account":
                account_settled += payment.get("credit") or 0
            for method in payment.get("methods", []):
                key = (method.get("method_id"), method["mode_of_payment"])
                entry = methods.setdefault(key, {"method_id": key[0], "mode_of_payment": key[1], "amount": 0,
                    "account_name": method.get("account_name")})
                entry["amount"] += method["amount"]
            if payment.get("payment_catalog") and str(payment.get("checked_at")) > catalog_checked:
                catalog = payment["payment_catalog"]
                catalog_checked = str(payment.get("checked_at"))
    return {"count": count, "revenue": flt(revenue), "returns": sum(bool(o.is_return) for o in orders),
        "source_payments": payment_overview(orders), "credit_report": credit_customers(orders),
        "payment_methods": sorted(methods.values(), key=lambda row: -row["amount"]),
        "direct_received": direct_received, "account_settled": account_settled, "payment_catalog": catalog}


@frappe.whitelist()
def get_order(name):
    doc = frappe.get_doc("Sales Invoice", name)
    doc.check_permission("read")
    source = for_invoice(doc)
    items = source.get("items") if source else None
    projected = bool(items and source["total"] is not None)
    item_total = sum(item["amount"] for item in items) if projected else doc.base_total
    grand_total = source["total"] if projected else doc.base_grand_total
    return {
        "name": doc.name,
        "posting_date": doc.posting_date,
        "posting_time": doc.posting_time,
        "status": doc.status,
        "is_return": doc.is_return,
        "return_against": doc.return_against,
        "remarks": doc.remarks,
        "owner_name": frappe.utils.get_fullname(doc.owner),
        "total": item_total,
        "discount_amount": max(item_total - grand_total, 0) if projected else doc.base_discount_amount,
        "source_extra_amount": max(grand_total - item_total, 0) if projected else 0,
        "grand_total": grand_total,
        "source_items_current": projected,
        "original_grand_total": doc.base_grand_total,
        "items": items if projected else [
            {"item_code": i.item_code, "item_name": display_item_name(i.item_code, i.item_name), "qty": i.qty, "rate": i.base_rate, "amount": i.base_amount}
            for i in doc.items
        ],
        "payments": order_payments(doc),
        "source_payment": source,
        "has_return": bool(frappe.db.exists("Sales Invoice", {"return_against": doc.name, "docstatus": 1})),
    }


@frappe.whitelist()
def return_order(name, reason=None):
    """Full refund: a submitted credit note that also puts the ingredients back in stock."""
    if source_key(frappe.db.get_value("Sales Invoice", name, "remarks")):
        frappe.throw(_("مرجوعی فاکتور سپهریار باید در خود سپهریار ثبت شود تا اقلام و مبلغ اصلی آن درست بماند"))
    if frappe.db.exists("Sales Invoice", {"return_against": name, "docstatus": 1}):
        frappe.throw(_("این سفارش قبلاً مرجوع شده"))

    credit_note = make_sales_return(name)
    credit_note.remarks = reason or _("مرجوعی سفارش {0}").format(name)
    credit_note.insert()
    credit_note.submit()
    return credit_note.name
