"""Run standalone with python -m unittest apps/cafe_app/tests/test_agent_attachments.py."""

import importlib.util
import io
import sys
import types
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch


class Upload(io.BytesIO):
    def __init__(self, name, content):
        super().__init__(content)
        self.filename = name


class AttachmentTest(unittest.TestCase):
    def setUp(self):
        self.frappe = types.ModuleType("frappe")
        self.frappe.request = types.SimpleNamespace(files={})
        self.frappe.throw = lambda message: (_ for _ in ()).throw(RuntimeError(message))
        source = Path(__file__).resolve().parents[1] / "cafe_app" / "agent" / "attachments.py"
        with patch.dict(sys.modules, {"frappe": self.frappe}):
            spec = importlib.util.spec_from_file_location("cafe_attachments_under_test", source)
            self.attachments = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self.attachments)

    def test_text_and_word_are_extracted_without_saving(self):
        self.frappe.request.files["file"] = Upload("receipt.txt", "خرید شیر: ۲۵۰٬۰۰۰ تومان".encode())
        name, text, mime, content = self.attachments.read_upload()
        self.assertEqual((name, mime, content), ("receipt.txt", None, None))
        self.assertIn("خرید شیر", text)

        doc = io.BytesIO()
        with zipfile.ZipFile(doc, "w") as archive:
            archive.writestr("word/document.xml", (
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                '<w:body><w:p><w:r><w:t>فاکتور خرید</w:t></w:r></w:p></w:body></w:document>'
            ))
        self.frappe.request.files["file"] = Upload("receipt.docx", doc.getvalue())
        self.assertIn("فاکتور خرید", self.attachments.read_upload()[1])

    def test_rejects_spoofed_and_oversized_images(self):
        self.frappe.request.files["file"] = Upload("fake.png", b"not a png")
        with self.assertRaisesRegex(RuntimeError, "فرمت واقعی"):
            self.attachments.read_upload()

        self.frappe.request.files["file"] = Upload("large.png", b"\x89PNG\r\n\x1a\n" + b"a" * 3_000_000)
        with self.assertRaisesRegex(RuntimeError, "۳ مگابایت"):
            self.attachments.read_upload()

    def test_pdf_page_limit(self):
        reader = types.ModuleType("pypdf")
        reader.PdfReader = lambda _content: types.SimpleNamespace(pages=[None] * 9)
        self.frappe.request.files["file"] = Upload("large.pdf", b"%PDF-1.7\n")
        with patch.dict(sys.modules, {"pypdf": reader}):
            with self.assertRaisesRegex(RuntimeError, "۸ صفحه"):
                self.attachments.read_upload()


if __name__ == "__main__":
    unittest.main()
