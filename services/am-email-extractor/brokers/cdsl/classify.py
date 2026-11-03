"""Asset-class labels aligned with CDSL statement cover table."""
from __future__ import annotations


def classify_asset(isin: str, name: str, depository: str | None, section: str) -> str:
    if section == "mf_folio":
        return "mutual_fund_folio"
    u_name = (name or "").upper()
    u_isin = (isin or "").upper()
    if u_isin.startswith("INF"):
        return "mutual_fund_demat"
    debt_hints = (
        " NCD",
        "NCD ",
        "NGRT",
        "SEC GRT",
        "SEC NGRT",
        "CORPORATE BOND",
        "DEBENTURE",
        "BOND /",
    )
    if depository == "NSDL" or any(h in u_name for h in debt_hints):
        return "debt"
    return "equity"
