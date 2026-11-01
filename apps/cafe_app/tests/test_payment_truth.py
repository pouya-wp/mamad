import importlib.util
import base64
import gzip
import json
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("payment_truth", Path(__file__).resolve().parents[1] / "cafe_app" / "payment_truth.py")
truth = importlib.util.module_from_spec(spec)
spec.loader.exec_module(truth)


class PaymentTruthTest(unittest.TestCase):
    catalog = {1: "پوز ملت", 2: "وجه نقد", 3: "کارت به کارت"}

    def payment(self, rows, **fields):
        header = {"total": 1000, "closed": True, **fields}
        return truth.normalize_payment(header, [{"method": method, "amount": amount} for method, amount in rows], self.catalog)

    def test_closed_credit_is_not_received_money(self):
        payment = self.payment([(99, 1000)])
        self.assertEqual(payment["status"], "Credit")
        self.assertEqual(payment["received"], 0)
        self.assertEqual(payment["outstanding"], 1000)
        self.assertEqual(payment["methods"], [])

    def test_multiple_receipts_and_partial_credit(self):
        payment = self.payment([(1, 400), (1, 100), (3, 200), (99, 300)])
        self.assertEqual(payment["status"], "Partial")
        self.assertEqual(payment["received"], 700)
        self.assertEqual(payment["outstanding"], 300)
        self.assertEqual(len(payment["methods"]), 2)
        self.assertEqual(payment["direct_received"], 700)

    def test_two_terminals_with_same_name_keep_separate_source_ids(self):
        paid = truth.normalize_payment({"total": 1000, "closed": True},
            [{"method": 1, "amount": 300}, {"method": 4, "amount": 700}], {1: "پوز", 4: "پوز"})
        self.assertEqual(paid["status"], "Paid")
        self.assertEqual({m["method_id"] for m in paid["methods"]}, {1, 4})

    def test_customer_report_deduplicates_account_and_uses_latest_balance(self):
        invoices = []
        for name, balance, checked in [('old', 6000, '2026-09-29 10:00'), ('new', 4000, '2026-09-29 11:00')]:
            payment = self.payment([(1, 200), (99, 800)], account_verified=True, account_balance=balance, unallocated_receipts=500)
            payment.update(checked_at=checked, customer={'id': 175, 'name': 'تیام', 'account_key': '110:1:175', 'account_verified': True})
            invoices.append({'name': name, 'posting_date': '2026-09-29', 'source_payment': payment})
        report = truth.credit_customers(invoices)
        self.assertEqual(report['account_debt'], 4000)
        self.assertEqual(report['verified_accounts'], 1)
        self.assertEqual(report['customers'][0]['credit'], 1600)
        self.assertEqual(report['customers'][0]['unallocated_count'], 2)
        self.assertEqual(report['customers'][0]['known_outstanding'], 0)

    def test_unverified_accounts_and_cancellation_do_not_create_debt_totals(self):
        payment = self.payment([(99, 1000)], account_verified=False)
        payment['customer'] = {'id': 10, 'name': 'مشتری', 'account_key': '110:1:10', 'account_verified': False}
        invoices = [{'name': 'a', 'posting_date': '2026-09-29', 'source_payment': payment},
            {'name': 'b', 'posting_date': '2026-09-29', 'source_payment': self.payment([(99, 1000)], cancelled=True)}]
        report = truth.credit_customers(invoices)
        self.assertEqual(report['account_debt'], 0)
        self.assertEqual(report['unverified_customers'], 1)
        self.assertEqual(len(report['customers']), 1)

    def test_replacing_credit_with_source_receipt_settles_invoice(self):
        self.assertEqual(self.payment([(99, 1000)])["status"], "Credit")
        paid = self.payment([(2, 300), (1, 700)])
        self.assertEqual(paid["status"], "Paid")
        self.assertEqual(paid["outstanding"], 0)

    def test_unallocated_account_receipts_do_not_invent_invoice_allocation(self):
        payment = self.payment([(99, 1000)], account_verified=True, account_balance=3500, unallocated_receipts=10000)
        self.assertEqual(payment["status"], "Credit")
        self.assertIsNone(payment["outstanding"])
        self.assertEqual(payment["basis"], "Unallocated")

    def test_full_customer_account_clearance_can_settle_credit(self):
        paid = self.payment([(1, 200), (99, 800)], account_verified=True, account_balance=0, unallocated_receipts=800)
        self.assertEqual(paid["status"], "Paid")
        self.assertEqual(paid["received"], 1000)
        self.assertEqual(paid["basis"], "Customer Account")
        self.assertEqual(sum(method["amount"] for method in paid["methods"]), 1000)

    def test_unverified_account_and_cancelled_bill_cannot_be_marked_paid(self):
        unverified = self.payment([(99, 1000)], account_verified=False, account_balance=0)
        self.assertEqual(unverified["status"], "Unknown")
        self.assertIsNone(unverified["outstanding"])
        self.assertEqual(self.payment([(99, 1000)], cancelled=True, account_verified=True, account_balance=0)["status"], "Cancelled")

    def test_unknown_method_or_unbalanced_closed_bill_is_unknown(self):
        for rows in [[(900, 1000)], [(1, 900)], [(1, 1200)], [(1, -1000)]]:
            payment = self.payment(rows)
            self.assertEqual(payment["status"], "Unknown")
            self.assertIsNone(payment["outstanding"])

    def test_open_unpaid_bill_and_open_partial_receipt(self):
        self.assertEqual(self.payment([], closed=False)["status"], "Unpaid")
        self.assertEqual(self.payment([(1, 400)], closed=False)["status"], "Partial")

    def test_non_finite_amounts_are_rejected(self):
        for amount in ["NaN", "Infinity", True, None, 10**20]:
            with self.subTest(amount=amount), self.assertRaises(ValueError):
                self.payment([(1, amount)])

    def test_bounded_unicode_report_roundtrip_and_oversized_rejection(self):
        data = {"name": "پوز ملت"}
        encode = lambda value: "GZIP:" + base64.b64encode(gzip.compress(value)).decode()
        self.assertEqual(truth.decode_report(encode(json.dumps(data, ensure_ascii=False).encode())), data)
        with self.assertRaises(ValueError):
            truth.decode_report(encode(b" " * (truth.MAX_DECODED_BYTES + 1)))
        with self.assertRaises(ValueError):
            truth.decode_report("GZIP:not base64")


if __name__ == "__main__":
    unittest.main()
