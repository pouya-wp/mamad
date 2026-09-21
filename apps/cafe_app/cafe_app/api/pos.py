import frappe
from frappe import _
from frappe.utils import flt, now_datetime

from cafe_app.utils import get_cafe_settings, menu_groups

ORDER_TYPES = ("سالن", "بیرون‌بر", "پیک")


@frappe.whitelist()
def get_menu():
	settings = get_cafe_settings()
	groups = menu_groups()
	items = frappe.get_all(
		"Item",
		filters={"item_group": ["in", groups], "disabled": 0, "is_sales_item": 1},
		fields=["item_code", "item_name", "item_group", "image", "description"],
		order_by="item_name asc",
	)
	prices = dict(
		frappe.get_all(
			"Item Price",
			filters={"price_list": settings.price_list, "item_code": ["in", [i.item_code for i in items] or [""]]},
			fields=["item_code", "price_list_rate"],
			as_list=True,
		)
	)
	for item in items:
		item.rate = flt(prices.get(item.item_code))

	return {"groups": groups[1:], "items": items}


@frappe.whitelist()
def create_order(items, payments, order_type="سالن", table_no=None, discount_amount=0, note=None):
	"""Ring up a sale: a submitted POS Sales Invoice that deducts recipe ingredients from stock."""
	items = frappe.parse_json(items)
	payments = frappe.parse_json(payments)
	if not items:
		frappe.throw(_("سفارش خالی است"))

	remarks = " | ".join(filter(None, [order_type, f"میز {table_no}" if table_no else None, note]))
	invoice = build_pos_invoice(items, payments, remarks, discount_amount)
	return {"name": invoice.name, "grand_total": flt(invoice.rounded_total or invoice.grand_total)}


def build_pos_invoice(items, payments, remarks=None, discount_amount=0, posting_date=None, posting_time=None):
	"""Insert and submit a POS Sales Invoice; payments without an amount absorb the remaining total."""
	settings = get_cafe_settings()

	invoice = frappe.new_doc("Sales Invoice")
	invoice.update(
		{
			"company": settings.company,
			"customer": settings.customer,
			"pos_profile": settings.pos_profile,
			"is_pos": 1,
			"update_stock": 1,
			"set_warehouse": settings.warehouse,
			"selling_price_list": settings.price_list,
			"currency": settings.currency,
			"remarks": remarks,
		}
	)
	if posting_date:
		invoice.update(
			{"set_posting_time": 1, "posting_date": posting_date, "posting_time": posting_time, "due_date": posting_date}
		)
	for row in items:
		invoice.append("items", {"item_code": row["item_code"], "qty": flt(row["qty"])})

	if flt(discount_amount):
		invoice.apply_discount_on = "Grand Total"
		invoice.discount_amount = flt(discount_amount)

	invoice.set_missing_values()
	invoice.calculate_taxes_and_totals()

	total = flt(invoice.rounded_total or invoice.grand_total)
	invoice.set("payments", [])
	remaining = total
	for payment in payments:
		amount = min(flt(payment.get("amount")) or remaining, remaining)
		if amount <= 0:
			continue
		invoice.append("payments", {"mode_of_payment": payment["mode_of_payment"], "amount": amount})
		remaining -= amount

	if remaining > 0:
		frappe.throw(_("مبلغ پرداختی از جمع سفارش کمتر است"))

	invoice.insert()
	invoice.submit()
	return invoice


@frappe.whitelist()
def current_shift():
	name = frappe.db.get_value("Cafe Shift", {"user": frappe.session.user, "status": "Open"}, "name")
	if not name:
		return None

	shift = frappe.get_doc("Cafe Shift", name)
	shift.update(_shift_totals(shift.opening_time, now_datetime(), shift.user))
	return shift.as_dict()


@frappe.whitelist()
def open_shift(opening_cash=0):
	if frappe.db.exists("Cafe Shift", {"user": frappe.session.user, "status": "Open"}):
		frappe.throw(_("یک شیفت باز دارید"))

	shift = frappe.get_doc(
		{
			"doctype": "Cafe Shift",
			"user": frappe.session.user,
			"status": "Open",
			"opening_time": now_datetime(),
			"opening_cash": flt(opening_cash),
		}
	).insert()
	return shift.as_dict()


@frappe.whitelist()
def close_shift(closing_cash, note=None):
	name = frappe.db.get_value("Cafe Shift", {"user": frappe.session.user, "status": "Open"}, "name")
	if not name:
		frappe.throw(_("شیفت بازی ندارید"))

	shift = frappe.get_doc("Cafe Shift", name)
	closing_time = now_datetime()
	shift.update(_shift_totals(shift.opening_time, closing_time, shift.user))
	shift.update(
		{
			"status": "Closed",
			"closing_time": closing_time,
			"closing_cash": flt(closing_cash),
			"difference": flt(closing_cash) - flt(shift.expected_cash),
			"note": note,
		}
	)
	shift.save()
	return shift.as_dict()


@frappe.whitelist()
def list_shifts(limit=30):
	return frappe.get_all(
		"Cafe Shift",
		fields=[
			"name",
			"user",
			"status",
			"opening_time",
			"closing_time",
			"opening_cash",
			"closing_cash",
			"expected_cash",
			"total_sales",
			"orders_count",
			"difference",
		],
		order_by="opening_time desc",
		limit=int(limit),
	)


def _shift_totals(start, end, user):
	rows = frappe.db.sql(
		"""
		select p.mode_of_payment, mop.type, sum(p.base_amount) amount
		from `tabSales Invoice Payment` p
		join `tabSales Invoice` si on si.name = p.parent
		left join `tabMode of Payment` mop on mop.name = p.mode_of_payment
		where si.docstatus = 1 and si.owner = %(user)s
			and timestamp(si.posting_date, si.posting_time) between %(start)s and %(end)s
		group by p.mode_of_payment, mop.type
		""",
		{"user": user, "start": start, "end": end},
		as_dict=True,
	)
	orders = frappe.db.sql(
		"""
		select count(*) from `tabSales Invoice`
		where docstatus = 1 and is_return = 0 and owner = %(user)s
			and timestamp(posting_date, posting_time) between %(start)s and %(end)s
		""",
		{"user": user, "start": start, "end": end},
	)[0][0]

	cash_sales = sum(flt(r.amount) for r in rows if r.type == "Cash")
	total_sales = sum(flt(r.amount) for r in rows)
	opening_cash = flt(frappe.db.get_value("Cafe Shift", {"user": user, "opening_time": start}, "opening_cash"))
	return {
		"cash_sales": cash_sales,
		"card_sales": total_sales - cash_sales,
		"total_sales": total_sales,
		"orders_count": orders,
		"expected_cash": opening_cash + cash_sales,
	}
