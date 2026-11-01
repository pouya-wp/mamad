"""Smoke-test the live One Cafe panel API without printing credentials."""

import json
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import HTTPCookieProcessor, Request, build_opener


BASE = "https://onecafe.beyondex.one"
opener = build_opener(HTTPCookieProcessor(CookieJar()))
csrf_token = None


def call(path, payload=None):
    body = json.dumps(payload).encode() if payload is not None else None
    request = Request(
        BASE + path,
        data=body,
        headers={
            "Content-Type": "application/json",
            **({"X-Frappe-CSRF-Token": csrf_token} if csrf_token else {}),
        } if body is not None else {},
    )
    try:
        with opener.open(request, timeout=30) as response:
            return json.load(response)
    except HTTPError as error:
        raise RuntimeError(f"{path}: HTTP {error.code}: {error.read(400).decode(errors='replace')}") from error


password = Path("/root/one-cafe-admin-password").read_text().strip()
call("/api/method/login", {"usr": "Administrator", "pwd": password})
boot = call("/api/method/cafe_app.api.session.boot")["message"]
csrf_token = boot["csrf_token"]
print("login: ok")
print("company:", boot["cafe"]["company"])
print("user:", boot["user"]["name"])

# The installed desktop connector still sends a catalog batch before orders.
# This must acknowledge it without adding or editing products.
before = call("/api/method/cafe_app.api.menu.list_menu")["message"]
probe_code = "SEPAND-2147483000"
assert all(item["item_code"] != probe_code for item in before)
catalog_result = call(
    "/api/method/cafe_app.api.sepehryar.sync_products",
    {"products": [{"sourceItemId": 2147483000, "name": "Catalog sync must be disabled"}]},
)["message"]
assert catalog_result == {"created": [], "existing": [], "disabled": True}
after = call("/api/method/cafe_app.api.menu.list_menu")["message"]
assert len(after) == len(before) and all(item["item_code"] != probe_code for item in after)
print("product sync: acknowledged without catalog writes")

empty_sales = call("/api/method/cafe_app.api.sepehryar.import_sales", {"invoices": []})["message"]
assert empty_sales == {"created": [], "skipped": []}
print("sales sync: endpoint operational")

orders = call("/api/method/cafe_app.api.orders.list_orders")["message"]
source_order = next((order for order in orders if "[Sepand:" in (order.get("remarks") or "")), None)
if source_order:
    detail = call("/api/method/cafe_app.api.orders.get_order?name=" + quote(source_order["name"]))["message"]
    assert detail["items"] and all("?" not in item["item_name"] for item in detail["items"])
    print("historical order detail: correct item labels")

for method in (
    "cafe_app.api.dashboard.summary",
    "cafe_app.api.dashboard.pulse",
    "cafe_app.api.menu.get_groups",
    "cafe_app.api.menu.list_menu",
    "cafe_app.api.menu.list_ingredients",
    "cafe_app.api.pos.get_menu",
    "cafe_app.api.pos.current_shift",
    "cafe_app.api.pos.list_shifts",
    "cafe_app.api.orders.list_orders",
    "cafe_app.api.inventory.movements",
    "cafe_app.api.inventory.list_purchases",
    "cafe_app.api.inventory.list_suppliers",
    "cafe_app.api.accounting.overview",
    "cafe_app.api.accounting.list_expenses",
    "cafe_app.api.accounting.expense_accounts",
    "cafe_app.api.agent.status",
    "cafe_app.api.agent.insights",
):
    call("/api/method/" + method)
    print(method + ": ok")

print("agent mode:", call("/api/method/cafe_app.api.agent.status")["message"]["mode"])
