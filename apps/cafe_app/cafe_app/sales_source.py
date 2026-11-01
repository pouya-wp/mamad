"""Present imported receipts by their source without guessing how they were paid."""
import frappe

SEPEHRYAR_LABEL = "سپهریار"
SOURCE_MARKER = "[Sepand:"


def is_source_order(remarks, return_against=None):
	if SOURCE_MARKER in (remarks or ""):
		return True
	if return_against:
		return SOURCE_MARKER in (frappe.db.get_value("Sales Invoice", return_against, "remarks") or "")
	return False


def order_payment_modes(order, modes):
	return [SEPEHRYAR_LABEL] if is_source_order(order.remarks, order.return_against) else modes


def order_payments(invoice):
	if is_source_order(invoice.remarks, invoice.return_against):
		from cafe_app.source_payments import for_invoice
		source = for_invoice(invoice)
		return source["methods"] if source else []
	return [{"mode_of_payment": payment.mode_of_payment, "amount": payment.base_amount} for payment in invoice.payments]
