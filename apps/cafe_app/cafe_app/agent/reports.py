"""The manager assistant's wider reach: any date range, orders, cheques, staff,
the calendar, menu costing and ingredient prices, plus proposals for cheques and
ingredient prices. Every amount handed to the model is in toman.
"""

import frappe
from frappe.utils import add_days, date_diff, flt, getdate, nowdate

from cafe_app import jalali
from cafe_app.agent.fa import fa, normalize
from cafe_app.api import cheques as cheque_api
from cafe_app.api import daybook, menu, orders, staff
from cafe_app.api.dashboard import _hourly, _payments
from cafe_app.recipes import get_recipe
from cafe_app.source_reporting import by_group, invoice_items
from cafe_app.utils import get_cafe_settings

T = lambda rial: round(flt(rial) / 10)  # noqa: E731


# ---------------------------------------------------------------- dates


def parse_date(text):
	"""'today', 'yesterday', '1405/07/10' (Shamsi) or '2026-10-02' -> date."""
	text = normalize(str(text or "")).strip().lower()
	today = getdate(nowdate())
	if text in ("", "today", "امروز"):
		return today
	if text in ("yesterday", "دیروز"):
		return add_days(today, -1)
	if text[:2] in ("13", "14"):
		day = jalali.parse(text)
		if day:
			return day
	return getdate(text)


def _shamsi_month_start(day):
	jy, jm, _jd = jalali.from_gregorian(day)
	return jalali.to_gregorian(jy, jm, 1)


def span(period=None, from_date=None, to_date=None, date=None):
	"""(start, end, label) from a named period, one day or an explicit range."""
	today = getdate(nowdate())
	if date:
		day = parse_date(date)
		return day, day, str(day)
	if from_date or to_date:
		start = parse_date(from_date) if from_date else today
		end = parse_date(to_date) if to_date else today
		return min(start, end), max(start, end), f"{start} تا {end}"
	period = period or "today"
	if period == "yesterday":
		day = add_days(today, -1)
		return day, day, "دیروز"
	if period == "this_shamsi_month":
		return _shamsi_month_start(today), today, "این ماه شمسی"
	if period == "last_shamsi_month":
		end = add_days(_shamsi_month_start(today), -1)
		return _shamsi_month_start(end), end, "ماه شمسی قبل"
	if period == "this_shamsi_year":
		jy = jalali.from_gregorian(today)[0]
		return jalali.to_gregorian(jy, 1, 1), today, "امسال"
	days = {"today": 0, "week": 6, "month": 29, "quarter": 89, "year": 364}.get(period, 0)
	labels = {"today": "امروز", "week": "۷ روز اخیر", "month": "۳۰ روز اخیر", "quarter": "۹۰ روز اخیر", "year": "یک سال اخیر"}
	return add_days(today, -days), today, labels.get(period, period)


DATE_ARGS = {
	"period": {
		"type": "string",
		"enum": ["today", "yesterday", "week", "month", "quarter", "year", "this_shamsi_month", "last_shamsi_month", "this_shamsi_year"],
	},
	"from_date": {"type": "string", "description": "Shamsi like 1405/07/01 or YYYY-MM-DD"},
	"to_date": {"type": "string", "description": "Shamsi like 1405/07/15 or YYYY-MM-DD"},
	"date": {"type": "string", "description": "One day: Shamsi, YYYY-MM-DD, today or yesterday"},
}


def _match(name, candidates, key):
	"""Best fuzzy match of a Persian name among dicts/rows."""
	wanted = normalize(name)
	if not wanted:
		return None
	rows = [(normalize(c[key]), c) for c in candidates]
	for text, c in rows:
		if text == wanted:
			return c
	contained = sorted(((t, c) for t, c in rows if wanted in t or t in wanted), key=lambda tc: abs(len(tc[0]) - len(wanted)))
	if contained:
		return contained[0][1]
	words = [w for w in wanted.split() if len(w) > 1]
	scored = sorted(((sum(w in t for w in words), c) for t, c in rows), key=lambda sc: -sc[0])
	return scored[0][1] if scored and scored[0][0] else None


# ---------------------------------------------------------------- sales


