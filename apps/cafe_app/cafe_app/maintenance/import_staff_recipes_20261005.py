"""One-off import (2026-10-05): staff contracts, recipe costs and the two purchase desks.

    bench --site frontend execute cafe_app.maintenance.import_staff_recipes_20261005.run --kwargs '{"commit": 0}'

Recipes are attached to EXISTING menu items only; no item name, price, group or
other field is changed. Costs from the kitchen sheet are thousand toman per
serving. Drink recipes are quantities, priced later from purchase prices.
"""

import os

import frappe
from frappe.utils.password import update_password

from cafe_app.access import CAFE_BUYER, RESTAURANT_BUYER, ensure_roles
from cafe_app.jalali import parse as jdate
from cafe_app.recipes import set_recipe

# ------------------------------------------------------------------ staff

STAFF = [
	("شایان رزاقی", "4421689306", "09926187981", "خیابان خرمشهر", None, [
		("پرسنل بار / باریستا", "1405/06/23", "1405/12/23", "16:00", "23:45", "شنبه / جمعه", 150000000, 23, "1405/06/23"),
	]),
	("امیرعلی دهقانی", "6480116428", "09134526744", "کوچه زیتون", None, [
		# The contract has 1405/7/5 in both the start and the end field.
		("پرسنل بار / باریستا", "1405/07/05", "1405/12/05", "16:00", "23:45", None, 170000000, 5, "1405/07/05",
			"فرضی: پایان ۶ماهه مثل بقیه؛ در قرارداد پایان هم ۱۴۰۵/۷/۵ نوشته شده"),
	]),
	("زهرا سیدی", "4421269195", "09137754075", "میدان امید", "1384/06/22", [
		("سالن‌کار", "1405/07/09", "1405/12/09", "16:00", "23:45", None, 150000000, 9, None,
			"فرضی: پایان، شیفت، حقوق و روز پرداخت مثل سالن‌کارهای دیگر؛ در قرارداد خالی است و کارفرما امضا نکرده"),
	]),
	("بهنام کعبه‌ای", "1900552799", "09391204499", "شهرک دانشگاه", None, [
		("سالن‌کار", "1405/07/06", "1405/12/06", "16:00", "23:45", None, 150000000, 6, "1405/07/06",
			"فرضی: روز پرداخت = روز شروع؛ در قرارداد خالی است"),
	]),
	("مصطفی پوربابائی", "4432653381", "09134520176", "بلوار شهید قندی، خ طراح، خ طراح ۴، پلاک ۲۱", None, [
		("پرسنل بار / باریستا", "1404/07/18", None, "18:00", "23:45", None, 150000000, 18, "1404/07/18",
			"فرضی: شروع و روز پرداخت = تاریخ امضا؛ مدت قرارداد خالی است و کارفرما امضا نکرده"),
	]),
	# Two contracts on the sheet: a morning shift and an evening shift.
	("سمیرا قادری جوان", "0927441983", "09399629924", "پاسداران ۸", None, [
		("پرسنل آشپزخانه", "1405/06/09", "1405/12/09", "08:00", "13:30", None, 200000000, 9, "1405/06/09",
			"فرضی: روز پرداخت = روز شروع"),
		("پرسنل آشپزخانه", "1405/07/03", "1405/12/03", "17:00", "23:45", None, 200000000, 3, "1405/07/03",
			"فرضی: روز پرداخت = روز شروع"),
	]),
	("زینب افشره", "4421618934", "09136285093", "خ شهید بهشتی", "1386/12/02", [
		("پرسنل آشپزخانه", "1405/07/30", "1405/12/30", "08:00", "14:00", None, 150000000, 30, "1405/07/09",
			"فرضی: روز پرداخت = روز شروع"),
	]),
	("سارینا یاوری", "4421671922", "09945589955", "پاسداران", "1386/10/30", [
		("پرسنل بار / باریستا", "1405/07/10", "1405/12/10", "08:30", "16:00", None, 170000000, 10, "1405/07/09"),
	]),
]

# ------------------------------------------------------------------ ingredients

