"""Serialize CasDocument / holdings to Kafka camelCase payloads (Java twins)."""
from __future__ import annotations

from typing import Any, Optional
from uuid import uuid4

from brokers._common.models import CasDocument, DematAccountExtract, HoldingLine, MfFolioExtract
from brokers.cdsl.mapping import kafka_broker_code


def holding_to_equity_dict(h: HoldingLine) -> dict[str, Any]:
    # CDSL CAS usually has market value only — never invent avg/cost from LTP
    # (that poisoned invested/return on the dashboard).
    d: dict[str, Any] = {
        "isin": h.isin,
        "companyName": h.name,
        "name": h.name,
        "symbol": h.isin,
        "quantity": h.quantity,
        "currentValue": h.current_value,
        "assetClass": h.asset_class,
    }
    if h.current_price is not None:
        d["currentPrice"] = h.current_price
    if h.avg_cost is not None:
        d["avgBuyingPrice"] = h.avg_cost
    if h.amount_invested is not None:
        d["investmentValue"] = h.amount_invested
    return {k: v for k, v in d.items() if v is not None}


def holding_to_mf_dict(h: HoldingLine, folio: MfFolioExtract | None = None) -> dict[str, Any]:
    d: dict[str, Any] = {
        "isin": h.isin,
        "name": h.name,
        "symbol": h.isin,
        "quantity": h.quantity,
        "nav": h.current_price,
        "currentValue": h.current_value,
        "assetClass": h.asset_class or "mutual_fund_folio",
        "schemeCode": h.scheme_code,
        "folioNumber": (folio.folio if folio else None) or h.folio,
    }
    if h.avg_cost is not None:
        d["avgBuyingPrice"] = h.avg_cost
    if h.amount_invested is not None:
        d["investmentValue"] = h.amount_invested
    if folio:
        d["amcName"] = folio.amc_name
        d["rtaName"] = folio.rta_name
        d["advisorName"] = folio.advisor_name
        d["ucc"] = folio.ucc
    return {k: v for k, v in d.items() if v is not None}


def demat_ref(acct: DematAccountExtract) -> dict[str, Any]:
    return {
        "boid": acct.boid,
        "dpId": acct.dp_id,
        "clientId": acct.client_id,
        "dpName": acct.dp_name,
    }


def to_portfolio_update_payload(
    *,
    user_id: str,
    broker_internal: str,
    equities: list[dict[str, Any]],
    mutual_funds: list[dict[str, Any]] | None = None,
    as_of_date: str | None = None,
    demat: DematAccountExtract | None = None,
    total_value: float | None = None,
    process_id: str | None = None,
    timestamp: str | None = None,
    portfolio_name: str | None = None,
    identity_match: str | None = None,
    holder_name: str | None = None,
    holder_email: str | None = None,
    holder_pan: str | None = None,
) -> dict[str, Any]:
    code = kafka_broker_code(broker_internal)
    if not code:
        raise ValueError(
            f"broker_internal={broker_internal!r} is not a known Kafka BrokerType; "
            "fanout must skip unknown DPs"
        )
    default_name = code.replace("_", " ").title()
    payload: dict[str, Any] = {
        "id": process_id or str(uuid4()),
        "userId": user_id,
        "brokerType": code,
        "portfolioId": portfolio_name or default_name,
        "name": portfolio_name or default_name,
        "source": "DOCUMENT",
        "documentSource": "CDSL_CAS",
        "equities": equities,
        "mutualFunds": mutual_funds or [],
    }
    if identity_match:
        payload["identityMatch"] = identity_match
    if holder_name:
        payload["holderName"] = holder_name
    if holder_email:
        payload["holderEmail"] = holder_email
    if holder_pan:
        payload["holderPan"] = holder_pan
    if as_of_date:
        payload["asOfDate"] = as_of_date
    if timestamp:
        payload["timestamp"] = timestamp
    if demat:
        payload["dematRef"] = demat_ref(demat)
        if total_value is None:
            total_value = demat.holdings_value_sum
    if total_value is not None:
        payload["totalValue"] = total_value
    return payload


def to_cas_document_payload(
    doc: CasDocument,
    *,
    user_id: str,
    process_id: str | None = None,
    timestamp: str | None = None,
    identity_match: str | None = None,
    holder_name: str | None = None,
    holder_email: str | None = None,
    holder_pan: str | None = None,
) -> dict[str, Any]:
    unmapped: list[dict[str, Any]] = []
    for acct in doc.demat_accounts:
        if acct.mapped_broker:
            continue
        unmapped.append(
            {
                "boid": acct.boid,
                "dpName": acct.dp_name,
                "equities": [holding_to_equity_dict(h) for h in acct.holdings],
            }
        )

    mf_folios = []
    for folio in doc.mf_folios:
        mf_folios.append(
            {
                "folio": folio.folio,
                "amcName": folio.amc_name,
                "rtaName": folio.rta_name,
                "advisorName": folio.advisor_name,
                "ucc": folio.ucc,
                "holdings": [holding_to_mf_dict(h, folio) for h in folio.holdings],
            }
        )

    directory = []
    for row in doc.account_directory:
        directory.append(
            {
                "accountNo": row.account_no,
                "accountType": row.account_type,
                "status": row.status,
                "email": row.email,
                "mobile": row.mobile,
                "holderName": row.holder_name,
                "dpId": row.dp_id,
                "clientId": row.client_id,
                "boid": row.boid,
                "nominee": row.nominee,
                "nomineeRegistered": row.nominee_registered,
                "frozenStatus": row.frozen_status,
                "holdingValue": row.holding_value,
                "mappedBroker": kafka_broker_code(row.mapped_broker) if row.mapped_broker else None,
                "dpName": row.dp_name,
                "amcName": row.amc_name,
                "folio": row.folio,
                "active": row.active,
            }
        )

    cover = doc.cover
    validation = doc.validation
    payload: dict[str, Any] = {
        "id": process_id or str(uuid4()),
        "eventType": "CAS_DOCUMENT",
        "source": "DOCUMENT",
        "documentSource": doc.document_source,
        "userId": user_id,
        "asOfDate": doc.as_of_date,
        "statementFrom": doc.statement_from,
        "statementTo": doc.statement_to,
        "cover": {
            "totalAccounts": cover.total_accounts,
            "dematAccounts": cover.demat_accounts,
            "mfFolios": cover.mf_folios,
            "totalValue": cover.total_portfolio_value,
            "cdslDematAccounts": cover.cdsl_demat_accounts,
            "nsdlDematAccounts": cover.nsdl_demat_accounts,
            "mutualFundFolios": cover.mutual_fund_folios,
        },
        "validation": {
            "allOk": validation.all_ok,
            "extractedTotal": validation.extracted_total,
            "extractedByAssetClass": validation.extracted_by_asset_class,
            "checks": [
                {
                    "name": c.name,
                    "expected": c.expected,
                    "actual": c.actual,
                    "diff": c.diff,
                    "ok": c.ok,
                }
                for c in validation.checks
            ],
        },
        "accountDirectory": directory,
        "mfFolios": mf_folios,
        "unmappedDematHoldings": unmapped,
    }
    if identity_match:
        payload["identityMatch"] = identity_match
    if holder_name:
        payload["holderName"] = holder_name
    if holder_email:
        payload["holderEmail"] = holder_email
    if holder_pan:
        payload["holderPan"] = holder_pan
    if timestamp:
        payload["timestamp"] = timestamp
    return payload
