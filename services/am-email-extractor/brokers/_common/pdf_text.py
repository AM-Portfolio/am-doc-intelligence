"""PDF unlock + plain text extraction (PyMuPDF)."""
from __future__ import annotations

from pathlib import Path


class PdfPasswordError(ValueError):
    """Structured unlock failure for API mapping."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def is_pdf_encrypted(path: str | Path) -> bool:
    import fitz  # PyMuPDF

    doc = fitz.open(str(path))
    try:
        return bool(doc.is_encrypted)
    finally:
        doc.close()


def load_pdf_text(path: str | Path, password: str | None = None) -> str:
    import fitz  # PyMuPDF

    doc = fitz.open(str(path))
    try:
        if doc.is_encrypted:
            pwd = (password or "").strip()
            if not pwd:
                raise PdfPasswordError(
                    "PASSWORD_REQUIRED",
                    "Password is required to unlock this PDF",
                )
            ok = doc.authenticate(pwd)
            if not ok:
                raise PdfPasswordError(
                    "PASSWORD_INVALID",
                    "Incorrect password",
                )
        return "\n".join(doc.load_page(i).get_text("text") for i in range(doc.page_count))
    finally:
        doc.close()