RAW, SUPPLY = "مواد اولیه", "بسته‌بندی و مصرفی"
INGREDIENTS = {
	# name: (group, stock uom, description)
	"چای خشک": (RAW, "Gram", None),
	"چای سبز": (RAW, "Gram", None),
	"دمنوش اقیانوس": (RAW, "Gram", None),
	"دمنوش ابریشم": (RAW, "Gram", None),
	"آویشن": (RAW, "Gram", None),
	"عسل": (RAW, "Gram", None),
	"یخ": (RAW, "Gram", None),
	"اسپرسو": (RAW, "Gram", "وزن اسپرسوی عصاره‌گیری‌شده در فنجان"),
	"قهوه": (RAW, "Gram", "دانه قهوه (دوز دوپیو)"),
	"قهوه ترک": (RAW, "Gram", None),
	"شیر": (RAW, "Gram", None),
	"کارامل": (RAW, "Gram", None),
	"مایع شکلات": (RAW, "Gram", "آماده‌سازی ۱/۵: نارگیل ۲۵ گرم، پودر هات چاکلت ۲۵۰ گرم، نوتلا ۹۰ گرم، فندق ۴۵ گرم، نمک ۲ گرم."),
	"ماچا": (RAW, "Gram", None),
	"شیر نارگیل": (RAW, "Millilitre", None),
	"آب انبه": (RAW, "Millilitre", None),
	"بستنی": (RAW, "Gram", None),
	"شکلات": (RAW, "Gram", None),
	"شکر": (RAW, "Gram", None),
	"فندق": (RAW, "Gram", None),
	"گردو": (RAW, "Gram", None),
	"کرک": (RAW, "Gram", "پودر/مخلوط کرک"),
	"دمنوش آفرینش": (RAW, "Gram", None),
	"دمنوش پراگ": (RAW, "Gram", None),
	"سودا": (RAW, "Millilitre", None),
	"لیمو": (RAW, "Gram", "آب لیمو یا سیروپ لیمو"),
	"ماسالا": (RAW, "Gram", None),
	"وایت چاکلت": (RAW, "Gram", None),
	"نسکافه": (RAW, "Gram", None),
	"نبات": (SUPPLY, "Nos", None),
	"قند": (SUPPLY, "Nos", None),
	"دستمال": (SUPPLY, "Nos", None),
	"کوکی": (SUPPLY, "Nos", None),
	"نی": (SUPPLY, "Nos", None),
	# Resold as bought: the cost is the purchase price of one unit.
	"آب معدنی (بطری)": (SUPPLY, "Nos", "خرید آماده؛ هر بطری"),
	"چیزکیک نیویورکی (آماده)": (SUPPLY, "Nos", "فرضی: آماده خریداری می‌شود؛ هر برش"),
	"تارت (آماده)": (SUPPLY, "Nos", "فرضی: آماده خریداری می‌شود؛ هر عدد"),
	"فرضیه (آماده)": (SUPPLY, "Nos", "فرضی: آماده خریداری می‌شود؛ هر عدد"),
	"موس کیک شکلاتی (آماده)": (SUPPLY, "Nos", "فرضی: آماده خریداری می‌شود؛ هر عدد"),
	"چوب دارچین": (SUPPLY, "Nos", None),
	"لیمو ترش": (RAW, "Nos", "هر عدد"),
	"سیروپ ایریش": (RAW, "Gram", None),
	"سیروپ فندق": (RAW, "Gram", None),
	"سیروپ نارگیل": (RAW, "Gram", None),
}
UNIT = {"Gram": "گرم", "Millilitre": "میلی‌لیتر", "Nos": "عدد"}

# ------------------------------------------------------------------ recipes

def K(name, thousand_toman, note=None):
	"""A kitchen-sheet row: fixed cost per serving in thousand toman."""
	return {"ingredient_name": name, "fixed_cost": thousand_toman * 1000 * 10, "note": note}


def Q(name, qty=None, note=None):
	"""A quantity row priced from the ingredient's purchase price; water stays free text."""
	if name == "آب":
		return {"ingredient_name": "آب", "qty": qty, "unit": "میلی‌لیتر" if qty else None, "note": note}
	uom = INGREDIENTS[name][1]
	return {"ingredient_name": name, "ingredient": name, "qty": qty, "unit": UNIT[uom], "note": note}


SERVE = [Q("دستمال", 1), Q("کوکی", 1)]
SERVE_STRAW = SERVE + [Q("نی", 1)]
TEA = [Q("نبات", 1), Q("قند", 1), Q("دستمال", 1)]
NO_QTY = "مقدار در رسپی نیامده"

