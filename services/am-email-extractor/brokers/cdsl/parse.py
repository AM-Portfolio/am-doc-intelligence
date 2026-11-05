"""CDSL CAS text parsers (ported from local verify script)."""
from __future__ import annotations

import re
from typing import Any

from brokers._common.numbers import DATE_LINE_RE, NUM_TOKEN, fnum, norm_date
from brokers.cdsl.classify import classify_asset
from brokers.cdsl.mapping import map_broker

ISIN_RE = re.compile(r"^(IN[A-Z0-9]{10})$")

# CDSL/RTA placeholder text — not a real nominee name
_NOMINEE_PLACEHOLDERS = frozenset(
    {
        "not registered",
        "notregistered",
        "please nominate",
        "opt-out",
        "opt out",
        "na",
        "n/a",
        "-",
        "--",
    }
)


def normalize_nominee(raw: str | None) -> tuple[str | None, bool]:
    """Return (nominee_name_or_none, nominee_registered).

    Placeholders like \"Please Nominate\" / \"Not Registered\" are cleared so
    APIs never expose them as a nominee display name.
    """
    if raw is None:
        return None, False
    nominee = re.sub(r"\s+", " ", str(raw)).strip()
    if not nominee:
        return None, False
    nom_l = nominee.lower()
    if nom_l == "registered":
        # CAS sometimes prints only the word Registered (no name)
        return None, True
    if nom_l in _NOMINEE_PLACEHOLDERS or "not registered" in nom_l or "please nominate" in nom_l:
        return None, False
    return nominee, True


def parse_statement_asset_classes(text: str) -> dict:
    block = re.search(
        r"Consolidated Portfolio for Accounts for the Month\s+Asset Class\s+Value\s+Percentage\s+(.*?)\s+Total\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)",
        text,
        re.DOTALL | re.IGNORECASE,
    )
    out: dict[str, Any] = {"rows": [], "totalValue": None, "totalPct": None}
    if not block:
        return out
    body, total_v, total_pct = block.group(1), block.group(2), block.group(3)
    out["totalValue"] = fnum(total_v)
    out["totalPct"] = fnum(total_pct)
    lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
    i = 0
    while i + 2 < len(lines):
        name, val, pct = lines[i], lines[i + 1], lines[i + 2]
        if fnum(val) is None:
            i += 1
            continue
        key = name.strip().lower()
        asset_class = {
            "debts": "debt",
            "equity": "equity",
            "mutual fund folios": "mutual_fund_folio",
            "mutual funds held in demat form": "mutual_fund_demat",
        }.get(key, key.replace(" ", "_"))
        out["rows"].append(
            {
                "label": name.strip(),
                "assetClass": asset_class,
                "value": fnum(val),
                "percentage": fnum(pct),
            }
        )
        i += 3
    return out


def parse_cover_buckets(text: str) -> dict:
    m = re.search(
        r"CDSL Demat Accounts\s*\n\s*NSDL Demat Accounts\s*\n\s*Mutual Fund Folios\s*\n"
        r"([\d,]+\.?\d*)\s*\n([\d,]+\.?\d*)\s*\n([\d,]+\.?\d*)",
        text,
    )
    total_m = re.search(r"Total Portfolio Value\s*\n\s*([\d,]+\.?\d*)", text)
    return {
        "cdslDematAccounts": fnum(m.group(1)) if m else None,
        "nsdlDematAccounts": fnum(m.group(2)) if m else None,
        "mutualFundFolios": fnum(m.group(3)) if m else None,
        "totalPortfolioValue": fnum(total_m.group(1)) if total_m else None,
    }


