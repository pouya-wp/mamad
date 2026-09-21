"""Tools the café agent can use.

Every tool returns {"data": <facts for the model>, "block": <card for the panel>}.
Read tools answer immediately. Write tools never touch the books: they create a
proposal the user has to confirm in the panel (confirm_proposal).
"""

import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate, nowdate

from cafe_app.agent.fa import percent, toman
from cafe_app.api import accounting, dashboard, inventory, menu
from cafe_app.cafe_setup import CAFE_EXPENSE_ACCOUNTS
from cafe_app.utils import get_cafe_settings, period_range

PERIOD_LABELS = {
	"today": "امروز",
	"yesterday": "دیروز",
	"week": "۷ روز اخیر",
	"month": "۳۰ روز اخیر",
	"year": "یک سال اخیر",
}
PAYMENT_MODES = {"cash": "Cash", "card": "Credit Card", "credit": None}
PAYMENT_LABELS = {"Cash": "نقدی", "Credit Card": "کارتخوان", None: "نسیه"}

# unit word -> (stock uom it converts to, factor)
UNITS = {
	"کیلو": ("Gram", 1000),
	"کیلوگرم": ("Gram", 1000),
	"kg": ("Gram", 1000),
	"گرم": ("Gram", 1),
	"لیتر": ("Millilitre", 1000),
	"میلی‌لیتر": ("Millilitre", 1),
	"میلی لیتر": ("Millilitre", 1),
	"میل": ("Millilitre", 1),
	"عدد": ("Nos", 1),
	"تا": ("Nos", 1),
	"بسته": ("Nos", 1),
}

PROPOSAL_TTL = 60 * 60


def _range(period):
	if period == "yesterday":
		day = getdate(add_days(nowdate(), -1))
		return day, day
	start, end, _prev_start, _prev_end = period_range(period if period in PERIOD_LABELS else "today")
	return start, end


# ---------------------------------------------------------------- read tools


def sales_report(period="today"):
	start, end = _range(period)
	summary = dashboard.summary(from_date=start, to_date=end)
	kpis, prev = summary["kpis"], summary["previous"]
	change = (kpis["revenue"] - prev["revenue"]) / prev["revenue"] * 100 if prev["revenue"] else None
	top = summary["top_items"][:3]

	return {
		"data": {
			"period": PERIOD_LABELS.get(period, period),
			"revenue_toman": round(kpis["revenue"] / 10),
			"orders": kpis["orders"],
			"avg_ticket_toman": round(kpis["avg_ticket"] / 10),
			"gross_profit_toman": round(kpis["gross_profit"] / 10),
			"previous_period_revenue_toman": round(prev["revenue"] / 10),
			"change_percent": round(change, 1) if change is not None else None,
			"top_items": [{"name": t.item_name, "qty": t.qty} for t in top],
		},
		"block": {
			"type": "metrics",
			"title": f"فروش {PERIOD_LABELS.get(period, '')}",
			"items": [
				{"label": "فروش", "value": kpis["revenue"], "format": "toman", "change": change},
				{"label": "سفارش", "value": kpis["orders"], "format": "number"},
				{"label": "میانگین فاکتور", "value": kpis["avg_ticket"], "format": "toman"},
				{"label": "سود ناخالص", "value": kpis["gross_profit"], "format": "toman"},
			],
		},
	}


def top_selling(period="week", limit=5):
	start, end = _range(period)
	rows = dashboard._top_items(get_cafe_settings().company, start, end, int(limit))
	return {
		"data": [{"name": r.item_name, "qty": r.qty, "revenue_toman": round(r.revenue / 10)} for r in rows],
		"block": {
			"type": "list",
			"title": f"پرفروش‌های {PERIOD_LABELS.get(period, '')}",
			"items": [
				{"label": r.item_name, "value": r.qty, "format": "number", "hint": f"{toman(r.revenue)} تومان"}
				for r in rows
			],
		},
	}