def sales_breakdown(period=None, from_date=None, to_date=None, date=None):
	start, end, label = span(period, from_date, to_date, date)
	company = get_cafe_settings().company
	groups = sorted(by_group(company, start, end), key=lambda g: -g["revenue"])
	hours = sorted((h for h in _hourly(company, start, end) if h["orders"]), key=lambda h: -h["revenue"])
	payments = _payments(company, start, end)
	return {
		"data": {
			"range": label,
			"by_category": [{"category": g["item_group"], "qty": round(g["qty"]), "toman": T(g["revenue"])} for g in groups],
			"busiest_hours": [{"hour": h["hour"], "orders": h["orders"], "toman": T(h["revenue"])} for h in hours[:6]],
			"payment_methods": [{"method": p["mode_of_payment"], "toman": T(p["amount"])} for p in payments],
		},
		"block": {
			"type": "list",
			"title": f"فروش به تفکیک دسته · {label}",
			"items": [{"label": g["item_group"], "value": g["revenue"], "format": "toman", "hint": f"{fa(g['qty'])} عدد"} for g in groups[:10]],
		}
		if groups
		else None,
	}


def item_sales(item_name, period=None, from_date=None, to_date=None, date=None):
	start, end, label = span(period or "month", from_date, to_date, date)
	rows = invoice_items(get_cafe_settings().company, start, end)
	names = {}
	for r in rows:
		names.setdefault(r["item_code"], {"item_code": r["item_code"], "item_name": r["item_name"]})
	hit = _match(item_name, list(names.values()), "item_name")
	if not hit:
		return {"data": {"error": f"در این بازه فروشی برای «{item_name}» پیدا نشد"}, "block": None}
	qty = sum(flt(r["qty"]) for r in rows if r["item_code"] == hit["item_code"])
	revenue = sum(flt(r["revenue"]) for r in rows if r["item_code"] == hit["item_code"])
	return {
		"data": {"item": hit["item_name"], "range": label, "qty": round(qty), "revenue_toman": T(revenue), "days": date_diff(end, start) + 1},
		"block": {"type": "metrics", "title": f"{hit['item_name']} · {label}", "items": [
			{"label": "تعداد فروش", "value": qty, "format": "number"},
			{"label": "درآمد", "value": revenue, "format": "toman"},
		]},
	}


def find_orders(period=None, from_date=None, to_date=None, date=None, search=None, payment_state=None, limit=12):
	start, end, label = span(period, from_date, to_date, date)
	limit = max(1, min(int(limit or 12), 25))
	rows = orders.list_orders(from_date=start, to_date=end, search=search, start=0, limit=limit, payment_state=payment_state)
	totals = orders.order_totals(from_date=start, to_date=end, search=search, payment_state=payment_state)
	return {
		"data": {
			"range": label,
			"count": totals["count"],
			"revenue_toman": T(totals["revenue"]),
			"orders": [
				{
					"name": o.name, "date": str(o.posting_date), "time": str(o.posting_time)[:5], "toman": T(o.base_grand_total),
					"items": o.get("items_count"), "payment": "، ".join(o.payment_modes or []),
					"customer": ((o.get("source_payment") or {}).get("customer") or {}).get("name"),
				}
				for o in rows
			],
		},
		"block": {
			"type": "list",
			"title": f"سفارش‌ها · {label}",
			"items": [
				{"label": f"{o.name} · {str(o.posting_time)[:5]}", "value": o.base_grand_total, "format": "toman", "hint": "، ".join(o.payment_modes or [])}
				for o in rows[:10]
			],
		}
		if rows
		else None,
	}


def order_detail(name):
	o = orders.get_order(name)
	return {
		"data": {
			"name": o["name"], "date": str(o["posting_date"]), "time": str(o["posting_time"])[:5], "total_toman": T(o["grand_total"]),
			"items": [{"name": i["item_name"], "qty": i["qty"], "toman": T(i["amount"])} for i in o["items"]],
			"payments": [{"method": p.get("mode_of_payment"), "toman": T(p.get("amount"))} for p in (o.get("payments") or [])],
			"customer": ((o.get("source_payment") or {}).get("customer") or {}).get("name"),
		},
		"block": {"type": "list", "title": f"سفارش {o['name']}", "items": [
			{"label": f"{i['item_name']} × {fa(i['qty'])}", "value": i["amount"], "format": "toman"} for i in o["items"]
		]},
	}


# ---------------------------------------------------------------- money and paper