def parse_holding_block(block: str, depository: str | None) -> list[dict]:
    lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
    skip_exact = {
        "ISIN",
        "Security",
        "Current",
        "Bal",
        "Frozen",
        "Pledge",
        "Setup",
        "Free Bal",
        "Free bal",
        "Market",
        "Price /",
        "Face",
        "Value",
        "Value (`)",
        "Value(`)",
        "a)",
        "b)",
        "a) Current",
        "a) Frozen",
        "a) Locked",
        "in Bal",
        "a) Remat",
        "Locked in",
        "b) Pledge",
        "Transit",
        "Confirmed",
        "b) Pledged",
        "locked in",
        "Pending",
        "Demat",
    }
    skip_prefixes = (
        "Central Depository",
        "A Wing",
        "CONSOLIDATED",
        "Summary of",
        "Account Details",
        "CDSL Demat",
        "NSDL Demat",
        "MF Details",
        "Notes",
        "About CDSL",
        "Page ",
        "Munish",
        "a) ",
        "b) ",
    )
    holdings: list[dict] = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln in skip_exact or any(ln.startswith(p) for p in skip_prefixes):
            i += 1
            continue
        if ln.startswith(
            (
                "Portfolio Value",
                "BO ID",
                "DP Name",
                "DPID",
                "STATEMENT",
                "Nil Holding",
                "No Transaction",
                "TER ",
                "DEMAT ACCOUNTS",
                "MUTUAL FUND",
                "For any queries",
                "No Margin",
                "HOLDING STATEMENT",
            )
        ):
            break
        if not ISIN_RE.match(ln):
            i += 1
            continue
        isin = ln
        i += 1
        name_parts: list[str] = []
        while i < len(lines):
            cur = lines[i]
            if ISIN_RE.match(cur) or cur.startswith("Portfolio Value") or cur.startswith("BO ID"):
                break
            if DATE_LINE_RE.match(cur):
                name_parts.append(cur)
                i += 1
                continue
            if NUM_TOKEN.fullmatch(cur.replace(" ", "")) or re.match(r"^[\d,]+\.\d+", cur):
                break
            if cur in skip_exact or any(cur.startswith(p) for p in skip_prefixes):
                i += 1
                continue
            name_parts.append(cur)
            i += 1
        need = 13 if depository == "NSDL" else 7
        nums: list[str] = []
        while i < len(lines):
            raw = lines[i]
            if ISIN_RE.match(raw) or raw.startswith("Portfolio Value") or raw.startswith("BO ID"):
                break
            if raw.startswith("Page ") or DATE_LINE_RE.match(raw):
                i += 1
                continue
            parts = NUM_TOKEN.findall(raw)
            if not parts:
                break
            nums.extend(parts)
            i += 1
            if len(nums) >= need:
                break
        non_dash = [n for n in nums if n != "--"]
        current = fnum(nums[0]) if nums else None
        price = fnum(non_dash[-2]) if len(non_dash) >= 2 else None
        value = fnum(non_dash[-1]) if non_dash else None
        free = fnum(nums[4]) if len(nums) >= 5 and nums[4] != "--" else current
        if depository == "NSDL" and len(nums) >= 3:
            free = fnum(nums[-3]) if nums[-3] != "--" else current
            price = fnum(nums[-2])
            value = fnum(nums[-1])
        if current is None or current <= 0:
            continue
        name = " ".join(name_parts).strip()
        name = re.sub(r"\s+\d{2}[-./]\d{2}[-./]\d{4}$", "", name).strip()
        asset_class = classify_asset(isin, name, depository, "demat")
        holdings.append(
            {
                "isin_code": isin,
                "company_name": name,
                "current_bal": current,
                "free_bal": free,
                "rate": price,
                "value": value,
                "assetClass": asset_class,
            }
        )
    return holdings


