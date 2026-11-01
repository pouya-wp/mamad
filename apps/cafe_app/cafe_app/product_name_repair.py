"""One-time, server-side repair for product names exported directly from SepandYar.

Run with bench execute. Preview is the default; only apply=True changes data.
The source database and desktop application are never modified by this module.
"""

import json
from pathlib import Path

import frappe


def _garbled(name):
	name = (name or "").strip()
	return name.startswith("SEPAND-") or name.count("?") >= 2


def _clean_name(value):
	name = str(value or "").strip()
	if not name or len(name) > 140 or "?" in name or not any(char.isalpha() for char in name):
		return None
	if any(ord(char) < 32 for char in name):
		return None
	return name


def repair_from_file(path, apply=False, include_invoice_items=False):
	"""Preview or update garbled SEPAND item labels from a UTF-8 JSON export.

	Only item_name fields are changed. Prices, quantities, recipes, and stock are untouched.
	Invoice item labels are optional because they are historical document snapshots.
	"""
	if isinstance(apply, str):
		apply = apply.lower() in {"1", "true", "yes"}
	if isinstance(include_invoice_items, str):
		include_invoice_items = include_invoice_items.lower() in {"1", "true", "yes"}
	products = json.loads(Path(path).read_text(encoding="utf-8-sig"))
	if not isinstance(products, list):
		raise ValueError("Expected a JSON array of products")
	if len(products) > 10000:
		raise ValueError("Product export is unexpectedly large")

	mapping = {}
	for product in products:
		source_id = int(product["sourceItemId"])
		if source_id <= 0:
			raise ValueError("Invalid sourceItemId")
		name = _clean_name(product.get("name"))
		if not name:
			continue
		if source_id in mapping and mapping[source_id] != name:
			raise ValueError(f"Conflicting names for source item {source_id}")
		mapping[source_id] = name

	plan = []
	missing = 0
	preserved = 0
	for source_id, name in sorted(mapping.items()):
		code = f"SEPAND-{source_id}"
		current = frappe.db.get_value("Item", code, "item_name")
		if current is None:
			missing += 1
		elif current == name or not _garbled(current):
			preserved += 1
		else:
			plan.append((code, current, name))

	if apply:
		for code, _old, name in plan:
			frappe.db.set_value("Item", code, "item_name", name, update_modified=False)
			if include_invoice_items:
				frappe.db.sql(
					"""UPDATE `tabSales Invoice Item`
					SET item_name = %s
					WHERE item_code = %s AND item_name LIKE %s""",
					(name, code, "%?%"),
				)
		frappe.db.commit()
		frappe.clear_cache(doctype="Item")

	return {
		"exported": len(products),
		"valid_names": len(mapping),
		"to_repair": len(plan),
		"missing_on_server": missing,
		"preserved_existing": preserved,
		"applied": bool(apply),
		"sample": [{"code": code, "old": old, "new": name} for code, old, name in plan[:10]],
	}


def audit_names():
	"""Read-only verification of current catalog and historical sale snapshots."""
	counts = frappe.db.sql(
		"""SELECT
			(SELECT COUNT(*) FROM `tabItem` WHERE item_code LIKE 'SEPAND-%'),
			(SELECT COUNT(*) FROM `tabItem` WHERE item_code LIKE 'SEPAND-%' AND item_name LIKE '%?%'),
			(SELECT COUNT(*) FROM `tabSales Invoice Item` WHERE item_code LIKE 'SEPAND-%'),
			(SELECT COUNT(*) FROM `tabSales Invoice Item` WHERE item_code LIKE 'SEPAND-%' AND item_name LIKE '%?%'),
			(SELECT COUNT(*) FROM `tabSales Invoice Item` sii
			 JOIN `tabItem` i ON i.name = sii.item_code
			 WHERE sii.item_code LIKE 'SEPAND-%' AND sii.item_name <> i.item_name)"""
	)[0]
	rows = frappe.db.sql(
		"""SELECT sii.item_code, sii.item_name, sii.parent, i.item_name AS current_name
		FROM `tabSales Invoice Item` sii
		LEFT JOIN `tabItem` i ON i.name = sii.item_code
		WHERE sii.item_code LIKE 'SEPAND-%'
		ORDER BY sii.creation DESC LIMIT 5""",
		as_dict=True,
	)
	latest_import = frappe.db.sql(
		"""SELECT name, creation, posting_date, posting_time
		FROM `tabSales Invoice`
		WHERE remarks LIKE '%[Sepand:1405:%'
		ORDER BY creation DESC LIMIT 1""",
		as_dict=True,
	)
	return {
		"source_items": counts[0],
		"garbled_items": counts[1],
		"historical_order_rows": counts[2],
		"garbled_order_rows": counts[3],
		"order_rows_different_from_current_item": counts[4],
		"recent_order_rows": rows,
		"latest_import": latest_import[0] if latest_import else None,
	}
