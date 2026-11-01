"""CLI-only source category repair; never changes names, prices or accounting."""
import json
from collections import Counter
from pathlib import Path

import frappe

from cafe_app.install import create_cafe_item_groups
from cafe_app.source_categories import SOURCE_MENU_GROUPS, source_code_group


def classify(report_path, apply=False):
	if len(SOURCE_MENU_GROUPS) != 128:
		raise ValueError("Unexpected verified menu size")
	items, rows = [], []
	for item in frappe.get_all("Item", filters={"item_code": ["like", "SEPAND-%"]},
							 fields=["name", "item_code", "item_group"]):
		expected = source_code_group(item.item_code)
		if expected and expected != item.item_group:
			items.append({"name": item.name, "old": item.item_group, "new": expected})
	for row in frappe.get_all("Sales Invoice Item", filters={"item_code": ["like", "SEPAND-%"]},
							fields=["name", "parent", "item_code", "item_group"]):
		expected = source_code_group(row.item_code)
		if expected and expected != row.item_group:
			rows.append({"name": row.name, "parent": row.parent, "old": row.item_group, "new": expected})
	report = {"items": items, "invoice_rows": rows, "source_categories": dict(Counter(SOURCE_MENU_GROUPS.values())), "applied": bool(apply)}
	path = Path(report_path)
	path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
	path.chmod(0o600)
	if apply:
		create_cafe_item_groups()
		for item in items:
			frappe.db.set_value("Item", item["name"], "item_group", item["new"], update_modified=False)
		for row in rows:
			frappe.db.set_value("Sales Invoice Item", row["name"], "item_group", row["new"], update_modified=False)
		frappe.db.commit()
		frappe.clear_cache(doctype="Item")
	return {"items": len(items), "invoice_rows": len(rows), "source_categories": report["source_categories"], "applied": bool(apply)}