def expenses_report(period=None, from_date=None, to_date=None, date=None):
	start, end, label = span(period or "month", from_date, to_date, date)
	rows = frappe.db.sql(
		"""
		select je.posting_date, acc.account_name, je.user_remark, jea.debit amount
		from `tabJournal Entry` je
		join `tabJournal Entry Account` jea on jea.parent = je.name
		join `tabAccount` acc on acc.name = jea.account
		where je.docstatus = 1 and je.company = %(company)s and acc.root_type = 'Expense' and jea.debit > 0
			and je.posting_date between %(start)s and %(end)s
		order by je.posting_date desc
		""",
		{"company": get_cafe_settings().company, "start": start, "end": end},
		as_dict=True,
	)
	by_account = {}
	for r in rows:
		by_account[r.account_name] = by_account.get(r.account_name, 0) + flt(r.amount)
	return {
		"data": {
			"range": label,
			"total_toman": T(sum(by_account.values())),
			"by_type": [{"type": k, "toman": T(v)} for k, v in sorted(by_account.items(), key=lambda kv: -kv[1])],
			"latest": [{"date": str(r.posting_date), "type": r.account_name, "note": r.user_remark, "toman": T(r.amount)} for r in rows[:10]],
		},
		"block": {"type": "list", "title": f"هزینه‌ها · {label}", "items": [
			{"label": k, "value": v, "format": "toman"} for k, v in sorted(by_account.items(), key=lambda kv: -kv[1])
		]}
		if rows
		else None,
	}


def cheques_report(direction=None, status="Pending", due_within_days=None):
	data = cheque_api.list_cheques(direction=direction, status=status if status != "all" else None)
	rows = data["rows"]
	if due_within_days:
		limit = add_days(nowdate(), int(due_within_days))
		rows = [r for r in rows if r.due_date and getdate(r.due_date) <= getdate(limit)]
	today = getdate(nowdate())
	return {
		"data": {
			"summary_toman": {
				d: {"pending": T(s["pending"]), "count": s["pending_count"], "due_this_week": T(s["due_week"]), "overdue": s["overdue"], "bounced": s["bounced"]}
				for d, s in data["summary"].items()
			},
			"cheques": [
				{
					"party": r.party, "direction": r.direction, "kind": r.kind, "toman": T(r.amount), "status": r.status,
					"due": str(r.due_date) if r.due_date else None,
					"due_shamsi": "/".join(map(str, jalali.from_gregorian(getdate(r.due_date)))) if r.due_date else None,
					"days_left": date_diff(r.due_date, today) if r.due_date else None, "bank": r.bank,
				}
				for r in rows[:20]
			],
		},
		"block": {"type": "list", "title": "چک‌ها", "items": [
			{
				"label": f"{'دریافتی از' if r.direction == 'Received' else 'پرداختی به'} {r.party}",
				"value": r.amount, "format": "toman",
				"hint": f"سررسید {'/'.join(map(str, jalali.from_gregorian(getdate(r.due_date))))}" if r.due_date else "بدون سررسید",
				"tone": "danger" if r.due_date and getdate(r.due_date) < today and r.status == "Pending" else None,
			}
			for r in rows[:10]
		]}
		if rows
		else None,
	}


def staff_report(name=None):
	people = staff.list_staff()
	if name:
		hit = _match(name, people, "full_name")
		people = [hit] if hit else []
		if not people:
			return {"data": {"error": f"کارمندی به اسم «{name}» پیدا نشد"}, "block": None}
	shamsi = lambda d: "/".join(map(str, jalali.from_gregorian(getdate(d)))) if d else None  # noqa: E731
	# Paydays exactly as the calendar shows them: the first one falls a month after the start.
	today = getdate(nowdate())
	upcoming = []
	for day, events in sorted(daybook._staff_events(add_days(today, -31), add_days(today, 45)).items()):
		for e in events:
			if e["type"] == "payday" and (not name or any(e["title"].endswith(p["full_name"]) for p in people)):
				upcoming.append({"date_shamsi": shamsi(day), "days_from_today": date_diff(day, today), "who": e["title"], "toman": T(e["amount"])})
	return {
		"data": {
			"active": sum(1 for p in people if p["status"] == "Active"),
			"monthly_payroll_toman": T(sum(p["monthly_salary"] or 0 for p in people if p["status"] == "Active")),
			"paydays_last_31_and_next_45_days": upcoming,
			"people": [
				{
					"name": p["full_name"], "phone": p["phone"], "status": p["status"],
					"contracts": [
						{
							"position": c["position"], "start": shamsi(c["start_date"]), "end": shamsi(c["end_date"]),
							"state": c["state"], "days_left": c["days_left"], "salary_toman": T(c["monthly_salary"]),
							"payday_of_shamsi_month": c["payment_day"], "shift": f"{c['shift_start'] or '?'}-{c['shift_end'] or '?'}",
							"note": c.get("note"),
						}
						for c in p["contracts"]
					],
				}
				for p in people
			],
		},
		"block": {"type": "list", "title": "پرسنل", "items": [
			{"label": p["full_name"], "value": p["monthly_salary"] or 0, "format": "toman", "hint": "، ".join(c["position"] or "" for c in p["current"])}
			for p in people
		]},
	}


