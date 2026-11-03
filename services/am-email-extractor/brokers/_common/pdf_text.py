"""PDF unlock + plain text extraction (PyMuPDF)."""
from __future__ import annotations

from pathlib import Path


def load_pdf_text(path: str | Path, password: str | None = None) -> str:
    import fitz  # PyMuPDF

    doc = fitz.open(str(path))
    try:
        if doc.is_encrypted:
            ok = doc.authenticate(password or "")
            if not ok:
                raise ValueError(f"PDF unlock failed for {path}")
        return "\n".join(doc.load_page(i).get_text("text") for i in range(doc.page_count))
    finally:
        doc.close()
