"""VPS-only HTTP smoke test; no orders, no secrets in output, probe revoked."""
import hashlib
import secrets

import frappe
import requests


def verify():
    base = "https://onecafe.beyondex.one/api/method/"
    token = secrets.token_hex(32)
    device_id = hashlib.sha256(token.encode()).hexdigest()
    device = frappe.get_doc({
        "doctype": "Cafe Desktop Device", "token_hash": device_id,
        "machine_name": "SALES-AUTH-PROBE", "app_version": "0.3.1-test",
        "enrolled_by": "Administrator", "enabled": 1,
    }).insert(ignore_permissions=True)
    frappe.db.commit()
    result = {}
    headers = {"X-OneCafe-Device-Token": token, "User-Agent": "ONECAFE/0.3.1 device-sync-probe"}
    try:
        boot = requests.post(base + "cafe_app.api.sepehryar.device_boot", headers=headers, json={}, timeout=20)
        result["device_boot_without_browser_login"] = boot.status_code
        assert boot.status_code == 200 and boot.json()["message"]["ready"]
        sales = requests.post(base + "cafe_app.api.sepehryar.device_import_sales", headers=headers, json={"invoices": []}, timeout=20)
        result["empty_sales_without_browser_login"] = sales.status_code
        assert sales.status_code == 200 and sales.json()["message"] == {"created": [], "skipped": []}
        result["no_panel_credentials_issued"] = all(
            response.cookies.get("user_id") != "Administrator" and response.cookies.get("sid") in (None, "Guest")
            for response in [boot, sales]
        )
        assert result["no_panel_credentials_issued"]
        denied = requests.post(base + "cafe_app.api.sepehryar.device_boot", json={}, timeout=20)
        result["missing_token_denied"] = denied.status_code
        assert denied.status_code == 401
        frappe.db.set_value("Cafe Desktop Device", device.name, "enabled", 0)
        frappe.db.commit()
        revoked = requests.post(base + "cafe_app.api.sepehryar.device_boot", headers=headers, json={}, timeout=20)
        result["revoked_device_denied"] = revoked.status_code
        assert revoked.status_code == 401
        return result
    finally:
        frappe.db.set_value("Cafe Desktop Device", device.name, "enabled", 0)
        frappe.db.commit()
