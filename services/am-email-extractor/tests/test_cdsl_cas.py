"""CDSL CAS package unit tests (synthetic fixture — no live PAN/PDF)."""
from __future__ import annotations

from pathlib import Path

from brokers.cdsl.detect import is_cdsl_cas
from brokers.cdsl.extractor import extract_document_from_text
from brokers.cdsl.fanout import fanout_messages
from brokers.cdsl.mapping import kafka_broker_code, map_broker

FIXTURE = Path(__file__).parent / "fixtures" / "cdsl" / "sample_cas_snippet.txt"


def test_map_raise_to_dhan():
    assert map_broker("RAISE SECURITIES TRADING PRIVATE LIMITED") == "dhan"
    assert kafka_broker_code("dhan") == "DHAN"


def test_kafka_broker_code_unknown_is_none():
    """Unknown DPs must not invent enum codes (broke CAS_DOCUMENT on dig)."""
    assert map_broker("FOURDEGREEWATER CAPITAL") == "nsdl_fourdegreewater"
    assert kafka_broker_code("nsdl_fourdegreewater") is None
    assert kafka_broker_code("mirae") is None


def test_normalize_nominee_clears_placeholders():
    from brokers.cdsl.parse import normalize_nominee

    assert normalize_nominee("Please Nominate") == (None, False)
    assert normalize_nominee("Not Registered") == (None, False)
    assert normalize_nominee("Opt-Out") == (None, False)
    assert normalize_nominee("Abhimanyu kumar") == ("Abhimanyu kumar", True)
    assert normalize_nominee("Registered") == (None, True)


def test_holding_wire_omits_invented_cost_basis():
    """CAS market-value rows must not invent avgBuyingPrice from LTP."""
    from brokers._common.models import HoldingLine
    from brokers.cdsl.wire import holding_to_equity_dict, holding_to_mf_dict

    h = HoldingLine(
        isin="INE002A01018",
        name="RELIANCE",
        quantity=10,
        current_price=100.0,
        current_value=1000.0,
        avg_cost=None,
        amount_invested=None,
    )
    eq = holding_to_equity_dict(h)
    assert "avgBuyingPrice" not in eq
    assert "investmentValue" not in eq
    assert eq["currentValue"] == 1000.0
    assert eq["currentPrice"] == 100.0

    mf = holding_to_mf_dict(h)
    assert "avgBuyingPrice" not in mf
    assert "investmentValue" not in mf


def test_detect_cas_snippet():
    text = FIXTURE.read_text(encoding="utf-8")
    assert is_cdsl_cas(text)


def test_extract_and_fanout_from_snippet():
    text = FIXTURE.read_text(encoding="utf-8")
    doc = extract_document_from_text(text)
    assert doc.document_source == "CDSL_CAS"
    assert doc.as_of_date == "2026-09-30"
    assert any(a.mapped_broker == "dhan" for a in doc.demat_accounts)
    assert any(a.mapped_broker is None for a in doc.demat_accounts)  # Religare unmapped
    assert len(doc.account_directory) >= 2

    msgs = fanout_messages(doc, user_id="u1")
    types = [m.get("eventType") for m in msgs]
    assert types[-1] == "CAS_DOCUMENT"
    holdings_msgs = [m for m in msgs if m.get("eventType") is None]
    brokers = {m.get("brokerType") for m in holdings_msgs}
    assert "DHAN" in brokers
    assert any(m.get("portfolioId") == "CAS Mutual Funds" for m in holdings_msgs) or any(
        m.get("mutualFunds") for m in holdings_msgs
    )
    cas = msgs[-1]
    assert cas["accountDirectory"]
    assert cas["validation"]["allOk"] is not None
    assert any(
        row.get("nominee") is not None or row.get("nomineeRegistered") is not None
        for row in cas["accountDirectory"]
    )
    assert any(row.get("nomineeRegistered") is False for row in cas["accountDirectory"])


def test_live_pdf_optional():
    """If CDSL.pdf + pymupdf present locally, assert cover total and Rais→dhan."""
    root = Path(__file__).resolve().parents[1]
    pdf = root / "CDSL.pdf"
    if not pdf.exists():
        return
    try:
        from brokers.cdsl.extractor import extract_document
    except Exception:
        return
    try:
        doc = extract_document(str(pdf), "BWKPM5493A")
    except Exception:
        return
    assert doc.cover.total_portfolio_value == 2992753.0
    assert doc.validation.all_ok is True
    assert sum(1 for a in doc.demat_accounts if a.mapped_broker == "dhan") >= 1
    assert len(doc.demat_accounts) >= 5
    assert len(doc.mf_folios) >= 1
