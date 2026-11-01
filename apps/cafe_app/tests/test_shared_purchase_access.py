"""Standalone permission checks for the two shared purchase desks."""

import datetime as dt
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1] / "cafe_app"


class SharedPurchaseAccessTest(unittest.TestCase):
    def setUp(self):
        self.roles = {
            "restaurant": ["Restaurant Purchase Manager", "Cafe Purchase Manager"],
            "cafe": ["Restaurant Purchase Manager", "Cafe Purchase Manager"],
            "single": ["Cafe Purchase Manager"],
            "admin": ["System Manager"],
        }
        self.calls = []
        frappe = types.ModuleType("frappe")
        frappe.PermissionError = PermissionError
        frappe._ = lambda message: message
        frappe.session = types.SimpleNamespace(user="restaurant")
        frappe.get_roles = lambda user=None: self.roles.get(user or frappe.session.user, [])
        frappe.throw = lambda message, error=ValueError: (_ for _ in ()).throw(error(message))
        frappe.whitelist = lambda: lambda fn: fn
        frappe.get_all = self.get_all
        frappe.db = types.SimpleNamespace(sql=lambda query, values=None, as_dict=False: self.calls.append((query, values)) or [])
        frappe.request = types.SimpleNamespace(path="/api/method/cafe_app.api.purchasing.calendar_month")
        frappe.form_dict = {}
        utils = types.ModuleType("frappe.utils")
        utils.add_days = lambda day, count: day + dt.timedelta(days=count)
        utils.date_diff = lambda end, start: (end - start).days
        utils.flt = float
        utils.getdate = lambda value: value if isinstance(value, dt.date) else dt.date.fromisoformat(value)
        utils.nowdate = lambda: "2026-10-21"
        cafe = types.ModuleType("cafe_app")
        api = types.ModuleType("cafe_app.api")
        buyer_activity = types.ModuleType("cafe_app.api.buyer_activity")
        buyer_activity.purchase_snapshot = lambda _doc: {}
        buyer_activity.log = lambda *_args, **_kwargs: None
        api.buyer_activity = buyer_activity
        cafe_utils = types.ModuleType("cafe_app.utils")
        cafe_utils.ingredient_groups = lambda: ()
        modules = {"frappe": frappe, "frappe.utils": utils, "cafe_app": cafe,
                   "cafe_app.api": api, "cafe_app.api.buyer_activity": buyer_activity,
                   "cafe_app.utils": cafe_utils}
        self.modules = patch.dict(sys.modules, modules)
        self.modules.start()
        self.fr = frappe
        self.access = self.load("cafe_app.access", ROOT / "access.py")
        sys.modules["cafe_app.access"] = self.access
        self.purchasing = self.load("cafe_app.api.purchasing", ROOT / "api" / "purchasing.py")

    def tearDown(self):
        self.modules.stop()

    def load(self, name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def get_all(self, doctype, **kwargs):
        self.calls.append((doctype, kwargs))
        if doctype == "Cafe Purchase" and "purchase_date" in kwargs.get("filters", {}):
            return [types.SimpleNamespace(name="P1", scope="Cafe", supplier="vendor", total=1000, purchase_date=dt.date(2026, 10, 21))]
        return []

    def test_both_accounts_have_both_desks_without_manager_access(self):
        for user in ("restaurant", "cafe"):
            self.fr.session.user = user
            self.assertEqual(self.access.buyer_scopes(), ("Restaurant", "Cafe"))
            self.assertFalse(self.access.is_manager())
            self.assertTrue(self.access.can_edit_recipes())
            self.assertEqual(self.purchasing._scope_for_write("Restaurant"), "Restaurant")
            self.assertEqual(self.purchasing._scope_for_write("Cafe"), "Cafe")
            self.fr.request.path = "/api/method/cafe_app.api.menu.save_recipe"
            self.access.restrict_buyers()
            with self.assertRaises(PermissionError):
                self._restricted_manager_api()

    def _restricted_manager_api(self):
        self.fr.request.path = "/api/method/cafe_app.api.daybook.month"
        self.access.restrict_buyers()

    def test_single_desk_stays_limited(self):
        self.fr.session.user = "single"
        self.assertEqual(self.purchasing._scope_for_write(None), "Cafe")
        with self.assertRaises(PermissionError):
            self.purchasing._scope_for_write("Restaurant")
        with self.assertRaises(PermissionError):
            self.purchasing.list_purchases(scope="Restaurant")

    def test_buyer_calendar_contains_only_purchase_data(self):
        days = self.purchasing.calendar_month("2026-10-21", "2026-10-22")
        self.assertEqual(len(days["2026-10-21"]["purchases"]), 1)
        self.assertIsNone(days["2026-10-21"]["sales"])
        self.assertEqual(days["2026-10-21"]["expenses"], [])
        self.assertEqual(days["2026-10-21"]["cheques"], [])
        self.assertEqual(days["2026-10-21"]["events"], [])
        self.assertEqual(self.calls[-1][1]["filters"]["scope"], ["in", ("Restaurant", "Cafe")])


if __name__ == "__main__":
    unittest.main()
