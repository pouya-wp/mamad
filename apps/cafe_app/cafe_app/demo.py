"""Demo data for developing the panel: a month of One Cafe activity.

Only for development sites:  bench --site <site> execute cafe_app.demo.seed
"""

import random

import frappe
from frappe.utils import add_days, getdate, now_datetime, nowdate

from cafe_app.api.accounting import record_expense
from cafe_app.api.inventory import record_purchase, save_supplier, stock_count
from cafe_app.api.menu import save_ingredient, save_menu_item
from cafe_app.api.pos import build_pos_invoice
from cafe_app.utils import get_mode_of_payment_account

# name, group, stock uom, safety stock, cost per uom (IRR), opening qty
INGREDIENTS = [
	("دانه قهوه اسپرسو", "مواد اولیه", "Gram", 2000, 25000, 26000),
	("دانه قهوه دمی", "مواد اولیه", "Gram", 800, 22000, 6000),
	("شیر", "مواد اولیه", "Millilitre", 10000, 700, 190000),
	("خامه", "مواد اولیه", "Millilitre", 1500, 1600, 12000),
	("پودر شکلات", "مواد اولیه", "Gram", 500, 9000, 5000),
	("پودر ماچا", "مواد اولیه", "Gram", 150, 60000, 1500),
	("سیروپ کارامل", "مواد اولیه", "Millilitre", 500, 3500, 5000),
	("سیروپ وانیل", "مواد اولیه", "Millilitre", 500, 3500, 4000),
	("لیمو تازه", "مواد اولیه", "Gram", 1000, 1500, 14000),
	("نعناع تازه", "مواد اولیه", "Gram", 200, 4000, 2500),
	("شکر", "مواد اولیه", "Gram", 2000, 450, 15000),
	("یخ", "مواد اولیه", "Gram", 5000, 50, 120000),
	("خمیر پیتزا", "مواد اولیه", "Nos", 10, 180000, 120),
	("پنیر موزارلا", "مواد اولیه", "Gram", 2000, 9500, 30000),
	("پپرونی", "مواد اولیه", "Gram", 1000, 14000, 12000),
	("سس گوجه", "مواد اولیه", "Gram", 1000, 2500, 12000),
	("تخم مرغ", "مواد اولیه", "Nos", 30, 70000, 700),
	("نان تست", "مواد اولیه", "Nos", 20, 25000, 500),
	("کره", "مواد اولیه", "Gram", 500, 12000, 7000),
	("کیک شکلاتی (برش)", "مواد اولیه", "Nos", 6, 450000, 110),
	("چیزکیک (برش)", "مواد اولیه", "Nos", 6, 520000, 90),
	("لیوان کاغذی", "بسته‌بندی و مصرفی", "Nos", 100, 18000, 1200),
	("جعبه پیتزا", "بسته‌بندی و مصرفی", "Nos", 20, 45000, 150),
]

