import frappe
from frappe.utils import add_days, flt, getdate, nowdate, nowtime

from cafe_app.source_catalog import display_item_name
from cafe_app.sales_source import SEPEHRYAR_LABEL
from cafe_app.source_payments import source_key, snapshots, payment_overview, unknown_snapshot
from cafe_app.source_reporting import payment_join, total_sql, invoice_items, top_items, by_group
from cafe_app.utils import get_cafe_settings, ingredient_groups, period_range


@frappe.whitelist()
def summary(period="today", from_date=None, to_date=None):
	settings = get_cafe_settings()
	company = settings.company
	start, end, prev_start, prev_end = period_range(period, from_date, to_date)

	# A day still in progress is compared with the previous day up to the same hour.
	until_time = nowtime() if start == end == getdate(nowdate()) else None
	current = _sales_kpis(company, start, end)
	previous = _sales_kpis(company, prev_start, prev_end, until_time)

	return {
		"range": {"from": start, "to": end},
		"kpis": current,
		"previous": previous,
		"trend": _daily_trend(company, add_days(getdate(nowdate()), -29), getdate(nowdate())),
		"hourly": _hourly(company, start, end),
		"top_items": _top_items(company, start, end),
		"by_group": _by_group(company, start, end),
		"group_items": _group_items(company, start, end),
		"payments": _payments(company, start, end),
		"source_payments": payment_overview(_source_orders(company, start, end)),
		"low_stock": low_stock(settings.warehouse),
		"recent_orders": _recent_orders(company),
	}


def _sales_kpis(company, start, end, until_time=None):
	"""Sales KPIs between two dates; until_time cuts the last day off at that time of day."""
	params = {"company": company, "start": start, "end": end, "until": until_time}
	cutoff = "and (%(until)s is null or {table}posting_date < %(end)s or {table}posting_time <= %(until)s)"

	row = frappe.db.sql(
		f"""
		select
			coalesce(sum({total_sql()}), 0) revenue,
			coalesce(sum(case when si.is_return = 0 and coalesce(sp.status,'')<>'Cancelled' then 1 else 0 end), 0) orders,
			coalesce(sum({total_sql(field='base_net_total')}), 0) net
		from `tabSales Invoice` si {payment_join()}
		where si.docstatus = 1 and si.company = %(company)s and si.posting_date between %(start)s and %(end)s
			{cutoff.format(table="si.")}
		""",
		params,
		as_dict=True,
	)[0]
	items_sold = sum(flt(item["qty"]) for item in invoice_items(company, start, end, until_time))
	cogs = frappe.db.sql(
		f"""
		select coalesce(sum(-stock_value_difference), 0)
		from `tabStock Ledger Entry`
		where is_cancelled = 0 and voucher_type = 'Sales Invoice' and company = %(company)s
			and posting_date between %(start)s and %(end)s
			{cutoff.format(table="")}
		""",
		params,
	)[0][0]

	orders = int(row.orders)
	return {
		"revenue": flt(row.revenue),
		"orders": orders,
		"avg_ticket": flt(row.revenue) / orders if orders else 0,
		"items_sold": flt(items_sold),
		"cogs": flt(cogs),
		"gross_profit": flt(row.net) - flt(cogs),
	}


def _daily_trend(company, start, end):
	rows = frappe.db.sql(
		f"""
		select si.posting_date date, sum({total_sql()}) revenue,
			sum(case when si.is_return = 0 and coalesce(sp.status,'')<>'Cancelled' then 1 else 0 end) orders
		from `tabSales Invoice` si {payment_join()}
		where si.docstatus = 1 and si.company = %(company)s and si.posting_date between %(start)s and %(end)s
		group by si.posting_date
		""",
		{"company": company, "start": start, "end": end},
		as_dict=True,
	)
	by_date = {getdate(r.date): r for r in rows}
	days = (end - start).days + 1
	trend = []
	for offset in range(days):
		day = add_days(start, offset)
		r = by_date.get(day)
		trend.append({"date": day, "revenue": flt(r.revenue) if r else 0, "orders": int(r.orders) if r else 0})
	return trend


def _hourly(company, start, end):
	rows = frappe.db.sql(
		f"""
		select hour(si.posting_time) h, sum({total_sql()}) revenue, count(*) orders
		from `tabSales Invoice` si {payment_join()}
		where si.docstatus = 1 and si.is_return = 0 and si.company = %(company)s and si.posting_date between %(start)s and %(end)s
		and coalesce(sp.status,'')<>'Cancelled'
		group by hour(si.posting_time)
		""",
		{"company": company, "start": start, "end": end},
		as_dict=True,
	)
	by_hour = {int(r.h): r for r in rows}
	return [
		{"hour": h, "revenue": flt(by_hour[h].revenue) if h in by_hour else 0, "orders": int(by_hour[h].orders) if h in by_hour else 0}
		for h in range(24)
	]


def _top_items(company, start, end, limit=8):
	return top_items(company, start, end, limit)


def _by_group(company, start, end):
	groups = {}
	for row in by_group(company, start, end):
		name = row["item_group"] or "سایر"
		total = groups.setdefault(name, {"item_group": name, "qty": 0, "revenue": 0})
		total["qty"] += flt(row["qty"])
		total["revenue"] += flt(row["revenue"])
	return sorted(groups.values(), key=lambda group: -group["revenue"])


