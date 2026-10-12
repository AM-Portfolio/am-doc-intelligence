"""
Enrich statement holdings via market-data batch-search (ISIN → symbol/sector/name).

Fail-open: network/API errors return empty maps so Kafka still publishes isin+qty.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, Iterable, List, Optional

import requests

logger = logging.getLogger(__name__)

# API hard cap (am-market-data BATCH_SEARCH_MAX_QUERIES)
_MAX_QUERIES = 1000
_DEFAULT_TIMEOUT_S = 60.0


def market_data_base_url() -> str:
    return (
        os.environ.get("MARKET_DATA_BASE_URL")
        or os.environ.get("MARKET_DATA_API_URL")
        or ""
    ).rstrip("/")


def _chunked(items: List[str], size: int) -> Iterable[List[str]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def _best_match(matches: List[dict]) -> Optional[dict]:
    if not matches:
        return None
    return max(matches, key=lambda m: float(m.get("matchScore") or 0.0))


def _match_to_enrichment(match: dict) -> Dict[str, Any]:
    name = (match.get("companyName") or match.get("name") or "").strip() or None
    return {
        "symbol": (match.get("symbol") or "").strip() or None,
        "sector": (match.get("sector") or "").strip() or None,
        "industry": (match.get("industry") or "").strip() or None,
        "name": name,
        "companyName": name,
        "marketCap": match.get("marketCapValue"),
        "marketCapType": match.get("marketCapType"),
    }


def enrich_by_isins(
    isins: Iterable[str],
    *,
    authorization: Optional[str] = None,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> Dict[str, Dict[str, Any]]:
    """
    POST /v1/securities/batch-search with searchFields=["ISIN"].

    Returns map: ISIN (upper) → {symbol, sector, name, companyName, ...}.
    """
    unique: List[str] = []
    seen = set()
    for raw in isins or []:
        isin = (raw or "").strip().upper()
        if not isin or isin in seen:
            continue
        seen.add(isin)
        unique.append(isin)

    if not unique:
        return {}

    base = market_data_base_url()
    if not base:
        logger.warning("MARKET_DATA_BASE_URL unset; skipping security enrichment")
        return {}

    url = f"{base}/v1/securities/batch-search"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if authorization:
        headers["Authorization"] = authorization

    out: Dict[str, Dict[str, Any]] = {}
    try:
        for chunk in _chunked(unique, _MAX_QUERIES):
            payload = {
                "queries": chunk,
                "limit": 1,
                "searchFields": ["ISIN"],
                "minMatchScore": 0.0,
            }
            try:
                resp = requests.post(url, json=payload, headers=headers, timeout=timeout_s)
                if resp.status_code >= 400:
                    logger.warning(
                        "batch-search HTTP %s: %s",
                        resp.status_code,
                        (resp.text or "")[:300],
                    )
                    continue
                body = resp.json() if resp.content else {}
            except Exception as exc:
                logger.warning("batch-search request failed: %s", exc)
                continue

            for result in body.get("results") or []:
                query = (result.get("query") or "").strip().upper()
                best = _best_match(result.get("matches") or [])
                if not query or not best:
                    continue
                out[query] = _match_to_enrichment(best)
    except Exception as exc:
        logger.warning("security enrichment failed open: %s", exc)
        return out

    return out
