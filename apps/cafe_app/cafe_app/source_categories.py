"""Menu categories read from the café's warehouse-3 SepandYar catalog."""
import json
from pathlib import Path

from cafe_app.utils import MENU_ROOT

SOURCE_MENU_GROUPS = json.loads(
	Path(__file__).with_name("sepehryar-menu-groups-1405.json").read_text(encoding="utf-8")
)


def source_item_group(source_id, warehouse_id=None):
	if warehouse_id is not None and int(warehouse_id) != 3:
		return MENU_ROOT
	return SOURCE_MENU_GROUPS.get(str(int(source_id)), MENU_ROOT)


def source_code_group(item_code):
	parts = item_code.split("-")
	if parts[0] != "SEPAND":
		return None
	if len(parts) == 2 and parts[1] in SOURCE_MENU_GROUPS:
		return source_item_group(parts[1])
	if len(parts) == 3 and parts[1] == "3" and parts[2] in SOURCE_MENU_GROUPS:
		return source_item_group(parts[2], 3)
	return None
