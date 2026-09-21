import frappe

from cafe_app.agent import insights as agent_insights
from cafe_app.agent import llm, offline, tools


@frappe.whitelist()
def status():
	return {"mode": "live" if llm.configured() else "demo", "suggestions": offline.SUGGESTIONS}


@frappe.whitelist()
def chat(message, history=None):
	message = (message or "").strip()
	if not message:
		frappe.throw("پیام خالی است")

	history = frappe.parse_json(history) or []
	if llm.configured():
		return llm.run(message, history)
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
