"""DP name → internal broker id used for Kafka portfolio fan-out."""
from __future__ import annotations

import re

DP_MAP = [
    ("RAISE SECURITIES", "dhan"),
    ("GROWW INVEST TECH", "groww"),
    ("ANGEL ONE", "angleone"),
    ("ZERODHA BROKING", "zerodha"),
    ("UPSTOX SECURITIES", "upstox"),
    ("FYERS SECURITIES", "fyers"),
    ("KOTAK SECURITIES", "kotak"),
    ("MIRAE ASSET", "mirae"),
    ("FINWIZARD", "finwizard"),
    ("HDFC BANK", "hdfc"),
    ("HDFC SECURITIES", "hdfc"),
    ("FOURDEGREEWATER", "nsdl_fourdegreewater"),
]

# Kafka / Java BrokerType codes (uppercase enum-ish)
BROKER_KAFKA_CODE = {
    "dhan": "DHAN",
    "groww": "GROWW",
    "grow": "GROWW",
    "angleone": "ANGEL_ONE",
    "angelone": "ANGEL_ONE",
    "zerodha": "ZERODHA",
    "upstox": "UPSTOX",
    "fyers": "FYERS",
    "kotak": "KOTAK",
    "hdfc": "HDFC",
    "hdfc_bank": "HDFC",
    "mstock": "MSTOCK",
    "cdsl": "CDSL",
    "cas_demat": "CAS_DEMAT",
    "mirae": "CAS_DEMAT",
    "finwizard": "CAS_DEMAT",
}

_FIRST_CLASS = frozenset(
    {
        "DHAN",
        "GROWW",
        "ANGEL_ONE",
        "ZERODHA",
        "UPSTOX",
        "FYERS",
        "KOTAK",
        "HDFC",
        "MSTOCK",
        "CDSL",
        "NPS",
    }
)

_SUFFIX_RE = re.compile(
    r"\b(SECURITIES|BROKING|BANK|CAPITAL|INVEST|TECH|ASSET|SHAREKHAN|"
    r"SOLUTIONS|PRIVATE|LIMITED|LTD|TRADING)\b",
    re.IGNORECASE,
)

_FORBIDDEN_SHORT = frozenset({"cdsl", "cas", "cas_demat", "trade", "demat"})


def map_broker(dp: str) -> str | None:
    u = (dp or "").upper()
    for needle, br in DP_MAP:
        if needle in u:
            return br
    return None


def kafka_broker_code(internal: str | None) -> str | None:
    """Map to Java BrokerType enum names only — never invent codes (breaks CAS_DOCUMENT)."""
    if not internal:
        return None
    return BROKER_KAFKA_CODE.get(internal.lower())


def is_first_class_kafka(code: str | None) -> bool:
    return bool(code) and code.upper() in _FIRST_CLASS


def short_dp_name(dp_name: str | None) -> str:
    """Human list label from DP legal name. Never CDSL / CAS / Trade."""
    raw = (dp_name or "").strip()
    if not raw:
        return "Demat"
    cleaned = _SUFFIX_RE.sub(" ", raw.upper())
    cleaned = re.sub(r"[^A-Z0-9\s]", " ", cleaned)
    tokens = [t for t in cleaned.split() if t]
    if not tokens:
        return "Demat"
    candidate = tokens[0].title()
    if candidate.lower() in _FORBIDDEN_SHORT:
        for t in tokens[1:]:
            alt = t.title()
            if alt.lower() not in _FORBIDDEN_SHORT:
                return alt
        return "Demat"
    return candidate


def resolve_fanout_broker(
    *,
    mapped_broker: str | None,
    dp_name: str | None,
    has_holdings: bool,
) -> tuple[str, str, str] | None:
    """
    Return (internal, kafka_code, portfolio_name) for a valued demat, or None to skip.
    Unmapped / non-first-class valued demats → CAS_DEMAT + short_dp_name.
    """
    if not has_holdings:
        return None
    code = kafka_broker_code(mapped_broker) if mapped_broker else None
    if code and is_first_class_kafka(code):
        display = code.replace("_", " ").title()
        if code == "GROWW":
            display = "Groww"
        elif code == "ANGEL_ONE":
            display = "Angel One"
        return mapped_broker or code.lower(), code, display
    # Valued demat without first-class Kafka broker → named CAS_DEMAT book.
    return "cas_demat", "CAS_DEMAT", short_dp_name(dp_name)
