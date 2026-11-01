"""Read-only: which menu items are fully costed, which recipes still lack prices, which have no recipe.

    bench --site frontend execute cafe_app.maintenance.recipe_cost_report.run
"""

import frappe
from frappe.utils import flt

from cafe_app.api import menu
from cafe_app.recipes import get_recipe


def run():
	items = menu.list_menu()
	priced, unpriced, missing = [], [], []
	needs = {}
	for item in items:
		row = {"code": item.item_code, "name": item.item_name, "group": item.item_group, "rate_toman": round(flt(item.rate) / 10)}
		if not item.has_recipe:
			missing.append(row)
			continue
		if not item.unpriced:
			priced.append({**row, "cost_toman": round(item.cost / 10)})
			continue
		gaps = []
		for r in get_recipe(item.item_code)["rows"]:
			if r["cost"] is None:
				gaps.append(r["ingredient_name"] if r["qty"] else f"{r['ingredient_name']} (بدون مقدار)")
				if r["qty"]:
					needs.setdefault(r["ingredient_name"], set()).add(item.item_name)
		unpriced.append({**row, "missing": gaps})

	print(frappe.as_json({
		"priced": priced,
		"unpriced": unpriced,
		"no_recipe": missing,
		"ingredient_prices_needed": {k: len(v) for k, v in sorted(needs.items(), key=lambda kv: -len(kv[1]))},
	}))
