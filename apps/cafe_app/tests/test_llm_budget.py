"""Run standalone with python -m unittest apps/cafe_app/tests/test_llm_budget.py."""

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


class FakeCache:
    def __init__(self):
        self.used = 0

    def eval(self, _script, _keys, _key, amount, limit=None):
        if limit is None:
            # usage correction after a reported response
            self.used += int(amount)
            return 1
        if self.used + int(amount) > int(limit):
            return 0
        self.used += int(amount)
        return 1


class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "choices": [{"message": {"content": "سلام", "role": "assistant"}, "finish_reason": "stop"}],
            "usage": {"total_tokens": 900},
        }


class BudgetTest(unittest.TestCase):
    def test_model_request_is_bounded_and_stops_at_daily_cap(self):
        cache = FakeCache()
        sent = []
        frappe = types.ModuleType("frappe")
        frappe.conf = {
            "ai_api_key": "test-only",
            "ai_model": "gpt-6-luna",
            "ai_daily_token_limit": 300000,
        }
        frappe.cache = cache
        frappe.local = types.SimpleNamespace(site="test")
        frappe.throw = lambda message: (_ for _ in ()).throw(RuntimeError(message))
        frappe_utils = types.ModuleType("frappe.utils")
        frappe_utils.nowdate = lambda: "2026-09-27"
        frappe_utils.getdate = lambda value: __import__("datetime").date.fromisoformat(value)
        requests = types.ModuleType("requests")
        requests.RequestException = RuntimeError
        requests.post = lambda *_args, **kwargs: sent.append(kwargs) or FakeResponse()
        tools = types.ModuleType("cafe_app.agent.tools")
        tools.toolset = lambda: ([], {})
        agent = types.ModuleType("cafe_app.agent")
        agent.tools = tools
        access = types.ModuleType("cafe_app.access")
        access.SCOPE_LABELS = {}
        access.buyer_scopes = lambda: ()
        jalali_source = Path(__file__).resolve().parents[1] / "cafe_app" / "jalali.py"
        jalali_spec = importlib.util.spec_from_file_location("cafe_jalali_under_test", jalali_source)
        jalali = importlib.util.module_from_spec(jalali_spec)
        jalali_spec.loader.exec_module(jalali)

        modules = {
            "frappe": frappe,
            "frappe.utils": frappe_utils,
            "requests": requests,
            "cafe_app": types.ModuleType("cafe_app"),
            "cafe_app.agent": agent,
            "cafe_app.agent.tools": tools,
            "cafe_app.access": access,
            "cafe_app.jalali": jalali,
        }
        source = Path(__file__).resolve().parents[1] / "cafe_app" / "agent" / "llm.py"
        with patch.dict(sys.modules, modules):
            spec = importlib.util.spec_from_file_location("cafe_llm_under_test", source)
            llm = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(llm)

            self.assertFalse(llm.configured(), "A stored key alone must not enable business-data export")
            frappe.conf["ai_enabled"] = "true"
            self.assertTrue(llm.configured())

            self.assertEqual(llm.run("سلام", [])["text"], "سلام")
            self.assertEqual(len(sent), 1)
            self.assertEqual(sent[0]["json"]["model"], "gpt-6-luna")
            self.assertEqual(sent[0]["json"]["reasoning_effort"], "none")
            self.assertEqual(sent[0]["json"]["max_completion_tokens"], 1000)
            # the byte-based reservation is replaced by the reported usage
            self.assertEqual(cache.used, 900)

            self.assertEqual(llm.inspect_media("این چیست؟", "sample.png", "image/png", b"test"), "سلام")
            self.assertEqual(sent[1]["json"]["messages"][1]["content"][1]["type"], "image_url")
            self.assertEqual(cache.used, 1800, "Media reservation should settle to reported usage")

            frappe.conf["ai_daily_token_limit"] = cache.used
            with self.assertRaisesRegex(RuntimeError, "سقف مصرف"):
                llm.run("سلام دوباره", [])
            self.assertEqual(len(sent), 2, "No network request after budget exhaustion")


if __name__ == "__main__":
    unittest.main()
