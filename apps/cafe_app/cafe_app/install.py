import frappe
from frappe.utils.nestedset import get_root_of

# Top-level item groups a café needs. Ingredients are stock items; menu items are
# non-stock items whose Product Bundle (recipe) deducts the ingredients on sale.
CAFE_ITEM_GROUPS = {
	"مواد اولیه": 0,
	"بسته‌بندی و مصرفی": 0,
	"منوی کافه": 1,
}
MENU_SUB_GROUPS = ("نوشیدنی گرم", "نوشیدنی سرد", "کیک و دسر", "غذا و میان‌وعده")


def after_install():
	# Fresh sites run the setup wizard later; setup_wizard_complete handles those.
	if get_root_of("Item Group"):
		create_cafe_item_groups()


def setup_wizard_complete(args=None):
	create_cafe_item_groups()


def create_cafe_item_groups():
	root = get_root_of("Item Group")
	if not root:
		return

	for name, is_group in CAFE_ITEM_GROUPS.items():
		_ensure_item_group(name, root, is_group)

	for name in MENU_SUB_GROUPS:
		_ensure_item_group(name, "منوی کافه")


def _ensure_item_group(name, parent, is_group=0):
	if frappe.db.exists("Item Group", name):
		return

	frappe.get_doc(
		{
			"doctype": "Item Group",
			"item_group_name": name,
			"parent_item_group": parent,
			"is_group": is_group,
		}
	).insert(ignore_permissions=True)
