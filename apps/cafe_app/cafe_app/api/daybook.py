"""The café's day-by-day calendar and the alerts shown above it (manager only)."""

import frappe
from frappe.utils import add_days, date_diff, flt, get_datetime, getdate, now_datetime, nowdate

from cafe_app import jalali
from cafe_app.access import SCOPE_LABELS, require_manager
from cafe_app.agent.fa import fa
from cafe_app.api.dashboard import _daily_trend
from cafe_app.utils import get_cafe_settings

DIRECTION = {"Received": "دریافتی", "Issued": "پرداختی"}
KIND = {"Regular": "چک", "Guarantee": "چک ضمانت", "Promissory": "سفته"}
JALALI_MONTHS = ("فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور", "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند")
MAX_DAYS = 62


def _days(start, end):
	return [add_days(start, i) for i in range(date_diff(end, start) + 1)]


def _contracts():
	return frappe.db.sql(
		"""
		select e.name employee, e.full_name, e.birth_date, e.status, c.position, c.start_date, c.end_date,
			c.monthly_salary, c.payment_day
		from `tabCafe Employee` e left join `tabCafe Employee Contract` c on c.parent = e.name and c.parenttype = 'Cafe Employee'
		""",
		as_dict=True,
	)


def _staff_events(start, end):
	"""{date: [event]} for contract starts/ends, Shamsi paydays and birthdays."""
	events = {}

	def add(day, event):
		events.setdefault(getdate(day), []).append(event)

	days = _days(start, end)
	shamsi = {day: jalali.from_gregorian(day) for day in days}
	birthdays = {}
	for c in _contracts():
		if c.birth_date and c.employee not in birthdays:
			birthdays[c.employee] = (jalali.from_gregorian(getdate(c.birth_date))[1:], c.full_name)
		if not c.position and not c.start_date:
			continue
		if c.start_date and start <= getdate(c.start_date) <= end:
			add(c.start_date, {"type": "contract", "title": f"شروع قرارداد {c.full_name}", "hint": c.position, "tone": "info"})
		if c.end_date and start <= getdate(c.end_date) <= end:
			add(c.end_date, {"type": "contract", "title": f"پایان قرارداد {c.full_name}", "hint": c.position, "tone": "warn"})
		if c.payment_day and c.status == "Active":
			for day in days:
				if shamsi[day][2] != c.payment_day:
					continue
				if c.start_date and day <= getdate(c.start_date):
					continue
				if c.end_date and day > add_days(getdate(c.end_date), 31):
					continue
				add(day, {"type": "payday", "title": f"حقوق {c.full_name}", "amount": flt(c.monthly_salary), "tone": "info"})
	for (month, day_of_month), name in birthdays.values():
		for day in days:
			if shamsi[day][1:] == (month, day_of_month):
				add(day, {"type": "birthday", "title": f"تولد {name}", "tone": "ok"})
	return events


@frappe.whitelist()
def month(from_date, to_date):
	require_manager()
	start, end = getdate(from_date), getdate(to_date)
	if date_diff(end, start) > MAX_DAYS or end < start:
		frappe.throw("بازه تقویم نامعتبر است")
	company = get_cafe_settings().company
	days = {str(day): {"sales": None, "purchases": [], "expenses": [], "cheques": [], "events": []} for day in _days(start, end)}

	for row in _daily_trend(company, start, end):
		if row["orders"] or row["revenue"]:
			days[str(row["date"])]["sales"] = {"revenue": row["revenue"], "orders": row["orders"]}

	for p in frappe.get_all(
		"Cafe Purchase",
		filters={"purchase_date": ["between", [start, end]]},
		fields=["name", "scope", "supplier", "total", "purchase_date"],
		order_by="creation asc",
	):
		days[str(p.purchase_date)]["purchases"].append({"name": p.name, "scope": p.scope, "desk": SCOPE_LABELS.get(p.scope), "supplier": p.supplier, "amount": p.total})

	for e in frappe.db.sql(
		"""
		select je.name, je.posting_date, je.user_remark, acc.account_name, jea.debit amount
		from `tabJournal Entry` je
		join `tabJournal Entry Account` jea on jea.parent = je.name
		join `tabAccount` acc on acc.name = jea.account
		where je.docstatus = 1 and je.company = %(company)s and acc.root_type = 'Expense' and jea.debit > 0
			and je.posting_date between %(start)s and %(end)s
		""",
		{"company": company, "start": start, "end": end},
		as_dict=True,
	):
		days[str(e.posting_date)]["expenses"].append({"name": e.name, "title": e.account_name, "note": e.user_remark, "amount": e.amount})

	for c in frappe.get_all(
		"Cafe Cheque",
		filters={"due_date": ["between", [start, end]], "direction": "Issued", "status": ["!=", "Cancelled"]},
		fields=["name", "direction", "kind", "party", "amount", "due_date", "status", "bank", "journal_entry"],
	):
		days[str(c.due_date)]["cheques"].append(c)

	for day, events in _staff_events(start, end).items():
		days[str(day)]["events"].extend(events)
	return days


