"""NPS Kafka messages: 1 holdings + 1 NPS_DOCUMENT envelope."""
from __future__ import annotations

from typing import Any
from uuid import uuid4

from brokers.nps.wire import to_nps_document_payload, to_portfolio_update_payload


def fanout_messages(
    doc: dict[str, Any],
    *,
    user_id: str,
    timestamp: str | None = None,
) -> list[dict[str, Any]]:
    return [
        to_portfolio_update_payload(
            doc, user_id=user_id, process_id=str(uuid4()), timestamp=timestamp
        ),
        to_nps_document_payload(
            doc, user_id=user_id, process_id=str(uuid4()), timestamp=timestamp
        ),
    ]
