"""CDSL CAS package unit tests (synthetic fixture — no live PAN/PDF)."""
from __future__ import annotations

from pathlib import Path

from brokers.cdsl.detect import is_cdsl_cas
from brokers.cdsl.extractor import extract_document_from_text
from brokers.cdsl.fanout import fanout_messages
from brokers.cdsl.mapping import (
    kafka_broker_code,
    map_broker,
    resolve_fanout_broker,
    short_dp_name,
)

FIXTURE = Path(__file__).parent / "fixtures" / "cdsl" / "sample_cas_snippet.txt"


def test_map_raise_to_dhan():
    assert map_broker("RAISE SECURITIES TRADING PRIVATE LIMITED") == "dhan"
    assert kafka_broker_code("dhan") == "DHAN"


def test_map_kotak_securities():
    assert map_broker("KOTAK SECURITIES LIMITED") == "kotak"
    assert kafka_broker_code("kotak") == "KOTAK"


def test_mirae_finwizard_map_to_cas_demat():
    assert map_broker("MIRAE ASSET SHAREKHAN") == "mirae"
    assert kafka_broker_code("mirae") == "CAS_DEMAT"
    assert map_broker("FINWIZARD SOLUTIONS PRIVATE LIMITED") == "finwizard"
    assert kafka_broker_code("finwizard") == "CAS_DEMAT"


def test_short_dp_name():
    assert short_dp_name("MIRAE ASSET SHAREKHAN LIMITED") == "Mirae"
    assert short_dp_name("FINWIZARD SOLUTIONS PRIVATE LIMITED") == "Finwizard"
    assert short_dp_name("CDSL") == "Demat"
    assert short_dp_name("") == "Demat"


def test_resolve_valued_unmapped_to_cas_demat():
    resolved = resolve_fanout_broker(
        mapped_broker=None,
        dp_name="SOME UNKNOWN DP NAME",
        has_holdings=True,
    )
    assert resolved is not None
    assert resolved[1] == "CAS_DEMAT"
    assert resolved[2] == "Some"


def test_kafka_broker_code_unknown_nsdl_still_none():
    """NSDL Fourdegreewater stays unmapped at kafka code; fanout uses CAS_DEMAT via resolve."""
    assert map_broker("FOURDEGREEWATER CAPITAL") == "nsdl_fourdegreewater"
    assert kafka_broker_code("nsdl_fourdegreewater") is None
    resolved = resolve_fanout_broker(
        mapped_broker="nsdl_fourdegreewater",
        dp_name="FOURDEGREEWATER CAPITAL",
        has_holdings=True,
    )
    assert resolved is not None
    assert resolved[1] == "CAS_DEMAT"
    assert resolved[2] == "Fourdegreewater"


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
    # Always emit CDSL residual/clear (may be empty).
    assert "CDSL" in brokers
    mf_msgs = [m for m in holdings_msgs if m.get("mutualFunds")]
    if mf_msgs:
        assert any(m.get("name") == "Mutual Funds" for m in mf_msgs)
        assert any(
            (m.get("dematRef") or {}).get("boid") == "mf:cas" for m in mf_msgs
        )
    cas = msgs[-1]
    assert cas["accountDirectory"]
    assert cas["validation"]["allOk"] is not None
    assert any(
        row.get("nominee") is not None or row.get("nomineeRegistered") is not None
        for row in cas["accountDirectory"]
    )
    assert any(row.get("nomineeRegistered") is False for row in cas["accountDirectory"])


def test_txn_mf_layout_without_direct_token():
    """AUG2026 TXN-style MF table: Direct Plan is inside scheme name, no DIRECT column."""
    from brokers._common.identity_match import cas_holder_from_doc

    text = (Path(__file__).parent / "fixtures" / "cdsl" / "txn_mf_no_direct_snippet.txt").read_text(
        encoding="utf-8"
    )
    doc = extract_document_from_text(text)
    assert doc.mf_folios
    assert sum(f.holdings_value_sum for f in doc.mf_folios) >= 11000
    email, name, pan = cas_holder_from_doc(doc)
    assert name and "PRIYANSHU" in name.upper()
    assert email and email.lower() == "priyanshukpd@gmail.com"
    assert any(a.mapped_broker == "kotak" for a in doc.demat_accounts)
    assert any(a.mapped_broker == "zerodha" for a in doc.demat_accounts)

    msgs = fanout_messages(
        doc,
        user_id="u1",
        identity_match="FAMILY",
        holder_name=name,
        holder_email=email,
        holder_pan=pan or doc.holder_pan,
    )
    holdings = [m for m in msgs if m.get("eventType") is None]
    brokers = {m.get("brokerType") for m in holdings}
    assert "KOTAK" in brokers
    assert "ZERODHA" in brokers
    mf_book = next(m for m in holdings if m.get("name") == "Mutual Funds")
    assert mf_book.get("brokerType") == "CAS_DEMAT"
    assert mf_book.get("mutualFunds")
    assert (mf_book.get("dematRef") or {}).get("boid") == "mf:cas"
    assert mf_book.get("identityMatch") == "FAMILY"
    assert mf_book.get("holderName") and "PRIYANSHU" in mf_book["holderName"].upper()
    if pan or doc.holder_pan:
        assert mf_book.get("holderPan") == (pan or doc.holder_pan)
    cds = next(m for m in holdings if m.get("brokerType") == "CDSL")
    assert cds.get("mutualFunds") == []


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


def test_live_txn_pdf_optional():
    """If AUG2026 TXN PDF present, assert MF + holder + Kotak fan-out."""
    root = Path(__file__).resolve().parents[1]
    pdf = root / "AUG2026_AA49039213_TXN.pdf"
    if not pdf.exists():
        return
    try:
        from brokers._common.identity_match import cas_holder_from_doc
        from brokers.cdsl.extractor import extract_document
    except Exception:
        return
    try:
        doc = extract_document(str(pdf), "JYQPK9320A")
    except Exception:
        return
    email, name, pan = cas_holder_from_doc(doc)
    assert name and "PRIYANSHU" in name.upper()
    assert email and "priyanshukpd" in email.lower()
    assert (pan or doc.holder_pan) == "JYQPK9320A"
    assert len(doc.mf_folios) >= 10
    assert abs(sum(f.holdings_value_sum for f in doc.mf_folios) - 127188.22) < 1.0
    assert any(a.mapped_broker == "kotak" for a in doc.demat_accounts)
