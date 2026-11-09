"""Build N per-DP PortfolioUpdate payloads + 1 CAS_DOCUMENT envelope."""
from __future__ import annotations

from typing import Any
from uuid import uuid4

from brokers._common.models import CasDocument
from brokers.cdsl.mapping import is_first_class_kafka, resolve_fanout_broker
from brokers.cdsl.wire import (
    holding_to_equity_dict,
    holding_to_mf_dict,
    to_cas_document_payload,
    to_portfolio_update_payload,
)

MF_CAS_BOID = "mf:cas"


def fanout_messages(
    doc: CasDocument,
    *,
    user_id: str,
    as_of_date: str | None = None,
    timestamp: str | None = None,
    identity_match: str | None = None,
    holder_name: str | None = None,
    holder_email: str | None = None,
    holder_pan: str | None = None,
) -> list[dict[str, Any]]:
    """Return Kafka-ready dicts: named demat books, MF book, CDSL residual/clear, CAS envelope."""
    as_of = as_of_date or doc.as_of_date
    messages: list[dict[str, Any]] = []
    id_kw = dict(
        identity_match=identity_match,
        holder_name=holder_name,
        holder_email=holder_email,
        holder_pan=holder_pan or doc.holder_pan,
    )
    placed_boids: set[str] = set()

    for acct in doc.demat_accounts:
        resolved = resolve_fanout_broker(
            mapped_broker=acct.mapped_broker,
            dp_name=acct.dp_name,
            has_holdings=bool(acct.holdings),
            statement_value=acct.holdings_value_sum,
        )
        if not resolved:
            continue
        internal, code, portfolio_name = resolved
        equities = [holding_to_equity_dict(h) for h in acct.holdings]
        # First-class: no dematRef on wire (keep single Groww book). CAS_DEMAT: dematRef=BOID.
        attach_demat = not is_first_class_kafka(code)
        messages.append(
            to_portfolio_update_payload(
                user_id=user_id,
                broker_internal=internal,
                equities=equities,
                as_of_date=as_of,
                demat=acct if attach_demat else None,
                total_value=acct.holdings_value_sum,
                process_id=str(uuid4()),
                timestamp=timestamp,
                portfolio_name=portfolio_name,
                include_demat_ref=attach_demat,
                **id_kw,
            )
        )
        if acct.boid:
            placed_boids.add(acct.boid)

    # MF folios → named Mutual Funds book (never CDSL label).
    # Emit when scheme lines exist OR folio/cover value is greater than 0.
    mfs: list[dict[str, Any]] = []
    for folio in doc.mf_folios:
        for h in folio.holdings:
            mfs.append(holding_to_mf_dict(h, folio))
    mf_total = round(sum(f.holdings_value_sum for f in doc.mf_folios), 2)
    if mfs or mf_total > 0:
        messages.append(
            to_portfolio_update_payload(
                user_id=user_id,
                broker_internal="cas_demat",
                equities=[],
                mutual_funds=mfs,
                as_of_date=as_of,
                total_value=mf_total,
                process_id=str(uuid4()),
                timestamp=timestamp,
                portfolio_name="Mutual Funds",
                demat_boid_override=MF_CAS_BOID,
                include_demat_ref=True,
                **id_kw,
            )
        )

    # Always emit CDSL residual/clear so upsert replaces stale valued dump.
    residual_eq: list[dict[str, Any]] = []
    for acct in doc.demat_accounts:
        if not acct.holdings:
            continue
        if acct.boid and acct.boid in placed_boids:
            continue
        # Skip if resolve would place it (should already be in placed_boids)
        if resolve_fanout_broker(
            mapped_broker=acct.mapped_broker,
            dp_name=acct.dp_name,
            has_holdings=True,
            statement_value=acct.holdings_value_sum,
        ):
            continue
        residual_eq.extend(holding_to_equity_dict(h) for h in acct.holdings)
    residual_total = round(sum(e.get("currentValue") or 0 for e in residual_eq), 2)
    messages.append(
        to_portfolio_update_payload(
            user_id=user_id,
            broker_internal="cdsl",
            equities=residual_eq,
            mutual_funds=[],
            as_of_date=as_of,
            total_value=residual_total,
            process_id=str(uuid4()),
            timestamp=timestamp,
            portfolio_name="CDSL CAS",
            include_demat_ref=False,
            **id_kw,
        )
    )

    messages.append(
        to_cas_document_payload(
            doc,
            user_id=user_id,
            process_id=str(uuid4()),
            timestamp=timestamp,
            **id_kw,
        )
    )
    return messages