def parse_mf_folios(text: str) -> list[dict]:
    m = re.search(r"MUTUAL FUND UNITS HELD AS ON\s*([\d-]+)\s*(.*)", text, re.DOTALL)
    if not m:
        return []
    as_of = norm_date(m.group(1))
    body = m.group(2)
    body = re.split(r"Grand Total|Average\s+Total Expense Ratio|Notes", body, maxsplit=1)[0]
    body = re.sub(r"[\uf000-\uf8ff\ufffd\xad]", "", body)
    body = re.sub(r"(\d)\s*\n\s*(\d+/\d+)", r"\1\2", body)
    folios: list[dict] = []

    def _append_folio(
        scheme_code: str | None,
        scheme_name: str | None,
        isin: str,
        folio: str,
        units: str | None,
        nav: str | None,
        invested: str | None,
        value: str | None,
    ) -> None:
        folios.append(
            {
                "schemeCode": scheme_code,
                "scheme_name": scheme_name,
                "isin_code": isin,
                "folio": folio,
                "units": fnum(units),
                "nav": fnum(nav),
                "amountInvested": fnum(invested),
                "value": fnum(value),
                "asOfDate": as_of,
                "assetClass": "mutual_fund_folio",
            }
        )

    # Legacy layout: scheme - name / ISIN / folio / DIRECT / units nav invested value
    for sm in re.finditer(
        r"([A-Z0-9]{2,6})\s*-\s*([\s\S]*?)(INF[A-Z0-9]{9})\s*"
        r"([\d/]+)\s*DIRECT\s*"
        r"([\d,]+\.?\d*)\s+"
        r"([\d,]+\.?\d*)\s+"
        r"([\d,]+\.?\d*)\s+"
        r"([\d,]+\.?\d*)",
        body,
    ):
        name = re.sub(r"\s+", " ", sm.group(2)).strip()
        _append_folio(
            sm.group(1), name, sm.group(3), sm.group(4),
            sm.group(5), sm.group(6), sm.group(7), sm.group(8),
        )
    if folios:
        return folios

    # TXN / modern CAS: no standalone DIRECT token — "Direct Plan" is inside scheme name.
    # scheme - name\nISIN\nfolio\nunits\nnav\ninvested\nvalue[\nPnL\nPnL%]
    for sm in re.finditer(
        r"([A-Z0-9]{2,6})\s*-\s*([\s\S]*?)(INF[A-Z0-9]{9})\s*"
        r"([\d/]+)\s+"
        r"([\d,]+\.?\d*)\s+"
        r"([\d,]+\.?\d*)\s+"
        r"([\d,]+\.?\d*)\s+"
        r"([\d,]+\.?\d*)",
        body,
    ):
        name = re.sub(r"\s+", " ", sm.group(2)).strip()
        # Skip if we accidentally matched a header / junk name without fund words
        if not name or name.lower() in {"scheme name", "isin"}:
            continue
        _append_folio(
            sm.group(1), name, sm.group(3), sm.group(4),
            sm.group(5), sm.group(6), sm.group(7), sm.group(8),
        )
    if folios:
        return folios

    for sm in re.finditer(
        r"(INF[A-Z0-9]{9})\s*([\d/]+)\s*DIRECT\s*([\d.,\s]+?)(?=\n[A-Z0-9]{2,6}\s*-|\nINF|\Z)",
        body,
    ):
        nums = [n for n in NUM_TOKEN.findall(sm.group(3)) if n != "--"]
        if len(nums) < 3:
            continue
        if len(nums) >= 4:
            units, nav, invested, value = nums[0], nums[1], nums[2], nums[3]
        else:
            units, invested, value = nums[0], nums[1], nums[2]
            nav = None
        _append_folio(None, None, sm.group(1), sm.group(2), units, nav, invested, value)
    return folios


_PAN_RE = re.compile(
    r"\(\s*PAN\s*[:\-]?\s*([A-Z]{5}\d{4}[A-Z])\s*\)",
    re.IGNORECASE,
)
_PAN_BARE_RE = re.compile(
    r"\bPAN\s*[:\-]?\s*([A-Z]{5}\d{4}[A-Z])\b",
    re.IGNORECASE,
)


def parse_holder_pan(text: str) -> str | None:
    """Primary holder PAN from CDSL cover (e.g. ``( PAN :JYQPK9320A )``)."""
    if not text:
        return None
    m = _PAN_RE.search(text) or _PAN_BARE_RE.search(text)
    if not m:
        return None
    return m.group(1).strip().upper()


def parse_holder_name(text: str) -> str | None:
    """Best-effort primary holder from CAS cover / PAN line."""
    m = re.search(
        r"name of\s*\n?\s*([A-Z][A-Z .'-]{1,80}?)\s*\(\s*PAN",
        text,
        re.IGNORECASE,
    )
    if m:
        return re.sub(r"\s+", " ", m.group(1)).strip(" .")
    m = re.search(
        r"Name/Joint Name\s*\(s\)\s*\n(?:Portfolio Valuation[^\n]*\n)?([A-Z][A-Za-z .'-]{1,80})",
        text,
    )
    if m:
        name = re.sub(r"\s+", " ", m.group(1)).strip(" .")
        if name.lower() not in {"portfolio valuation", "view statement", "cdsl demat accounts"}:
            return name
    return None


