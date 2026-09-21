import frappe
from frappe.utils import add_months, flt, get_first_day, get_last_day, getdate, nowdate

from cafe_app.utils import get_cafe_settings, get_mode_of_payment_account, period_range


@frappe.whitelist()
def overview(period="month", from_date=None, to_date=None):
	company = get_cafe_settings().company
	start, end, _prev_start, _prev_end = period_range(period, from_date, to_date)

	totals = _totals_by_root_type(company, start, end)
	cogs = _cogs(company, start, end)
	income = totals.get("Income", 0)
	expense = totals.get("Expense", 0)

	return {
		"range": {"from": start, "to": end},
		"income": income,
		"cogs": cogs,
		"gross_profit": income - cogs,
		"operating_expenses": expense - cogs,
		"net_profit": income - expense,
		"expenses_by_account": _expenses_by_account(company, start, end),
		"balances": balances(company),
		"monthly": _monthly(company),
	}


def _totals_by_root_type(company, start, end):
	rows = frappe.db.sql(
		"""
		select acc.root_type, sum(gle.debit) debit, sum(gle.credit) credit
		from `tabGL Entry` gle join `tabAccount` acc on acc.name = gle.account
		where gle.is_cancelled = 0 and gle.company = %(company)s and acc.root_type in ('Income', 'Expense')
			and gle.posting_date between %(start)s and %(end)s
		group by acc.root_type
		""",
		{"company": company, "start": start, "end": end},
		as_dict=True,
	)
	return {
		r.root_type: flt(r.credit - r.debit) if r.root_type == "Income" else flt(r.debit - r.credit) for r in rows
	}


def _cogs(company, start, end):
	return flt(
		frappe.db.sql(
			"""
			select sum(gle.debit - gle.credit)
			from `tabGL Entry` gle join `tabAccount` acc on acc.name = gle.account
			where gle.is_cancelled = 0 and gle.company = %(company)s and acc.account_type = 'Cost of Goods Sold'
				and gle.posting_date between %(start)s and %(end)s
			""",
			{"company": company, "start": start, "end": end},
		)[0][0]
	)


# Persian names for the English accounts ERPNext's standard chart creates.
ACCOUNT_LABELS = {
	"Stock Adjustment": "تعدیل و ضایعات انبار",
	"Round Off": "گرد کردن مبالغ",
	"Write Off": "سوخت مطالبات",
	"Exchange Gain/Loss": "سود و زیان تسعیر ارز",
	"Cash": "صندوق نقدی",
}


def _expenses_by_account(company, start, end):
	"""Operating expenses by account; cost of goods sold is reported separately."""
	rows = frappe.db.sql(
		"""
		select acc.account_name, gle.account, sum(gle.debit - gle.credit) amount
		from `tabGL Entry` gle join `tabAccount` acc on acc.name = gle.account
		where gle.is_cancelled = 0 and gle.company = %(company)s and acc.root_type = 'Expense'
			and coalesce(acc.account_type, '') != 'Cost of Goods Sold'
			and gle.posting_date between %(start)s and %(end)s
		group by gle.account, acc.account_name
		having amount != 0
		order by amount desc
		""",
		{"company": company, "start": start, "end": end},
		as_dict=True,
	)
	for row in rows:
		row.account_name = ACCOUNT_LABELS.get(row.account_name, row.account_name)
	return rows


def balances(company):
	return frappe.db.sql(
		"""
		select acc.name account, acc.account_name, acc.account_type, coalesce(sum(gle.debit - gle.credit), 0) balance
		from `tabAccount` acc
		left join `tabGL Entry` gle on gle.account = acc.name and gle.is_cancelled = 0
		where acc.company = %(company)s and acc.is_group = 0 and acc.account_type in ('Cash', 'Bank')
		group by acc.name, acc.account_name, acc.account_type
		order by acc.account_type, acc.account_name
		""",
		{"company": company},
		as_dict=True,
	)


def _monthly(company, months=6):
	result = []
	today = getdate(nowdate())
	for offset in range(months - 1, -1, -1):
		month_start = get_first_day(add_months(today, -offset))
		month_end = get_last_day(month_start)
		totals = _totals_by_root_type(company, month_start, month_end)
		income, expense = totals.get("Income", 0), totals.get("Expense", 0)
		result.append({"month": month_start, "income": income, "expense": expense, "profit": income - expense})
	return result


@frappe.whitelist()
def expense_accounts():
	company = get_cafe_settings().company
	return frappe.get_all(
		"Account",
		filters={"company": company, "root_type": "Expense", "is_group": 0, "disabled": 0, "account_type": ["not in", ["Cost of Goods Sold", "Stock Adjustment", "Depreciation", "Round Off"]]},
		fields=["name", "account_name"],
		order_by="account_name",
	)


@frappe.whitelist()
def record_expense(account, amount, mode_of_payment="Cash", posting_date=None, note=None):
	"""Pay an operating expense (rent, salaries, bills…) from cash or card account."""
	settings = get_cafe_settings()
	amount = flt(amount)
	company_cost_center = frappe.get_cached_value("Company", settings.company, "cost_center")

	entry = frappe.get_doc(
		{
			"doctype": "Journal Entry",
			"voucher_type": "Journal Entry",
			"company": settings.company,
			"posting_date": posting_date or nowdate(),
			"user_remark": note,
			"accounts": [
				{"account": account, "debit_in_account_currency": amount, "cost_center": company_cost_center},
				{
					"account": get_mode_of_payment_account(mode_of_payment, settings.company),
					"credit_in_account_currency": amount,
					"cost_center": company_cost_center,
				},
			],
		}
	)
	entry.insert()
	entry.submit()
	return entry.name


@frappe.whitelist()
def list_expenses(limit=50):
	company = get_cafe_settings().company
	return frappe.db.sql(
		"""
		select je.name, je.posting_date, je.user_remark, jea.account, acc.account_name, jea.debit amount, je.owner
		from `tabJournal Entry` je
		join `tabJournal Entry Account` jea on jea.parent = je.name
		join `tabAccount` acc on acc.name = jea.account
		where je.docstatus = 1 and je.company = %(company)s and acc.root_type = 'Expense' and jea.debit > 0
		order by je.posting_date desc, je.creation desc
		limit %(limit)s
		""",
		{"company": company, "limit": int(limit)},
		as_dict=True,
	)
