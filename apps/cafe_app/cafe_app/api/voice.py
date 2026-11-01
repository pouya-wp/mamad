"""Bounded Persian speech input/output for the assistant; the API key stays on the server."""

import base64

import frappe
import requests
from frappe.utils import nowdate

from cafe_app.agent.llm import configured

MAX_RECORDING_BYTES = 2_000_000
MAX_SPEECH_CHARS = 1000
SPEECH_VOICES = {"marin", "cedar", "nova", "coral"}
MIME_EXTENSIONS = {"audio/webm": "webm", "audio/mp4": "mp4", "audio/ogg": "ogg", "audio/mpeg": "mp3"}

_LIMIT_SCRIPT = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then redis.call('EXPIRE', KEYS[1], 172800) end
return count <= tonumber(ARGV[1])
"""


def _ready(kind, daily_limit):
	if not configured():
		frappe.throw("گفت‌وگوی صوتی در حال حاضر فعال نیست")
	try:
		allowed = frappe.cache.eval(_LIMIT_SCRIPT, 1, f"cafe_voice:{frappe.local.site}:{nowdate()}:{kind}", daily_limit)
	except Exception:
		frappe.throw("کنترل مصرف ویس در دسترس نیست؛ کمی بعد دوباره امتحان کن")
	if not allowed:
		frappe.throw("سقف مصرف روزانه ویس پر شده؛ فردا دوباره امتحان کن")
	return (frappe.conf.get("ai_base_url") or "https://api.openai.com/v1").rstrip("/"), {
		"Authorization": f"Bearer {frappe.conf.get('ai_api_key')}"
	}


@frappe.whitelist()
def transcribe():
	file = frappe.request.files.get("file")
	if not file:
		frappe.throw("فایل صوتی ارسال نشده است")
	mime = (file.mimetype or "").split(";", 1)[0]
	if mime not in MIME_EXTENSIONS:
		frappe.throw("فرمت صدای ضبط‌شده پشتیبانی نمی‌شود")
	content = file.read(MAX_RECORDING_BYTES + 1)
	if not content or len(content) > MAX_RECORDING_BYTES:
		frappe.throw("صدای ضبط‌شده باید کمتر از ۲ مگابایت باشد")
	base, headers = _ready("transcribe", 80)
	try:
		response = requests.post(f"{base}/audio/transcriptions", headers=headers,
			data={"model": frappe.conf.get("ai_transcription_model") or "gpt-4o-mini-transcribe", "language": "fa"},
			files={"file": (f"voice.{MIME_EXTENSIONS[mime]}", content, mime)}, timeout=60)
		response.raise_for_status()
		return {"text": str(response.json().get("text") or "").strip()}
	except (requests.RequestException, ValueError):
		frappe.throw("تبدیل صدا به متن انجام نشد؛ دوباره امتحان کن")


@frappe.whitelist()
def speak(text, voice="nova"):
	text = (text or "").strip()
	if not text or len(text) > MAX_SPEECH_CHARS:
		frappe.throw("متن پاسخ صوتی باید کوتاه‌تر باشد")
	voice = (voice or "").strip()
	if voice not in SPEECH_VOICES:
		frappe.throw("صدای انتخاب‌شده پشتیبانی نمی‌شود")
	base, headers = _ready("speak", 120)
	instructions = "به فارسی روان و طبیعی، با لحنی گرم و صمیمی صحبت کن."
	if voice == "nova":
		instructions = "به فارسی روان و طبیعی، با صدایی زنانه و لحنی گرم و صمیمی صحبت کن."
	try:
		response = requests.post(f"{base}/audio/speech", headers={**headers, "Content-Type": "application/json"},
			json={"model": frappe.conf.get("ai_speech_model") or "gpt-4o-mini-tts", "voice": voice,
				"input": text, "instructions": instructions,
				"response_format": "mp3"}, timeout=60)
		response.raise_for_status()
		if len(response.content) > 2_000_000:
			frappe.throw("پاسخ صوتی بیش از حد بزرگ است")
		return {"audio": base64.b64encode(response.content).decode("ascii"), "mime": "audio/mpeg"}
	except requests.RequestException:
		frappe.throw("ساخت پاسخ صوتی انجام نشد؛ دوباره امتحان کن")
