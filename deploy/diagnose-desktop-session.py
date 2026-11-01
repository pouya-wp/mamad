"""Run inside an initialized bench console; print only non-secret test results."""
import json
import secrets
import time

import frappe
import requests

from cafe_app.api.session import DESKTOP_COOKIE, DESKTOP_LIFETIME, _encode, _sign

base = "https://onecafe.beyondex.one"
client = requests.Session()
client.headers["User-Agent"] = "ONECAFE/0.2.1 desktop-auth-recovery-test"
payload = _encode(json.dumps({"u": "Administrator", "e": int(time.time()) + DESKTOP_LIFETIME, "n": secrets.token_hex(12)}, separators=(",", ":")).encode())
client.cookies.set(DESKTOP_COOKIE, payload + "." + _sign(payload), domain="onecafe.beyondex.one", path="/", secure=True)
client.cookies.set("sid", secrets.token_hex(24), domain="onecafe.beyondex.one", path="/")

first = client.get(base + "/api/method/cafe_app.api.session.boot", timeout=20)
second = client.get(base + "/api/method/cafe_app.api.session.boot", timeout=20)
csrf = second.json().get("message", {}).get("csrf_token", "")
headers = {"X-Frappe-CSRF-Token": csrf}
sales = client.post(base + "/api/method/cafe_app.api.sepehryar.import_sales", json={"invoices": []}, headers=headers, timeout=20)
result = {"restore_from_expired_sid": first.status_code, "subsequent_boot": second.status_code, "empty_sales": sales.status_code, "device_cookie_retained": bool(client.cookies.get(DESKTOP_COOKIE))}
logout = client.post(base + "/api/method/logout", headers=headers, timeout=20)
result["logout"] = logout.status_code
result["boot_after_logout"] = client.get(base + "/api/method/cafe_app.api.session.boot", timeout=20).status_code
result["device_cookie_removed_by_logout"] = not bool(client.cookies.get(DESKTOP_COOKIE))
print(json.dumps(result, sort_keys=True))
