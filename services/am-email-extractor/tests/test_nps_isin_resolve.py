"""NPS catalog resolve + parse smoke (no live NAV required for resolve tests)."""
from __future__ import annotations

from pathlib import Path

from brokers.nps.isin_resolve import resolve, resolve_from_scheme_name
from brokers.nps.parse import parse_nps_text
from brokers.nps.detect import is_nps_statement
from brokers.nps.fanout import fanout_messages


def test_hdfc_tier1_pop_and_tier2_direct_codes():
    e1 = resolve(pf="hdfc", scheme="E", tier="I", option="POP")
    assert e1["schemeCode"] == "SM008001"
    assert e1["isinResolveStatus"] == "MAPPED"
    c2 = resolve(pf="hdfc", scheme="C", tier="II", option="DIRECT")
    assert c2["schemeCode"] == "SM008022"


def test_resolve_from_pdf_scheme_name():
    name = (
        "NPS TRUST- A/C HDFC PENSION FUND MANAGEMENT LIMITED SCHEME E - TIER I POP"
    )
    r = resolve_from_scheme_name(name, "I")
    assert r["schemeCode"] == "SM008001"


def test_parse_live_pdf_optional():
    root = Path(__file__).resolve().parents[1]
    pdf = root / "nps-statements.pdf"
    if not pdf.exists():
        return
    from brokers.nps.extractor import extract_document

    doc = extract_document(str(pdf), "muni2611", enrich_live_nav=False)
    assert doc["subscriber"]["pran"] == "110115289881"
    assert len(doc["tiers"]) == 2
    schemes = [s for t in doc["tiers"] for s in t["schemes"]]
    assert len(schemes) == 6
    assert all(s.get("isinResolveStatus") == "MAPPED" for s in schemes)
    assert doc["validation"]["allOk"] is True
    msgs = fanout_messages(doc, user_id="u1")
    assert msgs[0]["brokerType"] == "NPS"
    assert len(msgs[0]["npsHoldings"]) == 6
    assert msgs[1]["eventType"] == "NPS_DOCUMENT"


def test_detect_snippet():
    assert is_nps_statement("NPS TRANSACTION STATEMENT\nPRAN\n110")
