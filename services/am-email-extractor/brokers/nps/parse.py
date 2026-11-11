"""Parse NPS Tier I / Tier II transaction statement text."""
from __future__ import annotations

import re
from typing import Any

from brokers._common.numbers import fnum, norm_date
from brokers.nps.isin_resolve import (
    parse_option,
    parse_scheme_class,
    resolve_from_scheme_name,
    slug_pf,
)


def _period(text: str) -> tuple[str | None, str | None]:
    m = re.search(
        r"([A-Za-z]{3}\s+\d{1,2},\s+\d{4})\s+To\s+([A-Za-z]{3}\s+\d{1,2},\s+\d{4})",
        text,
    )
    if not m:
        return None, None
    return _mdy(m.group(1)), _mdy(m.group(2))


def _mdy(s: str) -> str | None:
    from datetime import datetime

    try:
        return datetime.strptime(s.strip(), "%b %d, %Y").date().isoformat()
    except ValueError:
        return None


def _field(seg: str, label: str) -> str | None:
    m = re.search(rf"{re.escape(label)}\s*\n\s*([^\n]+)", seg)
    if m:
        v = m.group(1).strip()
        return v or None
    m = re.search(rf"{re.escape(label)}\s*:\s*([^\n]+)", seg, re.I)
    if m:
        return m.group(1).strip() or None
    return None


def _split_tiers(text: str) -> dict[str, str]:
    parts = re.split(
        r"NPS Transaction Statement for Tier\s+(I{1,2})\s+Account",
        text,
        flags=re.I,
    )
    # parts: [preamble, 'I', body1, 'II', body2, ...]
    out: dict[str, str] = {}
    i = 1
    while i + 1 < len(parts):
        tier = parts[i].upper()
        body = parts[i + 1]
        out[tier] = body
        i += 2
    return out


def _scheme_holdings(body: str, tier: str) -> list[dict[str, Any]]:
    """Parse Investment Details - Scheme Wise Summary rows."""
    block = re.search(
        r"Investment Details\s*-\s*Scheme Wise Summary(.*?)(?:Changes made|Contribution/Redemption|Note:)",
        body,
        re.DOTALL | re.I,
    )
    if not block:
        return []
    seg = block.group(1)
    holdings: list[dict[str, Any]] = []
    # Name may wrap across lines; then value, units, nav
    for m in re.finditer(
        r"(NPS TRUST[\s\S]*?SCHEME\s+[ECGA][\s\S]*?(?:POP|DIRECT)?)\s*\n"
        r"([\d,]+\.?\d*)\s*\n"
        r"([\d,]+\.?\d*)\s*\n"
        r"([\d,]+\.?\d*)",
        seg,
        re.I,
    ):
        name = re.sub(r"\s+", " ", m.group(1)).strip()
        value = fnum(m.group(2))
        units = fnum(m.group(3))
        nav = fnum(m.group(4))
        resolved = resolve_from_scheme_name(name, tier)
        holdings.append(
            {
                "name": name,
                "tier": tier,
                "schemeClass": parse_scheme_class(name),
                "option": parse_option(name),
                "pf": slug_pf(name),
                "statementValue": value,
                "units": units,
                "statementNav": nav,
                "isin": resolved.get("isin"),
                "schemeCode": resolved.get("schemeCode"),
                "isinResolveStatus": resolved.get("isinResolveStatus"),
                "catalogName": resolved.get("name"),
                "assetClass": "nps",
            }
        )
    return holdings


def _investment_summary(body: str) -> dict[str, Any]:
    # XIRR then big numbers: holdings, contrib count, total contrib, withdrawal, gain
    m = re.search(
        r"Return on Investment\s*\(XIRR\)\s*\n\s*([\d.]+)%\s*\n\s*"
        r"([\d,]+\.?\d*)\s*\n\s*(\d+)\s*\n\s*"
        r"([\d,]+\.?\d*)\s*\n\s*([\d,]+\.?\d*)\s*\n\s*"
        r"([\d,]+\.?\d*)",
        body,
        re.I,
    )
    if not m:
        return {}
    return {
        "xirrPct": fnum(m.group(1)),
        "holdingsValue": fnum(m.group(2)),
        "contributionCount": int(m.group(3)),
        "totalContribution": fnum(m.group(4)),
        "totalWithdrawal": fnum(m.group(5)),
        "notionalGainLoss": fnum(m.group(6)),
    }