@frappe.whitelist()
def alerts():
	require_manager()
	today = getdate(nowdate())
	out = []

	def add(tone, title, text=None, link=None):
		out.append({"tone": tone, "title": title, "text": text, "link": link})

	# Cheques
	for c in frappe.get_all(
		"Cafe Cheque",
		# Guarantee cheques and notes may have no due date; those never fall due.
		filters={"due_date": ["is", "set"], "direction": "Issued", "status": ["!=", "Cancelled"]},
		fields=["direction", "kind", "party", "amount", "due_date", "status", "journal_entry"],
		order_by="due_date asc",
	):
		left = date_diff(c.due_date, today)
		if left > 7:
			break
		if c.status == "Cleared" and c.journal_entry and frappe.db.get_value("Journal Entry", c.journal_entry, "docstatus") == 1:
			continue
		what = f"{KIND[c.kind]} {DIRECTION[c.direction]} {c.party}"
		amount = f"{fa(flt(c.amount) / 10)} تومان"
		if left < 0:
			add("danger", f"سررسید {what} گذشته", f"{amount} · {fa(-left)} روز پیش · تسویه و سند حسابداری لازم است", "/cheques")
		elif left == 0:
			add("danger" if c.direction == "Issued" else "warn", f"سررسید امروز: {what}", amount, "/cheques")
		else:
			add("warn" if c.direction == "Issued" else "info", f"{fa(left)} روز تا سررسید {what}", amount, "/cheques")
	bounced = frappe.db.count("Cafe Cheque", {"status": "Bounced", "direction": "Issued"})
	if bounced:
		add("danger", f"{fa(bounced)} چک برگشتی پیگیری نشده", None, "/cheques")

	# Staff
	for c in _contracts():
		if c.status != "Active" or not c.end_date:
			continue
		left = date_diff(c.end_date, today)
		if 0 <= left <= 30:
			add("warn", f"قرارداد {c.full_name} {fa(left)} روز دیگر تمام می‌شود", c.position, "/staff")
		elif -30 <= left < 0:
			add("danger", f"قرارداد {c.full_name} تمام شده", f"{fa(-left)} روز پیش · تمدید یا قطع همکاری را ثبت کن", "/staff")
	for day, events in sorted(_staff_events(today, add_days(today, 3)).items()):
		left = date_diff(day, today)
		when = "امروز" if left == 0 else ("فردا" if left == 1 else f"{fa(left)} روز دیگر")
		for e in events:
			if e["type"] == "payday":
				add("info", f"{when}: {e['title']}", f"{fa(e['amount'] / 10)} تومان", "/staff")
			elif e["type"] == "birthday":
				add("ok", f"{when}: {e['title']}", None, "/staff")

	# Till sync: during opening hours a quiet till for two hours is unusual.
	now = now_datetime()
	clock = now.hour + now.minute / 60
	if 10.5 <= clock < 23.5:
		last = frappe.db.sql("select max(creation) from `tabSales Invoice` where docstatus = 1")[0][0]
		if last and (now - get_datetime(last)).total_seconds() > 2 * 3600:
			hours = int((now - get_datetime(last)).total_seconds() // 3600)
			add("warn", "فروشی از صندوق نرسیده", f"آخرین سفارش {fa(hours)} ساعت پیش ثبت شد؛ کامپیوتر کافه و برنامه همگام‌سازی را چک کن", "/orders")

	# Data gaps
	from cafe_app.api import menu
	items = [i for i in menu.list_menu() if i.rate and not i.disabled]
	no_recipe = sum(1 for i in items if not i.has_recipe)
	unpriced = sum(1 for i in items if i.has_recipe and i.unpriced)
	if unpriced:
		add("info", f"بهای تمام‌شده {fa(unpriced)} محصول کامل نیست", "قیمت خرید مواد اولیه یا مقدار بعضی مواد ثبت نشده", "/menu")
	if no_recipe:
		add("info", f"{fa(no_recipe)} محصول فروشی رسپی ندارد", None, "/menu")

	order = {"danger": 0, "warn": 1, "info": 2, "ok": 3}
	return sorted(out, key=lambda a: order[a["tone"]])