def day_overview(date=None):
	day = parse_date(date)
	d = daybook.month(day, day)[str(day)]
	return {
		"data": {
			"date": str(day), "shamsi": "/".join(map(str, jalali.from_gregorian(day))),
			"sales": {"toman": T(d["sales"]["revenue"]), "orders": d["sales"]["orders"]} if d["sales"] else None,
			"purchases": [{"desk": p["desk"], "supplier": p["supplier"], "toman": T(p["amount"])} for p in d["purchases"]],
			"expenses": [{"type": e["title"], "toman": T(e["amount"])} for e in d["expenses"]],
			"cheques": [{"party": c.party, "direction": c.direction, "toman": T(c.amount), "status": c.status} for c in d["cheques"]],
			"staff_events": [e["title"] for e in d["events"]],
		},
		"block": None,
	}


def alerts():
	rows = daybook.alerts()
	tone = {"danger": "danger", "warn": "warn", "info": None, "ok": "ok"}
	return {
		"data": [{"level": a["tone"], "title": a["title"], "detail": a["text"]} for a in rows],
		"block": {"type": "list", "title": "هشدارها", "items": [
			{"label": a["title"], "value": a["text"] or "", "format": "text", "tone": tone[a["tone"]]} for a in rows[:8]
		]}
		if rows
		else None,
	}


# ---------------------------------------------------------------- menu and costs


def menu_item_info(name):
	items = menu.list_menu()
	hit = _match(name, items, "item_name")
	if not hit:
		return {"data": {"error": f"محصولی به اسم «{name}» در منو نیست"}, "block": None}
	recipe = get_recipe(hit.item_code)
	return {
		"data": {
			"name": hit.item_name, "category": hit.item_group, "price_toman": T(hit.rate),
			"cost_toman": T(hit.cost) if hit.has_recipe else None,
			"margin_percent": round(hit.margin, 1) if hit.has_recipe and not hit.unpriced else None,
			"recipe_complete": bool(hit.has_recipe and not hit.unpriced),
			"recipe": [
				{"ingredient": r["ingredient_name"], "qty": r["qty"], "unit": r["unit"], "cost_toman": T(r["cost"]) if r["cost"] is not None else "بی‌قیمت"}
				for r in recipe["rows"]
			],
			"notes": recipe["notes"],
		},
		"block": {"type": "metrics", "title": hit.item_name, "items": [
			{"label": "قیمت فروش", "value": hit.rate, "format": "toman"},
			{"label": "بهای تمام‌شده", "value": hit.cost, "format": "toman", "hint": f"{fa(hit.unpriced)} قلم بی‌قیمت" if hit.unpriced else None},
		]},
	}


def menu_costing(view="low_margin", limit=10):
	items = [i for i in menu.list_menu() if i.rate and not i.disabled]
	limit = max(1, min(int(limit or 10), 30))
	if view == "no_recipe":
		rows = [i for i in items if not i.has_recipe]
	elif view == "unpriced":
		rows = [i for i in items if i.has_recipe and i.unpriced]
	else:
		rows = sorted((i for i in items if i.has_recipe and not i.unpriced), key=lambda i: i.margin, reverse=view == "best_margin")
	rows = rows[:limit]
	return {
		"data": {
			"view": view,
			"items": [
				{"name": i.item_name, "price_toman": T(i.rate), "cost_toman": T(i.cost) if i.has_recipe else None,
				 "margin_percent": round(i.margin, 1) if i.has_recipe and not i.unpriced else None}
				for i in rows
			],
		},
		"block": {"type": "list", "title": "بهای تمام‌شده منو", "items": [
			{"label": i.item_name, "value": i.margin if i.has_recipe and not i.unpriced else i.rate,
			 "format": "percent" if i.has_recipe and not i.unpriced else "toman"}
			for i in rows
		]}
		if rows
		else None,
	}


def ingredient_prices(name=None):
	rows = menu.list_ingredients()
	if name:
		hit = _match(name, rows, "item_name")
		rows = [hit] if hit else []
	unit = {"Gram": "کیلو", "Millilitre": "لیتر", "Nos": "عدد"}
	scale = {"Gram": 1000, "Millilitre": 1000, "Nos": 1}
	return {
		"data": [
			{"ingredient": r.item_name, "price_toman": T(flt(r.valuation_rate) * scale.get(r.stock_uom, 1)) or None, "per": unit.get(r.stock_uom, r.stock_uom)}
			for r in rows
		],
		"block": None,
	}


# ---------------------------------------------------------------- proposals


