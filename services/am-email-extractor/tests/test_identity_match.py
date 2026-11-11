from brokers._common.identity_match import resolve_identity_match
from brokers.cdsl.parse import parse_holder_pan


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


def test_email_match_is_self():
    assert (
        resolve_identity_match(
            profile_email="me@x.com",
            profile_name="Me",
            doc_email="ME@x.com",
            doc_name="Someone Else",
        )
        == "SELF"
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
