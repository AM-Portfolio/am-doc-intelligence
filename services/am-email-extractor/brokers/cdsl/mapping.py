"""DP name → internal broker id used for Kafka portfolio fan-out."""
from __future__ import annotations

DP_MAP = [
    ("RAISE SECURITIES", "dhan"),
    ("GROWW INVEST TECH", "groww"),
    ("ANGEL ONE", "angleone"),
    ("ZERODHA BROKING", "zerodha"),
    ("UPSTOX SECURITIES", "upstox"),
    ("FYERS SECURITIES", "fyers"),
    ("KOTAK SECURITIES", "kotak"),
    ("MIRAE ASSET", "mirae"),
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
}


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
