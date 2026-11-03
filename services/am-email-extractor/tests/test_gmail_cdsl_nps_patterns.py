"""Gmail discovery defaults include CDSL CAS and NPS."""

from gmail_integration import DEFAULT_BROKER_PATTERNS


def test_default_patterns_include_cdsl_and_nps():
    assert "cdsl" in DEFAULT_BROKER_PATTERNS
    assert "nps" in DEFAULT_BROKER_PATTERNS
    assert DEFAULT_BROKER_PATTERNS["cdsl"]["file_pattern"] == [".pdf"]
    assert DEFAULT_BROKER_PATTERNS["nps"]["file_pattern"] == [".pdf"]
    assert "cdslstatement.com" in DEFAULT_BROKER_PATTERNS["cdsl"]["from"].lower()
    assert "proteantech.in" in DEFAULT_BROKER_PATTERNS["nps"]["from"].lower()
    assert "consolidated account statement" in (
        DEFAULT_BROKER_PATTERNS["cdsl"]["subject"] or ""
    ).lower()
    assert "monthly transaction statement" in (
        DEFAULT_BROKER_PATTERNS["nps"]["subject"] or ""
    ).lower()
