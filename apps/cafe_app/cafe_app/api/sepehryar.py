"""Receive products and sales from the local SepandYar connector."""
from datetime import date

import frappe
from frappe import _
from frappe.utils import flt

from cafe_app.api.pos import build_pos_invoice
from cafe_app.utils import MENU_ROOT, get_cafe_settings


def _sync_device():
	"""Authenticate an enrolled device independently of browser sessions."""
	from cafe_app.api.desktop_remote import _device_from_header

	device_id = _device_from_header()
	user = frappe.db.get_value("Cafe Desktop Device", device_id, "enrolled_by")
	if not user or not frappe.db.get_value("User", user, "enabled") or (
		user != "Administrator" and "System Manager" not in frappe.get_roles(user)
	):
		frappe.throw(_("مجوز همگام‌سازی این دستگاه لغو شده است"), frappe.AuthenticationError)
	# The maintenance poll owns the heartbeat. Writing it in a sale transaction
	# holds this device row throughout the batch and conflicts with polling.
	return device_id, user


@frappe.whitelist(allow_guest=True, methods=["POST"])
def device_boot():
	"""A credential check, not a panel login; returns no user session or CSRF."""
	device_id, _user = _sync_device()
	return {"ready": True, "device_id": device_id, "products_disabled": True}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def device_import_sales(invoices):
	"""Only the enrolled device may upload; no browser login is created."""
	_device_id, user = _sync_device()
	previous_user = frappe.session.user
	try:
		frappe.set_user(user)
		return import_sales(invoices)
	finally:
		frappe.set_user(previous_user)


def _require_manager():
	if frappe.session.user == "Guest" or (
		frappe.session.user != "Administrator" and "System Manager" not in frappe.get_roles()
	):
		frappe.throw(_("دسترسی مدیریت برای همگام‌سازی سپهریار لازم است"), frappe.PermissionError)


def _source_item_code(source_id, warehouse_id=None):
	"""SepandYar item IDs are only unique within a source warehouse."""
	source_id = int(source_id)
	if source_id <= 0:
		frappe.throw(_("شناسهٔ کالای سپهریار نامعتبر است"))
	if warehouse_id is None:
		# Older clients may omit the warehouse. Keep their existing item code.
		return f"SEPAND-{source_id}"
	warehouse_id = int(warehouse_id)
	if warehouse_id < 0:
		frappe.throw(_("شناسهٔ انبار سپهریار نامعتبر است"))
	return f"SEPAND-{warehouse_id}-{source_id}"


def _item_for_source(source_id, source_name, warehouse_id=None):
	from cafe_app.source_categories import source_item_group

	code = _source_item_code(source_id, warehouse_id)
	if frappe.db.exists("Item", code):
		return code
	clean_name = (source_name or "").strip()
	if not clean_name or "?" in clean_name:
		clean_name = f"کالای سپهریار {code}"
	item = frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": code,
			"item_name": clean_name[:140],
			"item_group": source_item_group(source_id, warehouse_id),
			"stock_uom": "Nos",
			"is_sales_item": 1,
			"is_stock_item": 0,
			"include_item_in_manufacturing": 0,
		}
	).insert()
	return item.name


@frappe.whitelist(methods=["POST"])
def sync_products(products):
	"""Acknowledge older desktop clients without changing the product catalog.

	The installed importer calls this before import_sales. Returning an error
	would stop order uploads, so keep the endpoint as a compatibility no-op.
	"""
	_require_manager()
	return {"created": [], "existing": [], "disabled": True}


def _payment_mode():
	settings = get_cafe_settings()
	if not settings.pos_profile:
		frappe.throw(_("پروفایل فروش کافه تنظیم نشده است"))
	mode_name = "تسویه سپهریار"
	account_name = "تسویه سپهریار"
	account = frappe.db.get_value("Account", {"company": settings.company, "account_name": account_name}, "name")
	if not account:
		parent = frappe.db.get_value("Account", {"company": settings.company, "is_group": 1, "account_type": "Bank"}, "name")
		if not parent:
			frappe.throw(_("حساب بانکی مادر برای تسویه سپهریار پیدا نشد"))
		account = frappe.get_doc({
			"doctype": "Account", "account_name": account_name,
			"company": settings.company, "parent_account": parent,
			"account_type": "Bank",
		}).insert(ignore_permissions=True).name
	if not frappe.db.exists("Mode of Payment", mode_name):
		frappe.get_doc({
			"doctype": "Mode of Payment", "mode_of_payment": mode_name,
			"type": "Bank", "enabled": 1,
			"accounts": [{"company": settings.company, "default_account": account}],
		}).insert(ignore_permissions=True)
	elif not frappe.db.exists("Mode of Payment Account", {"parent": mode_name, "company": settings.company}):
		mode = frappe.get_doc("Mode of Payment", mode_name)
		mode.append("accounts", {"company": settings.company, "default_account": account})
		mode.save(ignore_permissions=True)
	profile = frappe.get_doc("POS Profile", settings.pos_profile)
	if not any(p.mode_of_payment == mode_name for p in profile.payments):
		profile.append("payments", {"mode_of_payment": mode_name})
		profile.save(ignore_permissions=True)
	return mode_name


@frappe.whitelist(methods=["POST"])
def import_sales(invoices):
	"""Submit each source FactorID once and reject any amount mismatch."""
	_require_manager()
	invoices = frappe.parse_json(invoices)
	if not isinstance(invoices, list) or len(invoices) > 20:
		frappe.throw(_("فهرست فاکتورها نامعتبر است"))
	created, skipped = [], []
	mode = _payment_mode()
	for source in invoices:
		factor_id = int(source["sourceInvoiceId"])
		if factor_id <= 0:
			frappe.throw(_("شماره فاکتور سپهریار نامعتبر است"))
		marker = f"[Sepand:1405:{factor_id}]"
		if frappe.db.exists("Sales Invoice", {"remarks": ["like", f"%{marker}%"]}):
			skipped.append(factor_id)
			continue
		rows = source.get("items") or []
		if not rows:
			skipped.append(factor_id)
			continue
		posting_date = date.fromisoformat(source["postingDate"])
		posting_time = source["postingTime"]
		items, expected_total = [], 0
		for row in rows:
			qty = flt(row.get("quantity"))
			amount = flt(row.get("amount"))
			if qty <= 0 or amount <= 0:
				frappe.throw(_("تعداد یا مبلغ یکی از اقلام سپهریار نامعتبر است"))
			source_name = (row.get("name") or "").strip()
			if "?" in source_name:
				source_name = ""
			items.append({
				"item_code": _item_for_source(row["sourceItemId"], source_name, row.get("warehouseId")),
				"item_name": source_name[:140] or None,
				"qty": qty,
				"rate": amount / qty,
			})
			expected_total += amount
		invoice = build_pos_invoice(
			items,
			[{"mode_of_payment": mode}],
			remarks=f"{marker} | SepandYar | روش پرداخت در سپهریار نامشخص",
			posting_date=str(posting_date),
			posting_time=posting_time,
			expected_total=expected_total,
		)
		created.append({"sourceInvoiceId": factor_id, "name": invoice.name})
	if created:
		frappe.enqueue(
			"cafe_app.api.mobile_push.notify_sales_import",
			count=len(created),
			queue="short",
			enqueue_after_commit=True,
		)
	return {"created": created, "skipped": skipped}