def _join_wrapped_email(value: str, rest: str) -> str:
    """CDSL wraps emails across lines: ``user@gmail.\\nCOM`` or ``user@\\ngmail.com``."""
    v = (value or "").strip()
    if not v or "@" not in v:
        return v
    # Already looks complete
    if re.search(r"@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$", v):
        return v
    cont = re.match(r"\s*\n\s*([A-Za-z0-9.-]{2,40})\b", rest)
    if not cont:
        return v
    piece = cont.group(1).strip()
    if v.endswith(".") or v.endswith("@"):
        return f"{v}{piece}"
    if "." not in v.split("@", 1)[-1]:
        return f"{v}.{piece}" if not piece.startswith(".") else f"{v}{piece}"
    return v


def _field(seg: str, *labels: str) -> str | None:
    for lab in labels:
        m = re.search(rf"{re.escape(lab)}[ \t]*:[ \t]*([^\n]*)", seg, re.IGNORECASE)
        if m:
            v = m.group(1).strip()
            if not v:
                continue
            if lab.lower().startswith("email"):
                v = _join_wrapped_email(v, seg[m.end() :])
            return v if v else None
    return None


def parse_demat_account_profiles(text: str) -> list[dict]:
    profiles: list[dict] = []
    for m in re.finditer(
        r"DP Name\s*:\s*([^\n]+)\s*\nDP ID\s*:\s*(\S+)\s+CLIENT ID\s*:\s*(\S+)\s*\n(.*?)(?=\nDP Name\s*:|\nNSDL Demat Accounts|\nMF Folios|\nDEMAT ACCOUNTS HELD|\Z)",
        text,
        re.DOTALL | re.IGNORECASE,
    ):
        dp_name, dp_id, client_id, rest = (
            m.group(1).strip(),
            m.group(2).strip(),
            m.group(3).strip(),
            m.group(4),
        )
        rest = re.split(
            r"\n(?:Summary of|Consolidated Portfolio|YOUR CONSOLIDATED|DEMAT ACCOUNTS HELD)",
            rest,
            maxsplit=1,
        )[0]
        depository = "NSDL" if dp_id.upper().startswith("IN") else "CDSL"
        email = _field(rest, "Email Id", "Email id", "Email ID")
        nominee, nominee_registered = normalize_nominee(_field(rest, "Nominee", "Nominee "))
        status = _field(rest, "Account Status")
        profiles.append(
            {
                "dpName": dp_name,
                "dpId": dp_id,
                "clientId": client_id,
                "boId": f"{dp_id}{client_id}",
                "depository": depository,
                "broker": map_broker(dp_name),
                "email": email.lower() if email else None,
                "emailRaw": email,
                "mobile": _field(rest, "Mobile No"),
                "accountStatus": status,
                "active": (status or "").strip().lower() == "active",
                "frozenStatus": _field(rest, "Frozen Status"),
                "nominee": nominee,
                "nomineeRegistered": nominee_registered,
                "boStatus": _field(rest, "BO Status", "BO Type"),
                "boSubStatus": _field(rest, "BO Sub Status", "BO Sub Type"),
                "bsda": _field(rest, "BSDA"),
                "rgess": _field(rest, "RGESS"),
            }
        )
    return profiles


def parse_mf_folio_profiles(text: str) -> list[dict]:
    profiles: list[dict] = []
    for m in re.finditer(
        r"AMC Name[ \t]*:[ \t]*([^\n]+)\s*\n"
        r"Scheme Name[ \t]*:[ \t]*([\s\S]*?)"
        r"Scheme Code[ \t]*:[ \t]*(\S+)\s*\n"
        r"Folio No[ \t]*:[ \t]*([^\n]+)\s*\n"
        r"(.*?)(?=\nAMC Name[ \t]*:|\nNotes|\nDEMAT ACCOUNTS HELD|\nMUTUAL FUND UNITS HELD|\nPage \d|\Z)",
        text,
        re.DOTALL | re.IGNORECASE,
    ):
        scheme_name = re.sub(r"\s+", " ", m.group(2)).strip()
        rest = m.group(5)
        email = _field(rest, "Email id", "Email Id", "Email ID")
        nominee, nominee_registered = normalize_nominee(_field(rest, "Nominee"))
        ucc = _field(rest, "UCC")
        profiles.append(
            {
                "amcName": m.group(1).strip(),
                "schemeName": scheme_name,
                "schemeCode": m.group(3).strip(),
                "folio": m.group(4).strip(),
                "modeOfHolding": _field(rest, "Mode of Holding"),
                "email": email.lower() if email else None,
                "emailRaw": email,
                "mobile": _field(rest, "Mobile No"),
                "nominee": nominee,
                "nomineeRegistered": nominee_registered,
                "kyc": _field(rest, "KYC of Investor/s"),
                "isin": _field(rest, "ISIN"),
                "ucc": ucc,
                "rta": _field(rest, "RTA"),
                "assetClass": "mutual_fund_folio",
            }
        )
    return profiles


