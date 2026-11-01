"""Audited remote maintenance jobs for explicitly enrolled ONE CAFE Windows devices.

Only the VPS shell can enqueue a script. Browser/API users cannot call queue_script.
An enrolled device can only claim jobs addressed to its own token hash.
"""

import hashlib
import hmac
import secrets
from pathlib import Path

import frappe
from frappe import _
from frappe.utils import now_datetime


MAX_SCRIPT_BYTES = 32 * 1024
MAX_RESULT_CHARS = 64 * 1024
MIN_TIMEOUT = 5
MAX_TIMEOUT = 600


def _require_manager():
	if frappe.session.user == "Guest" or (
		frappe.session.user != "Administrator" and "System Manager" not in frappe.get_roles()
	):
		frappe.throw(_("دسترسی مدیریت لازم است"), frappe.PermissionError)


def _device_from_header():
	token = frappe.get_request_header("X-OneCafe-Device-Token") or ""
	if not token:
		frappe.throw(_("توکن دستگاه لازم است"), frappe.AuthenticationError)
	if len(token) != 64 or any(char not in "0123456789abcdef" for char in token):
		frappe.throw(_("توکن دستگاه نامعتبر است"), frappe.AuthenticationError)
	token_hash = hashlib.sha256(token.encode("ascii")).hexdigest()
	device = frappe.db.get_value(
		"Cafe Desktop Device", token_hash, ["name", "enabled"], as_dict=True
	)
	if not device or not device.enabled or not hmac.compare_digest(device.name, token_hash):
		frappe.throw(_("دستگاه مجاز نیست"), frappe.AuthenticationError)
	return device.name


@frappe.whitelist(methods=["POST"])
def enroll(machine_name, app_version):
	"""One-time enrollment through the desktop app's signed-in manager session."""
	_require_manager()
	if not isinstance(machine_name, str) or not machine_name.strip() or len(machine_name) > 100:
		frappe.throw(_("نام دستگاه نامعتبر است"))
	if not isinstance(app_version, str) or not app_version.strip() or len(app_version) > 32:
		frappe.throw(_("نسخهٔ برنامه نامعتبر است"))
	token = secrets.token_hex(32)
	token_hash = hashlib.sha256(token.encode("ascii")).hexdigest()
	frappe.get_doc({
		"doctype": "Cafe Desktop Device",
		"token_hash": token_hash,
		"machine_name": machine_name.strip(),
		"app_version": app_version.strip(),
		"enrolled_by": frappe.session.user,
		"enabled": 1,
		"last_seen": now_datetime(),
	}).insert(ignore_permissions=True)
	return {"device_id": token_hash, "device_token": token}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def poll():
	"""Claim at most one queued job; a claimed job is never auto-retried."""
	device = _device_from_header()
	frappe.db.set_value("Cafe Desktop Device", device, "last_seen", now_datetime(), update_modified=False)
	from cafe_app.source_payments import maybe_queue
	try:
		maybe_queue(device)
	except Exception as error:
		# Source payment reads must not stop ordinary remote maintenance.
		frappe.logger("cafe_payments").warning("Payment scheduling failed: %s", type(error).__name__)
	rows = frappe.db.sql(
		"""SELECT name, script, script_sha256, timeout_seconds
		FROM `tabCafe Desktop Job`
		WHERE device = %s AND status = 'Queued'
		ORDER BY creation ASC LIMIT 1 FOR UPDATE""",
		(device,), as_dict=True,
	)
	if not rows:
		frappe.db.commit()
		return {"job": None}
	job = rows[0]
	frappe.db.set_value(
		"Cafe Desktop Job", job.name,
		{"status": "Running", "started_at": now_datetime()},
		update_modified=False,
	)
	frappe.db.commit()
	return {"job": {
		"id": job.name,
		"script": job.script,
		"sha256": job.script_sha256,
		"timeoutSeconds": job.timeout_seconds,
	}}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def report(job_id, exit_code, stdout="", stderr="", timed_out=False):
	"""Accept a bounded result only from the device that claimed the job."""
	device = _device_from_header()
	if not isinstance(job_id, str) or len(job_id) > 140:
		frappe.throw(_("شناسهٔ فرمان نامعتبر است"))
	job = frappe.db.get_value("Cafe Desktop Job", job_id, ["device", "status", "purpose"], as_dict=True)
	if not job or job.device != device:
		frappe.throw(_("فرمان برای این دستگاه نیست"), frappe.PermissionError)
	if job.status in ("Succeeded", "Failed", "Timed Out"):
		return {"recorded": True, "status": job.status}
	if job.status != "Running":
		frappe.throw(_("وضعیت فرمان نامعتبر است"))
	try:
		exit_code = int(exit_code)
	except (TypeError, ValueError):
		frappe.throw(_("کد خروج نامعتبر است"))
	if not isinstance(stdout, str) or not isinstance(stderr, str):
		frappe.throw(_("خروجی نامعتبر است"))
	if len(stdout) > MAX_RESULT_CHARS or len(stderr) > MAX_RESULT_CHARS:
		frappe.throw(_("خروجی بیش از حد مجاز است"))
	status = "Timed Out" if timed_out in (True, "true", "1", 1) else "Succeeded" if exit_code == 0 else "Failed"
	frappe.db.set_value("Cafe Desktop Job", job_id, {
		"status": status,
		"finished_at": now_datetime(),
		"exit_code": exit_code,
		"stdout": stdout,
		"stderr": stderr,
	}, update_modified=False)
	if status == "Succeeded" and job.purpose == "source_payments_v1":
		from cafe_app.source_payments import accept_report
		accept_report(job_id)
	return {"recorded": True, "status": status}


def queue_script(script_path, device_id=None, timeout_seconds=120):
	"""Run with `bench execute` on the VPS. Never exposed as an HTTP method."""
	script = Path(script_path).read_text(encoding="utf-8-sig")
	if not script.strip() or len(script.encode("utf-8")) > MAX_SCRIPT_BYTES:
		raise ValueError("Script must be 1 to 32768 UTF-8 bytes")
	timeout_seconds = int(timeout_seconds)
	if not MIN_TIMEOUT <= timeout_seconds <= MAX_TIMEOUT:
		raise ValueError("Timeout must be between 5 and 600 seconds")
	if device_id:
		devices = frappe.get_all("Cafe Desktop Device", filters={"name": device_id, "enabled": 1}, pluck="name")
	else:
		devices = frappe.get_all("Cafe Desktop Device", filters={"enabled": 1}, pluck="name")
	if len(devices) != 1:
		raise ValueError("Specify an exact enabled device_id when there is not exactly one enabled device")
	job = frappe.get_doc({
		"doctype": "Cafe Desktop Job",
		"device": devices[0],
		"status": "Queued",
		"timeout_seconds": timeout_seconds,
		"script": script,
		"script_sha256": hashlib.sha256(script.encode("utf-8")).hexdigest(),
	}).insert(ignore_permissions=True)
	frappe.db.commit()
	return {"job_id": job.name, "device_id": devices[0], "sha256": job.script_sha256}


def job_result(job_id):
	"""Read a job's status and result with `bench execute` on the VPS."""
	job = frappe.get_doc("Cafe Desktop Job", job_id)
	return {
		"job_id": job.name, "device_id": job.device, "status": job.status,
		"started_at": job.started_at, "finished_at": job.finished_at,
		"exit_code": job.exit_code, "stdout": job.stdout, "stderr": job.stderr,
	}
