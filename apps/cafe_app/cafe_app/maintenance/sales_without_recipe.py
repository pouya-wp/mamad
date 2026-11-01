"""Read-only: products that actually sell, ranked by revenue, with their recipe status.

    bench --site frontend execute cafe_app.maintenance.sales_without_recipe.run
"""

import frappe
from frappe.utils import add_days, flt, getdate, nowdate

from cafe_app.recipes import recipe_costs
from cafe_app.source_reporting import invoice_items
from cafe_app.utils import get_cafe_settings


def run(days=0):
	settings = get_cafe_settings()
	end = getdate(nowdate())
	first = frappe.db.sql("select min(posting_date) from `tabSales Invoice` where docstatus=1 and company=%s", settings.company)[0][0]
	start = add_days(end, -int(days) + 1) if int(days) else getdate(first)

	sold = {}
	for row in invoice_items(settings.company, start, end):
		item = sold.setdefault(row["item_code"], {"code": row["item_code"], "name": row["item_name"], "group": row["item_group"], "qty": 0, "revenue": 0})
		item["qty"] += flt(row["qty"])
		item["revenue"] += flt(row["revenue"])

	costs = recipe_costs(list(sold))
	prices = dict(frappe.get_all("Item Price", filters={"price_list": settings.price_list, "item_code": ["in", list(sold) or [""]]}, fields=["item_code", "price_list_rate"], as_list=True))
	rows = []
	for code, item in sold.items():
		recipe = costs.get(code)
		item["status"] = "priced" if recipe and not recipe["unpriced"] else ("unpriced" if recipe else "none")
		item["price_toman"] = round(flt(prices.get(code)) / 10)
		item["revenue_toman"] = round(item.pop("revenue") / 10)
		rows.append(item)
	rows.sort(key=lambda r: -r["revenue_toman"])
	total = sum(r["revenue_toman"] for r in rows) or 1
	print(frappe.as_json({
		"from": str(start), "to": str(end),
		"share_no_recipe": round(sum(r["revenue_toman"] for r in rows if r["status"] == "none") / total * 100, 1),
		"rows": rows,
	}))