def _account(bo, dp, depository, holds, as_of, note, profile: dict | None = None):
    by_class: dict[str, float] = {}
    for h in holds:
        ac = h.get("assetClass") or "unknown"
        by_class[ac] = round(by_class.get(ac, 0.0) + (h.get("value") or 0.0), 2)
    row = {
        "boId": bo,
        "dpName": dp,
        "broker": map_broker(dp),
        "depository": depository,
        "asOfDate": as_of,
        "note": note,
        "holdings": holds,
        "holdingsCount": len(holds),
        "holdingsValueSum": round(sum(h.get("value") or 0.0 for h in holds), 2),
        "valueByAssetClass": by_class,
    }
    if profile:
        row.update(
            {
                "dpId": profile.get("dpId"),
                "clientId": profile.get("clientId"),
                "email": profile.get("email"),
                "emailRaw": profile.get("emailRaw"),
                "mobile": profile.get("mobile"),
                "accountStatus": profile.get("accountStatus"),
                "active": profile.get("active"),
                "frozenStatus": profile.get("frozenStatus"),
                "nominee": profile.get("nominee"),
                "nomineeRegistered": profile.get("nomineeRegistered"),
                "boStatus": profile.get("boStatus"),
                "boSubStatus": profile.get("boSubStatus"),
                "bsda": profile.get("bsda"),
                "rgess": profile.get("rgess"),
            }
        )
        if profile.get("broker"):
            row["broker"] = profile["broker"]
    return row


def extract_accounts(text: str, as_of: str | None) -> list[dict]:
    profiles = {p["boId"]: p for p in parse_demat_account_profiles(text)}
    accounts: list[dict] = []
    for m in re.finditer(r"BO ID\s*:\s*(\S+)\s*\nDP Name\s*:\s*([^\n]+)", text):
        bo, dp = m.group(1), m.group(2).strip()
        start = m.end()
        nxt = re.search(
            r"(?:BO ID\s*:|DEMAT ACCOUNTS HELD WITH NSDL|MUTUAL FUND UNITS HELD WITH MF/RTA|TER & COMMISSION)",
            text[start:],
        )
        end = start + (nxt.start() if nxt else len(text) - start)
        seg = text[start:end]
        holds: list[dict] = []
        note = None
        if "Nil Holding" in seg and "HOLDING STATEMENT AS ON" not in seg:
            note = "nil_holding"
        elif "HOLDING STATEMENT AS ON" in seg:
            hm = re.search(r"HOLDING STATEMENT AS ON\s*[\d-]+\s*(.*)", seg, re.DOTALL)
            holds = parse_holding_block(hm.group(1) if hm else "", "CDSL")
        else:
            note = "no_holding_statement"
        accounts.append(_account(bo, dp, "CDSL", holds, as_of, note, profiles.get(bo)))

    ns = re.search(
        r"DEMAT ACCOUNTS HELD WITH NSDL\s*DPID\s*:\s*(\S+)\s*\nDP Name\s*:\s*([^\n]+)",
        text,
    )
    if ns:
        dpid, dp = ns.group(1), ns.group(2).strip()
        start = ns.end()
        nxt = re.search(r"MUTUAL FUND UNITS HELD WITH MF/RTA", text[start:])
        end = start + (nxt.start() if nxt else len(text) - start)
        seg = text[start:end]
        holds: list[dict] = []
        if "HOLDING STATEMENT AS ON" in seg:
            hm = re.search(r"HOLDING STATEMENT AS ON\s*[\d-]+\s*(.*)", seg, re.DOTALL)
            holds = parse_holding_block(hm.group(1) if hm else "", "NSDL")
        accounts.append(_account(dpid, dp, "NSDL", holds, as_of, None, profiles.get(dpid)))

    seen = {a["boId"] for a in accounts}
    for bo, prof in profiles.items():
        if bo not in seen:
            accounts.append(
                _account(bo, prof["dpName"], prof["depository"], [], as_of, "profile_only", prof)
            )
    return accounts


