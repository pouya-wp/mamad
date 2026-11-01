"""Payment snapshots are source facts, separate from the ERP clearing account."""
import base64
import gzip
import io
import json
from decimal import Decimal, InvalidOperation

MAX_DECODED_BYTES = 2 * 1024 * 1024


def decode_report(stdout):
    text = stdout.strip()
    if not text.startswith("GZIP:") or len(text) > 65536:
        raise ValueError("Invalid payment report envelope")
    compressed = base64.b64decode(text[5:], validate=True)
    with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as stream:
        data = stream.read(MAX_DECODED_BYTES + 1)
    if len(data) > MAX_DECODED_BYTES:
        raise ValueError("Payment report is too large")
    return json.loads(data.decode("utf-8-sig"))


def money(value):
    if isinstance(value, bool) or value is None:
        raise ValueError("Invalid source amount")
    try:
        amount = Decimal(str(value))
    except InvalidOperation as error:
        raise ValueError("Invalid source amount") from error
    if not amount.is_finite() or abs(amount) > Decimal("1000000000000"):
        raise ValueError("Invalid source amount")
    return amount


def normalize_payment(header, rows, catalog):
    """IdAmel 99 is the verified receivable posting, never money collected.

    Closed flags also occur on credit invoices. Only reconciled receipt amounts
    can establish Paid. Unknown methods or unbalanced entries stay Unknown.
    """
    total = money(header["total"])
    if total < 0:
        raise ValueError("Negative source invoice total")
    received = Decimal(0)
    credit = Decimal(0)
    methods = {}
    unknown = False
    for row in rows:
        amount = money(row["amount"])
        if amount < 0:
            unknown = True
            continue
        method = int(row["method"] or 0)
        if method == 99:
            credit += amount
            continue
        label = catalog.get(method)
        if not label:
            unknown = True
            continue
        received += amount
        entry = methods.setdefault(method, {"mode_of_payment": label, "method_id": method, "amount": Decimal(0)})
        entry["amount"] += amount
    outstanding = max(total - received, Decimal(0))
    # A discrepancy can be an in-progress source transaction, a fee or an
    # unsupported payment posting. It must not establish a settled invoice.
    if received > total or (header.get("closed") and received + credit != total):
        unknown = True
    if header.get("cancelled"):
        status = "Cancelled"
    elif unknown:
        status = "Unknown"
    elif total > 0 and outstanding == 0:
        status = "Paid"
    elif received > 0:
        status = "Partial"
    elif credit > 0:
        status = "Credit"
    else:
        status = "Unpaid"
    direct_received = None if unknown or status == "Cancelled" else float(received)
    basis = "Invoice"
    account_balance = None
    if credit and status != "Cancelled" and header.get("account_verified"):
        account_balance = money(header["account_balance"])
        if not unknown and account_balance <= 0:
            # All receivables for this customer, including unposted daily
            # invoices, are cleared. No FIFO allocation is invented.
            received = total
            outstanding = Decimal(0)
            status = "Paid"
            basis = "Customer Account"
            methods["account"] = {"mode_of_payment": "تسویه حساب مشتری", "method_id": None, "amount": credit}
        elif money(header.get("unallocated_receipts", 0)) > 0:
            # Source receipts have Factor=0. The remaining customer debt is
            # known, but its allocation to this particular bill is not.
            outstanding = None
            basis = "Unallocated"
    elif credit and status != "Cancelled" and "account_verified" in header:
        # An unidentified or shared receivable account cannot establish the
        # remaining debt of one customer after later account settlements.
        status = "Unknown"
        unknown = True
        outstanding = None
    return {
        "status": status,
        "total": float(total),
        "received": None if unknown or status == "Cancelled" else float(received),
        "outstanding": None if unknown or status == "Cancelled" or outstanding is None else float(outstanding),
        "methods": [{**entry, "amount": float(entry["amount"])} for entry in methods.values()
                    if entry["amount"] and status != "Cancelled"],
        "credit": float(credit),
        "basis": basis,
        "account_balance": float(account_balance) if account_balance is not None else None,
        "direct_received": direct_received,
    }


def credit_customers(invoices):
    """Group selected source invoices; use each verified customer account once.

    Account balance covers the entire source account, not the selected date range.
    Unknown invoice allocations never become a guessed per-invoice debt.
    """
    grouped = {}
    for invoice in invoices:
        payment = invoice.get("source_payment")
        if not payment or payment["status"] == "Cancelled" or not payment.get("credit"):
            continue
        customer = payment.get("customer") or {}
        identity = str(customer.get("id") or "invoice:" + invoice["name"])
        row = grouped.setdefault(identity, {
            "customer_id": customer.get("id"), "customer_name": customer.get("name"),
            "credit": 0, "direct_received": 0, "known_outstanding": 0,
            "account_balance": None, "account_key": None, "checked_at": None,
            "unallocated_count": 0, "unknown_count": 0, "invoices": [],
        })
        row["credit"] += payment["credit"]
        row["direct_received"] += payment.get("direct_received") or 0
        row["known_outstanding"] += payment.get("outstanding") or 0
        row["unallocated_count"] += payment.get("basis") == "Unallocated"
        row["unknown_count"] += payment["status"] == "Unknown"
        timestamp = str(payment.get("checked_at") or "")
        if row["checked_at"] is None or timestamp >= str(row["checked_at"]):
            row["checked_at"] = payment.get("checked_at")
            row["customer_name"] = customer.get("name")
            row["account_key"] = customer.get("account_key") if customer.get("account_verified") else None
            row["account_balance"] = payment.get("account_balance") if row["account_key"] else None
        row["invoices"].append({"name": invoice["name"], "posting_date": str(invoice["posting_date"]),
            "total": payment["total"], "credit": payment["credit"], "received": payment["received"],
            "outstanding": payment["outstanding"], "status": payment["status"], "basis": payment["basis"]})
    rows = sorted(grouped.values(), key=lambda row: (-(row["account_balance"] or 0), -(row["credit"] or 0)))
    accounts = {}
    for row in rows:
        if row["account_key"] and row["account_balance"] is not None:
            accounts[row["account_key"]] = max(row["account_balance"], 0)
    return {"customers": rows, "account_debt": sum(accounts.values()),
            "verified_accounts": len(accounts), "unverified_customers": sum(row["account_balance"] is None for row in rows)}
