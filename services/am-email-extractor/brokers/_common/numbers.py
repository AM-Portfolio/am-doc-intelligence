"""Numeric / date helpers for statement parsers."""
from __future__ import annotations

import re

DATE_LINE_RE = re.compile(r"^\d{1,2}[-./]\d{1,2}[-./]\d{2,4}$")
NUM_TOKEN = re.compile(r"--|[\d,]+\.\d+|[\d,]+")


def norm_date(d: str | None) -> str | None:
    if not d:
        return None
    m = re.match(r"(\d{2})-(\d{2})-(\d{4})", d)
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else d


def fnum(x: str | None) -> float | None:
    if x is None or x in ("", "--"):
        return None
    try:
        return float(str(x).replace(",", "").replace("`", "").strip())
    except ValueError:
        return None
