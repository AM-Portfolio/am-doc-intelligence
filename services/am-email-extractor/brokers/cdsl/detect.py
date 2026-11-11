"""Detect CDSL CAS PDFs from unlocked text."""
from __future__ import annotations


def is_cdsl_cas(text: str) -> bool:
    u = text or ""
    markers = (
        "CONSOLIDATED ACCOUNT STATEMENT",
        "Central Depository Services",
        "DEMAT ACCOUNTS HELD WITH CDSL",
        "MUTUAL FUND UNITS HELD WITH MF/RTA",
    )
    hits = sum(1 for m in markers if m.lower() in u.lower())
    return hits >= 2
