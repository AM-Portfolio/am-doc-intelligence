"""Build N per-DP PortfolioUpdate payloads + 1 CAS_DOCUMENT envelope."""
from __future__ import annotations

from typing import Any
from uuid import uuid4

from brokers._common.models import CasDocument, HoldingLine
from brokers.cdsl.mapping import kafka_broker_code
from brokers.cdsl.wire import (
    holding_to_equity_dict,
    holding_to_mf_dict,
    to_cas_document_payload,
    to_portfolio_update_payload,
)


def fanout_messages(
    doc: CasDocument,
    *,
    user_id: str,
    as_of_date: str | None = None,
    timestamp: str | None = None,
) -> list[dict[str, Any]]:
    """Return Kafka-ready dicts: mapped DP holdings first, then CAS envelope."""
    as_of = as_of_date or doc.as_of_date
    messages: list[dict[str, Any]] = []

    for acct in doc.demat_accounts:
        # Only fan out brokers that map to a Java BrokerType code; unknown DPs
        # (e.g. nsdl_fourdegreewater) go into the CDSL book / CAS directory only.
        if not acct.mapped_broker or not acct.holdings or not kafka_broker_code(acct.mapped_broker):
            continue
        equities = [holding_to_equity_dict(h) for h in acct.holdings]
        messages.append(
            to_portfolio_update_payload(
                user_id=user_id,
                broker_internal=acct.mapped_broker,
                equities=equities,
                as_of_date=as_of,
                demat=acct,
                process_id=str(uuid4()),
                timestamp=timestamp,
            )
        )

    # One CDSL book: MF folios + unmapped demat equities (unique owner+brokerType index)
    mfs: list[dict[str, Any]] = []
    for folio in doc.mf_folios:
        for h in folio.holdings:
            mfs.append(holding_to_mf_dict(h, folio))
    unmapped_eq: list[dict[str, Any]] = []
    for acct in doc.demat_accounts:
        # Unmapped OR mapped-but-not-in-BrokerType enum → CDSL book
        if not acct.holdings:
            continue
        if acct.mapped_broker and kafka_broker_code(acct.mapped_broker):
            continue
        unmapped_eq.extend(holding_to_equity_dict(h) for h in acct.holdings)
    if mfs or unmapped_eq:
        total = round(
            sum(f.holdings_value_sum for f in doc.mf_folios)
            + sum(e.get("currentValue") or 0 for e in unmapped_eq),
            2,
        )
        messages.append(
            to_portfolio_update_payload(
                user_id=user_id,
                broker_internal="cdsl",
                equities=unmapped_eq,
                mutual_funds=mfs,
                as_of_date=as_of,
                total_value=total,
                process_id=str(uuid4()),
                timestamp=timestamp,
                portfolio_name="CDSL CAS",
            )
        )

    messages.append(
        to_cas_document_payload(
            doc,
            user_id=user_id,
            process_id=str(uuid4()),
            timestamp=timestamp,
        )
    )
    return messages
