from types import SimpleNamespace

from brokers._common.identity_match import (
    cas_holder_from_doc,
    profile_from_jwt,
    resolve_identity_match,
)
from brokers.cdsl.parse import parse_holder_name, parse_holder_pan


def test_same_email_different_pan_is_family():
    assert (
        resolve_identity_match(
            profile_email="me@x.com",
            profile_name="Primary User",
            doc_email="me@x.com",
            doc_name="Test Holder",
            profile_pan="AAAAA0000A",
            doc_pan="ABCDE1234F",
        )
        == "FAMILY"
    )


def test_same_email_same_pan_is_self():
    assert (
        resolve_identity_match(
            profile_email="me@x.com",
            profile_name="Primary User",
            doc_email="me@x.com",
            doc_name="Primary User",
            profile_pan="AAAAA0000A",
            doc_pan="aaaaa0000a",
        )
        == "SELF"
    )


def test_matching_pan_takes_precedence_over_stale_email_and_name():
    assert (
        resolve_identity_match(
            profile_email="primary@x.com",
            profile_name="Primary User",
            doc_email="old-address@x.com",
            doc_name="Different OCR Name",
            profile_pan="AAAAA0000A",
            doc_pan="aaaaa0000a",
        )
        == "SELF"
    )


def test_email_match_same_name_is_self():
    assert (
        resolve_identity_match(
            profile_email="me@x.com",
            profile_name="Me",
            doc_email="ME@x.com",
            doc_name="Me",
        )
        == "SELF"
    )


def test_email_match_different_name_is_family():
    """Shared inbox must not classify a family holder as SELF."""
    assert (
        resolve_identity_match(
            profile_email="me@x.com",
            profile_name="Md Sahim",
            doc_email="ME@x.com",
            doc_name="PRIYANSHU KUMAR",
        )
        == "FAMILY"
    )


def test_email_mismatch_is_family():
    assert (
        resolve_identity_match(
            profile_email="me@x.com",
            profile_name="Me",
            doc_email="spouse@x.com",
            doc_name="Spouse",
        )
        == "FAMILY"
    )


def test_name_mismatch_without_email_is_family():
    assert (
        resolve_identity_match(
            profile_email=None,
            profile_name="Primary User",
            doc_email=None,
            doc_name="Spouse Name",
        )
        == "FAMILY"
    )


def test_name_match_without_email_is_self():
    assert (
        resolve_identity_match(
            profile_email=None,
            profile_name="Primary User",
            doc_email=None,
            doc_name="  primary   user ",
        )
        == "SELF"
    )


def test_empty_doc_is_unknown():
    assert (
        resolve_identity_match(
            profile_email="me@x.com",
            profile_name="Me",
            doc_email=None,
            doc_name=None,
        )
        == "UNKNOWN"
    )


def test_profile_name_uses_full_name_claims_without_username_fallback():
    assert profile_from_jwt({"given_name": "Jane", "family_name": "Doe"}) == (
        None,
        "Jane Doe",
        None,
    )
    assert profile_from_jwt({"preferred_username": "jane@example.com"}) == (
        "jane@example.com",
        None,
        None,
    )


def test_pan_mismatch_without_email_is_family():
    assert (
        resolve_identity_match(
            profile_email=None,
            profile_name=None,
            doc_email=None,
            doc_name=None,
            profile_pan="AAAAA0000A",
            doc_pan="ABCDE1234F",
        )
        == "FAMILY"
    )


def test_pan_match_without_email_is_self():
    assert (
        resolve_identity_match(
            profile_email=None,
            profile_name=None,
            doc_email=None,
            doc_name=None,
            profile_pan="abcde1234f",
            doc_pan="ABCDE1234F",
        )
        == "SELF"
    )


def test_doc_pan_only_is_family():
    assert (
        resolve_identity_match(
            profile_email=None,
            profile_name="Primary",
            doc_email=None,
            doc_name=None,
            profile_pan=None,
            doc_pan="ABCDE1234F",
        )
        == "FAMILY"
    )


def test_parse_holder_pan_from_cover_line():
    text = "name of\nTest Holder ( PAN :ABCDE1234F )"
    assert parse_holder_pan(text) == "ABCDE1234F"


def test_different_email_and_pan_is_family():
    assert (
        resolve_identity_match(
            profile_email="primary@example.com",
            profile_name="Primary User",
            doc_email="user@example.com",
            doc_name="Test Holder",
            profile_pan=None,
            doc_pan="ABCDE1234F",
        )
        == "FAMILY"
    )


def test_parse_holder_name_client_name_variant():
    text = "Client Name :\nMD SAHIM\nPortfolio Valuation"
    assert parse_holder_name(text) == "MD SAHIM"


def test_parse_holder_name_does_not_use_next_field_label():
    text = "Client Name :\nEmail :\nuser@example.com"
    assert parse_holder_name(text) is None


def test_cas_holder_from_doc_uses_document_holder_name():
    doc = SimpleNamespace(
        holder_name="Cover Holder",
        holder_pan="ABCDE1234F",
        account_directory=[],
        demat_accounts=[],
    )
    email, name, pan = cas_holder_from_doc(doc)
    assert email is None
    assert name == "Cover Holder"
    assert pan == "ABCDE1234F"
