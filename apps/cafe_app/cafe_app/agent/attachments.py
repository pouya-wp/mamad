"""Read one bounded chat attachment in memory; never create a Frappe File."""

import io
import zipfile
from pathlib import PurePosixPath
from xml.etree import ElementTree

import frappe

MAX_FILE_BYTES = 4_000_000
MAX_IMAGE_BYTES = 3_000_000
MAX_TEXT_CHARS = 8_000
MAX_ZIP_CONTENT_BYTES = 20_000_000
MAX_PDF_PAGES = 8

IMAGE_TYPES = {
	".jpg": ("image/jpeg", lambda data: data.startswith(b"\xff\xd8\xff")),
	".jpeg": ("image/jpeg", lambda data: data.startswith(b"\xff\xd8\xff")),
	".png": ("image/png", lambda data: data.startswith(b"\x89PNG\r\n\x1a\n")),
	".webp": ("image/webp", lambda data: data.startswith(b"RIFF") and data[8:12] == b"WEBP"),
	".gif": ("image/gif", lambda data: data.startswith((b"GIF87a", b"GIF89a"))),
}
TEXT_EXTENSIONS = {".txt", ".md", ".csv", ".json"}
SUPPORTED_EXTENSIONS = set(IMAGE_TYPES) | TEXT_EXTENSIONS | {".pdf", ".docx", ".xlsx"}


def read_upload():
	"""Return (name, context text, media MIME, media bytes)."""
	file = frappe.request.files.get("file")
	if not file:
		return None
	name = (file.filename or "").replace("\\", "/").rsplit("/", 1)[-1].strip()
	if not name or len(name) > 120 or any(ord(char) < 32 for char in name):
		frappe.throw("نام فایل معتبر نیست")
	ext = PurePosixPath(name.lower()).suffix
	if ext not in SUPPORTED_EXTENSIONS:
		frappe.throw("فایل باید تصویر، PDF، Word، Excel، CSV یا متن باشد")
	content = file.read(MAX_FILE_BYTES + 1)
	if not content or len(content) > MAX_FILE_BYTES:
		frappe.throw("حجم فایل باید کمتر از ۴ مگابایت باشد")
	if ext in IMAGE_TYPES:
		mime, matches = IMAGE_TYPES[ext]
		if len(content) > MAX_IMAGE_BYTES:
			frappe.throw("حجم تصویر باید کمتر از ۳ مگابایت باشد")
		if not matches(content):
			frappe.throw("فرمت واقعی تصویر با پسوند آن یکی نیست")
		return name, "", mime, content
	if ext == ".pdf":
		if not content.startswith(b"%PDF-"):
			frappe.throw("فایل PDF معتبر نیست")
		try:
			from pypdf import PdfReader
			pages = PdfReader(io.BytesIO(content)).pages
			page_count = len(pages)
		except Exception:
			frappe.throw("PDF قابل خواندن نیست؛ فایل دیگری بفرست")
		if page_count > MAX_PDF_PAGES:
			frappe.throw("PDF باید حداکثر ۸ صفحه باشد")
		return name, "", "application/pdf", content
	if ext in TEXT_EXTENSIONS:
		text = _decode_text(content)
	elif ext == ".docx":
		text = _read_docx(content)
	else:
		text = _read_xlsx(content)
	text = text.strip()
	if not text:
		frappe.throw("متنی در فایل پیدا نشد")
	if len(text) > MAX_TEXT_CHARS:
		text = text[:MAX_TEXT_CHARS] + "\n[ادامهٔ فایل به‌خاطر محدودیت حجم خوانده نشد]"
	return name, text, None, None


def _decode_text(content):
	for encoding in ("utf-8-sig", "cp1256"):
		try:
			return content.decode(encoding)
		except UnicodeDecodeError:
			continue
	frappe.throw("کدگذاری فایل متنی پشتیبانی نمی‌شود؛ UTF-8 بفرست")


def _open_zip(content):
	try:
		archive = zipfile.ZipFile(io.BytesIO(content))
		if sum(info.file_size for info in archive.infolist()) > MAX_ZIP_CONTENT_BYTES:
			archive.close()
			frappe.throw("محتوای فایل فشرده بیش از حد بزرگ است")
		return archive
	except zipfile.BadZipFile:
		frappe.throw("فایل Word یا Excel معتبر نیست")


def _read_docx(content):
	with _open_zip(content) as archive:
		try:
			root = ElementTree.fromstring(archive.read("word/document.xml"))
		except (KeyError, ElementTree.ParseError):
			frappe.throw("فایل Word قابل خواندن نیست")
	ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
	paragraphs = []
	for paragraph in root.iter(f"{ns}p"):
		line = "".join(node.text or "" for node in paragraph.iter(f"{ns}t"))
		if line.strip():
			paragraphs.append(line)
		if sum(map(len, paragraphs)) >= MAX_TEXT_CHARS:
			break
	return "\n".join(paragraphs)


def _read_xlsx(content):
	with _open_zip(content):
		pass
	from openpyxl import load_workbook
	try:
		workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
		lines = []
		for sheet in workbook.worksheets[:4]:
			lines.append(f"[برگه: {sheet.title}]")
			for row in sheet.iter_rows(max_row=100, max_col=20, values_only=True):
				values = [str(value) if value is not None else "" for value in row]
				if any(values):
					lines.append(" | ".join(values))
				if sum(map(len, lines)) >= MAX_TEXT_CHARS:
					break
			if sum(map(len, lines)) >= MAX_TEXT_CHARS:
				break
		return "\n".join(lines)
	except Exception:
		frappe.throw("فایل Excel قابل خواندن نیست")
	finally:
		if "workbook" in locals():
			workbook.close()