def stock_status(item_name=None):
	if item_name:
		item = find_ingredient(item_name)
		if not item:
			return {"data": {"error": f"ماده‌ای به اسم «{item_name}» پیدا نشد"}, "block": None}
		low = item.actual_qty <= item.safety_stock
		return {
			"data": {"name": item.item_name, "qty": item.actual_qty, "uom": item.stock_uom, "safety_stock": item.safety_stock, "is_low": low},
			"block": {
				"type": "list",
				"title": "موجودی انبار",
				"items": [
					{
						"label": item.item_name,
						"value": item.actual_qty,
						"format": "number",
						"uom": item.stock_uom,
						"hint": f"حد مجاز {item.safety_stock:g}",
						"tone": "warn" if low else "ok",
					}
				],
			},
		}

	rows = dashboard.low_stock()
	return {
		"data": [{"name": r.item_name, "qty": r.actual_qty, "uom": r.stock_uom, "safety_stock": r.safety_stock} for r in rows],
		"block": {
			"type": "list",
			"title": "اقلام رو به اتمام",
			"items": [
				{
					"label": r.item_name,
					"value": r.actual_qty,
					"format": "number",
					"uom": r.stock_uom,
					"hint": f"حد مجاز {r.safety_stock:g}",
					"tone": "danger" if r.actual_qty <= 0 else "warn",
				}
				for r in rows
			],
		}
		if rows
		else None,
	}


def profit_loss(period="month"):
	report = accounting.overview(period if period in ("week", "month", "year") else "month")
	margin = report["net_profit"] / report["income"] * 100 if report["income"] else 0
	return {
		"data": {
			"period": PERIOD_LABELS.get(period, period),
			"income_toman": round(report["income"] / 10),
			"cost_of_goods_toman": round(report["cogs"] / 10),
			"operating_expenses_toman": round(report["operating_expenses"] / 10),
			"net_profit_toman": round(report["net_profit"] / 10),
			"net_margin_percent": round(margin, 1),
			"biggest_expenses": [
				{"name": e.account_name, "toman": round(e.amount / 10)} for e in report["expenses_by_account"][:4]
			],
		},
		"block": {
			"type": "metrics",
			"title": f"سود و زیان {PERIOD_LABELS.get(period, '')}",
			"items": [
				{"label": "درآمد", "value": report["income"], "format": "toman"},
				{"label": "بهای تمام‌شده", "value": report["cogs"], "format": "toman"},
				{"label": "هزینه‌های جاری", "value": report["operating_expenses"], "format": "toman"},
				{"label": "سود خالص", "value": report["net_profit"], "format": "toman", "hint": f"حاشیه {percent(margin, signed=True)}"},
			],
		},
	}


def cash_balances():
	rows = accounting.balances(get_cafe_settings().company)
	return {
		"data": [{"account": r.account_name, "type": r.account_type, "toman": round(r.balance / 10)} for r in rows],
		"block": {
			"type": "list",
			"title": "موجودی صندوق و بانک",
			"items": [{"label": r.account_name, "value": r.balance, "format": "toman"} for r in rows],
		},
	}


def recent_expenses(limit=6):
	rows = accounting.list_expenses(limit=int(limit))
	return {
		"data": [{"date": r.posting_date, "type": r.account_name, "toman": round(r.amount / 10), "note": r.user_remark} for r in rows],
		"block": {
			"type": "list",
			"title": "آخرین هزینه‌ها",
			"items": [{"label": r.account_name, "value": r.amount, "format": "toman", "hint": str(r.posting_date)} for r in rows],
		},
	}


# ---------------------------------------------------------------- write tools (proposals)


def propose_expense(category, amount_toman, payment="cash", note=None, date=None):
	company = get_cafe_settings().company
	account_name = match_expense_account(category)
	account = frappe.db.get_value("Account", {"company": company, "account_name": account_name, "is_group": 0}, "name")
	mode = PAYMENT_MODES.get(payment, "Cash") or "Cash"
	amount = flt(amount_toman) * 10

	return _proposal(
		{
			"kind": "expense",
			"account": account,
			"amount": amount,
			"mode_of_payment": mode,
			"posting_date": date or nowdate(),
			"note": note or account_name,
		},
		title="ثبت هزینه",
		lines=[
			{"label": "نوع هزینه", "value": account_name},
			{"label": "مبلغ", "value": amount, "format": "toman"},
			{"label": "پرداخت از", "value": PAYMENT_LABELS[mode]},
			{"label": "تاریخ", "value": str(date or nowdate()), "format": "date"},
		],
	)