RECIPES = [
	# (menu item codes, recipe as written on the sheet, notes, rows)
	# Food rows as typed by the owner from the kitchen sheet on 2026-10-06.
	(["SEPAND-3-147"], "سیر و استیک", None, [
		K("خمیر", 80), K("سس کف", 50), K("گوشت", 250), K("مخلفات", 20), K("پنیر", 50), K("سس", 45)]),
	(["SEPAND-3-149"], "چیکن پستو (شام)", "جمع نوشته‌شده روی برگه ۳۷۵ ولی جمع اقلام ۳۷۰ هزار تومان است.", [
		K("خمیر", 80), K("سس کف", 50), K("مرغ", 110), K("مخلفات", 35), K("پنیر", 50), K("سس", 45)]),
	(["SEPAND-3-144"], "پاستا چیکن آلفردو", None, [
		K("خمیر", 60), K("سس", 110), K("مرغ", 140), K("پنیر", 25), K("سمیو", 5, "نام روی برگه خوانا نیست")]),
	(["SEPAND-3-145"], "پاستا چیکن پستو", None, [
		K("خمیر", 60), K("سس", 85), K("مرغ", 140), K("پنیر", 25), K("سمیو", 5, "نام روی برگه خوانا نیست")]),

	(["SEPAND-3-64"], "چای", None, [Q("چای خشک", 2), Q("آب", 300), *TEA]),
	(["SEPAND-3-125"], "چای سبز", None, [Q("چای سبز", 2), Q("آب", 300), *TEA]),
	(["SEPAND-3-68"], "اقیانوس", None, [Q("دمنوش اقیانوس", 2.5), Q("آب", 300), *TEA]),
	(["SEPAND-3-106"], "آفرینش", None, [Q("دمنوش آفرینش", 20), Q("آب", 270, "آب‌جوش"), *TEA]),
	(["SEPAND-3-67"], "پراگ", None, [Q("دمنوش پراگ", 2.5), Q("آب", 300), *TEA]),
	(["SEPAND-3-105"], "ابریشم", None, [Q("دمنوش ابریشم", 2.5), Q("آب", 300), *TEA]),
	(["SEPAND-3-120"], "آویشن عسل لیمو", None, [Q("عسل", 30), Q("لیمو", 15, "آب‌لیمو"), Q("آویشن", 3), Q("دستمال", 1)]),

	# Drinks as dictated by the café on 2026-10-06 (voice messages), replacing the sheet reading.
	(["SEPAND-3-31", "SEPAND-3-32"], "آیس آمریکانو", None, [Q("یخ", 130), Q("آب", 120), Q("اسپرسو", 35), *SERVE_STRAW]),
	(["SEPAND-3-33", "SEPAND-3-34"], "آیس لته", "یخ: صوتی ۴۰، برگه ۱۲۰؛ برگه گذاشته شد.", [Q("یخ", 120), Q("اسپرسو", 32, "فرضی: مقدار در رسپی نیامده؛ مثل لته ۳۲ گرم"), Q("شیر", 120), *SERVE_STRAW]),
	(["SEPAND-3-96", "SEPAND-3-97"], "آیس لته کارامل", None, [Q("کارامل", 30), Q("اسپرسو", 32, "فرضی: مقدار در رسپی نیامده؛ مثل لته ۳۲ گرم"), Q("شیر", 90), *SERVE_STRAW]),
	(["SEPAND-3-35", "SEPAND-3-36"], "آیس موکا", "شیر: صوتی ۵۰، برگه ۱۵۰؛ برگه گذاشته شد.", [Q("مایع شکلات", 70, "هات چاکلت"), Q("شیر", 150), Q("اسپرسو", 32, "فرضی: مقدار در رسپی نیامده؛ مثل لته ۳۲ گرم"), *SERVE_STRAW]),
	(["SEPAND-3-41", "SEPAND-3-42"], "کن هیلو", None, [Q("یخ", 100), Q("اسپرسو", 35, "فرضی: اسپرسو دبل ۳۵ گرم"), *SERVE]),
	(["SEPAND-3-37", "SEPAND-3-38"], "تونیک", None, [Q("یخ", 140), Q("سودا", 120), Q("لیمو", 15), Q("اسپرسو", 32, "فرضی: مقدار در رسپی نیامده؛ مثل لته ۳۲ گرم"), *SERVE_STRAW]),
	(["SEPAND-3-161"], "ماچا لته", None, [Q("ماچا", 2), Q("آب", 30, "آب‌جوش"), Q("شیر", 250), *SERVE]),
	(["SEPAND-3-157"], "آیس کوکو ماچا", "شیر نارگیل: صوتی ۴۰؛ ۱۴۰ گذاشته شد.", [
		Q("یخ", 140), Q("شیر نارگیل", 140), Q("ماچا", 2), Q("آب", 30, "آب‌جوش"), *SERVE_STRAW]),
	(["SEPAND-3-160"], "منگو ماچا", None, [Q("یخ", 140), Q("آب انبه", 140), Q("ماچا", 2), Q("آب", 130, "آب‌جوش"), *SERVE_STRAW]),
	(["SEPAND-158"], "هانی ماچا", None, [Q("عسل", 30), Q("ماچا", 2), Q("آب", 3, "آب‌جوش"), Q("شیر", 200)]),
	(["SEPAND-3-39", "SEPAND-3-40"], "آفوگاتو", None, [Q("بستنی", 160), Q("اسپرسو", 30), *SERVE]),

	(["SEPAND-3-2"], "دوپیو ۸۰/۲۰", None, [Q("قهوه", 18, "شات اسپرسو"), Q("آب", 200), *SERVE]),
	(["SEPAND-3-1"], "دوپیو ۱۰۰", None, [Q("قهوه", 18, "شات اسپرسو"), Q("آب", 200), Q("دستمال", 1)]),
	(["SEPAND-3-5"], "قهوه ترک", "قهوه: صوتی ۱۴، برگه ۲۴؛ برگه گذاشته شد.", [
		Q("قهوه ترک", 24), Q("آب", 20), Q("شکلات", 80), Q("شکر", 5, "فرضی: مقدار در رسپی نیامده"), Q("دستمال", 1)]),
	(["SEPAND-3-8"], "هات چاکلت (فندق)", None, [Q("مایع شکلات", 60), Q("شیر", 180), Q("فندق", 5), *SERVE]),
	(["SEPAND-3-7"], "هات چاکلت (گردو)", None, [Q("مایع شکلات", 60), Q("شیر", 180), Q("گردو", 5), *SERVE]),
	(["SEPAND-3-12"], "کرک", None, [Q("شیر", 120), Q("کرک", 30), *SERVE]),
	(["SEPAND-3-10"], "شیر شکلات", None, [Q("مایع شکلات", 115, "هات چاکلت"), Q("شیر", 80), *SERVE]),
	(["SEPAND-3-11"], "ماسالا", None, [Q("شیر", 120), Q("ماسالا", 30), *SERVE]),
	(["SEPAND-3-9"], "وایت چاکلت", None, [Q("شیر", 120), Q("وایت چاکلت", 20), *SERVE]),
	(["SEPAND-3-91"], "شیر نسکافه کارامل", None, [
		Q("نسکافه", 3), Q("آب", 20, "آب‌جوش"), Q("شیر", 220), Q("کارامل", 30), *SERVE]),
	(["SEPAND-3-14"], "شیر عسل", None, [Q("عسل", 40), Q("شیر", 270), *SERVE]),
	(["SEPAND-3-13"], "شیر نسکافه", None, [Q("نسکافه", 3), Q("آب", 20, "آب‌جوش"), Q("شیر", 220), *SERVE]),

	(["SEPAND-3-94", "SEPAND-3-95"], "کاپوچینو کارامل", None, [Q("کارامل", 30), Q("اسپرسو", 34), Q("شیر", 250), *SERVE]),
	(["SEPAND-3-88", "SEPAND-3-87"], "لته کارامل", None, [Q("کارامل", 30), Q("اسپرسو", 32), Q("شیر", 250), *SERVE]),
	(["SEPAND-3-23", "SEPAND-3-24"], "لته", None, [Q("اسپرسو", 32), Q("شیر", 250), *SERVE]),
	(["SEPAND-17", "SEPAND-3-18"], "اسپرسو ماکیاتو", None, [Q("اسپرسو", 35), Q("شیر", 80), *SERVE]),
	(["SEPAND-93", "SEPAND-3-92"], "لته ماکیاتو کارامل", None, [Q("کارامل", 30), Q("شیر", 200), Q("اسپرسو", 32), *SERVE]),
	(["SEPAND-3-15", "SEPAND-3-16"], "آمریکانو", None, [Q("آب", 150), Q("اسپرسو", 35), *SERVE]),
	(["SEPAND-21", "SEPAND-3-22"], "کاپوچینو", None, [Q("اسپرسو", 32), Q("شیر", 250), *SERVE]),
	(["SEPAND-25", "SEPAND-3-26"], "لته ماکیاتو", None, [Q("شیر", 200), Q("اسپرسو", 32), *SERVE]),
	(["SEPAND-27", "SEPAND-3-28"], "موکا", None, [Q("مایع شکلات", 70), Q("اسپرسو", 32), Q("شیر", 225), *SERVE]),
	(["SEPAND-3-62"], "چیزکیک نیویورکی", "فرضی: آماده خریداری می‌شود؛ بهای تمام‌شده = قیمت خرید", [Q("چیزکیک نیویورکی (آماده)", 1)]),
	(["SEPAND-3-61"], "تارت", "فرضی: آماده خریداری می‌شود؛ بهای تمام‌شده = قیمت خرید", [Q("تارت (آماده)", 1)]),
	(["SEPAND-3-59"], "فرضیه", "فرضی: آماده خریداری می‌شود؛ بهای تمام‌شده = قیمت خرید", [Q("فرضیه (آماده)", 1)]),
	(["SEPAND-3-121"], "موس کیک شکلاتی", "فرضی: آماده خریداری می‌شود؛ بهای تمام‌شده = قیمت خرید", [Q("موس کیک شکلاتی (آماده)", 1)]),
	(["SEPAND-3-75"], "Cookie", "همان کوکی کنار نوشیدنی‌ها", [Q("کوکی", 1)]),
	(["SEPAND-3-71"], "افزودنی کارامل", "فرضی: یک دوز ۳۰ گرمی، مثل کارامل نوشیدنی‌ها", [Q("کارامل", 30)]),
	(["SEPAND-3-74"], "افزودنی ایریش", "فرضی: یک دوز ۳۰ گرمی، مثل کارامل نوشیدنی‌ها", [Q("سیروپ ایریش", 30)]),
	(["SEPAND-3-73"], "افزودنی فندق", "فرضی: یک دوز ۳۰ گرمی، مثل کارامل نوشیدنی‌ها", [Q("سیروپ فندق", 30)]),
	(["SEPAND-3-81"], "افزودنی نارگیل", "فرضی: یک دوز ۳۰ گرمی، مثل کارامل نوشیدنی‌ها", [Q("سیروپ نارگیل", 30)]),
	(["SEPAND-3-118"], "چوب دارچین", None, [Q("چوب دارچین", 1)]),
	(["SEPAND-3-119"], "اسلایس لیمو", "فرضی: یک‌هشتم لیمو", [Q("لیمو ترش", 0.125)]),
	(["SEPAND-3-82"], "آب معدنی", "کالای آماده؛ بهای تمام‌شده همان قیمت خرید یک بطری است.", [Q("آب معدنی (بطری)", 1)]),
	(["SEPAND-3-20", "SEPAND-3-19"], "کورتادو", None, [Q("اسپرسو", 32), Q("شیر", 200, "۱۴۰ گرم داخل لیوان"), *SERVE]),
	(["SEPAND-3-6"], "قهوه یونانی", "قهوه: صوتی ۳، برگه ۲۴؛ برگه گذاشته شد.", [Q("قهوه ترک", 24), Q("آب", 20), Q("شیر", 250), Q("شکر", 5, "فرضی: مقدار در رسپی نیامده"), *SERVE]),
]

