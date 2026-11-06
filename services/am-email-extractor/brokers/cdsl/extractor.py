"""CDSL CAS entrypoints: extract_document (typed) + extract_holdings (legacy list)."""
from __future__ import annotations

import re
from typing import Any

from brokers._common.models import (
    AccountDirectoryRow,
    CasCover,
    CasDocument,
    CasValidation,
    CasValidationCheck,
    DematAccountExtract,
    HoldingLine,
    MfFolioExtract,
)
from brokers._common.numbers import norm_date
from brokers._common.pdf_text import load_pdf_text
from brokers.cdsl.detect import is_cdsl_cas
from brokers.cdsl.parse import (
    build_validation,
    extract_accounts,
    merge_mf_folio_profiles,
    parse_cover_buckets,
    parse_holder_name,
    parse_holder_pan,
    parse_mf_folio_profiles,
    parse_mf_folios,
    parse_statement_asset_classes,
)


def _holding_from_dict(h: dict[str, Any]) -> HoldingLine:
    return HoldingLine(
        isin=h.get("isin_code") or h.get("isin") or "",
        name=h.get("company_name") or h.get("scheme_name") or h.get("schemeName") or "",
        quantity=h.get("current_bal") if h.get("current_bal") is not None else h.get("units"),
        free_bal=h.get("free_bal"),
        current_price=h.get("rate") if h.get("rate") is not None else h.get("nav"),
        current_value=h.get("value"),
        amount_invested=h.get("amountInvested"),
        asset_class=h.get("assetClass") or "equity",
        scheme_code=h.get("schemeCode"),
        folio=h.get("folio"),
    )


def _demat_from_raw(a: dict[str, Any]) -> DematAccountExtract:
    return DematAccountExtract(
        boid=a.get("boId") or "",
        dp_name=a.get("dpName") or "",
        depository=a.get("depository") or "CDSL",
        dp_id=a.get("dpId"),
        client_id=a.get("clientId"),
        status=a.get("accountStatus"),
        active=a.get("active"),
        email=a.get("email"),
        mobile=a.get("mobile"),
        holder_name=a.get("holderName") or a.get("name"),
        nominee=a.get("nominee"),
        nominee_registered=a.get("nomineeRegistered"),
        frozen_status=a.get("frozenStatus"),
        mapped_broker=a.get("broker"),
        as_of_date=a.get("asOfDate"),
        note=a.get("note"),
        statement_value=a.get("holdingsValueSum"),
        holdings=[_holding_from_dict(h) for h in (a.get("holdings") or [])],
    )


def _group_mf_folios(raw_folios: list[dict[str, Any]]) -> list[MfFolioExtract]:
    by_folio: dict[str, MfFolioExtract] = {}
    for f in raw_folios:
        key = f.get("folio") or f.get("isin_code") or ""
        if key not in by_folio:
            by_folio[key] = MfFolioExtract(
                folio=f.get("folio") or key,
                amc_name=f.get("amcName"),
                rta_name=f.get("rta"),
                advisor_name=None,
                ucc=f.get("ucc"),
                email=f.get("email"),
                mobile=f.get("mobile"),
                nominee=f.get("nominee"),
                nominee_registered=f.get("nomineeRegistered"),
                as_of_date=f.get("asOfDate"),
                holdings=[],
            )
        folio = by_folio[key]
        if f.get("amcName") and not folio.amc_name:
            folio.amc_name = f.get("amcName")
        if f.get("rta") and not folio.rta_name:
            folio.rta_name = f.get("rta")
        if f.get("ucc") and not folio.ucc:
            folio.ucc = f.get("ucc")
        folio.holdings.append(
            HoldingLine(
                isin=f.get("isin_code") or f.get("isin") or "",
                name=f.get("schemeName") or f.get("scheme_name") or "",
                quantity=f.get("units"),
                current_price=f.get("nav"),
                current_value=f.get("value"),
                amount_invested=f.get("amountInvested"),
                asset_class="mutual_fund_folio",
                scheme_code=f.get("schemeCode"),
                folio=f.get("folio"),
            )
        )
    return list(by_folio.values())


