import frappe

from cafe_app.access import buyer_scopes
from cafe_app.agent import attachments
from cafe_app.agent import insights as agent_insights
from cafe_app.agent import llm, offline, tools


MANAGER_SUGGESTIONS = [
	"امروز چطور بود؟ فروش، خرید و هشدارها",
	"فروش این ماه شمسی رو با ماه قبل مقایسه کن",
	"کدوم محصولات کمترین حاشیه سود رو دارن؟",
	"چک‌هایی که این هفته سررسید می‌شن",
	"حقوق این ماه پرسنل چقدره و کی باید بدم؟",
	"شیر لیتری ۶۰ هزار تومنه",
]

BUYER_SUGGESTIONS = [
	"۲۰ کیلو گوشت از قصابی گرفتم کیلویی ۸۵۰ هزار",
	"۵ شانه تخم‌مرغ و ۱۰ لیتر شیر خریدم، جمعاً ۲ میلیون نقدی",
	"خریدهای این هفته چقدر شد؟",
	"خریدهای امروز رو نشون بده",
]


@frappe.whitelist()
def status():
	live = llm.configured()
	if buyer_scopes():
		return {"mode": "live" if live else "demo", "suggestions": BUYER_SUGGESTIONS}
	return {"mode": "live" if live else "demo", "suggestions": MANAGER_SUGGESTIONS if live else offline.SUGGESTIONS}


@frappe.whitelist()
def chat(message="", history=None):
	message = (message or "").strip()
	attachment = attachments.read_upload()
	if not message and not attachment:
		frappe.throw("پیام خالی است")
	if attachment and not llm.configured():
		frappe.throw("خواندن پیوست در حال حاضر فعال نیست")

	history = frappe.parse_json(history) or []
	if llm.configured():
		context = ""
		if attachment:
			name, extracted_text, mime, content = attachment
			if mime:
				extracted_text = llm.inspect_media(message, name, mime, content)
			context = f"فایل «{name}»:\n{extracted_text}"
		result = llm.run(message or "این پیوست را بررسی کن", history, context)
		if context:
			result["attachment_context"] = context[:1500]
		return result
	if buyer_scopes():
		# The offline demo brain only knows the manager's tools.
		return {"text": "دستیار هوشمند الان در دسترس نیست؛ خرید را از دکمه «خرید جدید» دستی ثبت کن.", "blocks": [], "suggestions": [], "mode": "demo"}
	return offline.respond(message)


@frappe.whitelist()
def confirm(proposal_id):
	return tools.confirm_proposal(proposal_id)


@frappe.whitelist()
def cancel(proposal_id):
	frappe.cache.delete_value(f"cafe_agent_proposal:{proposal_id}")


@frappe.whitelist()
def insights():
	return agent_insights.daily_insights()