# On the sheets but not on the menu.
UNMATCHED = ["ساندویچ مرغ", "ساندویچ گوشت", "ساندویچ بیکن پستو", "آیس چاکلت", "آیس لته ماچا"]

# Dictated on 2026-10-06 but not on the menu.
PENDING_DRINKS = {
	"آیس چاکلت": [Q("مایع شکلات", 110, "هات چاکلت"), Q("شیر", 40), *SERVE_STRAW],
	"آیس لته ماچا": [Q("ماچا", 2), Q("آب", 30, "آب‌جوش"), Q("یخ", 140), Q("شیر", 140), *SERVE_STRAW],
}

# Sandwich costs typed by the owner (2026-10-06). The menu has no sandwich item
# with a price yet; attach these once the owner names the matching menu items.
PENDING_SANDWICHES = {
	"مرغ": [K("سس کف", 35), K("نون", 80), K("سس کنار", 45), K("پنیر", 35), K("مایع", 65)],
	"بیکن پستو": [K("نون", 80), K("سس کنار", 45), K("سس کف", 51), K("بیکن", 200), K("مایع مخلفات", 35), K("پارمسان", 30), K("پنیر", 20)],
	"گوشت": [K("سس کف", 30), K("سس کنار", 45), K("سیر", 30, "مالک: «فکر کنم ۳۰»"), K("مایع", 145), K("نون", 80)],
}