def _directory(
    accounts: list[dict[str, Any]], mf_profiles: list[dict[str, Any]], mf_folios: list[MfFolioExtract]
) -> list[AccountDirectoryRow]:
    rows: list[AccountDirectoryRow] = []
    for a in accounts:
        rows.append(
            AccountDirectoryRow(
                account_no=a.get("boId") or "",
                account_type="demat",
                status=a.get("accountStatus"),
                email=a.get("email"),
                mobile=a.get("mobile"),
                holder_name=a.get("holderName") or a.get("name"),
                dp_id=a.get("dpId"),
                client_id=a.get("clientId"),
                boid=a.get("boId"),
                nominee=a.get("nominee"),
                nominee_registered=a.get("nomineeRegistered"),
                frozen_status=a.get("frozenStatus"),
                holding_value=a.get("holdingsValueSum"),
                mapped_broker=a.get("broker"),
                dp_name=a.get("dpName"),
                active=a.get("active"),
            )
        )
    seen_folios = set()
    for p in mf_profiles:
        folio = p.get("folio") or ""
        if folio in seen_folios:
            continue
        seen_folios.add(folio)
        val = next((f.holdings_value_sum for f in mf_folios if f.folio == folio), None)
        rows.append(
            AccountDirectoryRow(
                account_no=folio,
                account_type="mf",
                status="Active",
                email=p.get("email"),
                mobile=p.get("mobile"),
                holder_name=p.get("holderName") or p.get("name"),
                nominee=p.get("nominee"),
                nominee_registered=p.get("nomineeRegistered"),
                holding_value=val,
                amc_name=p.get("amcName"),
                folio=folio,
                active=True,
            )
        )
    return rows


def extract_document_from_text(text: str) -> CasDocument:
    if not is_cdsl_cas(text):
        raise ValueError("PDF text does not look like a CDSL Consolidated Account Statement")

    as_ofs = re.findall(r"HOLDING STATEMENT AS ON\s*([\d-]+)", text)
    as_of = norm_date(as_ofs[0] if as_ofs else None)
    cover_raw = parse_cover_buckets(text)
    statement_ac = parse_statement_asset_classes(text)
    accounts_raw = extract_accounts(text, as_of)
    folios_raw = parse_mf_folios(text)
    mf_profiles = parse_mf_folio_profiles(text)
    folios_raw = merge_mf_folio_profiles(folios_raw, mf_profiles)
    validation_raw = build_validation(cover_raw, statement_ac, accounts_raw, folios_raw)

    period = re.search(
        r"FOR THE PERIOD FROM\s+(\d{2}-\d{2}-\d{4})\s+TO\s+(\d{2}-\d{2}-\d{4})",
        text,
        re.I,
    )

    demat = [_demat_from_raw(a) for a in accounts_raw]
    mf_folios = _group_mf_folios(folios_raw)
    holder_name = parse_holder_name(text)
    holder_pan = parse_holder_pan(text)
    if holder_name:
        for acct in demat:
            if not acct.holder_name:
                acct.holder_name = holder_name
        for row in accounts_raw:
            if not row.get("holderName") and not row.get("name"):
                row["holderName"] = holder_name
        for p in mf_profiles:
            if not p.get("holderName") and not p.get("name"):
                p["holderName"] = holder_name
    cover = CasCover(
        cdsl_demat_accounts=cover_raw.get("cdslDematAccounts"),
        nsdl_demat_accounts=cover_raw.get("nsdlDematAccounts"),
        mutual_fund_folios=cover_raw.get("mutualFundFolios"),
        total_portfolio_value=cover_raw.get("totalPortfolioValue"),
        total_accounts=len(demat) + len(mf_profiles),
        demat_accounts=len(demat),
        mf_folios=len(mf_folios),
    )
    validation = CasValidation(
        all_ok=bool(validation_raw.get("allOk")),
        extracted_total=validation_raw.get("extractedTotal"),
        extracted_by_asset_class=validation_raw.get("extractedByAssetClass") or {},
        checks=[
            CasValidationCheck(
                name=c["name"],
                expected=c.get("expected"),
                actual=c.get("actual"),
                diff=c.get("diff"),
                ok=c.get("ok"),
            )
            for c in (validation_raw.get("checks") or [])
        ],
    )
    return CasDocument(
        as_of_date=as_of,
        statement_from=norm_date(period.group(1)) if period else None,
        statement_to=norm_date(period.group(2)) if period else None,
        cover=cover,
        validation=validation,
        account_directory=_directory(accounts_raw, mf_profiles, mf_folios),
        demat_accounts=demat,
        mf_folios=mf_folios,
        statement_asset_classes=statement_ac,
        holder_pan=holder_pan,
    )


def extract_document(file_path: str, password: str | None = None) -> CasDocument:
    text = load_pdf_text(file_path, password)
    return extract_document_from_text(text)


def extract_holdings(file_path: str, password: str | None = None) -> list[dict[str, Any]]:
    """Legacy flat list for Mongo / API responses."""
    return extract_document(file_path, password).flat_holdings_legacy()
