"""Source menu identities verified from the café's warehouse-3 SQL catalog."""

import json
from pathlib import Path

VERIFIED_MENU_NAMES = json.loads(
	Path(__file__).with_name("sepehryar-menu-1405.json").read_text(encoding="utf-8")
)

# These ID-only labels were reported as implausible, and the original source
# warehouse was not stored with historical invoice lines. Keep their amounts
# intact while making the uncertainty explicit to the reader.
UNVERIFIED_LEGACY_ITEMS = {"SEPAND-32", "SEPAND-64"}


def display_item_name(item_code, item_name):
	if item_code in UNVERIFIED_LEGACY_ITEMS and (item_name or "").strip() != VERIFIED_MENU_NAMES.get(item_code.split("-", 1)[1]):
		return f"کالای سپهریار {item_code.split('-', 1)[1]} (نام تأییدنشده)"
	return item_name


def is_source_menu_item(item_code):
	"""Hide raw-material warehouse entries without deleting the item master."""
	if not item_code.startswith("SEPAND-"):
		return True
	parts = item_code.split("-")
	if len(parts) == 2:
		return parts[1] in VERIFIED_MENU_NAMES
	return len(parts) == 3 and parts[1] == "3"