# name, group, price (toman), recipe [(ingredient, qty)], popularity weight
MENU = [
	("اسپرسو", "نوشیدنی گرم", 95000, [("دانه قهوه اسپرسو", 18)], 7),
	("آمریکانو", "نوشیدنی گرم", 110000, [("دانه قهوه اسپرسو", 18)], 8),
	("لاته", "نوشیدنی گرم", 145000, [("دانه قهوه اسپرسو", 18), ("شیر", 220)], 10),
	("کاپوچینو", "نوشیدنی گرم", 140000, [("دانه قهوه اسپرسو", 18), ("شیر", 160)], 8),
	("کارامل ماکیاتو", "نوشیدنی گرم", 165000, [("دانه قهوه اسپرسو", 18), ("شیر", 200), ("سیروپ کارامل", 20)], 6),
	("موکا", "نوشیدنی گرم", 160000, [("دانه قهوه اسپرسو", 18), ("شیر", 180), ("پودر شکلات", 20)], 5),
	("ماچا لاته", "نوشیدنی گرم", 175000, [("پودر ماچا", 4), ("شیر", 220)], 4),
	("هات چاکلت", "نوشیدنی گرم", 150000, [("پودر شکلات", 30), ("شیر", 220), ("خامه", 20)], 4),
	("دمی V60", "نوشیدنی گرم", 150000, [("دانه قهوه دمی", 15)], 3),
	("آیس لاته", "نوشیدنی سرد", 155000, [("دانه قهوه اسپرسو", 18), ("شیر", 200), ("یخ", 150)], 7),
	("آیس آمریکانو", "نوشیدنی سرد", 120000, [("دانه قهوه اسپرسو", 18), ("یخ", 180)], 5),
	("لیموناد", "نوشیدنی سرد", 130000, [("لیمو تازه", 80), ("شکر", 25), ("یخ", 180)], 5),
	("موهیتو", "نوشیدنی سرد", 150000, [("لیمو تازه", 60), ("نعناع تازه", 8), ("شکر", 20), ("یخ", 200)], 5),
	("آیس وانیل کافه", "نوشیدنی سرد", 165000, [("دانه قهوه اسپرسو", 18), ("شیر", 180), ("سیروپ وانیل", 20), ("یخ", 150)], 3),
	("کیک شکلاتی", "کیک و دسر", 140000, [("کیک شکلاتی (برش)", 1)], 5),
	("چیزکیک", "کیک و دسر", 160000, [("چیزکیک (برش)", 1)], 4),
	("پیتزا پپرونی", "غذا و میان‌وعده", 420000, [("خمیر پیتزا", 1), ("پنیر موزارلا", 120), ("پپرونی", 70), ("سس گوجه", 60)], 4),
	("پیتزا مارگاریتا", "غذا و میان‌وعده", 360000, [("خمیر پیتزا", 1), ("پنیر موزارلا", 150), ("سس گوجه", 70)], 3),
	("صبحانه انگلیسی", "غذا و میان‌وعده", 320000, [("تخم مرغ", 2), ("نان تست", 2), ("کره", 15)], 3),
	("املت", "غذا و میان‌وعده", 210000, [("تخم مرغ", 3), ("سس گوجه", 80), ("نان تست", 1)], 3),
]

SUPPLIERS = [("رست قهوه یزد", "09130000001"), ("لبنیات پگاه", "09130000002"), ("پخش مواد غذایی فرساد", "09130000003")]

MONTHLY_EXPENSES = [("اجاره", 200_000_000), ("حقوق و دستمزد", 300_000_000)]
WEEKLY_EXPENSES = [("آب، برق و گاز", 28_000_000), ("ملزومات و شوینده", 9_000_000)]

# Busy hours of a café open 8:30-23:30, weighted toward breakfast and evening.
HOUR_WEIGHTS = {8: 2, 9: 5, 10: 6, 11: 5, 12: 4, 13: 4, 14: 3, 15: 3, 16: 4, 17: 6, 18: 8, 19: 9, 20: 9, 21: 7, 22: 4, 23: 1}


def seed(days=30):
	if frappe.db.count("Sales Invoice"):
		frappe.throw("Site already has sales; demo data is only for empty development sites.")

	random.seed(1405)
	start = add_days(getdate(nowdate()), -days)

	for name, group, uom, safety, rate, _qty in INGREDIENTS:
		save_ingredient({"item_name": name, "item_group": group, "stock_uom": uom, "safety_stock": safety, "valuation_rate": rate})
	for name, group, price, recipe, _weight in MENU:
		save_menu_item(
			{
				"item_name": name,
				"item_group": group,
				"rate": price * 10,
				"recipe": [{"item_code": code, "qty": qty} for code, qty in recipe],
			}
		)
	for supplier, mobile in SUPPLIERS:
		save_supplier(supplier, mobile)
	frappe.db.commit()

	if not frappe.db.exists("Stock Reconciliation", {"purpose": "Opening Stock", "docstatus": 1}):
		_opening_stock(add_days(start, -1))
		opening_capital(add_days(start, -1))
		frappe.db.commit()

	for offset in range(days + 1):
		day = add_days(start, offset)
		_day_activity(day, offset, is_today=offset == days)
		frappe.db.commit()
		print(f"seeded {day}")

	# Leave a few ingredients under their safety stock so the panel shows real alerts.
	stock_count(
		[{"item_code": "پودر ماچا", "qty": 90}, {"item_code": "سیروپ کارامل", "qty": 320}, {"item_code": "جعبه پیتزا", "qty": 12}],
		note="انبارگردانی",
	)
	frappe.db.commit()


