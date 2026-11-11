import pytest

from brokers._common.pdf_text import PdfPasswordError, is_pdf_encrypted, load_pdf_text


def _make_encrypted_pdf(path):
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "secret")
    # Empty user password + owner password still marks encrypted in some builds;
    # set a real user password.
    doc.save(
        path,
        encryption=fitz.PDF_ENCRYPT_AES_256,
        user_pw="secretpan",
        owner_pw="owner",
    )
    doc.close()


def test_is_pdf_encrypted_true(tmp_path):
    pdf = tmp_path / "locked.pdf"
    _make_encrypted_pdf(str(pdf))
    assert is_pdf_encrypted(pdf) is True


def test_load_pdf_text_requires_password(tmp_path):
    pdf = tmp_path / "locked.pdf"
    _make_encrypted_pdf(str(pdf))
    with pytest.raises(PdfPasswordError) as ei:
        load_pdf_text(pdf, None)
    assert ei.value.code == "PASSWORD_REQUIRED"


def test_load_pdf_text_invalid_password(tmp_path):
    pdf = tmp_path / "locked.pdf"
    _make_encrypted_pdf(str(pdf))
    with pytest.raises(PdfPasswordError) as ei:
        load_pdf_text(pdf, "wrong")
    assert ei.value.code == "PASSWORD_INVALID"


def test_load_pdf_text_ok(tmp_path):
    pdf = tmp_path / "locked.pdf"
    _make_encrypted_pdf(str(pdf))
    text = load_pdf_text(pdf, "secretpan")
    assert "secret" in text
