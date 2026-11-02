"""Unit tests for market-data ISIN enrichment and slim Kafka equity mapping."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from security_enrichment import enrich_by_isins  # noqa: E402
from app_api import holdings_for_portfolio_event, to_portfolio_asset  # noqa: E402


def _match(isin, symbol, company_name, sector, industry="Banks"):
    return {
        "symbol": symbol,
        "isin": isin,
        "companyName": company_name,
        "sector": sector,
        "industry": industry,
        "matchScore": 1.0,
        "matchedField": "ISIN",
    }


class TestEnrichByIsins:
    def test_maps_batch_search_response(self, monkeypatch):
        monkeypatch.setenv("MARKET_DATA_BASE_URL", "https://market.test")

        body = {
            "results": [
                {
                    "query": "INE040A01034",
                    "matches": [
                        _match(
                            "INE040A01034",
                            "HDFCBANK",
                            "HDFC Bank Limited",
                            "Financial Services",
                        )
                    ],
                }
            ]
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b"{}"
        mock_resp.json.return_value = body
        mock_resp.text = ""

        with patch("security_enrichment.requests.post", return_value=mock_resp) as post:
            out = enrich_by_isins(["INE040A01034"], authorization="Bearer t")

        assert out["INE040A01034"]["symbol"] == "HDFCBANK"
        assert out["INE040A01034"]["sector"] == "Financial Services"
        assert out["INE040A01034"]["name"] == "HDFC Bank Limited"
        post.assert_called_once()
        kwargs = post.call_args.kwargs
        assert kwargs["headers"]["Authorization"] == "Bearer t"
        assert kwargs["json"]["searchFields"] == ["ISIN"]
        assert kwargs["json"]["queries"] == ["INE040A01034"]

    def test_fifty_plus_isins_one_post(self, monkeypatch):
        monkeypatch.setenv("MARKET_DATA_BASE_URL", "https://market.test")
        isins = [f"INE{i:09d}" for i in range(55)]
        results = [
            {
                "query": isin,
                "matches": [_match(isin, f"SYM{i}", f"Co {i}", "Sector")],
            }
            for i, isin in enumerate(isins)
        ]
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b"{}"
        mock_resp.json.return_value = {"results": results}

        with patch("security_enrichment.requests.post", return_value=mock_resp) as post:
            out = enrich_by_isins(isins)

        assert post.call_count == 1
        assert len(post.call_args.kwargs["json"]["queries"]) == 55
        assert len(out) == 55
        assert out[isins[0]]["symbol"] == "SYM0"

    def test_fail_open_on_http_error(self, monkeypatch):
        monkeypatch.setenv("MARKET_DATA_BASE_URL", "https://market.test")
        mock_resp = MagicMock()
        mock_resp.status_code = 503
        mock_resp.text = "down"
        mock_resp.content = b""

        with patch("security_enrichment.requests.post", return_value=mock_resp):
            out = enrich_by_isins(["INE040A01034"])
        assert out == {}

    def test_unset_base_url_returns_empty(self, monkeypatch):
        monkeypatch.delenv("MARKET_DATA_BASE_URL", raising=False)
        monkeypatch.delenv("MARKET_DATA_API_URL", raising=False)
        assert enrich_by_isins(["INE040A01034"]) == {}


class TestToPortfolioAsset:
    def test_no_fake_avg_from_rate(self):
        holding = {
            "isin_code": "INE040A01034",
            "company_name": "PDF NAME WRONG",
            "current_bal": "10",
            "rate": "1500.50",
            "value": "15005",
        }
        enrich = {
            "symbol": "HDFCBANK",
            "sector": "Financial Services",
            "name": "HDFC Bank Limited",
            "companyName": "HDFC Bank Limited",
        }
        asset = to_portfolio_asset(holding, enrich)
        assert asset["isin"] == "INE040A01034"
        assert asset["quantity"] == 10.0
        assert asset["symbol"] == "HDFCBANK"
        assert asset["sector"] == "Financial Services"
        assert asset["name"] == "HDFC Bank Limited"
        assert asset["companyName"] == "HDFC Bank Limited"
        assert "avgBuyingPrice" not in asset
        assert "investmentValue" not in asset
        assert "currentPrice" not in asset
        assert "currentValue" not in asset

    def test_pdf_name_fallback_when_enrich_misses(self):
        holding = {
            "isin_code": "INE999A01000",
            "company_name": "Only From PDF",
            "current_bal": "1",
            "rate": "10",
        }
        asset = to_portfolio_asset(holding, None)
        assert asset["name"] == "Only From PDF"
        assert asset.get("symbol") is None
        assert "avgBuyingPrice" not in asset


class TestHoldingsForPortfolioEvent:
    def test_dhan_inf_stay_equities_with_sector(self, monkeypatch):
        monkeypatch.setenv("MARKET_DATA_BASE_URL", "https://market.test")
        holdings = [
            {
                "isin_code": "INF204KB17I5",
                "company_name": "Some ETF PDF",
                "current_bal": "5",
                "rate": "100",
                "value": "500",
            },
            {
                "isin_code": "INE040A01034",
                "company_name": "HDFC PDF",
                "current_bal": "2",
                "rate": "1",
                "value": "2",
            },
        ]
        enrich_map = {
            "INF204KB17I5": {
                "symbol": "NIFTYBEES",
                "sector": "ETF",
                "name": "Nippon India ETF Nifty BeES",
            },
            "INE040A01034": {
                "symbol": "HDFCBANK",
                "sector": "Financial Services",
                "name": "HDFC Bank Limited",
            },
        }
        with patch(
            "security_enrichment.enrich_by_isins", return_value=enrich_map
        ) as enrich_fn:
            equities, mutual_funds = holdings_for_portfolio_event(
                holdings, "dhan", authorization="Bearer x"
            )

        enrich_fn.assert_called_once()
        assert mutual_funds == []
        assert len(equities) == 2
        by_isin = {e["isin"]: e for e in equities}
        assert by_isin["INF204KB17I5"]["sector"] == "ETF"
        assert by_isin["INF204KB17I5"]["symbol"] == "NIFTYBEES"
        assert "avgBuyingPrice" not in by_isin["INE040A01034"]
        assert by_isin["INE040A01034"]["name"] == "HDFC Bank Limited"

    def test_non_dhan_inf_to_mutual_funds(self, monkeypatch):
        monkeypatch.setenv("MARKET_DATA_BASE_URL", "https://market.test")
        holdings = [
            {
                "isin_code": "INF204KB17I5",
                "company_name": "ETF",
                "current_bal": "1",
            }
        ]
        with patch("security_enrichment.enrich_by_isins", return_value={}):
            equities, mutual_funds = holdings_for_portfolio_event(holdings, "groww")
        assert equities == []
        assert len(mutual_funds) == 1
        assert mutual_funds[0]["isin"] == "INF204KB17I5"
