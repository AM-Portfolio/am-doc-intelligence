"""Internal extract dataclasses (snake_case). Wire layer maps to Kafka camelCase."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class HoldingLine:
    isin: str
    name: str
    quantity: Optional[float] = None
    free_bal: Optional[float] = None
    avg_cost: Optional[float] = None
    current_price: Optional[float] = None
    current_value: Optional[float] = None
    asset_class: str = "equity"
    scheme_code: Optional[str] = None
    folio: Optional[str] = None
    amount_invested: Optional[float] = None

    def to_legacy_dict(self) -> dict[str, Any]:
        """Shape expected by holdings_for_portfolio_event / to_portfolio_asset."""
        d: dict[str, Any] = {
            "isin_code": self.isin,
            "isin": self.isin,
            "company_name": self.name,
            "scheme_name": self.name,
            "current_bal": self.quantity,
            "quantity": self.quantity,
            "free_bal": self.free_bal,
            "rate": self.current_price,
            "nav": self.current_price,
            "value": self.current_value,
            "amountInvested": self.amount_invested,
            "assetClass": self.asset_class,
        }
        if self.scheme_code:
            d["schemeCode"] = self.scheme_code
        if self.folio:
            d["folio"] = self.folio
        return d


@dataclass
class DematAccountExtract:
    boid: str
    dp_name: str
    depository: str
    dp_id: Optional[str] = None
    client_id: Optional[str] = None
    status: Optional[str] = None
    active: Optional[bool] = None
    email: Optional[str] = None
    mobile: Optional[str] = None
    holder_name: Optional[str] = None
    nominee: Optional[str] = None
    nominee_registered: Optional[bool] = None
    frozen_status: Optional[str] = None
    mapped_broker: Optional[str] = None
    as_of_date: Optional[str] = None
    note: Optional[str] = None
    holdings: list[HoldingLine] = field(default_factory=list)

    @property
    def holdings_value_sum(self) -> float:
        return round(sum(h.current_value or 0.0 for h in self.holdings), 2)


@dataclass
class MfFolioExtract:
    folio: str
    amc_name: Optional[str] = None
    rta_name: Optional[str] = None
    advisor_name: Optional[str] = None
    ucc: Optional[str] = None
    email: Optional[str] = None
    mobile: Optional[str] = None
    nominee: Optional[str] = None
    nominee_registered: Optional[bool] = None
    as_of_date: Optional[str] = None
    holdings: list[HoldingLine] = field(default_factory=list)

    @property
    def holdings_value_sum(self) -> float:
        return round(sum(h.current_value or 0.0 for h in self.holdings), 2)


@dataclass
class AccountDirectoryRow:
    account_no: str
    account_type: str  # demat | mf
    status: Optional[str] = None
    email: Optional[str] = None
    mobile: Optional[str] = None
    holder_name: Optional[str] = None
    dp_id: Optional[str] = None
    client_id: Optional[str] = None
    boid: Optional[str] = None
    nominee: Optional[str] = None
    nominee_registered: Optional[bool] = None
    frozen_status: Optional[str] = None
    holding_value: Optional[float] = None
    mapped_broker: Optional[str] = None
    dp_name: Optional[str] = None
    amc_name: Optional[str] = None
    folio: Optional[str] = None
    active: Optional[bool] = None


@dataclass
class CasCover:
    cdsl_demat_accounts: Optional[float] = None
    nsdl_demat_accounts: Optional[float] = None
    mutual_fund_folios: Optional[float] = None
    total_portfolio_value: Optional[float] = None
    total_accounts: Optional[int] = None
    demat_accounts: Optional[int] = None
    mf_folios: Optional[int] = None


@dataclass
class CasValidationCheck:
    name: str
    expected: Optional[float]
    actual: Optional[float]
    diff: Optional[float] = None
    ok: Optional[bool] = None


@dataclass
class CasValidation:
    checks: list[CasValidationCheck] = field(default_factory=list)
    all_ok: bool = False
    extracted_total: Optional[float] = None
    extracted_by_asset_class: dict[str, float] = field(default_factory=dict)


@dataclass
class CasDocument:
    as_of_date: Optional[str] = None
    statement_from: Optional[str] = None
    statement_to: Optional[str] = None
    cover: CasCover = field(default_factory=CasCover)
    validation: CasValidation = field(default_factory=CasValidation)
    account_directory: list[AccountDirectoryRow] = field(default_factory=list)
    demat_accounts: list[DematAccountExtract] = field(default_factory=list)
    mf_folios: list[MfFolioExtract] = field(default_factory=list)
    statement_asset_classes: dict[str, Any] = field(default_factory=dict)
    document_source: str = "CDSL_CAS"
    holder_pan: Optional[str] = None

    def flat_holdings_legacy(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for acct in self.demat_accounts:
            for h in acct.holdings:
                d = h.to_legacy_dict()
                d["boId"] = acct.boid
                d["dpName"] = acct.dp_name
                d["broker"] = acct.mapped_broker
                rows.append(d)
        for folio in self.mf_folios:
            for h in folio.holdings:
                d = h.to_legacy_dict()
                d["folio"] = folio.folio
                d["amcName"] = folio.amc_name
                d["rta"] = folio.rta_name
                d["ucc"] = folio.ucc
                rows.append(d)
        return rows
