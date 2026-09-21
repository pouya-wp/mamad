"""Offline Persian demo brain: understands common café requests without an LLM.

It uses exactly the same tools as the LLM path, so answers are real site data.
"""

import re

from cafe_app.agent import tools
from cafe_app.agent.fa import fa, normalize, percent

SUGGESTIONS = [
	"فروش امروز چطور بود؟",
	"سود و زیان این ماه",
	"چی داره تموم میشه؟",
	"پرفروش‌های این هفته",
	"۱۲ میلیون حقوق باریستا دادم",
	"۵ کیلو شیر خریدم ۳۰۰ هزار تومن",
]

_MULTIPLIERS = {"میلیارد": 1_000_000_000, "میلیون": 1_000_000, "هزار": 1_000}
_AMOUNT = re.compile(r"(\d+(?:\.\d+)?)\s*(میلیارد|میلیون|هزار)?\s*(تومان|تومن|ریال)?")
_QTY = re.compile(r"(\d+(?:\.\d+)?)\s*(کیلوگرم|کیلو|گرم|لیتر|میلی ?لیتر|میل|عدد|تا|بسته)")


def _has(text, *words):
	return any(w in text for w in words)


def _period(text, default="today"):
	if "دیروز" in text:
		return "yesterday"
	if "امروز" in text:
		return "today"
	if _has(text, "هفته"):
		return "week"
	if _has(text, "ماه"):
		return "month"
	if _has(text, "سال"):
		return "year"
	return default


def _amounts(text):
	"""All money amounts in toman, largest first."""
	found = []
	for number, multiplier, currency in _AMOUNT.findall(text):
		value = float(number) * _MULTIPLIERS.get(multiplier, 1)
		if currency == "ریال":
			value /= 10
		if multiplier or currency or value >= 1000:
			found.append(value)
	return sorted(found, reverse=True)


def _payment(text, default):
	if _has(text, "نسیه"):
		return "credit"
	if _has(text, "نقد", "کش"):
		return "cash"
	if _has(text, "کارت"):
		return "card"
	return default


