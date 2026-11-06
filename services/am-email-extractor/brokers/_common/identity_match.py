"""Compare JWT profile vs document holder/subscriber → SELF | FAMILY | UNKNOWN."""
from __future__ import annotations

from typing import Any, Mapping


def _norm_email(value: str | None) -> str:
    return (value or "").strip().lower()


def _norm_name(value: str | None) -> str:
    return " ".join((value or "").strip().lower().split())


def _norm_pan(value: str | None) -> str:
    return (value or "").strip().upper()


def resolve_identity_match(
    *,
    profile_email: str | None,
    profile_name: str | None,
    doc_email: str | None,
    doc_name: str | None,
    profile_pan: str | None = None,
    doc_pan: str | None = None,
) -> str:
    """
    Match order: PAN → email → name.
    - both PANs present and differ → FAMILY (even when the email matches)
    - email differs → FAMILY
    - email matches and PAN does not contradict → SELF
    - email absent, both PANs present and equal → SELF
    - email absent, both PANs present and differ → FAMILY
    - email absent, name differs → FAMILY
    - insufficient data → UNKNOWN
    """
    pe = _norm_email(profile_email)
    de = _norm_email(doc_email)
    pn = _norm_name(profile_name)
    dn = _norm_name(doc_name)
    pp = _norm_pan(profile_pan)
    dp = _norm_pan(doc_pan)

    if not de and not dn and not dp:
        return "UNKNOWN"

    # A different PAN is another person even when the CAS arrived in this inbox.
    if dp and pp and dp != pp:
        return "FAMILY"

    if de and pe:
        return "SELF" if de == pe else "FAMILY"

    if dp and pp:
        return "SELF" if dp == pp else "FAMILY"

    if not de or not pe:
        if dn and pn:
            return "SELF" if dn == pn else "FAMILY"
        if de and not pe:
            # Document has an email the profile does not — treat as family persona.
            return "FAMILY"
        if dp and not pp:
            # Doc PAN known, profile has none — family until proven otherwise.
            return "FAMILY"
        return "UNKNOWN"

    return "UNKNOWN"


def profile_from_jwt(claims: Mapping[str, Any] | None) -> tuple[str | None, str | None, str | None]:
    """Return (email, name, pan) from JWT claims. Pan is optional (custom claim)."""
    if not claims:
        return None, None, None
    email = claims.get("email") or claims.get("preferred_username")
    if isinstance(email, str) and "@" not in email:
        # preferred_username may be a username; keep only if it looks like email
        email = claims.get("email")
    name = (
        claims.get("name")
        or claims.get("given_name")
        or claims.get("preferred_username")
    )
    pan_raw = claims.get("pan") or claims.get("pan_number") or claims.get("panNumber")
    pan = _norm_pan(str(pan_raw)) if pan_raw else None
    if pan and len(pan) != 10:
        pan = None
    return (
        str(email).strip() if email else None,
        str(name).strip() if name else None,
        pan or None,
    )


def _email_looks_complete(email: str | None) -> bool:
    if not email or "@" not in email:
        return False
    domain = email.split("@", 1)[-1]
    return "." in domain and not domain.endswith(".")


def cas_holder_from_doc(doc: Any) -> tuple[str | None, str | None, str | None]:
    """Best-effort (email, name, pan) from CDSL CAS."""
    directory = getattr(doc, "account_directory", None) or []
    name = None
    email = None
    for row in directory:
        row_email = getattr(row, "email", None)
        if row_email and (email is None or (not _email_looks_complete(email) and _email_looks_complete(row_email))):
            email = row_email
        if name is None and getattr(row, "holder_name", None):
            name = row.holder_name
        if email and _email_looks_complete(email) and name:
            break
    if not name or not _email_looks_complete(email):
        for acct in getattr(doc, "demat_accounts", None) or []:
            if not name and getattr(acct, "holder_name", None):
                name = acct.holder_name
            acct_email = getattr(acct, "email", None)
            if acct_email and (email is None or (not _email_looks_complete(email) and _email_looks_complete(acct_email))):
                email = acct_email
    pan = getattr(doc, "holder_pan", None)
    if pan:
        pan = _norm_pan(str(pan))
    return (
        str(email).strip() if email else None,
        str(name).strip() if name else None,
        pan or None,
    )


def nps_holder_from_doc(doc: Mapping[str, Any] | None) -> tuple[str | None, str | None, str | None]:
    if not doc:
        return None, None, None
    sub = doc.get("subscriber") or {}
    email = sub.get("email")
    name = sub.get("name")
    pan_raw = sub.get("pan") or sub.get("panNumber")
    pan = _norm_pan(str(pan_raw)) if pan_raw else None
    if pan and len(pan) != 10:
        pan = None
    return (
        str(email).strip() if email else None,
        str(name).strip() if name else None,
        pan or None,
    )