BUYERS = [
	("restaurant.buyer@onecafe.beyondex.one", "مدیر خرید رستوران", RESTAURANT_BUYER, "BUYER_PW_RESTAURANT"),
	("cafe.buyer@onecafe.beyondex.one", "مدیر خرید کافه", CAFE_BUYER, "BUYER_PW_CAFE"),
]


def _check():
	problems = []
	groups = set(frappe.get_all("Item Group", pluck="name"))
	for codes, _label, _notes, _rows in RECIPES:
		for code in codes:
			group = frappe.db.get_value("Item", code, "item_group")
			if not group:
				problems.append(f"missing menu item {code}")
			elif group in (RAW, SUPPLY):
				problems.append(f"{code} is not a menu item")
	for name, (group, uom, _d) in INGREDIENTS.items():
		if group not in groups:
			problems.append(f"missing item group {group}")
		existing = frappe.db.get_value("Item", name, ["item_group", "stock_uom"], as_dict=True)
		if existing and (existing.item_group not in (RAW, SUPPLY) or existing.stock_uom != uom):
			problems.append(f"item {name} exists with group {existing.item_group} / {existing.stock_uom}")
	if problems:
		frappe.throw("\n".join(problems))


def _ingredients():
	created = []
	for name, (group, uom, description) in INGREDIENTS.items():
		if frappe.db.exists("Item", name):
			continue
		frappe.get_doc({
			"doctype": "Item",
			"item_code": name,
			"item_name": name,
			"item_group": group,
			"stock_uom": uom,
			"is_stock_item": 0,
			"is_purchase_item": 1,
			"is_sales_item": 0,
			"include_item_in_manufacturing": 0,
			"description": description or name,
		}).insert(ignore_permissions=True)
		created.append(name)
	return created