def _opening_stock(posting_date):
	recon = frappe.new_doc("Stock Reconciliation")
	warehouse = frappe.db.get_value("POS Profile", {"disabled": 0}, "warehouse")
	recon.update(
		{
			"purpose": "Opening Stock",
			"set_posting_time": 1,
			"posting_date": posting_date,
			"posting_time": "07:00:00",
			"company": frappe.db.get_value("POS Profile", {"disabled": 0}, "company"),
			"expense_account": frappe.db.get_value(
				"Account", {"account_name": "Temporary Opening", "is_group": 0}, "name"
			),
		}
	)
	for name, _group, _uom, _safety, rate, qty in INGREDIENTS:
		recon.append("items", {"item_code": name, "warehouse": warehouse, "qty": qty, "valuation_rate": rate})
	recon.insert()
	recon.submit()


def opening_capital(posting_date, cash=200_000_000, bank=1_500_000_000):
	"""The owners' starting money in the cash register and the card/bank account (IRR)."""
	company = frappe.db.get_value("POS Profile", {"disabled": 0}, "company")
	cost_center = frappe.get_cached_value("Company", company, "cost_center")
	equity = frappe.db.get_value(
		"Account", {"company": company, "root_type": "Equity", "is_group": 0, "account_name": "Opening Balance Equity"}, "name"
	) or frappe.db.get_value("Account", {"company": company, "root_type": "Equity", "is_group": 0}, "name")

	entry = frappe.get_doc(
		{
			"doctype": "Journal Entry",
			"voucher_type": "Opening Entry",
			"company": company,
			"posting_date": posting_date,
			"user_remark": "سرمایه اولیه",
			"accounts": [
				{"account": get_mode_of_payment_account("Cash", company), "debit_in_account_currency": cash, "cost_center": cost_center},
				{"account": get_mode_of_payment_account("Credit Card", company), "debit_in_account_currency": bank, "cost_center": cost_center},
				{"account": equity, "credit_in_account_currency": cash + bank, "cost_center": cost_center},
			],
		}
	)
	entry.insert()
	entry.submit()
	return entry.name


def _day_activity(day, offset, is_today):
	if offset % 10 == 5:
		_restock(day)
	if day.day == 1 or offset == 0:
		for account, amount in MONTHLY_EXPENSES:
			_expense(account, amount, day)
	if offset % 7 == 3:
		for account, amount in WEEKLY_EXPENSES:
			_expense(account, amount, day)

	weekend = day.weekday() in (3, 4)  # Thursday/Friday
	orders = random.randint(14, 22) if weekend else random.randint(9, 16)
	now = now_datetime()
	names = [m[0] for m in MENU]
	weights = [m[4] for m in MENU]

	for _ in range(orders):
		hour = random.choices(list(HOUR_WEIGHTS), weights=list(HOUR_WEIGHTS.values()))[0]
		minute = random.randint(30 if hour == 8 else 0, 59)
		if is_today and (hour, minute) >= (now.hour, now.minute):
			continue

		lines = {}
		for code in random.choices(names, weights=weights, k=random.choices([1, 2, 3, 4], weights=[4, 5, 2, 1])[0]):
			lines[code] = lines.get(code, 0) + 1

		table = random.randint(1, 14)
		build_pos_invoice(
			[{"item_code": code, "qty": qty} for code, qty in lines.items()],
			[{"mode_of_payment": "Credit Card" if random.random() < 0.7 else "Cash"}],
			remarks=random.choice(["سالن", "سالن", "سالن", "بیرون‌بر"]) + f" | میز {table}",
			posting_date=day,
			posting_time=f"{hour:02d}:{minute:02d}:{random.randint(0, 59):02d}",
		)


def _restock(day):
	rate = {i[0]: i[4] for i in INGREDIENTS}
	purchases = [
		("رست قهوه یزد", [("دانه قهوه اسپرسو", 5000), ("دانه قهوه دمی", 1000)]),
		("لبنیات پگاه", [("شیر", 40000), ("خامه", 3000)]),
		("پخش مواد غذایی فرساد", [("لیوان کاغذی", 300), ("لیمو تازه", 4000), ("پنیر موزارلا", 6000)]),
	]
	for supplier, items in purchases:
		record_purchase(
			supplier,
			[{"item_code": code, "qty": qty, "rate": rate[code]} for code, qty in items],
			mode_of_payment="Credit Card",
			posting_date=day,
		)


def _expense(account_name, amount, day):
	account = frappe.db.get_value("Account", {"account_name": account_name, "is_group": 0}, "name")
	record_expense(account, amount, mode_of_payment="Cash", posting_date=day, note=account_name)
