import frappe
from frappe import _
from frappe.utils import cint, flt

from cafe_app.utils import MENU_ROOT, get_cafe_settings, ingredient_groups, menu_groups


@frappe.whitelist()
def get_groups():
	return {"menu": menu_groups()[1:], "ingredients": ingredient_groups()}


@frappe.whitelist()
def list_menu():
	settings = get_cafe_settings()
	items = frappe.get_all(
		"Item",
		filters={"item_group": ["in", menu_groups()]},
		fields=["item_code", "item_name", "item_group", "image", "description", "disabled"],
		order_by="item_group asc, item_name asc",
	)
	codes = [i.item_code for i in items] or [""]
	prices = dict(
		frappe.get_all(
			"Item Price",
			filters={"price_list": settings.price_list, "item_code": ["in", codes]},
			fields=["item_code", "price_list_rate"],
			as_list=True,
		)
	)
	costs = _recipe_costs(codes, settings.warehouse)

	for item in items:
		item.rate = flt(prices.get(item.item_code))
		item.has_recipe = item.item_code in costs
		item.cost = flt(costs.get(item.item_code))
		item.margin = (item.rate - item.cost) / item.rate * 100 if item.rate else 0
	return items


@frappe.whitelist()
def get_menu_item(item_code):
	settings = get_cafe_settings()
	item = frappe.get_doc("Item", item_code)
	recipe = []
	if frappe.db.exists("Product Bundle", {"new_item_code": item_code}):
		bundle = frappe.get_doc("Product Bundle", {"new_item_code": item_code})
		rates = _valuation_rates([r.item_code for r in bundle.items], settings.warehouse)
		recipe = [
			{
				"item_code": r.item_code,
				"item_name": frappe.get_cached_value("Item", r.item_code, "item_name"),
				"qty": r.qty,
				"uom": r.uom or frappe.get_cached_value("Item", r.item_code, "stock_uom"),
				"rate": flt(rates.get(r.item_code)),
			}
			for r in bundle.items
		]

	return {
		"item_code": item.item_code,
		"item_name": item.item_name,
		"item_group": item.item_group,
		"description": item.description,
		"image": item.image,
		"disabled": item.disabled,
		"rate": flt(
			frappe.db.get_value("Item Price", {"item_code": item_code, "price_list": settings.price_list}, "price_list_rate")
		),
		"recipe": recipe,
	}


@frappe.whitelist()
def save_menu_item(data):
	"""Create or update a menu item together with its selling price and recipe (Product Bundle)."""
	data = frappe._dict(frappe.parse_json(data))
	settings = get_cafe_settings()

	# Items are named after their title, so saving an existing name updates it instead of colliding.
	existing = data.item_code or data.item_name
	if existing and frappe.db.exists("Item", existing):
		item = frappe.get_doc("Item", existing)
	else:
		item = frappe.new_doc("Item")
		item.item_code = data.item_name
		item.is_stock_item = 0
		item.stock_uom = "Nos"
		item.include_item_in_manufacturing = 0

	item.update(
		{
			"item_name": data.item_name,
			"item_group": data.item_group or MENU_ROOT,
			"description": data.description,
			"image": data.image,
			"disabled": cint(data.disabled),
			"is_sales_item": 1,
		}
	)
	item.save()

	_set_price(item.name, settings.price_list, flt(data.rate))
	_set_recipe(item.name, data.recipe or [])
	return get_menu_item(item.name)


@frappe.whitelist()
def list_ingredients():
	settings = get_cafe_settings()
	return frappe.db.sql(
		"""
		select i.item_code, i.item_name, i.item_group, i.stock_uom, i.safety_stock, i.disabled,
			coalesce(b.actual_qty, 0) actual_qty,
			coalesce(nullif(b.valuation_rate, 0), i.valuation_rate, 0) valuation_rate,
			coalesce(b.stock_value, 0) stock_value
		from `tabItem` i
		left join `tabBin` b on b.item_code = i.item_code and b.warehouse = %(warehouse)s
		where i.item_group in %(groups)s
		order by i.item_group, i.item_name
		""",
		{"warehouse": settings.warehouse, "groups": ingredient_groups()},
		as_dict=True,
	)


@frappe.whitelist()
def save_ingredient(data):
	data = frappe._dict(frappe.parse_json(data))
	existing = data.item_code or data.item_name
	if existing and frappe.db.exists("Item", existing):
		item = frappe.get_doc("Item", existing)
	else:
		item = frappe.new_doc("Item")
		item.item_code = data.item_name
		item.is_stock_item = 1
		item.stock_uom = data.stock_uom or "Gram"
		item.is_sales_item = 0

	item.update(
		{
			"item_name": data.item_name,
			"item_group": data.item_group or ingredient_groups()[0],
			"safety_stock": flt(data.safety_stock),
			"valuation_rate": flt(data.valuation_rate) or item.valuation_rate,
			"disabled": cint(data.disabled),
			"is_purchase_item": 1,
		}
	)
	item.save()
	return item.name


def _set_price(item_code, price_list, rate):
	name = frappe.db.get_value("Item Price", {"item_code": item_code, "price_list": price_list}, "name")
	if name:
		frappe.db.set_value("Item Price", name, "price_list_rate", rate)
	elif rate:
		# Item Price defaults valid_from to today, which hides the price from back-dated sales.
		frappe.get_doc(
			{
				"doctype": "Item Price",
				"item_code": item_code,
				"price_list": price_list,
				"price_list_rate": rate,
				"valid_from": "2000-01-01",
			}
		).insert()


def _set_recipe(item_code, recipe):
	rows = [r for r in recipe if r.get("item_code") and flt(r.get("qty")) > 0]
	existing = frappe.db.get_value("Product Bundle", {"new_item_code": item_code}, "name")

	if not rows:
		if existing:
			frappe.delete_doc("Product Bundle", existing)
		return

	bundle = frappe.get_doc("Product Bundle", existing) if existing else frappe.new_doc("Product Bundle")
	bundle.new_item_code = item_code
	bundle.set("items", [])
	for r in rows:
		bundle.append(
			"items",
			{
				"item_code": r["item_code"],
				"qty": flt(r["qty"]),
				"uom": frappe.get_cached_value("Item", r["item_code"], "stock_uom"),
			},
		)
	bundle.save()


def _valuation_rates(item_codes, warehouse):
	if not item_codes:
		return {}
	rows = frappe.db.sql(
		"""
		select i.item_code, coalesce(nullif(b.valuation_rate, 0), i.valuation_rate, 0) rate
		from `tabItem` i left join `tabBin` b on b.item_code = i.item_code and b.warehouse = %(warehouse)s
		where i.item_code in %(codes)s
		""",
		{"codes": item_codes, "warehouse": warehouse},
	)
	return dict(rows)


def _recipe_costs(item_codes, warehouse):
	rows = frappe.db.sql(
		"""
		select pb.new_item_code, pbi.item_code, pbi.qty
		from `tabProduct Bundle` pb join `tabProduct Bundle Item` pbi on pbi.parent = pb.name
		where pb.new_item_code in %(codes)s and pb.disabled = 0
		""",
		{"codes": item_codes},
		as_dict=True,
	)
	rates = _valuation_rates(list({r.item_code for r in rows}), warehouse)
	costs = {}
	for r in rows:
		costs[r.new_item_code] = costs.get(r.new_item_code, 0) + flt(r.qty) * flt(rates.get(r.item_code))
	return costs
