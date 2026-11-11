"""Detect NPS transaction statement PDFs."""
from __future__ import annotations


def is_nps_statement(text: str) -> bool:
    u = text or ""
    return (
        "NPS TRANSACTION STATEMENT" in u.upper()
        and ("PRAN" in u.upper() or "Tier I" in u or "Tier II" in u)
    )
