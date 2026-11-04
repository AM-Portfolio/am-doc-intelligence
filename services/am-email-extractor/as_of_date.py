"""Resolve Gmail message as-of calendar day (Asia/Kolkata) for portfolio history."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Optional, Tuple

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None  # type: ignore


IST = ZoneInfo("Asia/Kolkata") if ZoneInfo else None

# When Gmail date is missing, stamp ~90d so portfolio FULL catch-up has a lifeStart
# without falling through to Kafka ingest "now" (which yields empty TF charts).
_DEFAULT_LOOKBACK_DAYS = 89


def _default_as_of() -> Tuple[str, str]:
    now = datetime.now(IST) if IST is not None else datetime.now(timezone.utc)
    day = now.date() - timedelta(days=_DEFAULT_LOOKBACK_DAYS)
    timestamp = datetime.combine(day, datetime.min.time()).isoformat(timespec="seconds")
    return day.isoformat(), timestamp


def resolve_as_of(
    email_meta: Optional[dict[str, Any]],
) -> Tuple[str, str]:
    """
    Returns (as_of_date YYYY-MM-DD, timestamp ISO) for Kafka PortfolioUpdateEvent.

    Prefer Gmail internalDate (ms epoch); fallback RFC 2822 Date header.
    Always returns a date so the next email sync auto-builds history (no manual fill).
    """
    if not email_meta:
        return _default_as_of()

    dt: Optional[datetime] = None
    internal_ms = email_meta.get("internal_date_ms")
    if internal_ms is not None:
        try:
            dt = datetime.fromtimestamp(int(internal_ms) / 1000.0, tz=timezone.utc)
        except (TypeError, ValueError, OSError):
            dt = None

    if dt is None:
        raw = email_meta.get("date")
        if raw and raw != "Unknown":
            try:
                parsed = parsedate_to_datetime(raw)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                dt = parsed
            except (TypeError, ValueError, IndexError):
                dt = None

    if dt is None:
        return _default_as_of()

    if IST is not None:
        local = dt.astimezone(IST)
    else:
        local = dt.astimezone(timezone.utc)

    as_of_date = local.date().isoformat()
    # Naive local wall time for Jackson LocalDateTime (same convention as prior utcnow ISO)
    timestamp = local.replace(tzinfo=None).isoformat(timespec="seconds")
    return as_of_date, timestamp
