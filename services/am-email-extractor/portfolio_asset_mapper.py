"""Map broker statement holdings → Kafka EquityModel / MutualFundModel JSON."""
from __future__ import annotations

# Statement `rate` is true average buy cost for these brokers (not LTP).
AVG_COST_BROKERS = frozenset({"angleone"})


def holding_float(value, default=None):
    """Parse a numeric statement field; returns default when missing/invalid."""
    try:
        if value is None or value == "" or str(value).strip().upper() in ("N/A", "NA", "-"):
            return default
        return float(str(value).replace(",", "").replace("%", "").strip())
    except (TypeError, ValueError):
        return default


def _explicit_avg(holding):
    """Prefer explicit avg fields when extractors (e.g. Zerodha Excel) provide them."""
    for key in (
        "avgBuyingPrice",
        "avg_buying_price",
        "avg_price",
        "average_price",
        "avg_buy",
    ):
        if key in holding and holding.get(key) is not None:
            val = holding_float(holding.get(key))
            if val is not None and val > 0:
                return val
    return None


def to_portfolio_asset(holding, enrich=None, broker=None):
    """
    Map extractor dict → EquityModel JSON for Kafka.

    - Brokers with real avg in `rate` (AngleOne): emit avgBuyingPrice + investmentValue.
    - Demat PDF LTP brokers (Zerodha/Groww/MStock/Dhan PDF): emit currentPrice/currentValue
      from rate/value; never invent avg from closing rate.
    - Explicit avg_* fields (Zerodha Excel) always win as cost basis.
    """
    enrich = enrich or {}
    broker_key = (broker or "").strip().lower()
    isin = (holding.get("isin") or holding.get("isin_code") or "").strip().upper()
    pdf_name = (
        holding.get("companyName")
        or holding.get("company_name")
        or holding.get("name")
        or ""
    ).strip()
    name = enrich.get("name") or enrich.get("companyName") or pdf_name or None
    if isinstance(name, str):
        name = name.strip() or None
    qty = holding_float(holding.get("quantity", holding.get("current_bal")), default=0.0) or 0.0
    symbol = enrich.get("symbol") or holding.get("symbol") or None
    if isinstance(symbol, str):
        symbol = symbol.strip() or None
    sector = enrich.get("sector") or None
    if isinstance(sector, str):
        sector = sector.strip() or None

    asset = {
        "isin": isin or None,
        "companyName": name,
        "name": name,
        "symbol": symbol,
        "quantity": qty,
    }
    if sector:
        asset["sector"] = sector
    industry = enrich.get("industry")
    if industry:
        asset["industry"] = industry

    rate = holding_float(holding.get("rate"))
    value = holding_float(holding.get("value"))
    avg = _explicit_avg(holding)

    if avg is None and broker_key in AVG_COST_BROKERS and rate is not None and rate > 0:
        avg = rate

    if avg is not None and avg > 0:
        asset["avgBuyingPrice"] = avg
        invested = holding_float(
            holding.get("investmentValue") or holding.get("investment_value")
        )
        if invested is None or invested <= 0:
            invested = avg * qty if qty else None
        if invested is not None and invested > 0:
            asset["investmentValue"] = invested

    if value is not None and value > 0:
        asset["currentValue"] = value
        if qty > 0:
            asset["currentPrice"] = value / qty
    elif avg is None and rate is not None and rate > 0:
        asset["currentPrice"] = rate
        if qty > 0:
            asset["currentValue"] = rate * qty
    elif (
        avg is not None
        and value is None
        and rate is not None
        and rate > 0
        and broker_key not in AVG_COST_BROKERS
    ):
        asset["currentPrice"] = rate
        if qty > 0:
            asset["currentValue"] = rate * qty

    return asset


def holdings_for_portfolio_event(holdings, broker, authorization=None):
    """
    Split/map holdings for Kafka am-portfolio consumer.
    Demat brokers (e.g. Dhan): keep INF* ETFs as equities — they are listed demat units.
    Enrich symbol/sector/name via market-data batch-search (fail-open).
    """
    from security_enrichment import enrich_by_isins

    equities = []
    mutual_funds = []
    demat_all_equity = broker in ("dhan",)
    holdings = holdings or []
    isins = [
        (h.get("isin") or h.get("isin_code") or "").strip().upper() for h in holdings
    ]
    enrichment = enrich_by_isins(isins, authorization=authorization)

    for holding in holdings:
        isin = (holding.get("isin") or holding.get("isin_code") or "").strip().upper()
        asset = to_portfolio_asset(holding, enrichment.get(isin), broker=broker)
        out_isin = asset.get("isin") or ""
        if not demat_all_equity and out_isin.startswith("INF"):
            mutual_funds.append(asset)
        else:
            equities.append(asset)
    return equities, mutual_funds
