import frappe
from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_sales_return
from frappe import _
from frappe.utils import cint

from cafe_app.utils import get_cafe_settings


@frappe.whitelist()
def list_orders(from_date=None, to_date=None, search=None, start=0, limit=50):
	settings = get_cafe_settings()
	filters = {"docstatus": 1, "company": settings.company}
	if from_date and to_date:
		filters["posting_date"] = ["between", [from_date, to_date]]

	or_filters = None
	if search:
		or_filters = {"name": ["like", f"%{search}%"], "remarks": ["like", f"%{search}%"]}

	orders = frappe.get_all(
		"Sales Invoice",
		filters=filters,
		or_filters=or_filters,
		fields=[
			"name",
			"posting_date",
			"posting_time",
			"base_grand_total",
			"is_return",
			"return_against",
			"status",
			"remarks",
			"owner",
		],
		order_by="posting_date desc, posting_time desc",
		start=cint(start),
		limit=cint(limit),
	)

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
	for o in orders:
		o.payment_modes = modes.get(o.name, [])
		o.items_count = counts.get(o.name, 0)
		o.owner_name = frappe.utils.get_fullname(o.owner)
	return orders


@frappe.whitelist()
def get_order(name):
	doc = frappe.get_doc("Sales Invoice", name)
	doc.check_permission("read")
	return {
		"name": doc.name,
		"posting_date": doc.posting_date,
		"posting_time": doc.posting_time,
		"status": doc.status,
		"is_return": doc.is_return,
		"return_against": doc.return_against,
		"remarks": doc.remarks,
		"owner_name": frappe.utils.get_fullname(doc.owner),
		"total": doc.base_total,
		"discount_amount": doc.base_discount_amount,
		"grand_total": doc.base_grand_total,
		"items": [
			{"item_code": i.item_code, "item_name": i.item_name, "qty": i.qty, "rate": i.base_rate, "amount": i.base_amount}
			for i in doc.items
		],
		"payments": [{"mode_of_payment": p.mode_of_payment, "amount": p.base_amount} for p in doc.payments],
		"has_return": bool(frappe.db.exists("Sales Invoice", {"return_against": doc.name, "docstatus": 1})),
	}


@frappe.whitelist()
def return_order(name, reason=None):
	"""Full refund: a submitted credit note that also puts the ingredients back in stock."""
	if frappe.db.exists("Sales Invoice", {"return_against": name, "docstatus": 1}):
		frappe.throw(_("این سفارش قبلاً مرجوع شده"))

	credit_note = make_sales_return(name)
	credit_note.remarks = reason or _("مرجوعی سفارش {0}").format(name)
	credit_note.insert()
	credit_note.submit()
	return credit_note.name
