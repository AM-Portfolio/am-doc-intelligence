from brokers._common.identity_match import resolve_identity_match
from brokers.cdsl.parse import parse_holder_pan


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
            profile_name="Munish Kumar",
            doc_email=None,
            doc_name="Spouse Name",
        )
        == "FAMILY"
    )


def test_name_match_without_email_is_self():
    assert (
        resolve_identity_match(
            profile_email=None,
            profile_name="Munish Kumar",
            doc_email=None,
            doc_name="  munish   kumar ",
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
            doc_pan="JYQPK9320A",
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
            profile_pan="jyqpk9320a",
            doc_pan="JYQPK9320A",
        )
        == "SELF"
    )


def test_doc_pan_only_is_family():
    assert (
        resolve_identity_match(
            profile_email=None,
            profile_name="Munish",
            doc_email=None,
            doc_name=None,
            profile_pan=None,
            doc_pan="JYQPK9320A",
        )
        == "FAMILY"
    )


def test_parse_holder_pan_from_cover_line():
    text = "name of\nPRIYANSHU KUMAR ( PAN :JYQPK9320A )"
    assert parse_holder_pan(text) == "JYQPK9320A"


def test_priyanshu_vs_munish_email_is_family():
    assert (
        resolve_identity_match(
            profile_email="ssd2658@gmail.com",
            profile_name="Munish Asrax",
            doc_email="priyanshukpd@gmail.com",
            doc_name="PRIYANSHU KUMAR",
            profile_pan=None,
            doc_pan="JYQPK9320A",
        )
        == "FAMILY"
    )
