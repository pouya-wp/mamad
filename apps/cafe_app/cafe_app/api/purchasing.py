"""Purchase register for the restaurant and café purchase desks.

Both desks share the company, accounts and warehouse; each purchase manager
may see and edit only their granted desks, and a manager sees both. Every
purchase of a known ingredient refreshes that ingredient's
unit price, which is what recipe costs are calculated from.
"""

import frappe
from frappe import _
from frappe.utils import add_days, date_diff, flt, getdate, nowdate

from cafe_app.access import SCOPE_LABELS, buyer_scope, buyer_scopes, is_manager
from cafe_app.api import buyer_activity
from cafe_app.utils import ingredient_groups

PAYMENTS = ("Cash", "Card", "Transfer", "Credit")

# purchase unit -> (stock uom, factor). Kilo/litre also scale grams and
# millilitres alike, since people say «۵ کیلو شیر».
UNITS = {
	"کیلو": 1000, "کیلوگرم": 1000, "کیلو گرم": 1000, "kg": 1000,
	"لیتر": 1000, "litre": 1000,
	"گرم": 1, "g": 1, "میلی‌لیتر": 1, "میلی لیتر": 1, "میل": 1, "سی‌سی": 1, "سی سی": 1, "cc": 1, "ml": 1,
	"عدد": 1, "تا": 1, "دانه": 1,
}
MASS_VOLUME = ("Gram", "Millilitre")


def _scope_for_write(scope):
	allowed = buyer_scopes()
	if allowed:
		if not scope and len(allowed) == 1:
			return allowed[0]
		if scope not in allowed:
			frappe.throw(_("مشخص کن خرید برای کدام بخش مجاز است"), frappe.PermissionError)
		return scope
	if not is_manager():
		frappe.throw(_("دسترسی به این بخش فقط برای مدیر است"), frappe.PermissionError)
	if scope not in SCOPE_LABELS:
		frappe.throw(_("مشخص کن خرید برای رستوران است یا کافه"))
	return scope


def _check_access(doc):
	allowed = buyer_scopes()
	if allowed and doc.scope not in allowed:
		frappe.throw(_("این خرید مربوط به بخش دیگری است"), frappe.PermissionError)
	if not allowed and not is_manager():
		frappe.throw(_("دسترسی به این بخش فقط برای مدیر است"), frappe.PermissionError)


@frappe.whitelist()
def me():
	scope = buyer_scope()
	allowed = buyer_scopes()
	return {
		"is_manager": is_manager(),
		"is_buyer": bool(allowed),
		"scope": scope,
		"scope_label": SCOPE_LABELS.get(scope),
		"scopes": [{"value": k, "label": v} for k, v in SCOPE_LABELS.items() if is_manager() or k in allowed],
	}


@frappe.whitelist()
def ingredients():
	"""Known ingredients a purchase line can be linked to (name and stock unit only)."""
	return frappe.get_all(
		"Item",
		filters={"item_group": ["in", ingredient_groups()], "disabled": 0},
		fields=["item_code", "item_name", "stock_uom"],
		order_by="item_name asc",
	)


