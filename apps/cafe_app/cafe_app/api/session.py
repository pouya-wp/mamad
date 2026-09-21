import frappe
from frappe import _
from frappe.sessions import get_csrf_token

from cafe_app.cafe_setup import ensure_cafe_defaults
from cafe_app.utils import get_cafe_settings


@frappe.whitelist()
def boot():
	"""Session bootstrap for the panel: who is logged in, their CSRF token and the café context."""
	if frappe.session.user == "Guest":
		frappe.throw(_("Not logged in"), frappe.AuthenticationError)

	ensure_cafe_defaults()
	user = frappe.get_cached_doc("User", frappe.session.user)

	return {
		"csrf_token": get_csrf_token(),
		"user": {
			"name": user.name,
			"full_name": user.full_name,
			"image": user.user_image,
			"roles": frappe.get_roles(),
		},
		"cafe": get_cafe_settings(),
	}
