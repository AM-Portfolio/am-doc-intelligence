"""NPS catalog resolve + parse smoke (no live credentials required)."""
from __future__ import annotations

import os
from pathlib import Path

from brokers.nps.isin_resolve import resolve, resolve_from_scheme_name
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


def test_fanout_from_synthetic_doc():
    doc = {
        "subscriber": {"pran": "110000000000", "name": "Test Holder"},
        "tiers": [
            {
                "tier": "I",
                "schemes": [
                    {
                        "schemeCode": "SM008001",
                        "isinResolveStatus": "MAPPED",
                        "units": 1.0,
                        "nav": 10.0,
                        "value": 10.0,
                    }
                ]
                * 3,
            },
            {
                "tier": "II",
                "schemes": [
                    {
                        "schemeCode": "SM008022",
                        "isinResolveStatus": "MAPPED",
                        "units": 1.0,
                        "nav": 10.0,
                        "value": 10.0,
                    }
                ]
                * 3,
            },
        ],
        "validation": {"allOk": True},
    }
    assert doc["subscriber"]["pran"] == "110000000000"
    assert len(doc["tiers"]) == 2
    schemes = [s for t in doc["tiers"] for s in t["schemes"]]
    assert len(schemes) == 6
    assert all(s.get("isinResolveStatus") == "MAPPED" for s in schemes)
    assert doc["validation"]["allOk"] is True
    msgs = fanout_messages(doc, user_id="u1")
    assert msgs[0]["brokerType"] == "NPS"
    assert len(msgs[0]["npsHoldings"]) == 6
    assert msgs[1]["eventType"] == "NPS_DOCUMENT"


def test_live_pdf_optional_uses_env_password():
    """Optional local PDF smoke — password only via NPS_TEST_PDF_PASSWORD env."""
    root = Path(__file__).resolve().parents[1]
    pdf = root / "nps-statements.pdf"
    password = (os.environ.get("NPS_TEST_PDF_PASSWORD") or "").strip()
    if not pdf.exists() or not password:
        return
    from brokers.nps.extractor import extract_document

    doc = extract_document(str(pdf), password, enrich_live_nav=False)
    pran = (doc.get("subscriber") or {}).get("pran")
    assert pran and len(str(pran)) == 12
    assert len(doc["tiers"]) == 2
    schemes = [s for t in doc["tiers"] for s in t["schemes"]]
    assert len(schemes) >= 1
    assert doc["validation"]["allOk"] is True


def test_detect_snippet():
    assert is_nps_statement("NPS TRANSACTION STATEMENT\nPRAN\n110")
