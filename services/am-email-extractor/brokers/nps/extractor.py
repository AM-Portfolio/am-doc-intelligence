"""NPS statement entrypoints."""
from __future__ import annotations

from typing import Any

from brokers._common.pdf_text import load_pdf_text
from brokers.nps.detect import is_nps_statement
from brokers.nps.nav_enrich import enrich_navs
from brokers.nps.parse import parse_nps_text


def _apply_live_nav(doc: dict[str, Any]) -> dict[str, Any]:
    codes = []
    for tier in doc.get("tiers") or []:
        for s in tier.get("schemes") or []:
            c = s.get("schemeCode") or s.get("isin")
            if c:
                codes.append(c)
    navs = enrich_navs(codes)
    for tier in doc.get("tiers") or []:
        for s in tier.get("schemes") or []:
            code = (s.get("schemeCode") or s.get("isin") or "").upper()
            live = navs.get(code)
            if live is not None:
                s["liveNav"] = live
                units = s.get("units") or 0
                s["liveValue"] = round(units * live, 2)
    return doc


def extract_document_from_text(text: str, *, enrich_live_nav: bool = True) -> dict[str, Any]:
    if not is_nps_statement(text):
        raise ValueError("PDF text does not look like an NPS Transaction Statement")
    doc = parse_nps_text(text)
    if enrich_live_nav:
        doc = _apply_live_nav(doc)
    return doc


def extract_document(
    file_path: str, password: str | None = None, *, enrich_live_nav: bool = True
) -> dict[str, Any]:
    text = load_pdf_text(file_path, password)
    return extract_document_from_text(text, enrich_live_nav=enrich_live_nav)


def extract_holdings(file_path: str, password: str | None = None) -> list[dict[str, Any]]:
    """Legacy flat list for Mongo / API."""
    from brokers.nps.wire import scheme_to_nps_holding

    doc = extract_document(file_path, password)
    pran = (doc.get("subscriber") or {}).get("pran")
    rows = []
    for tier in doc.get("tiers") or []:
        for s in tier.get("schemes") or []:
            h = scheme_to_nps_holding(s, pran=pran)
            # legacy keys for holdings_for_portfolio_event
            h["isin_code"] = h.get("isin")
            h["company_name"] = h.get("name")
            h["current_bal"] = h.get("quantity")
            h["rate"] = h.get("currentPrice")
            h["value"] = h.get("currentValue")
            rows.append(h)
    return rows
