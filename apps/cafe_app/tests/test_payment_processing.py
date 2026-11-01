import base64
import gzip
import importlib.util
import json
import sys
import types
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1] / "cafe_app"


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PaymentProcessingTest(unittest.TestCase):
    def setUp(self):
        self.device = "a" * 64
        self.job = types.SimpleNamespace(name="job1", device=self.device, purpose="source_payments_v1", status="Succeeded",
            processed_at=None, started_at=datetime(2026, 9, 29, 12), creation=datetime(2026, 9, 29, 12), script="FactorID IN (23702)")
        report = {"version": 1, "machine": "DESKTOP-GCTP2FH", "database": "Sepand_One_1405", "sets": [
            [{"f": 23702, "total": 1000, "closed": True, "account_verified": True, "account_balance": 3500, "unallocated_receipts": 500}],
            [{"f": 23702, "method": 99, "amount": 1000}], [{"id": 1, "name": "پوز ملت"}]]}
        self.job.stdout = "GZIP:" + base64.b64encode(gzip.compress(json.dumps(report).encode())).decode()
        frappe = types.ModuleType("frappe")
        frappe.conf = {"source_payment_device": self.device}
        frappe.db = types.SimpleNamespace(get_value=self.value, set_value=Mock())
        frappe.get_doc = lambda doctype, name: self.job
        frappe.get_roles = lambda user: []
        utils = types.ModuleType("frappe.utils")
        utils.now_datetime = lambda: datetime(2026, 9, 29, 12, 1)
        utils.get_datetime = lambda value: value if isinstance(value, datetime) else datetime.fromisoformat(value)
        self.frappe = frappe
        modules = {"frappe": frappe, "frappe.utils": utils, "cafe_app.payment_truth": load("payment_truth")}
        self.modules = patch.dict(sys.modules, modules)
        self.modules.start()
        self.addCleanup(self.modules.stop)
        self.payments = load("source_payments")

    def value(self, doctype, name, field):
        if doctype == "Cafe Desktop Device":
            return "Administrator" if field == "enrolled_by" else 1
        if doctype == "User":
            return 1
        if doctype == "Cafe Source Payment":
            return datetime(2026, 9, 29, 11)

    def test_unallocated_balance_updates_not_null_sql_and_preserves_unknown_json(self):
        result = self.payments.process_job("job1")
        self.assertEqual(result["applied"], 1)
        calls = self.frappe.db.set_value.call_args_list
        snapshot = next(call.args[2] for call in calls if call.args[0] == "Cafe Source Payment")
        self.assertEqual(snapshot["outstanding"], 0)
        self.assertIsNone(json.loads(snapshot["methods_json"])["outstanding"])
        self.assertTrue(all(call.args[0] in ("Cafe Source Payment", "Cafe Desktop Job") for call in calls))

    def test_processed_result_is_idempotent(self):
        self.job.processed_at = datetime(2026, 9, 29, 12, 1)
        self.assertEqual(self.payments.process_job("job1"), {"applied": 0})
        self.frappe.db.set_value.assert_not_called()

    def test_unrequested_factor_fails_before_any_write(self):
        self.job.script = "FactorID IN (23703)"
        with self.assertRaises(ValueError):
            self.payments.process_job("job1")
        self.frappe.db.set_value.assert_not_called()

    def test_result_from_other_device_is_denied(self):
        self.job.device = "b" * 64
        with self.assertRaises(ValueError):
            self.payments.process_job("job1")
        self.frappe.db.set_value.assert_not_called()

    def source_v3(self, account='110:4:8'):
        report = self.payments.decode_report(self.job.stdout)
        report['version'] = 3
        report['sets'][0][0].update(customer_id=10, customer_name='طاها بورقی', account_key=account)
        report['sets'][2][0]['account_name'] = 'پوز ملت'
        report['sets'].append([{'f': 23702, 'w': 3, 'k': 32, 'name': 'آمریکانو', 'qty': 1, 'amount': 1000}])
        self.job.stdout = 'GZIP:' + base64.b64encode(gzip.compress(json.dumps(report,ensure_ascii=False).encode('utf-8'))).decode()

    def test_v3_preserves_customer_identity_items_and_account_catalog(self):
        self.source_v3()
        self.payments.process_job('job1')
        snapshot = next(call.args[2] for call in self.frappe.db.set_value.call_args_list if call.args[0]=='Cafe Source Payment')
        value = json.loads(snapshot['methods_json'])
        self.assertEqual(value['customer']['name'], 'طاها بورقی')
        self.assertEqual(value['customer']['account_key'], '110:4:8')
        self.assertEqual(value['source_factor'], 23702)
        self.assertEqual(value['items'][0]['item_name'], 'آمریکانو')
        self.assertEqual(value['payment_catalog'][0]['account_name'], 'پوز ملت')

    def test_invalid_customer_account_cannot_write_a_snapshot(self):
        self.source_v3('110:4:8;DROP')
        with self.assertRaises(ValueError):
            self.payments.process_job('job1')
        self.frappe.db.set_value.assert_not_called()


if __name__ == "__main__":
    unittest.main()
