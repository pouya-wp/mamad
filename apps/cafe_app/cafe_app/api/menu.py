import frappe
from frappe import _
from frappe.utils import cint, flt

from cafe_app import recipes
from cafe_app.access import buyer_scopes, is_manager, require_manager, require_recipe_access
from cafe_app.api import buyer_activity
from cafe_app.source_catalog import UNVERIFIED_LEGACY_ITEMS, is_source_menu_item
from cafe_app.utils import MENU_ROOT, get_cafe_settings, ingredient_groups, menu_groups


@frappe.whitelist()
def get_groups():
	return {"menu": menu_groups()[1:], "ingredients": ingredient_groups()}


def _hide_money(item):
	"""A purchase manager keeps the recipes; what a dish costs and earns is not theirs."""
	for field in ("rate", "cost", "margin", "unpriced"):
		item.pop(field, None)
	return item


@frappe.whitelist()
def list_menu():
	settings = get_cafe_settings()
	items = frappe.get_all(
		"Item",
		filters={"item_group": ["in", menu_groups()]},
		fields=["item_code", "item_name", "item_group", "image", "description", "disabled"],
		order_by="item_group asc, item_name asc",
	)
	# Once an exact warehouse variant is observed, hide the older ID-only entry
	# whose catalog name may belong to a different SepandYar warehouse.
	variant_ids = {
		i.item_code.rsplit("-", 1)[1]
		for i in items
		if i.item_code.startswith("SEPAND-") and i.item_code.count("-") == 2
	}
	items = [
		i for i in items
		if is_source_menu_item(i.item_code) and i.item_code not in UNVERIFIED_LEGACY_ITEMS and not (
			i.item_code.startswith("SEPAND-")
			and i.item_code.count("-") == 1
			and i.item_code.split("-", 1)[1] in variant_ids
		)
	]
	codes = [i.item_code for i in items] or [""]
	prices = dict(
		frappe.get_all(
			"Item Price",
			filters={"price_list": settings.price_list, "item_code": ["in", codes]},
			fields=["item_code", "price_list_rate"],
			as_list=True,
		)
	)
	costs = recipes.recipe_costs(codes)

	for item in items:
		recipe = costs.get(item.item_code)
		item.rate = flt(prices.get(item.item_code))
		item.has_recipe = bool(recipe)
		item.cost = recipe["cost"] if recipe else 0
		item.unpriced = recipe["unpriced"] if recipe else 0
		item.margin = (item.rate - item.cost) / item.rate * 100 if item.rate else 0

	if not is_manager():
		for item in items:
			_hide_money(item)
	return items


@frappe.whitelist()
def get_menu_item(item_code):
	settings = get_cafe_settings()
	item = frappe.get_doc("Item", item_code)
	recipe = recipes.get_recipe(item_code)

	detail = {
		"item_code": item.item_code,
		"item_name": item.item_name,
		"item_group": item.item_group,
		"description": item.description,
		"image": item.image,
		"disabled": item.disabled,
		"rate": flt(
			frappe.db.get_value("Item Price", {"item_code": item_code, "price_list": settings.price_list}, "price_list_rate")
		),
		"recipe": recipe["rows"],
		"recipe_notes": recipe["notes"],
	}
	return detail if is_manager() else _hide_money(detail)


@frappe.whitelist()
def save_menu_item(data):
	"""Create or update a menu item together with its selling price and recipe."""
	require_manager()
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
	if data.recipe is not None:
		recipes.set_recipe(item.name, data.recipe, data.recipe_notes)
	return get_menu_item(item.name)


@frappe.whitelist()
def save_recipe(item_code, recipe, recipe_notes=None):
	"""Recipe-only save: the one write a restaurant purchase manager is allowed to make.

	Deliberately narrow — it touches the recipe and nothing else, so neither the
	selling price nor anything else about the item can be changed from that desk.
	"""
	require_recipe_access()
	if not frappe.db.exists("Item", item_code):
		frappe.throw(_("این آیتم پیدا نشد"))
	before = recipes.get_recipe(item_code) if buyer_scopes() else None
	recipes.set_recipe(item_code, frappe.parse_json(recipe), recipe_notes)
	if buyer_scopes():
		item_name = frappe.db.get_value("Item", item_code, "item_name") or item_code
		buyer_activity.log("recipe.update", "Item", item_code, None,
			f"ویرایش رسپی {item_name}", before=before, after=recipes.get_recipe(item_code))
	return get_menu_item(item_code)


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
