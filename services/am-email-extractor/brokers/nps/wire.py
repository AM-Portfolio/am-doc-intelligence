"""Serialize NPS extract → Kafka camelCase payloads."""
from __future__ import annotations

from typing import Any
from uuid import uuid4


def scheme_to_nps_holding(s: dict[str, Any], *, pran: str | None) -> dict[str, Any]:
    units = s.get("units")
    live_nav = s.get("liveNav")
    stmt_nav = s.get("statementNav")
    nav = live_nav if live_nav is not None else stmt_nav
    live_value = s.get("liveValue")
    stmt_value = s.get("statementValue")
    current_value = live_value if live_value is not None else stmt_value
    return {
        "isin": s.get("isin") or s.get("schemeCode"),
        "symbol": s.get("schemeCode") or s.get("isin"),
        "name": s.get("catalogName") or s.get("name"),
        "quantity": units,
        "avgBuyingPrice": stmt_nav,
        "currentPrice": nav,
        "currentValue": current_value,
        "assetClass": "nps",
        "pran": pran,
        "tier": s.get("tier"),
        "schemeClass": s.get("schemeClass"),
        "schemeOption": s.get("option"),
        "schemeCode": s.get("schemeCode"),
        "statementNav": stmt_nav,
        "liveNav": live_nav,
        "isinResolveStatus": s.get("isinResolveStatus"),
        "fundManager": s.get("pf"),
    }


def to_portfolio_update_payload(
    doc: dict[str, Any],
    *,
    user_id: str,
    process_id: str | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    pran = (doc.get("subscriber") or {}).get("pran")
    nps_holdings = []
    for tier in doc.get("tiers") or []:
        for s in tier.get("schemes") or []:
            nps_holdings.append(scheme_to_nps_holding(s, pran=pran))
    total = round(sum(h.get("currentValue") or 0 for h in nps_holdings), 2)
    payload: dict[str, Any] = {
        "id": process_id or str(uuid4()),
        "userId": user_id,
        "brokerType": "NPS",
        "portfolioId": "NPS",
        "name": "NPS",
        "source": "DOCUMENT",
        "documentSource": "NPS_STATEMENT",
        "asOfDate": doc.get("statementTo"),
        "equities": [],
        "mutualFunds": [],
        "npsHoldings": nps_holdings,
        "totalValue": total,
    }
    if timestamp:
        payload["timestamp"] = timestamp
    return payload


def to_nps_document_payload(
    doc: dict[str, Any],
    *,
    user_id: str,
    process_id: str | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": process_id or str(uuid4()),
        "eventType": "NPS_DOCUMENT",
        "source": "DOCUMENT",
        "documentSource": "NPS_STATEMENT",
        "userId": user_id,
        "asOfDate": doc.get("statementTo"),
        "statementFrom": doc.get("statementFrom"),
        "statementTo": doc.get("statementTo"),
        "subscriber": doc.get("subscriber"),
        "tiers": doc.get("tiers"),
        "validation": doc.get("validation"),
    }
    if timestamp:
        payload["timestamp"] = timestamp
    return payload
