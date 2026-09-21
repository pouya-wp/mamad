import frappe
from frappe import _
from frappe.utils import flt, nowdate

from cafe_app.utils import get_cafe_settings, get_mode_of_payment_account


@frappe.whitelist()
def record_purchase(supplier, items, mode_of_payment="Cash", bill_no=None, posting_date=None, note=None):
	"""A paid purchase: one Purchase Invoice that both receives stock and pays the supplier."""
	items = frappe.parse_json(items)
	settings = get_cafe_settings()

	invoice = frappe.new_doc("Purchase Invoice")
	invoice.update(
		{
			"company": settings.company,
			"supplier": supplier,
			"bill_no": bill_no,
			"posting_date": posting_date or nowdate(),
			"set_posting_time": 1 if posting_date else 0,
			"update_stock": 1,
			"set_warehouse": settings.warehouse,
			"remarks": note,
		}
	)
	for row in items:
		invoice.append("items", {"item_code": row["item_code"], "qty": flt(row["qty"]), "rate": flt(row["rate"])})

	invoice.set_missing_values()
	invoice.calculate_taxes_and_totals()

	if mode_of_payment:
		invoice.is_paid = 1
		invoice.mode_of_payment = mode_of_payment
		invoice.cash_bank_account = get_mode_of_payment_account(mode_of_payment, settings.company)
		invoice.paid_amount = invoice.rounded_total or invoice.grand_total

	invoice.insert()
	invoice.submit()
	return {"name": invoice.name, "grand_total": invoice.grand_total}


@frappe.whitelist()
def record_waste(items, reason=None):
	"""Write off spoiled or wasted ingredients (Material Issue)."""
	items = frappe.parse_json(items)
	settings = get_cafe_settings()

	entry = frappe.new_doc("Stock Entry")
	entry.update(
		{
			"company": settings.company,
			"stock_entry_type": "Material Issue",
			"from_warehouse": settings.warehouse,
			"remarks": reason,
		}
	)
	for row in items:
		entry.append("items", {"item_code": row["item_code"], "qty": flt(row["qty"]), "s_warehouse": settings.warehouse})

	entry.insert()
	entry.submit()
	return entry.name


@frappe.whitelist()
def stock_count(items, note=None):
	"""Physical count (انبارگردانی): set actual quantities, with a rate for items that have no valuation yet."""
	items = frappe.parse_json(items)
	settings = get_cafe_settings()

	recon = frappe.new_doc("Stock Reconciliation")
	recon.update({"company": settings.company, "purpose": "Stock Reconciliation", "remarks": note})
	for row in items:
		entry = {"item_code": row["item_code"], "warehouse": settings.warehouse, "qty": flt(row["qty"])}
		if flt(row.get("valuation_rate")):
			entry["valuation_rate"] = flt(row["valuation_rate"])
		recon.append("items", entry)

	if not recon.items:
		frappe.throw(_("هیچ قلمی وارد نشده"))

	recon.insert()
	recon.submit()
	return recon.name


@frappe.whitelist()
def movements(item_code=None, limit=50):
	settings = get_cafe_settings()
	filters = {"is_cancelled": 0, "warehouse": settings.warehouse}
	if item_code:
		filters["item_code"] = item_code

	rows = frappe.get_all(
		"Stock Ledger Entry",
		filters=filters,
		fields=[
			"posting_date",
			"posting_time",
			"item_code",
			"actual_qty",
			"qty_after_transaction",
			"stock_value_difference",
			"voucher_type",
			"voucher_no",
		],
		order_by="posting_datetime desc, creation desc",
		limit=int(limit),
	)
	names = {r.item_code for r in rows}
	item_names = dict(
		frappe.get_all("Item", filters={"name": ["in", list(names) or [""]]}, fields=["name", "item_name"], as_list=True)
	)
	uoms = dict(
		frappe.get_all("Item", filters={"name": ["in", list(names) or [""]]}, fields=["name", "stock_uom"], as_list=True)
	)
	for r in rows:
		r.item_name = item_names.get(r.item_code)
		r.stock_uom = uoms.get(r.item_code)
	return rows


@frappe.whitelist()
def list_suppliers():
	suppliers = frappe.get_all(
		"Supplier", filters={"disabled": 0}, fields=["name", "supplier_name", "mobile_no"], order_by="supplier_name"
	)
	totals = dict(
		frappe.db.sql(
			"""select supplier, sum(base_grand_total) from `tabPurchase Invoice`
			where docstatus = 1 group by supplier"""
		)
	)
	for s in suppliers:
		s.total_purchases = flt(totals.get(s.name))
	return suppliers


@frappe.whitelist()
def save_supplier(supplier_name, mobile_no=None):
	if frappe.db.exists("Supplier", supplier_name):
		doc = frappe.get_doc("Supplier", supplier_name)
	else:
		doc = frappe.new_doc("Supplier")
		doc.supplier_name = supplier_name
		doc.supplier_group = frappe.db.get_single_value("Buying Settings", "supplier_group") or frappe.db.get_value(
			"Supplier Group", {"is_group": 0}, "name"
		)
	doc.mobile_no = mobile_no
	doc.save()
	return doc.name


@frappe.whitelist()
def list_purchases(limit=50):
	return frappe.get_all(
		"Purchase Invoice",
		filters={"docstatus": 1},
		fields=["name", "supplier", "posting_date", "base_grand_total", "is_paid", "outstanding_amount", "bill_no"],
		order_by="posting_date desc, creation desc",
		limit=int(limit),
	)