@frappe.whitelist()
def list_purchases(scope=None, from_date=None, to_date=None, limit=200):
	allowed = buyer_scopes()
	if not allowed and not is_manager():
		frappe.throw(_("دسترسی به این بخش فقط برای مدیر است"), frappe.PermissionError)
	if scope and scope not in SCOPE_LABELS:
		frappe.throw(_("بخش خرید نامعتبر است"))
	if allowed and scope and scope not in allowed:
		frappe.throw(_("این خرید مربوط به بخش دیگری است"), frappe.PermissionError)
	scope = scope or (allowed[0] if len(allowed) == 1 else None)

	filters = {}
	if scope:
		filters["scope"] = scope
	elif allowed:
		filters["scope"] = ["in", allowed]
	if from_date and to_date:
		filters["purchase_date"] = ["between", [getdate(from_date), getdate(to_date)]]

	rows = frappe.get_all(
		"Cafe Purchase",
		filters=filters,
		fields=["name", "scope", "purchase_date", "supplier", "payment", "total", "source", "note", "owner", "creation"],
		order_by="purchase_date desc, creation desc",
		limit=min(int(limit), 500),
	)
	items = {}
	if rows:
		for it in frappe.get_all(
			"Cafe Purchase Item",
			filters={"parenttype": "Cafe Purchase", "parent": ["in", [r.name for r in rows]]},
			fields=["parent", "item_name", "ingredient", "qty", "unit", "unit_price", "amount"],
			order_by="idx asc",
		):
			items.setdefault(it.parent, []).append(it)
	owners = {
		u.name: u.full_name
		for u in frappe.get_all("User", filters={"name": ["in", list({r.owner for r in rows}) or [""]]}, fields=["name", "full_name"])
	}
	for r in rows:
		r["items"] = items.get(r.name, [])
		r.owner_name = owners.get(r.owner, r.owner)

	# Per-desk totals for the same dates, bounded by the caller's granted desks.
	conditions, values = [], {}
	if scope:
		conditions.append("scope = %(scope)s")
		values["scope"] = scope
	elif allowed:
		conditions.append("scope in %(allowed)s")
		values["allowed"] = allowed
	if from_date and to_date:
		conditions.append("purchase_date between %(from)s and %(to)s")
		values.update({"from": getdate(from_date), "to": getdate(to_date)})
	totals = frappe.db.sql(
		f"""select scope, sum(total) total, count(*) count from `tabCafe Purchase`
		{"where " + " and ".join(conditions) if conditions else ""} group by scope""",
		values,
		as_dict=True,
	)
	return {"rows": rows, "totals": {t.scope: {"total": flt(t.total), "count": t.count} for t in totals}}


@frappe.whitelist()
def calendar_month(from_date, to_date):
	"""Purchase-only calendar for purchase managers; no finance or staff data."""
	allowed = buyer_scopes()
	if not allowed and not is_manager():
		frappe.throw(_("دسترسی به این بخش فقط برای مدیر است"), frappe.PermissionError)
	start, end = getdate(from_date), getdate(to_date)
	if end < start or date_diff(end, start) > 62:
		frappe.throw(_("بازه تقویم نامعتبر است"))
	days = {}
	for i in range(date_diff(end, start) + 1):
		days[str(add_days(start, i))] = {"sales": None, "purchases": [], "expenses": [], "cheques": [], "events": []}
	filters = {"purchase_date": ["between", [start, end]]}
	if allowed:
		filters["scope"] = ["in", allowed]
	for p in frappe.get_all(
		"Cafe Purchase", filters=filters,
		fields=["name", "scope", "supplier", "total", "purchase_date"],
		order_by="creation asc",
	):
		days[str(p.purchase_date)]["purchases"].append({
			"name": p.name, "scope": p.scope, "desk": SCOPE_LABELS.get(p.scope),
			"supplier": p.supplier, "amount": p.total,
		})
	return days


@frappe.whitelist()
def save_purchase(data):
	data = frappe._dict(frappe.parse_json(data))
	if data.name:
		doc = frappe.get_doc("Cafe Purchase", data.name)
		_check_access(doc)
		scope = _scope_for_write(data.scope or doc.scope)
	else:
		scope = _scope_for_write(data.scope)
		doc = None
	return create_or_update(doc, scope, data.get("items"), data.supplier, data.payment, data.purchase_date, data.note, data.source or "Manual")


@frappe.whitelist()
def delete_purchase(name):
	doc = frappe.get_doc("Cafe Purchase", name)
	_check_access(doc)
	before = buyer_activity.purchase_snapshot(doc) if buyer_scopes() else None
	ingredients = {i.ingredient for i in doc.items if i.ingredient}
	doc.delete(ignore_permissions=True)
	for code in ingredients:
		refresh_ingredient_price(code)
	buyer_activity.log("purchase.delete", "Cafe Purchase", name, before["scope"] if before else None,
		f"حذف خرید {before['supplier'] or name}" if before else "", before=before)