def merge_mf_folio_profiles(folios: list[dict], profiles: list[dict]) -> list[dict]:
    by_isin = {(p.get("isin") or "").upper(): p for p in profiles if p.get("isin")}
    by_folio = {p.get("folio"): p for p in profiles if p.get("folio")}
    out = []
    for f in folios:
        p = by_isin.get((f.get("isin_code") or "").upper()) or by_folio.get(f.get("folio"))
        row = dict(f)
        if p:
            row.update(
                {
                    "amcName": p.get("amcName"),
                    "schemeName": p.get("schemeName") or row.get("scheme_name"),
                    "email": p.get("email"),
                    "emailRaw": p.get("emailRaw"),
                    "mobile": p.get("mobile"),
                    "nominee": p.get("nominee"),
                    "nomineeRegistered": p.get("nomineeRegistered"),
                    "kyc": p.get("kyc"),
                    "ucc": p.get("ucc"),
                    "rta": p.get("rta"),
                    "modeOfHolding": p.get("modeOfHolding"),
                }
            )
        out.append(row)
    return out


def build_validation(cover: dict, statement_ac: dict, accounts: list, folios: list) -> dict:
    extracted_by_class: dict[str, float] = {}
    for a in accounts:
        for h in a.get("holdings") or []:
            ac = h.get("assetClass") or "unknown"
            extracted_by_class[ac] = round(
                extracted_by_class.get(ac, 0.0) + (h.get("value") or 0.0), 2
            )
    folio_sum = round(sum(f.get("value") or 0.0 for f in folios), 2)
    extracted_by_class["mutual_fund_folio"] = folio_sum

    demat_equity = extracted_by_class.get("equity", 0.0)
    demat_mf = extracted_by_class.get("mutual_fund_demat", 0.0)
    debt = extracted_by_class.get("debt", 0.0)
    extracted_total = round(demat_equity + demat_mf + debt + folio_sum, 2)

    cdsl_sum = round(
        sum(a.get("holdingsValueSum") or 0.0 for a in accounts if a.get("depository") == "CDSL"),
        2,
    )
    nsdl_sum = round(
        sum(a.get("holdingsValueSum") or 0.0 for a in accounts if a.get("depository") == "NSDL"),
        2,
    )

    def check(name, expected, actual, tol=1.0):
        if expected is None or actual is None:
            return {"name": name, "expected": expected, "actual": actual, "ok": None}
        diff = round(abs(expected - actual), 2)
        return {
            "name": name,
            "expected": expected,
            "actual": actual,
            "diff": diff,
            "ok": diff <= tol,
        }

    stmt = {r["assetClass"]: r["value"] for r in statement_ac.get("rows") or []}
    checks = [
        check("totalPortfolioValue", cover.get("totalPortfolioValue"), extracted_total),
        check("cover.cdslDematAccounts", cover.get("cdslDematAccounts"), cdsl_sum),
        check("cover.nsdlDematAccounts", cover.get("nsdlDematAccounts"), nsdl_sum),
        check("cover.mutualFundFolios", cover.get("mutualFundFolios"), folio_sum),
        check("statement.equity", stmt.get("equity"), demat_equity),
        check("statement.mutual_fund_demat", stmt.get("mutual_fund_demat"), demat_mf),
        check("statement.debt", stmt.get("debt"), debt),
        check("statement.mutual_fund_folio", stmt.get("mutual_fund_folio"), folio_sum),
        check("statement.total", statement_ac.get("totalValue"), extracted_total),
    ]
    known = [c for c in checks if c["ok"] is not None]
    return {
        "extractedByAssetClass": extracted_by_class,
        "extractedTotal": extracted_total,
        "cdslDematValueSum": cdsl_sum,
        "nsdlDematValueSum": nsdl_sum,
        "mutualFundFolioValueSum": folio_sum,
        "checks": checks,
        "passed": sum(1 for c in known if c["ok"]),
        "failed": sum(1 for c in known if c["ok"] is False),
        "allOk": all(c["ok"] for c in known) if known else False,
    }