def propose_purchase(ingredient, quantity, unit=None, total_price_toman=None, unit_price_toman=None, supplier=None, payment="card"):
	item = find_ingredient(ingredient)
	if not item:
		return {"data": {"error": f"ماده اولیه‌ای به اسم «{ingredient}» تعریف نشده"}, "block": None}

	qty, factor = to_stock_qty(quantity, unit, item.stock_uom)
	if total_price_toman:
		rate = flt(total_price_toman) * 10 / qty
	elif unit_price_toman:
		rate = flt(unit_price_toman) * 10 / factor
	else:
		rate = flt(item.valuation_rate)

	supplier = match_supplier(supplier)
	if not supplier:
		return {"data": {"error": "هنوز تأمین‌کننده‌ای تعریف نشده"}, "block": None}
	mode = PAYMENT_MODES.get(payment, "Credit Card")

	return _proposal(
		{
			"kind": "purchase",
			"supplier": supplier,
			"items": [{"item_code": item.item_code, "qty": qty, "rate": rate}],
			"mode_of_payment": mode,
		},
		title="ثبت خرید",
		lines=[
			{"label": "کالا", "value": item.item_name},
			{"label": "مقدار", "value": qty, "format": "number", "uom": item.stock_uom},
			{"label": "تأمین‌کننده", "value": supplier},
			{"label": "پرداخت", "value": PAYMENT_LABELS[mode]},
			{"label": "جمع", "value": qty * rate, "format": "toman"},
		],
	)


def propose_waste(ingredient, quantity, unit=None, reason=None):
	item = find_ingredient(ingredient)
	if not item:
		return {"data": {"error": f"ماده اولیه‌ای به اسم «{ingredient}» تعریف نشده"}, "block": None}

	qty, _factor = to_stock_qty(quantity, unit, item.stock_uom)
	return _proposal(
		{"kind": "waste", "items": [{"item_code": item.item_code, "qty": qty}], "reason": reason or "ضایعات"},
		title="ثبت ضایعات",
		lines=[
			{"label": "کالا", "value": item.item_name},
			{"label": "مقدار", "value": qty, "format": "number", "uom": item.stock_uom},
			{"label": "ارزش تقریبی", "value": qty * flt(item.valuation_rate), "format": "toman"},
			{"label": "علت", "value": reason or "ضایعات"},
		],
	)


def _proposal(payload, title, lines):
	proposal_id = frappe.generate_hash(length=12)
	frappe.cache.set_value(
		f"cafe_agent_proposal:{proposal_id}",
		{"user": frappe.session.user, "payload": payload},
		expires_in_sec=PROPOSAL_TTL,
	)
	return {
		"data": {"proposal_id": proposal_id, "status": "waiting for the user to confirm in the panel", "details": lines},
		"block": {"type": "proposal", "id": proposal_id, "title": title, "lines": lines, "status": "pending"},
	}


def confirm_proposal(proposal_id):
	key = f"cafe_agent_proposal:{proposal_id}"
	entry = frappe.cache.get_value(key)
	if not entry or entry["user"] != frappe.session.user:
		frappe.throw(_("این پیشنهاد منقضی شده؛ دوباره از دستیار بخواه"))

	p = entry["payload"]
	if p["kind"] == "expense":
		name = accounting.record_expense(p["account"], p["amount"], p["mode_of_payment"], p["posting_date"], p["note"])
		message = f"هزینه ثبت شد: {toman(p['amount'])} تومان"
	elif p["kind"] == "purchase":
		name = inventory.record_purchase(p["supplier"], p["items"], p["mode_of_payment"])["name"]
		message = "خرید ثبت شد و موجودی انبار به‌روز شد"
	elif p["kind"] == "waste":
		name = inventory.record_waste(p["items"], p["reason"])
		message = "ضایعات ثبت شد و از انبار کسر شد"
	else:
		frappe.throw(_("نوع پیشنهاد نامعتبر است"))

	frappe.cache.delete_value(key)
	return {"message": message, "document": name}


# ---------------------------------------------------------------- matching helpers


def find_ingredient(name):
	name = (name or "").strip()
	if not name:
		return None
	items = menu.list_ingredients()
	exact = [i for i in items if i.item_name == name]
	if exact:
		return exact[0]
	# longest ingredient name mentioned in the text, or ingredients containing the text
	mentioned = sorted((i for i in items if i.item_name in name), key=lambda i: len(i.item_name), reverse=True)
	if mentioned:
		return mentioned[0]
	partial = [i for i in items if name in i.item_name or any(word in i.item_name for word in name.split() if len(word) > 2)]
	return partial[0] if partial else None


def to_stock_qty(quantity, unit, stock_uom):
	target = UNITS.get((unit or "").strip())
	factor = 1
	# People say "۵ کیلو شیر" for liquids too, so kilo/litre scale grams and millilitres alike.
	if target and (target[0] == stock_uom or (target[1] == 1000 and stock_uom in ("Gram", "Millilitre"))):
		factor = target[1]
	return flt(quantity) * factor, factor


