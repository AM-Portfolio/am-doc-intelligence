"""Fetch live NPS NAV (+ optional ISIN meta) via market-data MARKET_DATA_BASE_URL.

Uses POST /v1/nps/nav/batch and GET /v1/nps/schemes/{code}.
Fail-open when MARKET_DATA_BASE_URL unset or market returns errors.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, Iterable, List, Optional

import requests

from security_enrichment import market_data_base_url

logger = logging.getLogger(__name__)


def _headers() -> Dict[str, str]:
    h = {"Content-Type": "application/json", "Accept": "application/json"}
    auth = os.environ.get("MARKET_DATA_AUTHORIZATION") or os.environ.get("AUTHORIZATION")
    if auth:
        h["Authorization"] = auth
    return h


def fetch_scheme(scheme_code: str, *, timeout_s: float = 15.0) -> Dict[str, Any]:
    """GET /v1/nps/schemes/{code} → {isin, schemeCode, nav, name, ...}."""
    code = (scheme_code or "").strip().upper()
    if not code:
        return {}
    base = market_data_base_url()
    if not base:
        logger.warning("MARKET_DATA_BASE_URL unset; skipping NPS market enrich")
        return {}
    try:
        r = requests.get(
            f"{base}/v1/nps/schemes/{code}",
            headers=_headers(),
            timeout=timeout_s,
        )
        if r.status_code >= 400:
            logger.warning("NPS scheme HTTP %s for %s: %s", r.status_code, code, (r.text or "")[:200])
            return {}
        body = r.json() if r.content else {}
        return body if isinstance(body, dict) else {}
    except Exception as e:
        logger.warning("NPS scheme fetch failed for %s: %s", code, e)
        return {}


def enrich_navs(scheme_codes: Iterable[str], *, timeout_s: float = 30.0) -> Dict[str, float]:
    """POST /v1/nps/nav/batch → map schemeCode → nav."""
    unique: List[str] = []
    seen = set()
    for raw in scheme_codes or []:
        code = (raw or "").strip().upper()
        if not code or code in seen:
            continue
        seen.add(code)
        unique.append(code)
    if not unique:
        return {}

    base = market_data_base_url()
    if not base:
        logger.warning("MARKET_DATA_BASE_URL unset; skipping NPS NAV enrich")
        return {}

    try:
        r = requests.post(
            f"{base}/v1/nps/nav/batch",
            json={"schemeCodes": unique},
            headers=_headers(),
            timeout=timeout_s,
        )
        if r.status_code >= 400:
            logger.warning("NPS nav/batch HTTP %s: %s", r.status_code, (r.text or "")[:300])
            return {}
        body = r.json() if r.content else {}
        if not isinstance(body, dict):
            return {}
        out: Dict[str, float] = {}
        for k, v in body.items():
            try:
                out[str(k).upper()] = float(v)
            except (TypeError, ValueError):
                continue
        return out
    except Exception as e:
        logger.warning("NPS nav/batch failed: %s", e)
        return {}


def resolve_key(
    *,
    pf: str,
    scheme: str,
    tier: str,
    option: str = "POP",
    timeout_s: float = 15.0,
) -> Dict[str, Any]:
    """GET /v1/nps/resolve — market SoT for isin/schemeCode (+ nav when available)."""
    base = market_data_base_url()
    if not base:
        return {"isinResolveStatus": "UNMAPPED"}
    try:
        r = requests.get(
            f"{base}/v1/nps/resolve",
            params={"pf": pf, "scheme": scheme, "tier": tier, "option": option},
            headers=_headers(),
            timeout=timeout_s,
        )
        if r.status_code >= 400:
            return {"isinResolveStatus": "UNMAPPED"}
        body = r.json() if r.content else {}
        return body if isinstance(body, dict) else {"isinResolveStatus": "UNMAPPED"}
    except Exception as e:
        logger.warning("NPS resolve failed: %s", e)
        return {"isinResolveStatus": "UNMAPPED"}