def _staff():
	created = []
	for full_name, national_id, phone, address, birth, contracts in STAFF:
		name = frappe.db.get_value("Cafe Employee", {"national_id": national_id})
		doc = frappe.get_doc("Cafe Employee", name) if name else frappe.new_doc("Cafe Employee")
		doc.update({"full_name": full_name, "national_id": national_id, "phone": phone, "address": address, "birth_date": jdate(birth), "status": "Active"})
		doc.set("contracts", [])
		for position, start, end, s_start, s_end, days, salary, pay_day, signed, *note in contracts:
			doc.append("contracts", {
				"position": position, "start_date": jdate(start), "end_date": jdate(end),
				"shift_start": s_start, "shift_end": s_end, "working_days": days,
				"monthly_salary": salary or 0, "payment_day": pay_day, "sign_date": jdate(signed),
				"note": note[0] if note else None,
			})
		doc.save(ignore_permissions=True)
		created.append(full_name)
	return created


def _recipes():
	done = []
	for codes, label, notes, rows in RECIPES:
		text = f"رسپی: {label}" + (f"\n{notes}" if notes else "")
		for code in codes:
			set_recipe(code, rows, text)
			done.append(code)
	return done


def _buyers():
	out = []
	for email, full_name, role, env in BUYERS:
		password = os.environ.get(env)
		if frappe.db.exists("User", email):
			user = frappe.get_doc("User", email)
		else:
			if not password:
				frappe.throw(f"{env} is not set")
			user = frappe.get_doc({"doctype": "User", "email": email, "first_name": full_name, "send_welcome_email": 0, "language": "fa"})
			user.flags.no_welcome_mail = True
			user.insert(ignore_permissions=True)
		user.first_name = full_name
		user.enabled = 1
		user.set("roles", [])
		user.append("roles", {"role": role})
		user.save(ignore_permissions=True)
		if password:
			update_password(email, password)
		out.append({"user": email, "type": user.user_type, "roles": [r.role for r in user.roles]})
	return out


def run(commit=0, buyers=1):
	ensure_roles()
	_check()
	result = {
		"ingredients_created": _ingredients(),
		"staff": _staff(),
		"recipes": _recipes(),
		"unmatched_recipes": UNMATCHED,
	}
	if int(buyers):
		result["buyers"] = _buyers()
	if int(commit):
		frappe.db.commit()
	else:
		frappe.db.rollback()
	result["committed"] = bool(int(commit))
	print(frappe.as_json(result))
