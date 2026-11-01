"""Tools the café agent can use.

Every tool returns {"data": <facts for the model>, "block": <card for the panel>}.
Read tools answer immediately. Write tools never touch the books: they create a
proposal the user has to confirm in the panel (confirm_proposal).
"""

import copy

import frappe
from frappe import _
from frappe.utils import flt, nowdate

from cafe_app.access import SCOPE_LABELS, buyer_scopes, require_manager
from cafe_app.agent import reports
from cafe_app.agent.fa import fa, percent, toman
from cafe_app.api import accounting, cheques, dashboard, inventory, menu, purchasing
from cafe_app.cafe_setup import CAFE_EXPENSE_ACCOUNTS
from cafe_app.utils import get_cafe_settings

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


# ---------------------------------------------------------------- read tools


def sales_report(period="today", from_date=None, to_date=None, date=None):
	start, end, label = reports.span(period, from_date, to_date, date)
	summary = dashboard.summary(from_date=start, to_date=end)
	kpis, prev = summary["kpis"], summary["previous"]
	change = (kpis["revenue"] - prev["revenue"]) / prev["revenue"] * 100 if prev["revenue"] else None
	top = summary["top_items"][:3]

	return {
		"data": {
			"range": label,
			"days": (end - start).days + 1,
			"revenue_toman": round(kpis["revenue"] / 10),
			"orders": kpis["orders"],
			"avg_ticket_toman": round(kpis["avg_ticket"] / 10),
			"gross_profit_toman": round(kpis["gross_profit"] / 10),
			"previous_same_length_period_revenue_toman": round(prev["revenue"] / 10),
			"change_percent": round(change, 1) if change is not None else None,
			"top_items": [{"name": t["item_name"], "qty": t["qty"]} for t in top],
		},
		"block": {
			"type": "metrics",
			"title": f"فروش · {label}",
			"items": [
				{"label": "فروش", "value": kpis["revenue"], "format": "toman", "change": change},
				{"label": "سفارش", "value": kpis["orders"], "format": "number"},
				{"label": "میانگین فاکتور", "value": kpis["avg_ticket"], "format": "toman"},
				{"label": "سود ناخالص", "value": kpis["gross_profit"], "format": "toman"},
			],
		},
	}