def _group_items(company, start, end):
	"""Item level detail behind the category shares, using the same source projection."""
	groups = {}
	for row in invoice_items(company, start, end):
		group = row["item_group"] or "سایر"
		key = (row["item_code"], row["item_name"])
		items = groups.setdefault(group, {})
		item = items.setdefault(key, {"item_code": key[0], "item_name": key[1], "qty": 0, "revenue": 0})
		item["qty"] += flt(row["qty"])
		item["revenue"] += flt(row["revenue"])
	return {group: sorted(items.values(), key=lambda item: -item["revenue"]) for group, items in groups.items()}


def _payments(company, start, end):
	rows = frappe.db.sql(
		"""
		select p.mode_of_payment, sum(p.base_amount) amount
		from `tabSales Invoice Payment` p join `tabSales Invoice` si on si.name = p.parent
		left join `tabSales Invoice` original on original.name = si.return_against
		where si.docstatus = 1 and si.company = %(company)s and si.posting_date between %(start)s and %(end)s
			and (si.remarks is null or si.remarks not like %(source_marker)s)
			and (original.remarks is null or original.remarks not like %(source_marker)s)
		group by p.mode_of_payment
		order by amount desc
		""",
		{"company": company, "start": start, "end": end, "source_marker": "%[Sepand:%", "source_label": SEPEHRYAR_LABEL},
		as_dict=True,
	)
	amounts = {row.mode_of_payment: flt(row.amount) for row in rows}
	orders = _source_orders(company, start, end)
	payments = snapshots(source_key(order.remarks) for order in orders)
	for order in orders:
		if order.is_return:
			continue
		payment = payments.get(source_key(order.remarks), unknown_snapshot())
		if payment["status"] in ("Unknown", "Cancelled"):
			continue
		for method in payment["methods"]:
			label = method["mode_of_payment"]
			amounts[label] = amounts.get(label, 0) + method["amount"]
	return [{"mode_of_payment": label, "amount": amount} for label, amount in sorted(amounts.items(), key=lambda pair: -pair[1])]


def _source_orders(company, start, end):
	return frappe.db.sql("""SELECT remarks,is_return FROM `tabSales Invoice`
		WHERE docstatus=1 AND company=%s AND posting_date BETWEEN %s AND %s
		AND remarks LIKE %s""", (company, start, end, "%[Sepand:%"), as_dict=True)


def _recent_orders(company, limit=8):
	orders = frappe.get_all(
		"Sales Invoice",
		filters={"docstatus": 1, "company": company},
		fields=["name", "posting_date", "posting_time", "base_grand_total", "is_return", "remarks", "owner", "customer_name"],
		order_by="creation desc",
		limit=limit,
	)
	payments = snapshots(source_key(order.remarks) for order in orders if not order.is_return)
	for order in orders:
		payment = payments.get(source_key(order.remarks)) if not order.is_return else None
		if payment:
			order.customer_name = (payment.get("customer") or {}).get("name") or order.customer_name
		order.owner_name = frappe.utils.get_fullname(order.owner)
		if payment and payment["total"] is not None:
			order.base_grand_total = 0 if payment["status"] == "Cancelled" else payment["total"]
	return orders


@frappe.whitelist()
def pulse():
	"""A cheap heartbeat for the panel: today's running totals and the last order."""
	company = get_cafe_settings().company
	today = getdate(nowdate())
	row = frappe.db.sql(
		f"""
		select
			coalesce(sum({total_sql()}), 0) revenue,
			coalesce(sum(case when si.is_return = 0 and coalesce(sp.status,'')<>'Cancelled' then 1 else 0 end), 0) orders
		from `tabSales Invoice` si {payment_join()}
		where si.docstatus = 1 and si.company = %(company)s and si.posting_date = %(today)s
		""",
		{"company": company, "today": today},
		as_dict=True,
	)[0]
	last = frappe.get_all(
		"Sales Invoice",
		filters={"docstatus": 1, "company": company, "posting_date": today},
		fields=["name", "base_grand_total", "posting_time", "is_return"],
		order_by="creation desc",
		limit=1,
	)
	return {
		"orders": int(row.orders or 0),
		"revenue": flt(row.revenue),
		"last": last[0] if last else None,
		"source_payment_revision": frappe.db.sql("select max(checked_at) from `tabCafe Source Payment`")[0][0],
	}


@frappe.whitelist()
def low_stock(warehouse=None):
	warehouse = warehouse or get_cafe_settings().warehouse
	return frappe.db.sql(
		"""
		select i.item_code, i.item_name, i.stock_uom, i.safety_stock, coalesce(b.actual_qty, 0) actual_qty
		from `tabItem` i
		left join `tabBin` b on b.item_code = i.item_code and b.warehouse = %(warehouse)s
		where i.disabled = 0 and i.is_stock_item = 1 and i.item_group in %(groups)s
			and coalesce(b.actual_qty, 0) <= greatest(i.safety_stock, 0)
		order by coalesce(b.actual_qty, 0) / nullif(i.safety_stock, 0) asc
		limit 12
		""",
		{"warehouse": warehouse, "groups": ingredient_groups()},
		as_dict=True,
	)
