"""Discover Gmail statements without requiring PAN."""

from unittest.mock import MagicMock, patch

import app_api


def _call_discover(broker: str):
    """Invoke view function without JWT decorator."""
    fn = getattr(app_api.discover_from_gmail, "__wrapped__", app_api.discover_from_gmail)
    return fn(broker)


def test_discover_gmail_found(monkeypatch):
    fake_result = {
        "email": {
            "subject": "CAS",
            "date": "Mon, 1 Jan 2024",
            "from": "a@cdslindia.com",
        },
        "attachment": {"filename": "cas.pdf", "path": "/tmp/x.pdf"},
        "temp_dir": "/tmp/td",
    }

    class FakeDb:
        def resolve_mailbox_email(self, user_id, mailbox):
            return mailbox or "u@example.com"

    monkeypatch.setattr(app_api.database, "get_db", lambda: FakeDb())

    with patch.object(
        app_api.gmail_integration,
        "get_gmail_service",
        return_value=(MagicMock(), None, None),
    ), patch.object(
        app_api.gmail_integration,
        "get_latest_statement",
        return_value=fake_result,
    ), patch.object(app_api, "cleanup_temp_files") as cleanup:
        with app_api.app.test_request_context(
            "/api/v1/discover/gmail/cdsl?mailbox=u@example.com"
        ):
            from flask import request

            request.user_id = "user-1"
            resp = _call_discover("cdsl")
            data = resp[0].get_json() if isinstance(resp, tuple) else resp.get_json()
            status = resp[1] if isinstance(resp, tuple) else resp.status_code
            assert status == 200
            assert data["found"] is True
            assert data["email"]["subject"] == "CAS"
            assert data["attachment"]["filename"] == "cas.pdf"
            assert data["needs_password"] is True
            cleanup.assert_called_once()


def test_discover_gmail_not_found(monkeypatch):
    class FakeDb:
        def resolve_mailbox_email(self, user_id, mailbox):
            return "u@example.com"

    monkeypatch.setattr(app_api.database, "get_db", lambda: FakeDb())

    with patch.object(
        app_api.gmail_integration,
        "get_gmail_service",
        return_value=(MagicMock(), None, None),
    ), patch.object(
        app_api.gmail_integration,
        "get_latest_statement",
        return_value=None,
    ):
        with app_api.app.test_request_context("/api/v1/discover/gmail/nps"):
            from flask import request

            request.user_id = "user-1"
            resp = _call_discover("nps")
            data = resp[0].get_json() if isinstance(resp, tuple) else resp.get_json()
            status = resp[1] if isinstance(resp, tuple) else resp.status_code
            assert status == 404
            assert data["found"] is False
            assert "No recent emails" in data["error"]