def top_selling(period="week", limit=5, from_date=None, to_date=None, date=None, order_by="qty", worst=False):
	start, end, label = reports.span(period, from_date, to_date, date)
	rows = dashboard._top_items(get_cafe_settings().company, start, end, 1000)
	key = "revenue" if order_by == "revenue" else "qty"
	rows = sorted(rows, key=lambda r: r[key], reverse=not worst)[: max(1, min(int(limit or 5), 25))]
	return {
		"data": {"range": label, "items": [{"name": r["item_name"], "qty": r["qty"], "revenue_toman": round(r["revenue"] / 10)} for r in rows]},
		"block": {
			"type": "list",
			"title": f"{'کم‌فروش‌ها' if worst else 'پرفروش‌ها'} · {label}",
			"items": [
				{"label": r["item_name"], "value": r["qty"], "format": "number", "hint": f"{toman(r['revenue'])} تومان"}
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


def profit_loss(period="month", from_date=None, to_date=None):
	start, end, label = reports.span(period, from_date, to_date)
	report = accounting.overview("month", from_date=start, to_date=end)
	margin = report["net_profit"] / report["income"] * 100 if report["income"] else 0
	return {
		"data": {
			"range": label,
			"note": "Only what is recorded in ERP: till sales, expenses entered in the panel. Purchase-desk purchases are not in the books.",
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
			"title": f"سود و زیان · {label}",
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


BUY_PAYMENTS = {"cash": "Cash", "card": "Card", "transfer": "Transfer", "credit": "Credit"}
BUY_PAYMENT_LABELS = {"Cash": "نقدی", "Card": "کارت", "Transfer": "کارت به کارت", "Credit": "نسیه"}


def propose_purchase_entry(items, supplier=None, payment="card", date=None, note=None, scope=None):
	"""A purchase for the restaurant/café purchase register, waiting for confirmation."""
	allowed = buyer_scopes()
	if allowed and not scope and len(allowed) == 1:
		scope = allowed[0]
	if scope not in SCOPE_LABELS or (allowed and scope not in allowed):
		return {"data": {"error": "بپرس این خرید برای رستوران است یا کافه (scope: Restaurant یا Cafe)"}, "block": None}
	if not allowed:
		require_manager()

	lines, rows = [], []
	for raw in items if isinstance(items, list) else []:
		name = str(raw.get("name") or "").strip()
		qty = flt(raw.get("quantity"))
		total = flt(raw.get("total_price_toman")) * 10
		if not total and qty and raw.get("unit_price_toman"):
			total = qty * flt(raw["unit_price_toman"]) * 10
		if not name or total <= 0:
			return {"data": {"error": f"مبلغ «{name or 'یکی از اقلام'}» معلوم نیست؛ از کاربر بپرس"}, "block": None}
		rows.append({"item_name": name, "qty": qty, "unit": raw.get("unit") or "", "amount": total})
		lines.append({"label": f"{name} · {fa(qty, 0 if qty.is_integer() else 2) if qty else ''} {raw.get('unit') or ''}".strip(" ·"), "value": total, "format": "toman"})
	if not rows:
		return {"data": {"error": "هیچ قلمی برای خرید مشخص نشده"}, "block": None}

	mode = BUY_PAYMENTS.get(payment, "Card")
	total = sum(r["amount"] for r in rows)
	lines += [
		{"label": "بخش", "value": SCOPE_LABELS[scope]},
		{"label": "فروشنده", "value": supplier or "—"},
		{"label": "پرداخت", "value": BUY_PAYMENT_LABELS[mode]},
		{"label": "تاریخ", "value": str(date or nowdate()), "format": "date"},
		{"label": "جمع کل", "value": total, "format": "toman"},
	]
	return _proposal(
		{"kind": "buy", "scope": scope, "items": rows, "supplier": supplier, "payment": mode, "date": date or nowdate(), "note": note},
		title=f"ثبت خرید {SCOPE_LABELS[scope]}",
		lines=lines,
	)


def purchase_report(period="week", scope=None, from_date=None, to_date=None, date=None):
	allowed = buyer_scopes()
	if allowed and scope and scope not in allowed:
		return {"data": {"error": "به خریدهای این بخش دسترسی نداری"}, "block": None}
	scope = scope or (allowed[0] if len(allowed) == 1 else None)
	start, end, label = reports.span(period, from_date, to_date, date)
	result = purchasing.list_purchases(scope=scope, from_date=start, to_date=end, limit=60)
	rows = result["rows"]
	totals = result["totals"]
	return {
		"data": {
			"range": label,
			"totals_toman": {SCOPE_LABELS[k]: round(v["total"] / 10) for k, v in totals.items() if not scope or k == scope},
			"purchases": [
				{
					"date": str(r.purchase_date),
					"desk": SCOPE_LABELS.get(r.scope),
					"supplier": r.supplier,
					"toman": round(r.total / 10),
					"items": [f"{i.item_name} {i.qty or ''} {i.unit or ''}".strip() for i in r["items"]],
				}
				for r in rows[:15]
			],
		},
		"block": {
			"type": "list",
			"title": f"خریدها · {label}",
			"items": [
				{"label": f"{r.supplier or 'خرید'} · {'، '.join(i.item_name for i in r['items'][:3])}", "value": r.total, "format": "toman", "hint": str(r.purchase_date)}
				for r in rows[:8]
			],
		}
		if rows
		else None,
	}


def price_history(item_name):
	allowed = buyer_scopes()
	return reports.price_history(item_name, scope=allowed[0] if len(allowed) == 1 else None)


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
	elif p["kind"] == "cheque":
		require_manager()
		name = cheques.save_cheque(p["data"])
		message = "چک ثبت شد و در تقویم آمد"
	elif p["kind"] == "cheque_status":
		require_manager()
		name = cheques.set_status(p["name"], p["status"])
		message = "وضعیت چک به‌روز شد"
	elif p["kind"] == "ingredient_price":
		require_manager()
		frappe.db.set_value("Item", p["item_code"], "valuation_rate", p["rate"])
		name = p["item_code"]
		message = "قیمت ماده ثبت شد و بهای تمام‌شده محصولات به‌روز شد"
	elif p["kind"] == "buy":
		purchasing._scope_for_write(p["scope"])
		name = purchasing.create_or_update(
			None, p["scope"], p["items"], p["supplier"], p["payment"], p["date"], p["note"], source="Assistant"
		)["name"]
		message = f"خرید {SCOPE_LABELS[p['scope']]} ثبت شد"
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
	"sales_breakdown": reports.sales_breakdown,
	"top_selling": top_selling,
	"item_sales": reports.item_sales,
	"find_orders": reports.find_orders,
	"order_detail": reports.order_detail,
	"stock_status": stock_status,
	"profit_loss": profit_loss,
	"cash_balances": cash_balances,
	"expenses_report": reports.expenses_report,
	"purchase_report": purchase_report,
	"price_history": reports.price_history,
	"cheques_report": reports.cheques_report,
	"staff_report": reports.staff_report,
	"day_overview": reports.day_overview,
	"alerts": reports.alerts,
	"menu_item_info": reports.menu_item_info,
	"menu_costing": reports.menu_costing,
	"ingredient_prices": reports.ingredient_prices,
	"propose_expense": propose_expense,
	"propose_waste": propose_waste,
	"propose_purchase_entry": propose_purchase_entry,
	"propose_cheque": reports.propose_cheque,
	"propose_cheque_status": reports.propose_cheque_status,
	"propose_ingredient_price": reports.propose_ingredient_price,
}
# A purchase manager's assistant: their own desk's purchases, nothing else.
BUYER_TOOLS = {
	"propose_purchase_entry": propose_purchase_entry,
	"purchase_report": purchase_report,
	"price_history": price_history,
}

_UNIT = {"type": "string", "description": "واحد به فارسی: کیلو، گرم، لیتر، میل، عدد، بسته، شانه"}
_PAYMENT = {"type": "string", "enum": ["cash", "card", "credit"], "description": "cash=نقدی، card=کارتخوان، credit=نسیه"}
_DATES = reports.DATE_ARGS
_RANGE = {k: v for k, v in _DATES.items() if k != "date"}


def _spec(name, description, properties=None, required=None):
	return {
		"type": "function",
		"function": {
			"name": name,
			"description": description,
			"parameters": {"type": "object", "properties": properties or {}, "required": required or []},
		},
	}


_PURCHASE_ENTRY_SPEC = _spec(
	"propose_purchase_entry",
	"Prepare a purchase (ingredients, groceries, supplies) for the restaurant or café purchase register, for the user to confirm. "
	"Put every item the user bought in one call.",
	{
		"items": {
			"type": "array",
			"items": {
				"type": "object",
				"properties": {
					"name": {"type": "string", "description": "Item name in Persian, e.g. گوشت چرخ‌کرده"},
					"quantity": {"type": "number"},
					"unit": _UNIT,
					"total_price_toman": {"type": "number", "description": "What was paid for this line"},
					"unit_price_toman": {"type": "number", "description": "Price per the given unit, when the total is not given"},
				},
				"required": ["name"],
			},
		},
		"supplier": {"type": "string", "description": "Shop or supplier name"},
		"payment": {"type": "string", "enum": ["cash", "card", "transfer", "credit"], "description": "cash=نقدی، card=کارت، transfer=کارت به کارت، credit=نسیه"},
		"date": {"type": "string", "description": "Shamsi like 1405/07/14 or YYYY-MM-DD; omit for today"},
		"note": {"type": "string"},
		"scope": {"type": "string", "enum": ["Restaurant", "Cafe"], "description": "Purchase desk; required when the user manages both"},
	},
	["items"],
)
_PURCHASE_REPORT_SPEC = _spec(
	"purchase_report",
	"Recorded purchases with totals per desk, for any period or date range.",
	{**_DATES, "scope": {"type": "string", "enum": ["Restaurant", "Cafe"]}},
)
_PRICE_HISTORY_SPEC = _spec(
	"price_history",
	"Recent purchase prices of one item (e.g. «آخرین قیمت گوشت؟»), newest first, with unit price.",
	{"item_name": {"type": "string"}},
	["item_name"],
)


def _without_scope(spec):
	"""A purchase manager's desk is fixed by the server, so the model is not offered a choice."""
	spec = copy.deepcopy(spec)
	spec["function"]["parameters"]["properties"].pop("scope", None)
	return spec


def toolset():
	"""(tool specs, registry) the current user may use."""
	allowed = buyer_scopes()
	if allowed:
		if len(allowed) == 1:
			return [_without_scope(_PURCHASE_ENTRY_SPEC), _without_scope(_PURCHASE_REPORT_SPEC), _PRICE_HISTORY_SPEC], BUYER_TOOLS
		return [_PURCHASE_ENTRY_SPEC, _PURCHASE_REPORT_SPEC, _PRICE_HISTORY_SPEC], BUYER_TOOLS
	return TOOL_SPECS, TOOLS


TOOL_SPECS = [
	_spec("sales_report", "Sales KPIs (revenue, orders, average ticket, gross profit, change vs the previous period of equal length, top 3 items) for a period, one day or a range.", _DATES),
	_spec("sales_breakdown", "Sales by category, busiest hours and payment methods for a period, day or range.", _DATES),
	_spec(
		"top_selling",
		"Best (or worst) selling menu items by quantity or revenue.",
		{**_DATES, "limit": {"type": "integer"}, "order_by": {"type": "string", "enum": ["qty", "revenue"]}, "worst": {"type": "boolean"}},
	),
	_spec("item_sales", "How many of one menu item sold and its revenue in a period (default 30 days).", {"item_name": {"type": "string"}, **_DATES}, ["item_name"]),
	_spec(
		"find_orders",
		"List orders (invoices) of a day or range with count and revenue; search by customer name/ID or invoice number; filter by payment state.",
		{
			**_DATES,
			"search": {"type": "string"},
			"payment_state": {"type": "string", "enum": ["paid", "credit", "partial", "unpaid", "unknown", "cancelled"]},
			"limit": {"type": "integer"},
		},
	),
	_spec("order_detail", "Items and payments of one order by its invoice number (e.g. ACC-SINV-2026-01240).", {"name": {"type": "string"}}, ["name"]),
	_spec("stock_status", "Stock level of one ingredient, or all low-stock ingredients when item_name is omitted.", {"item_name": {"type": "string"}}),
	_spec("profit_loss", "Profit & loss from the books: income, cost of goods, operating expenses, net profit.", _RANGE),
	_spec("cash_balances", "Current cash register and bank/card account balances."),
	_spec("expenses_report", "Recorded operating expenses by type and the latest entries for a period (default 30 days).", _DATES),
	_PURCHASE_REPORT_SPEC,
	_PRICE_HISTORY_SPEC,
	_spec(
		"cheques_report",
		"Cheques and promissory notes: pending totals, due this week, overdue, bounced and the list with Shamsi due dates.",
		{
			"direction": {"type": "string", "enum": ["Received", "Issued"]},
			"status": {"type": "string", "enum": ["Pending", "Cleared", "Bounced", "Transferred", "Returned", "Cancelled", "all"]},
			"due_within_days": {"type": "integer"},
		},
	),
	_spec("staff_report", "Staff, their contracts (Shamsi dates, days left), salaries, shifts and Shamsi payday; one person when name is given.", {"name": {"type": "string"}}),
	_spec("day_overview", "Everything that happened on one day: sales, purchases, expenses, cheques due, staff events.", {"date": _DATES["date"]}),
	_spec("alerts", "Current warnings: cheques due or overdue, contracts ending, paydays, quiet till, recipe gaps."),
	_spec("menu_item_info", "One menu item: selling price, recipe rows, cost per serving and margin.", {"name": {"type": "string"}}, ["name"]),
	_spec(
		"menu_costing",
		"Menu costing lists: lowest or best margins, items without a recipe, or recipes missing ingredient prices.",
		{"view": {"type": "string", "enum": ["low_margin", "best_margin", "no_recipe", "unpriced"]}, "limit": {"type": "integer"}},
	),
	_spec("ingredient_prices", "Purchase price of ingredients per kilo/litre/unit (all, or one by name).", {"name": {"type": "string"}}),
	_spec(
		"propose_expense",
		"Prepare an operating expense (rent, salaries, bills, repairs...) for the user to confirm. Call when the user says they paid for something that is not a purchase of goods.",
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
		"propose_waste",
		"Prepare a write-off of spoiled or wasted ingredients for the user to confirm.",
		{"ingredient": {"type": "string"}, "quantity": {"type": "number"}, "unit": _UNIT, "reason": {"type": "string"}},
		["ingredient", "quantity"],
	),
	_PURCHASE_ENTRY_SPEC,
	_spec(
		"propose_cheque",
		"Prepare a new cheque or promissory note for the user to confirm. Received = the café gets it; Issued = the café gives it.",
		{
			"direction": {"type": "string", "enum": ["Received", "Issued"]},
			"party": {"type": "string", "description": "Person or company"},
			"amount_toman": {"type": "number"},
			"due_date": {"type": "string", "description": "Shamsi like 1405/08/15 or YYYY-MM-DD"},
			"kind": {"type": "string", "enum": ["Regular", "Guarantee", "Promissory"]},
			"bank": {"type": "string"},
			"cheque_no": {"type": "string"},
			"note": {"type": "string"},
		},
		["direction", "party", "amount_toman"],
	),
	_spec(
		"propose_cheque_status",
		"Prepare a non-settlement status change of an existing cheque. Clearing a cheque requires the Cheques page to select accounts and post a Journal Entry.",
		{
			"party": {"type": "string"},
			"status": {"type": "string", "enum": ["Pending", "Bounced", "Transferred", "Returned", "Cancelled"]},
			"amount_toman": {"type": "number"},
		},
		["party", "status"],
	),
	_spec(
		"propose_ingredient_price",
		"Prepare an ingredient's purchase price (used for recipe costs), e.g. شیر لیتری ۶۰ هزار.",
		{"ingredient": {"type": "string"}, "price_toman": {"type": "number"}, "per": {"type": "string", "enum": ["کیلو", "لیتر", "گرم", "میلی‌لیتر", "عدد"]}},
		["ingredient", "price_toman"],
	),
]