def propose_cheque(direction, party, amount_toman, due_date=None, kind="Regular", bank=None, cheque_no=None, note=None):
	from cafe_app.agent.tools import _proposal

	if direction not in ("Received", "Issued"):
		return {"data": {"error": "بپرس چک دریافتی است یا پرداختی"}, "block": None}
	due = parse_date(due_date) if due_date else None
	if kind == "Regular" and not due:
		return {"data": {"error": "تاریخ سررسید را بپرس"}, "block": None}
	amount = flt(amount_toman) * 10
	return _proposal(
		{"kind": "cheque", "data": {"direction": direction, "kind": kind if kind in ("Regular", "Guarantee", "Promissory") else "Regular",
			"party": party, "amount": amount, "due_date": str(due) if due else None, "bank": bank, "cheque_no": cheque_no, "note": note}},
		title="ثبت چک " + ("دریافتی" if direction == "Received" else "پرداختی"),
		lines=[
			{"label": "طرف حساب", "value": party},
			{"label": "مبلغ", "value": amount, "format": "toman"},
			{"label": "سررسید", "value": str(due) if due else "—", "format": "date" if due else "text"},
			{"label": "بانک", "value": bank or "—"},
		],
	)


STATUS_FA = {"Pending": "در جریان", "Cleared": "پاس شد", "Bounced": "برگشتی", "Transferred": "خرج شد", "Returned": "عودت", "Cancelled": "باطل"}


def propose_cheque_status(party, status, amount_toman=None):
	from cafe_app.agent.tools import _proposal

	if status not in STATUS_FA:
		return {"data": {"error": "وضعیت نامعتبر است"}, "block": None}
	if status == "Cleared":
		return {"data": {"error": "برای پاس کردن چک و ثبت هم‌زمان سند حسابداری، از بخش چک‌ها و دکمه «ثبت تسویه و سند» استفاده کن"}, "block": None}
	rows = [r for r in cheque_api.list_cheques(status="Pending")["rows"]] or cheque_api.list_cheques()["rows"]
	if amount_toman:
		rows = [r for r in rows if abs(T(r.amount) - flt(amount_toman)) < 1] or rows
	hit = _match(party, rows, "party")
	if not hit:
		return {"data": {"error": f"چکی برای «{party}» پیدا نشد"}, "block": None}
	return _proposal(
		{"kind": "cheque_status", "name": hit.name, "status": status},
		title="تغییر وضعیت چک",
		lines=[
			{"label": "طرف حساب", "value": hit.party},
			{"label": "مبلغ", "value": hit.amount, "format": "toman"},
			{"label": "وضعیت جدید", "value": STATUS_FA[status]},
		],
	)


def propose_ingredient_price(ingredient, price_toman, per="کیلو"):
	from cafe_app.agent.tools import _proposal

	rows = menu.list_ingredients()
	hit = _match(ingredient, rows, "item_name")
	if not hit:
		return {"data": {"error": f"ماده‌ای به اسم «{ingredient}» تعریف نشده"}, "block": None}
	scale = {"کیلو": 1000, "لیتر": 1000, "گرم": 1, "میلی‌لیتر": 1, "عدد": 1}.get(per, 1)
	if hit.stock_uom == "Nos":
		scale = 1
	rate = flt(price_toman) * 10 / scale
	return _proposal(
		{"kind": "ingredient_price", "item_code": hit.item_code, "rate": rate},
		title="قیمت ماده اولیه",
		lines=[
			{"label": "ماده", "value": hit.item_name},
			{"label": f"قیمت هر {per}", "value": flt(price_toman) * 10, "format": "toman"},
		],
	)


def price_history(item_name, scope=None):
	"""Recent purchase prices of one item, within the caller's desk for a purchase manager."""
	params = {"name": f"%{normalize(item_name)}%"}
	desk = ""
	if scope:
		desk = "and p.scope = %(scope)s"
		params["scope"] = scope
	rows = frappe.db.sql(
		f"""
		select p.purchase_date, p.scope, p.supplier, i.item_name, i.qty, i.unit, i.amount
		from `tabCafe Purchase Item` i join `tabCafe Purchase` p on p.name = i.parent
		where replace(replace(i.item_name, 'ي', 'ی'), 'ك', 'ک') like %(name)s {desk}
		order by p.purchase_date desc, p.creation desc limit 10
		""",
		params,
		as_dict=True,
	)
	return {
		"data": [
			{"date": str(r.purchase_date), "supplier": r.supplier, "item": r.item_name, "qty": r.qty, "unit": r.unit,
			 "total_toman": T(r.amount), "unit_price_toman": T(r.amount / r.qty) if r.qty else None}
			for r in rows
		] or {"info": "خریدی با این نام ثبت نشده"},
		"block": None,
	}
