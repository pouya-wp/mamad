"""Menu item recipes and their cost.

A recipe row is an ingredient with either a fixed cost per serving (the
kitchen's own costing, e.g. «نون ۸۰ هزار تومان») or a quantity that is priced
from the ingredient's latest purchase price. Recipes only cost a product; they
never move stock, so sales imported from the till are unaffected.
"""

import frappe
from frappe.utils import flt

from cafe_app.api.purchasing import unit_factor

ROW_FIELDS = ("ingredient_name", "ingredient", "qty", "unit", "fixed_cost", "note")


def _ingredient_info(codes):
	if not codes:
		return {}
	return {
		r.name: r
		for r in frappe.get_all(
			"Item", filters={"name": ["in", list(codes)]}, fields=["name", "item_name", "stock_uom", "valuation_rate"]
		)
	}


def price_row(row, info):
	"""Rial cost of one recipe row for one serving, or None when it cannot be priced yet."""
	if flt(row.get("fixed_cost")) > 0:
		return flt(row["fixed_cost"])
	if not row.get("ingredient"):
		# A free-text row without a cost (e.g. water) costs nothing.
		return 0.0
	item = info.get(row.get("ingredient"))
	if not item or flt(row.get("qty")) <= 0 or flt(item.valuation_rate) <= 0:
		return None
	factor = unit_factor(row.get("unit"), item.stock_uom)
	return flt(row["qty"]) * factor * flt(item.valuation_rate) if factor else None


def recipe_costs(item_codes):
	"""{menu item: {"cost", "rows", "unpriced"}} for the items that have a recipe."""
	if not item_codes:
		return {}
	rows = frappe.db.sql(
		"""
		select parent, ingredient, qty, unit, fixed_cost
		from `tabCafe Recipe Row`
		where parenttype = 'Cafe Recipe' and parent in %(codes)s
		""",
		{"codes": list(item_codes)},
		as_dict=True,
	)
	info = _ingredient_info({r.ingredient for r in rows if r.ingredient})
	costs = {}
	for r in rows:
		entry = costs.setdefault(r.parent, {"cost": 0.0, "rows": 0, "unpriced": 0})
		value = price_row(r, info)
		entry["rows"] += 1
		if value is None:
			entry["unpriced"] += 1
		else:
			entry["cost"] += value
	return costs


def get_recipe(item_code):
	if not frappe.db.exists("Cafe Recipe", item_code):
		return {"rows": [], "notes": None}
	doc = frappe.get_doc("Cafe Recipe", item_code)
	info = _ingredient_info({r.ingredient for r in doc.rows if r.ingredient})
	rows = []
	for r in doc.rows:
		row = {f: r.get(f) for f in ROW_FIELDS}
		item = info.get(r.ingredient)
		row["stock_uom"] = item.stock_uom if item else None
		row["unit_price"] = flt(item.valuation_rate) if item else 0
		row["cost"] = price_row(row, info)
		rows.append(row)
	return {"rows": rows, "notes": doc.notes}


def set_recipe(item_code, rows, notes=None):
	"""Replace the recipe of a menu item; an empty recipe removes it. Touches nothing else on the item."""
	clean = []
	for r in rows or []:
		r = frappe._dict(r)
		name = (r.ingredient_name or "").strip()
		if r.ingredient and not name:
			name = frappe.db.get_value("Item", r.ingredient, "item_name")
		if not name:
			continue
		clean.append({
			"ingredient_name": name,
			"ingredient": r.ingredient or None,
			"qty": flt(r.qty) or None,
			"unit": (r.unit or "").strip() or None,
			"fixed_cost": flt(r.fixed_cost) or None,
			"note": r.note,
		})

	exists = frappe.db.exists("Cafe Recipe", item_code)
	if not clean:
		if exists:
			frappe.delete_doc("Cafe Recipe", item_code, ignore_permissions=True)
		return

	doc = frappe.get_doc("Cafe Recipe", item_code) if exists else frappe.new_doc("Cafe Recipe")
	doc.item = item_code
	doc.notes = notes
	doc.set("rows", clean)
	doc.save(ignore_permissions=True)
