"""Resolve (pf, scheme, tier, option) → CRA schemeCode / isin via YAML catalog."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import re

_CATALOG_PATH = Path(__file__).resolve().parent / "isin_catalog.yaml"

_PF_ALIASES = (
    ("HDFC", "hdfc"),
    ("SBI PENSION", "sbi"),
    ("ICICI", "icici"),
    ("KOTAK", "kotak"),
    ("LIC ", "lic"),
    ("UTI ", "uti"),
    ("ADITYA BIRLA", "aditya_birla"),
    ("TATA", "tata"),
    ("MAX LIFE", "max"),
)


def slug_pf(scheme_name: str) -> Optional[str]:
    u = (scheme_name or "").upper()
    for needle, slug in _PF_ALIASES:
        if needle in u:
            return slug
    return None


def parse_scheme_class(scheme_name: str) -> Optional[str]:
    u = (scheme_name or "").upper()
    # Prefer "SCHEME E" / "SCHEME C" / "SCHEME G" / "SCHEME A"
    m = re.search(r"SCHEME\s+([ECGA])\b", u)
    if m:
        return m.group(1)
    return None


def parse_option(scheme_name: str) -> str:
    u = (scheme_name or "").upper()
    if "DIRECT" in u:
        return "DIRECT"
    if "POP" in u:
        return "POP"
    return "POP"


@lru_cache(maxsize=1)
def _load_catalog() -> list[dict[str, Any]]:
    try:
        import yaml
    except ImportError:
        # Minimal YAML subset parser for our flat list (no PyYAML in some envs)
        return _load_catalog_simple()
    data = yaml.safe_load(_CATALOG_PATH.read_text(encoding="utf-8")) or {}
    return list(data.get("entries") or [])


def _load_catalog_simple() -> list[dict[str, Any]]:
    """Fallback when PyYAML missing — parse our known flat entry blocks."""
    text = _CATALOG_PATH.read_text(encoding="utf-8")
    entries: list[dict[str, Any]] = []
    cur: dict[str, Any] = {}
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("  - pf:"):
            if cur:
                entries.append(cur)
            cur = {"pf": line.split(":", 1)[1].strip()}
        elif line.startswith("    ") and ":" in line and cur is not None:
            k, v = line.strip().split(":", 1)
            cur[k.strip()] = v.strip()
    if cur:
        entries.append(cur)
    return entries


def resolve(
    *,
    pf: str | None,
    scheme: str | None,
    tier: str | None,
    option: str | None,
) -> dict[str, Any]:
    """
    Returns {isin, schemeCode, name, isinResolveStatus: MAPPED|UNMAPPED}.

    Prefers market-data GET /v1/nps/resolve when MARKET_DATA_BASE_URL is set;
    falls back to local isin_catalog.yaml.
    """
    if not pf or not scheme or not tier:
        return {
            "isin": None,
            "schemeCode": None,
            "name": None,
            "isinResolveStatus": "UNMAPPED",
        }
    opt = (option or "POP").upper()
    key_pf = pf.lower()
    key_scheme = scheme.upper()
    key_tier = tier.upper().replace("TIER", "").strip()
    if key_tier in ("1", "I"):
        key_tier = "I"
    elif key_tier in ("2", "II"):
        key_tier = "II"

    # Market SoT for ISIN when reachable
    try:
        from brokers.nps.nav_enrich import resolve_key
        from security_enrichment import market_data_base_url

        if market_data_base_url():
            remote = resolve_key(pf=key_pf, scheme=key_scheme, tier=key_tier, option=opt)
            if remote.get("isinResolveStatus") == "MAPPED" and (
                remote.get("isin") or remote.get("schemeCode")
            ):
                code = remote.get("schemeCode") or remote.get("isin")
                return {
                    "isin": remote.get("isin") or code,
                    "schemeCode": code,
                    "name": remote.get("name"),
                    "isinResolveStatus": "MAPPED",
                }
    except Exception:
        pass

    for e in _load_catalog():
        if (
            str(e.get("pf", "")).lower() == key_pf
            and str(e.get("scheme", "")).upper() == key_scheme
            and str(e.get("tier", "")).upper() == key_tier
            and str(e.get("option", "")).upper() == opt
        ):
            code = e.get("schemeCode") or e.get("isin")
            return {
                "isin": e.get("isin") or code,
                "schemeCode": code,
                "name": e.get("name"),
                "isinResolveStatus": "MAPPED",
            }
    return {
        "isin": None,
        "schemeCode": None,
        "name": None,
        "isinResolveStatus": "UNMAPPED",
    }


def resolve_from_scheme_name(scheme_name: str, tier: str) -> dict[str, Any]:
    return resolve(
        pf=slug_pf(scheme_name),
        scheme=parse_scheme_class(scheme_name),
        tier=tier,
        option=parse_option(scheme_name),
    )