def create_or_update(doc, scope, items, supplier=None, payment=None, purchase_date=None, note=None, source="Manual"):
	before = buyer_activity.purchase_snapshot(doc) if doc and buyer_scopes() else None
	lines = []
	for row in frappe.parse_json(items) or []:
		row = frappe._dict(row)
		name = (row.item_name or "").strip()
		if not name:
			continue
		qty, price, amount = flt(row.qty), flt(row.unit_price), flt(row.amount)
		if not amount and qty and price:
			amount = qty * price
		if not price and qty and amount:
			price = amount / qty
		if amount <= 0:
			frappe.throw(_("مبلغ «{0}» را وارد کن").format(name))
		lines.append({
			"item_name": name,
			"ingredient": row.ingredient or match_ingredient(name),
			"qty": qty,
			"unit": (row.unit or "").strip(),
			"unit_price": price,
			"amount": amount,
		})
	if not lines:
		frappe.throw(_("حداقل یک قلم با مبلغ وارد کن"))

	previous = {i.ingredient for i in doc.items if i.ingredient} if doc else set()
	doc = doc or frappe.new_doc("Cafe Purchase")
	doc.update({
		"scope": scope,
		"purchase_date": getdate(purchase_date or nowdate()),
		"supplier": (supplier or "").strip() or None,
		"payment": payment if payment in PAYMENTS else "Card",
		"note": note,
		"source": source if source in ("Manual", "Assistant") else "Manual",
		"total": sum(l["amount"] for l in lines),
	})
	doc.set("items", lines)
	doc.save(ignore_permissions=True)

	for code in previous | {l["ingredient"] for l in lines if l["ingredient"]}:
		refresh_ingredient_price(code)
	buyer_activity.log("purchase.update" if before else "purchase.create", "Cafe Purchase", doc.name, scope,
		f"{'ویرایش' if before else 'ثبت'} خرید {doc.supplier or doc.name} · {len(lines)} قلم",
		before=before, after=buyer_activity.purchase_snapshot(doc) if buyer_scopes() else None)
	return {"name": doc.name, "total": doc.total}


def match_ingredient(text):
	"""Exact ingredient name, else the longest ingredient name contained in the text."""
	text = (text or "").strip()
	if not text:
		return None
	names = frappe.get_all("Item", filters={"item_group": ["in", ingredient_groups()], "disabled": 0}, fields=["name", "item_name"])
	for n in names:
		if n.item_name == text:
			return n.name
	contained = sorted((n for n in names if len(n.item_name) > 1 and n.item_name in text), key=lambda n: len(n.item_name), reverse=True)
	return contained[0].name if contained else None


def unit_factor(unit, stock_uom):
	"""How many stock units one purchase unit is, or None when they cannot be compared."""
	unit = (unit or "").strip()
	factor = UNITS.get(unit)
	if factor is None:
		return 1 if not unit and stock_uom == "Nos" else None
	if stock_uom == "Nos":
		return 1 if unit in ("عدد", "تا", "دانه") else None
	if stock_uom in MASS_VOLUME:
		return factor if unit not in ("عدد", "تا", "دانه") else None
	return None


def refresh_ingredient_price(item_code):
	"""Set the ingredient's unit price from its most recent comparable purchase."""
	stock_uom = frappe.db.get_value("Item", item_code, "stock_uom")
	if not stock_uom:
		return
	rows = frappe.db.sql(
		"""
		select i.qty, i.unit, i.amount
		from `tabCafe Purchase Item` i join `tabCafe Purchase` p on p.name = i.parent
		where i.ingredient = %s and i.qty > 0 and i.amount > 0
		order by p.purchase_date desc, p.creation desc
		limit 20
		""",
		item_code,
		as_dict=True,
	)
	for r in rows:
		factor = unit_factor(r.unit, stock_uom)
		if factor:
			frappe.db.set_value("Item", item_code, "valuation_rate", flt(r.amount) / (flt(r.qty) * factor), update_modified=False)
			return


def period_bounds(period):
	today = getdate(nowdate())
	days = {"today": 0, "week": 6, "month": 29}.get(period, 6)
	if period == "yesterday":
		day = add_days(today, -1)
		return day, day
	return add_days(today, -days), today
