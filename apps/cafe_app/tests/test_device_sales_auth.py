import hashlib
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


class DeviceSalesAuthTest(unittest.TestCase):
    def setUp(self):
        self.token = "a" * 64
        self.device_id = hashlib.sha256(self.token.encode()).hexdigest()
        self.device_enabled = True
        self.user_enabled = True
        self.owner = "Administrator"
        self.header = self.token
        self.frappe = frappe = types.ModuleType("frappe")
        frappe._ = lambda text: text
        frappe.AuthenticationError = PermissionError
        frappe.PermissionError = PermissionError
        frappe.whitelist = lambda **_kwargs: lambda function: function
        frappe.session = types.SimpleNamespace(user="Guest")
        frappe.get_request_header = lambda name: self.header
        frappe.get_roles = lambda user=None: []
        frappe.throw = lambda message, exception=ValueError: (_ for _ in ()).throw(exception(message))
        frappe.set_user = lambda user: setattr(frappe.session, "user", user)
        frappe.db = types.SimpleNamespace(get_value=self.get_value, set_value=Mock())
        utils = types.ModuleType("frappe.utils")
        utils.flt = float
        utils.now_datetime = lambda: "2026-09-28 20:00:00"
        pos = types.ModuleType("cafe_app.api.pos")
        pos.build_pos_invoice = Mock()
        cafe_utils = types.ModuleType("cafe_app.utils")
        cafe_utils.MENU_ROOT = "Menu"
        cafe_utils.get_cafe_settings = Mock()
        modules = {"frappe": frappe, "frappe.utils": utils, "cafe_app.api.pos": pos, "cafe_app.utils": cafe_utils}
        self.modules = patch.dict(sys.modules, modules)
        self.modules.start()
        self.addCleanup(self.modules.stop)
        self.remote = self.load("desktop_remote")
        sys.modules["cafe_app.api.desktop_remote"] = self.remote
        self.sales = self.load("sepehryar")

    def load(self, name):
        path = Path(__file__).resolve().parents[1] / "cafe_app" / "api" / (name + ".py")
        spec = importlib.util.spec_from_file_location("test_" + name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def get_value(self, doctype, name, field, **_kwargs):
        if doctype == "Cafe Desktop Device" and name == self.device_id:
            if field == "enrolled_by": return self.owner
            return types.SimpleNamespace(name=self.device_id, enabled=self.device_enabled)
        if doctype == "User": return self.user_enabled
        return None

    def test_boot_without_panel_session_returns_no_panel_credentials(self):
        response = self.sales.device_boot()
        self.assertEqual(response, {"ready": True, "device_id": self.device_id, "products_disabled": True})
        self.assertEqual(self.frappe.session.user, "Guest")
        self.frappe.db.set_value.assert_not_called()

    def test_device_token_required_even_when_panel_is_signed_in(self):
        self.frappe.session.user = "Administrator"
        for header in [None, "", "b" * 64, "a" * 63, "A" * 64]:
            with self.subTest(header=header):
                self.header = header
                with self.assertRaises(PermissionError): self.sales.device_boot()

    def test_revoked_device_disabled_owner_and_removed_role_are_denied(self):
        self.device_enabled = False
        with self.assertRaises(PermissionError): self.sales.device_boot()
        self.device_enabled = True
        self.user_enabled = False
        with self.assertRaises(PermissionError): self.sales.device_boot()
        self.user_enabled = True
        self.owner = "cashier"
        with self.assertRaises(PermissionError): self.sales.device_boot()

    def test_import_does_not_leave_a_manager_session_even_after_failure(self):
        def import_probe(invoices):
            self.assertEqual(self.frappe.session.user, "Administrator")
            raise ValueError("Invalid sale")
        self.sales.import_sales = import_probe
        with self.assertRaisesRegex(ValueError, "Invalid sale"):
            self.sales.device_import_sales([])
        self.assertEqual(self.frappe.session.user, "Guest")


if __name__ == "__main__":
    unittest.main()
