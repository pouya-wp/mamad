"""Verify diagnostic privacy and that logging cannot grant or break access."""
import importlib.util
import json
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


class DesktopAuthDiagnosticsTest(unittest.TestCase):
    def load_session(self):
        frappe = types.ModuleType("frappe")
        frappe.conf = {"cafe_desktop_signing_key": "private-test-key"}
        frappe.request = types.SimpleNamespace(cookies={"sid": "private-test-sid", "one_cafe_device": "invalid-private-test-cookie"})
        frappe.local = types.SimpleNamespace(request_ip="127.0.0.1")
        frappe.session = types.SimpleNamespace(user="Guest")
        frappe.get_request_header = lambda _name: "ONECAFE/0.2.1"
        frappe._ = lambda text: text
        frappe.whitelist = lambda **_kwargs: lambda function: function
        frappe.AuthenticationError = PermissionError
        frappe.throw = Mock(side_effect=PermissionError("Not logged in"))
        logger = Mock()
        frappe.logger = Mock(return_value=logger)
        sessions = types.ModuleType("frappe.sessions")
        sessions.get_csrf_token = Mock()
        setup = types.ModuleType("cafe_app.cafe_setup")
        setup.ensure_cafe_defaults = Mock()
        utils = types.ModuleType("cafe_app.utils")
        utils.get_cafe_settings = Mock()
        access = types.ModuleType("cafe_app.access")
        access.SCOPE_LABELS = {}
        access.buyer_scope = lambda: None
        access.buyer_scopes = lambda: ()
        with patch.dict(sys.modules, {"frappe": frappe, "frappe.sessions": sessions, "cafe_app": types.ModuleType("cafe_app"), "cafe_app.access": access, "cafe_app.cafe_setup": setup, "cafe_app.utils": utils}):
            path = Path(__file__).resolve().parents[1] / "cafe_app" / "api" / "session.py"
            spec = importlib.util.spec_from_file_location("session_diagnostic_test", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        return module, frappe, logger

    def test_invalid_credentials_remain_denied_without_logging_secrets(self):
        module, frappe, logger = self.load_session()
        with self.assertRaises(PermissionError):
            module.boot()
        message = logger.error.call_args.args[0]
        report = json.loads(message)
        self.assertTrue(report["sid_present"])
        self.assertTrue(report["device_cookie_present"])
        self.assertFalse(report["device_cookie_valid"])
        for secret in ["private-test-sid", "invalid-private-test-cookie", "private-test-key"]:
            self.assertNotIn(secret, message)
        self.assertEqual(frappe.session.user, "Guest")

    def test_logging_failure_preserves_authentication_error(self):
        module, frappe, logger = self.load_session()
        frappe.request.cookies = {}
        logger.error.side_effect = OSError("Log disk unavailable")
        with self.assertRaisesRegex(PermissionError, "Not logged in"):
            module.boot()
        self.assertEqual(frappe.session.user, "Guest")


if __name__ == "__main__":
    unittest.main()