def respond(message):
	text = normalize(message)
	blocks = []

	def run(result):
		if result.get("block"):
			blocks.append(result["block"])
		return result["data"]

	def reply(answer):
		return {"text": answer, "blocks": blocks, "suggestions": [], "mode": "demo"}

	qty_match = _QTY.search(text)
	amounts = _amounts(text)

	# ---- waste
	if _has(text, "خراب", "ریخت", "فاسد", "ضایع", "دور ریخت", "ترش") and qty_match:
		data = run(tools.propose_waste(text, qty_match.group(1), qty_match.group(2), reason=message))
		if "error" in data:
			return reply(data["error"])
		return reply("ضایعات رو آماده کردم. اگه درسته تأیید کن تا از انبار کسر بشه 👇")

	# ---- ingredient purchase
	if _has(text, "خریدم", "خرید", "گرفتم", "آوردن") and qty_match and tools.find_ingredient(text):
		price = amounts[0] if amounts else None
		# "کیلویی ۸۰ هزار" is a unit price, otherwise the amount is the total
		unit_price = price if _has(text, "کیلویی", "لیتری", "عددی", "هر کیلو", "هر لیتر") else None
		data = run(
			tools.propose_purchase(
				text,
				qty_match.group(1),
				qty_match.group(2),
				total_price_toman=None if unit_price else price,
				unit_price_toman=unit_price,
				supplier=text,
				payment=_payment(text, "card"),
			)
		)
		if "error" in data:
			return reply(data["error"])
		return reply("فاکتور خرید رو آماده کردم؛ با تأیید تو هم انبار شارژ میشه هم پرداخت در حساب‌ها ثبت میشه 👇")

	# ---- operating expense
	if amounts and _has(text, "دادم", "پرداخت", "واریز", "هزینه", "قبض", "اجاره", "حقوق", "خرج"):
		run(tools.propose_expense(text, amounts[0], payment=_payment(text, "cash"), note=message))
		return reply("این هزینه رو برات آماده کردم. یه نگاه بنداز و تأیید کن تا در حسابداری ثبت بشه 👇")

	# ---- profit & loss
	if _has(text, "سود", "زیان", "ضرر", "صورت مالی", "وضع مالی"):
		d = run(tools.profit_loss(_period(text, "month")))
		mood = "خوشبختانه سودده بودیم" if d["net_profit_toman"] >= 0 else "متأسفانه زیان داشتیم"
		biggest = d["biggest_expenses"][0] if d["biggest_expenses"] else None
		answer = (
			f"در {d['period']} درآمد {fa(d['income_toman'])} تومان بوده و {mood}: "
			f"سود خالص {fa(d['net_profit_toman'])} تومان (حاشیه {percent(d['net_margin_percent'], signed=True)})."
		)
		if biggest:
			answer += f" بزرگ‌ترین هزینه «{biggest['name']}» با {fa(biggest['toman'])} تومان بوده."
		return reply(answer)

	# ---- best sellers
	if _has(text, "پرفروش", "محبوب", "بیشترین فروش", "بیشتر فروش"):
		rows = run(tools.top_selling(_period(text, "week")))
		if not rows:
			return reply("در این بازه فروشی ثبت نشده.")
		return reply(f"«{rows[0]['name']}» با {fa(rows[0]['qty'])} فروش صدرنشینه. لیست کامل 👇")

	# ---- cash & bank (before stock: "موجودی صندوق" is about money, not the warehouse)
	if _has(text, "صندوق", "بانک", "حساب", "پول", "نقدینگی"):
		rows = run(tools.cash_balances())
		total = sum(r["toman"] for r in rows)
		return reply(f"جمع موجودی صندوق و حساب‌ها {fa(total)} تومانه.")

	# ---- stock
	if _has(text, "موجودی", "انبار", "تموم", "تمام", "اتمام", "کم داریم", "چی بخرم", "سفارش بدم"):
		item = tools.find_ingredient(text)
		if item and not _has(text, "چی ", "چه چیز", "کدا"):
			d = run(tools.stock_status(item.item_name))
			status = "زیر حد مجازه و باید سفارش بدی" if d["is_low"] else "کافیه"
			return reply(f"از «{d['name']}» {fa(d['qty'])} {_uom(d['uom'])} داریم که {status}.")
		rows = run(tools.stock_status())
		if not rows:
			return reply("همه‌چیز به اندازه کافی موجوده 👌")
		names = "، ".join(r["name"] for r in rows[:3])
		return reply(f"{fa(len(rows))} قلم زیر حد مجازه؛ فوری‌تر از همه: {names}. پیشنهاد می‌کنم امروز سفارش بدی.")

	# ---- expenses list
	if _has(text, "هزینه", "خرج"):
		run(tools.recent_expenses())
		return reply("آخرین هزینه‌های ثبت‌شده 👇")

	# ---- sales
	if _has(text, "فروش", "فروختیم", "درآمد", "چطور بود", "چند سفارش", "مشتری"):
		d = run(tools.sales_report(_period(text)))
		answer = f"فروش {d['period']} {fa(d['revenue_toman'])} تومان از {fa(d['orders'])} سفارش بوده"
		if d["change_percent"] is not None:
			direction = "بیشتر" if d["change_percent"] >= 0 else "کمتر"
			answer += f"؛ {percent(d['change_percent'])} {direction} از دوره قبل"
		if d["top_items"]:
			answer += f". پرفروش‌ترین: «{d['top_items'][0]['name']}»"
		return reply(answer + ".")

	if _has(text, "سلام", "درود", "خوبی", "ممنون", "مرسی", "کمک"):
		return {
			"text": "سلام! من دستیار One هستم 👋 حساب‌وکتاب کافه با منه: می‌تونی وضع فروش و سود رو بپرسی، یا فقط بگی چه پولی دادی و چی خریدی تا برات ثبتش کنم.",
			"blocks": [],
			"suggestions": SUGGESTIONS[:4],
			"mode": "demo",
		}

	return {
		"text": "هنوز این رو بلد نیستم 🙂 می‌تونی درباره فروش، سود و زیان، موجودی انبار بپرسی یا بگی چه هزینه‌ای دادی یا چی خریدی تا برات ثبتش کنم.",
		"blocks": [],
		"suggestions": SUGGESTIONS[:4],
		"mode": "demo",
	}


def _uom(value):
	return {"Gram": "گرم", "Millilitre": "میلی‌لیتر", "Nos": "عدد"}.get(value, value)
