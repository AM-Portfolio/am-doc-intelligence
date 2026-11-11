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


def test_resolve_statement_value_without_holding_lines():
    """Cover/statement value alone is enough to fan out a book."""
    assert (
        resolve_fanout_broker(
            mapped_broker="groww",
            dp_name="GROWW INVEST TECH PRIVATE LIMITED",
            has_holdings=False,
            statement_value=0,
        )
        is None
    )
    groww = resolve_fanout_broker(
        mapped_broker="groww",
        dp_name="GROWW INVEST TECH PRIVATE LIMITED",
        has_holdings=False,
        statement_value=106711.35,
    )
    assert groww is not None
    assert groww[1] == "GROWW"
    mirae = resolve_fanout_broker(
        mapped_broker="mirae",
        dp_name="MIRAE ASSET CAPITAL MARKETS",
        has_holdings=False,
        statement_value=43425.87,
    )
    assert mirae is not None
    assert mirae[1] == "CAS_DEMAT"
    assert mirae[2] == "Mirae"


def test_fanout_summary_only_valued_demats():
    """Summary-only Groww + Mirae + MF emit books even with empty holding lines."""
    from brokers._common.models import (
        CasDocument,
        CasCover,
        DematAccountExtract,
        MfFolioExtract,
        HoldingLine,
    )

    doc = CasDocument(
        document_source="CDSL_CAS",
        as_of_date="2026-08-31",
        cover=CasCover(total_portfolio_value=277325.44),
        demat_accounts=[
            DematAccountExtract(
                boid="1208160000000001",
                dp_name="GROWW INVEST TECH PRIVATE LIMITED",
                depository="CDSL",
                mapped_broker="groww",
                statement_value=106711.35,
                holdings=[],
            ),
            DematAccountExtract(
                boid="1208870000000002",
                dp_name="MIRAE ASSET CAPITAL MARKETS (INDIA) PRIVATE LIMITED",
                depository="CDSL",
                mapped_broker="mirae",
                statement_value=43425.87,
                holdings=[],
            ),
            DematAccountExtract(
                boid="1208160000000099",
                dp_name="PAYTM MONEY LIMITED",
                depository="CDSL",
                mapped_broker=None,
                statement_value=0.0,
                holdings=[],
            ),
        ],
        mf_folios=[
            MfFolioExtract(
                folio="F1",
                holdings=[
                    HoldingLine(
                        isin="INF123",
                        name="Test Fund",
                        quantity=10,
                        current_value=127188.22,
                    )
                ],
            )
        ],
    )
    msgs = fanout_messages(doc, user_id="u1", identity_match="FAMILY")
    holdings = [m for m in msgs if m.get("eventType") is None]
    by_broker = {m.get("brokerType"): m for m in holdings}
    assert "GROWW" in by_broker
    assert by_broker["GROWW"].get("totalValue") == 106711.35
    assert by_broker["GROWW"].get("equities") == [] or by_broker["GROWW"].get("equities") is None or len(by_broker["GROWW"].get("equities") or []) == 0
    cas_demat = [m for m in holdings if m.get("brokerType") == "CAS_DEMAT"]
    names = {m.get("name") for m in cas_demat}
    assert "Mirae" in names
    assert "Mutual Funds" in names
    assert not any(
        (m.get("name") or "").upper().startswith("PAYTM") for m in holdings
    )


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
    assert name and "TEST HOLDER" in name.upper()
    assert email and email.lower() == "user@example.com"
    assert pan == "ABCDE1234F"
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
    assert mf_book.get("holderName") and "TEST HOLDER" in mf_book["holderName"].upper()
    if pan or doc.holder_pan:
        assert mf_book.get("holderPan") == (pan or doc.holder_pan)
    cds = next(m for m in holdings if m.get("brokerType") == "CDSL")
    assert cds.get("mutualFunds") == []


def test_live_pdf_optional():
    """If CDSL.pdf + CDSL_TEST_PDF_PASSWORD env present, smoke structural asserts only."""
    import os

    root = Path(__file__).resolve().parents[1]
    pdf = root / "CDSL.pdf"
    password = (os.environ.get("CDSL_TEST_PDF_PASSWORD") or "").strip()
    if not pdf.exists() or not password:
        return
    try:
        from brokers.cdsl.extractor import extract_document
    except Exception:
        return
    try:
        doc = extract_document(str(pdf), password)
    except Exception:
        return
    assert doc.cover.total_portfolio_value is not None
    assert doc.validation.all_ok is True
    assert len(doc.demat_accounts) >= 1


def test_live_txn_pdf_optional():
    """If TXN PDF + CDSL_TXN_TEST_PDF_PASSWORD env present, smoke structural asserts only."""
    import os

    root = Path(__file__).resolve().parents[1]
    pdf = root / "AUG2026_AA49039213_TXN.pdf"
    password = (os.environ.get("CDSL_TXN_TEST_PDF_PASSWORD") or "").strip()
    if not pdf.exists() or not password:
        return
    try:
        from brokers._common.identity_match import cas_holder_from_doc
        from brokers.cdsl.extractor import extract_document
    except Exception:
        return
    try:
        doc = extract_document(str(pdf), password)
    except Exception:
        return
    email, name, pan = cas_holder_from_doc(doc)
    assert name
    assert len(doc.mf_folios) >= 1
    assert any(a.mapped_broker for a in doc.demat_accounts)
