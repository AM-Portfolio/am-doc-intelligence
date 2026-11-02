"""Unit tests for Gmail as-of resolution."""
from as_of_date import resolve_as_of


def test_prefer_internal_date_ms():
    # 2024-06-15 10:30 IST ≈ 2024-06-15 05:00 UTC
    ms = int(1718427600 * 1000)  # approximate; assert date only via known epoch
    # Use a fixed UTC epoch: 2024-01-15 12:00:00 UTC
    ms = 1705320000000
    as_of, ts = resolve_as_of({"internal_date_ms": ms, "date": "Mon, 01 Jan 2020 00:00:00 +0000"})
    assert as_of is not None
    assert as_of.startswith("2024-01-")
    assert ts is not None


def test_fallback_rfc2822_date():
    as_of, ts = resolve_as_of(
        {"date": "Wed, 15 May 2024 14:22:01 +0530"}
    )
    assert as_of == "2024-05-15"
    assert ts is not None


def test_missing_defaults_to_lookback():
    from datetime import datetime, timedelta, timezone

    try:
        from zoneinfo import ZoneInfo
        ist = ZoneInfo("Asia/Kolkata")
    except Exception:
        ist = timezone.utc
    expected = (datetime.now(ist).date() - timedelta(days=89)).isoformat()
    for meta in (None, {}, {"date": "Unknown"}):
        as_of, ts = resolve_as_of(meta)
        assert as_of == expected
        assert ts is not None
        assert ts.startswith(expected)