def _contributions(body: str) -> list[dict[str, Any]]:
    block = re.search(
        r"Contribution/Redemption Details during the selected period(.*?)(?:Transaction Details|Note:)",
        body,
        re.DOTALL | re.I,
    )
    if not block:
        return []
    seg = block.group(1)
    if "No change affected" in seg:
        return []
    rows = []
    for m in re.finditer(
        r"(\d{2}-[A-Za-z]{3}-\d{2})\s*\n"
        r"([^\n]+)\s*\n"
        r"([^\n]+)\s*\n"
        r"([\d,]+\.?\d*)\s*\n"
        r"([\d,]+\.?\d*)\s*\n"
        r"([\d,]+\.?\d*)",
        seg,
    ):
        rows.append(
            {
                "date": _dmy(m.group(1)),
                "particulars": m.group(2).strip(),
                "uploadedBy": m.group(3).strip(),
                "employeeContribution": fnum(m.group(4)),
                "employerContribution": fnum(m.group(5)),
                "total": fnum(m.group(6)),
            }
        )
    return rows


def _dmy(s: str) -> str | None:
    from datetime import datetime

    try:
        return datetime.strptime(s.strip(), "%d-%b-%y").date().isoformat()
    except ValueError:
        try:
            return datetime.strptime(s.strip(), "%d-%b-%Y").date().isoformat()
        except ValueError:
            return s


def _subscriber(text: str) -> dict[str, Any]:
    pran = None
    m = re.search(r"\bPRAN\b\s*\n\s*(\d{12})", text)
    if m:
        pran = m.group(1)
    name = _field(text, "Subscriber Name")
    if name:
        name = re.sub(r"\s+", " ", name).strip()
    email = _field(text, "Email ID")
    mobile = _field(text, "Mobile Number")
    reg = _field(text, "Registration Date")
    nominee = None
    nm = re.search(r"Tier\s+I+\s+Nominee Name/s\s*\n\s*Percentage\s*\n\s*([^\n]+)\s*\n\s*([\d.]+)%", text)
    if nm:
        nominee = {"name": re.sub(r"\s+", " ", nm.group(1)).strip(), "percentage": fnum(nm.group(2))}
    return {
        "pran": pran,
        "name": name,
        "email": email.lower() if email else None,
        "mobile": mobile,
        "registrationDate": norm_date(reg.replace("-", "-") if reg else None)
        if reg and re.match(r"\d{2}-", reg or "")
        else _parse_reg(reg),
        "nominee": nominee,
    }


def _parse_reg(reg: str | None) -> str | None:
    if not reg:
        return None
    from datetime import datetime

    for fmt in ("%d-%b-%y", "%d-%b-%Y", "%d-%b-%y"):
        try:
            return datetime.strptime(reg.strip(), fmt).date().isoformat()
        except ValueError:
            continue
    # 21-Dec-20
    try:
        return datetime.strptime(reg.strip(), "%d-%b-%y").date().isoformat()
    except ValueError:
        return reg


def parse_nps_text(text: str) -> dict[str, Any]:
    period_from, period_to = _period(text)
    gen = re.search(
        r"Statement Generation Date:\s*([A-Za-z]+\s+\d{1,2},\s+\d{4}\s+\d{1,2}:\d{2}\s*[AP]M)",
        text,
    )
    subscriber = _subscriber(text)
    tiers_out = []
    for tier, body in _split_tiers(text).items():
        schemes = _scheme_holdings(body, tier)
        summary = _investment_summary(body)
        as_of = period_to
        for s in schemes:
            s["asOfDate"] = as_of
        pref = re.search(r"Scheme Choice\s*:\s*([^\n]+)", body)
        status = _field(body, f"Tier {tier} Status") or _field(body, "Tier I Status") or _field(body, "Tier II Status")
        tiers_out.append(
            {
                "tier": tier,
                "status": status,
                "schemeChoice": pref.group(1).strip() if pref else None,
                "investmentSummary": summary,
                "schemes": schemes,
                "contributions": _contributions(body),
            }
        )

    # Validation
    checks = []
    for t in tiers_out:
        schemes = t.get("schemes") or []
        ssum = round(sum(s.get("statementValue") or 0 for s in schemes), 2)
        hv = (t.get("investmentSummary") or {}).get("holdingsValue")
        ok = hv is None or abs(ssum - hv) <= 1.0
        checks.append(
            {
                "name": f"tier{t['tier']}_schemeSumEqualsHoldings",
                "expected": hv,
                "actual": ssum,
                "ok": ok if hv is not None else None,
            }
        )
    known = [c for c in checks if c.get("ok") is not None]
    return {
        "documentSource": "NPS_STATEMENT",
        "statementFrom": period_from,
        "statementTo": period_to,
        "generatedAt": gen.group(1) if gen else None,
        "subscriber": subscriber,
        "tiers": tiers_out,
        "validation": {
            "allOk": all(c["ok"] for c in known) if known else False,
            "checks": checks,
        },
    }
