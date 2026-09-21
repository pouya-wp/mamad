import frappe
from frappe.utils import add_days, flt, getdate, nowdate, nowtime

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
		"payments": _payments(company, start, end),
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
			coalesce(sum(base_grand_total), 0) revenue,
			coalesce(sum(case when is_return = 0 then 1 else 0 end), 0) orders,
			coalesce(sum(base_net_total), 0) net
		from `tabSales Invoice`
		where docstatus = 1 and company = %(company)s and posting_date between %(start)s and %(end)s
			{cutoff.format(table="")}
		""",
		params,
		as_dict=True,
	)[0]
	items_sold = frappe.db.sql(
		f"""
		select coalesce(sum(sii.stock_qty), 0)
		from `tabSales Invoice Item` sii join `tabSales Invoice` si on si.name = sii.parent
		where si.docstatus = 1 and si.company = %(company)s and si.posting_date between %(start)s and %(end)s
			{cutoff.format(table="si.")}
		""",
		params,
	)[0][0]
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
		"""
		select posting_date date, sum(base_grand_total) revenue, sum(case when is_return = 0 then 1 else 0 end) orders
		from `tabSales Invoice`
		where docstatus = 1 and company = %(company)s and posting_date between %(start)s and %(end)s
		group by posting_date
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
		"""
		select hour(posting_time) h, sum(base_grand_total) revenue, count(*) orders
		from `tabSales Invoice`
		where docstatus = 1 and is_return = 0 and company = %(company)s and posting_date between %(start)s and %(end)s
		group by hour(posting_time)
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
	return frappe.db.sql(
		"""
		select sii.item_code, sii.item_name, sum(sii.stock_qty) qty, sum(sii.base_net_amount) revenue
		from `tabSales Invoice Item` sii join `tabSales Invoice` si on si.name = sii.parent
		where si.docstatus = 1 and si.company = %(company)s and si.posting_date between %(start)s and %(end)s
		group by sii.item_code, sii.item_name
		order by qty desc
		limit %(limit)s
		""",
		{"company": company, "start": start, "end": end, "limit": limit},
		as_dict=True,
	)


def _by_group(company, start, end):
	return frappe.db.sql(
		"""
		select sii.item_group, sum(sii.base_net_amount) revenue, sum(sii.stock_qty) qty
		from `tabSales Invoice Item` sii join `tabSales Invoice` si on si.name = sii.parent
		where si.docstatus = 1 and si.company = %(company)s and si.posting_date between %(start)s and %(end)s
		group by sii.item_group
		order by revenue desc
		""",
		{"company": company, "start": start, "end": end},
		as_dict=True,
	)


def _payments(company, start, end):
	return frappe.db.sql(
		"""
		select p.mode_of_payment, sum(p.base_amount) amount
		from `tabSales Invoice Payment` p join `tabSales Invoice` si on si.name = p.parent
		where si.docstatus = 1 and si.company = %(company)s and si.posting_date between %(start)s and %(end)s
		group by p.mode_of_payment
		order by amount desc
		""",
		{"company": company, "start": start, "end": end},
		as_dict=True,
	)


def _recent_orders(company, limit=8):
	return frappe.get_all(
		"Sales Invoice",
		filters={"docstatus": 1, "company": company},
		fields=["name", "posting_date", "posting_time", "base_grand_total", "is_return", "remarks", "owner"],
		order_by="creation desc",
		limit=limit,
	)


@frappe.whitelist()
def pulse():
	"""A cheap heartbeat for the panel: today's running totals and the last order."""
	company = get_cafe_settings().company
	today = getdate(nowdate())
	row = frappe.db.sql(
		"""
		select
			coalesce(sum(base_grand_total), 0) revenue,
			coalesce(sum(case when is_return = 0 then 1 else 0 end), 0) orders
		from `tabSales Invoice`
		where docstatus = 1 and company = %(company)s and posting_date = %(today)s
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
