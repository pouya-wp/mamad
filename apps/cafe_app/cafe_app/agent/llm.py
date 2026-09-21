"""Provider-agnostic LLM brain over any OpenAI-compatible Chat Completions API (OpenAI, DeepSeek...).

site_config.json:
    "ai_base_url": "https://api.deepseek.com"   (or https://api.openai.com/v1)
    "ai_api_key":  "<secret>"
    "ai_model":    "<model name>"
"""

import json

import frappe
import requests
from frappe.utils import nowdate

from cafe_app.agent import tools

MAX_STEPS = 6

SYSTEM_PROMPT = """تو «دستیار One» هستی: ایجنت هوش مصنوعی حسابداری و مدیریت کافه ONE CAFE در یزد.
مخاطبت مدیر یا صندوقدار کافه است که حسابدار نیست؛ ساده، صمیمی، کوتاه و فارسی جواب بده.
- هر عدد (فروش، سود، موجودی، هزینه) را فقط از ابزارها بگیر؛ هرگز عدد نساز.
- مبالغ را به تومان بگو.
- برای ثبت هزینه، خرید یا ضایعات از ابزارهای propose_* استفاده کن. این ابزارها فقط پیشنهاد می‌سازند؛
  به کاربر بگو کارت را بررسی و تأیید کند و هرگز نگو «ثبت شد».
- اگر اطلاعات لازم (مثل مبلغ) را نداری، کوتاه بپرس.
- وقتی نکته مهمی در داده‌ها می‌بینی (افت فروش، کمبود موجودی، هزینه غیرعادی) یک پیشنهاد عملی بده."""


def configured():
	return bool(frappe.conf.get("ai_api_key") and frappe.conf.get("ai_model"))


def run(message, history):
	conf = frappe.conf
	url = (conf.get("ai_base_url") or "https://api.openai.com/v1").rstrip("/") + "/chat/completions"
	headers = {"Authorization": f"Bearer {conf.get('ai_api_key')}", "Content-Type": "application/json"}

	messages = [{"role": "system", "content": f"{SYSTEM_PROMPT}\nتاریخ امروز: {nowdate()}"}]
	messages += [{"role": m["role"], "content": m["content"]} for m in history[-10:] if m.get("content")]
	messages.append({"role": "user", "content": message})
	blocks = []

	for _step in range(MAX_STEPS):
		response = requests.post(
			url,
			headers=headers,
			json={"model": conf.get("ai_model"), "messages": messages, "tools": tools.TOOL_SPECS},
			timeout=90,
		)
		if not response.ok:
			frappe.log_error("Cafe agent LLM error", response.text[:2000])
			frappe.throw("دستیار هوشمند در دسترس نیست؛ کمی بعد دوباره امتحان کن")

		reply = response.json()["choices"][0]["message"]
		messages.append(reply)
		calls = reply.get("tool_calls") or []
		if not calls:
			return {"text": reply.get("content") or "", "blocks": blocks, "suggestions": [], "mode": "live"}

		for call in calls:
			messages.append(
				{"role": "tool", "tool_call_id": call["id"], "content": _run_tool(call["function"], blocks)}
			)

	return {"text": "این درخواست طولانی شد؛ لطفاً ساده‌تر بپرس.", "blocks": blocks, "suggestions": [], "mode": "live"}


def _run_tool(function, blocks):
	fn = tools.TOOLS.get(function["name"])
	if not fn:
		return json.dumps({"error": "unknown tool"})
	try:
		result = fn(**json.loads(function.get("arguments") or "{}"))
	except Exception as error:
		frappe.db.rollback()
		return json.dumps({"error": str(error)}, ensure_ascii=False)

	if result.get("block"):
		blocks.append(result["block"])
	return json.dumps(result["data"], ensure_ascii=False, default=str)