def match_expense_account(category):
	category = category or ""
	for name in CAFE_EXPENSE_ACCOUNTS:
		if name in category or any(part.strip() in category for part in name.replace("،", " و ").split(" و ") if len(part.strip()) > 2):
			return name
	keywords = {
		"آب، برق و گاز": ("قبض", "برق", "گاز", "آب"),
		"اینترنت و تلفن": ("اینترنت", "تلفن", "موبایل", "شارژ"),
		"حقوق و دستمزد": ("حقوق", "دستمزد", "پرسنل", "کارگر", "باریستا"),
		"تعمیرات و نگهداری": ("تعمیر", "سرویس", "نگهداری"),
		"تبلیغات و بازاریابی": ("تبلیغ", "اینستا", "بازاریابی"),
		"ملزومات و شوینده": ("شوینده", "دستمال", "ملزومات"),
		"اجاره": ("اجاره", "رهن"),
	}
	for account, words in keywords.items():
		if any(w in category for w in words):
			return account
	return "سایر هزینه‌ها"


def match_supplier(name=None):
	suppliers = frappe.get_all("Supplier", filters={"disabled": 0}, pluck="name", order_by="creation asc")
	if name:
		for s in suppliers:
			if s in name or name in s:
				return s
	return suppliers[0] if suppliers else None


# ---------------------------------------------------------------- registry for LLM providers

TOOLS = {
	"sales_report": sales_report,
	"top_selling": top_selling,
	"stock_status": stock_status,
	"profit_loss": profit_loss,
	"cash_balances": cash_balances,
	"recent_expenses": recent_expenses,
	"propose_expense": propose_expense,
	"propose_purchase": propose_purchase,
	"propose_waste": propose_waste,
}

_PERIOD = {"type": "string", "enum": ["today", "yesterday", "week", "month", "year"]}
_UNIT = {"type": "string", "description": "واحد به فارسی: کیلو، گرم، لیتر، میل، عدد"}
_PAYMENT = {"type": "string", "enum": ["cash", "card", "credit"], "description": "cash=نقدی، card=کارتخوان، credit=نسیه"}


def _spec(name, description, properties=None, required=None):
	return {
		"type": "function",
		"function": {
			"name": name,
			"description": description,
			"parameters": {"type": "object", "properties": properties or {}, "required": required or []},
		},
	}


TOOL_SPECS = [
	_spec("sales_report", "Sales KPIs for a period. Call for any question about sales, revenue, orders or average ticket.", {"period": _PERIOD}),
	_spec("top_selling", "Best-selling menu items for a period.", {"period": _PERIOD, "limit": {"type": "integer"}}),
	_spec("stock_status", "Stock level of one ingredient, or all low-stock ingredients when item_name is omitted.", {"item_name": {"type": "string"}}),
	_spec("profit_loss", "Profit & loss: income, cost of goods, operating expenses, net profit.", {"period": {"type": "string", "enum": ["week", "month", "year"]}}),
	_spec("cash_balances", "Current cash register and bank/card account balances."),
	_spec("recent_expenses", "Most recently recorded expenses.", {"limit": {"type": "integer"}}),
	_spec(
		"propose_expense",
		"Prepare an operating expense (rent, salaries, bills, repairs...) for the user to confirm. Call when the user says they paid for something that is not an ingredient.",
		{
			"category": {"type": "string", "description": "What it was for, in Persian"},
			"amount_toman": {"type": "number"},
			"payment": _PAYMENT,
			"note": {"type": "string"},
			"date": {"type": "string", "description": "YYYY-MM-DD, omit for today"},
		},
		["category", "amount_toman"],
	),
	_spec(
		"propose_purchase",
		"Prepare an ingredient purchase (adds stock) for the user to confirm.",
		{
			"ingredient": {"type": "string"},
			"quantity": {"type": "number"},
			"unit": _UNIT,
			"total_price_toman": {"type": "number"},
			"unit_price_toman": {"type": "number", "description": "Price per the given unit"},
			"supplier": {"type": "string"},
			"payment": _PAYMENT,
		},
		["ingredient", "quantity"],
	),
	_spec(
		"propose_waste",
		"Prepare a write-off of spoiled or wasted ingredients for the user to confirm.",
		{"ingredient": {"type": "string"}, "quantity": {"type": "number"}, "unit": _UNIT, "reason": {"type": "string"}},
		["ingredient", "quantity"],
	),
]
