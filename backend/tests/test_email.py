"""Tests for ResendEmailer (Phase 3d).

The stub-emailer fallback and the "no API key" degraded path don't hit the
network. The success path is mocked at requests.post — we don't actually
talk to Resend here.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import requests

from app.auth.email import ResendEmailer
from app.config import settings


def test_resend_emailer_posts_with_link(monkeypatch):
    """With an API key set, send() POSTs to /emails with the magic link inline."""
    monkeypatch.setattr(settings, "resend_api_key", "re_test_key")
    monkeypatch.setattr(settings, "resend_from_email", "Greenroom <test@resend.dev>")

    post_mock = MagicMock()
    post_mock.return_value = MagicMock(status_code=200, text="ok")
    monkeypatch.setattr("requests.post", post_mock)

    ResendEmailer().send(
        to_email="foo@bar.com",
        magic_link_url="https://x.test/magic?t=abc",
    )

    post_mock.assert_called_once()
    args, kwargs = post_mock.call_args
    assert args[0] == "https://api.resend.com/emails"
    assert kwargs["headers"]["Authorization"] == "Bearer re_test_key"
    assert kwargs["json"]["to"] == ["foo@bar.com"]
    assert kwargs["json"]["from"] == "Greenroom <test@resend.dev>"
    assert kwargs["json"]["subject"] == "Sign in to Greenroom"
    assert "https://x.test/magic?t=abc" in kwargs["json"]["html"]


def test_resend_emailer_no_api_key_logs_and_returns(monkeypatch, capsys):
    """Empty resend_api_key → degraded stdout fallback, no exception."""
    monkeypatch.setattr(settings, "resend_api_key", "")

    ResendEmailer().send(
        to_email="foo@bar.com",
        magic_link_url="https://x.test/magic?t=abc",
    )

    captured = capsys.readouterr()
    assert "https://x.test/magic?t=abc" in captured.out
    assert "foo@bar.com" in captured.out


def test_resend_emailer_swallows_http_error(monkeypatch, capsys):
    """A 5xx from Resend logs but does not raise."""
    monkeypatch.setattr(settings, "resend_api_key", "re_test_key")

    fake_response = MagicMock(status_code=500, text="boom")
    monkeypatch.setattr("requests.post", MagicMock(return_value=fake_response))

    # No pytest.raises wrapper — assertion is the absence of an exception.
    ResendEmailer().send(to_email="foo@bar.com", magic_link_url="https://x.test/m")

    captured = capsys.readouterr()
    assert "send failed" in captured.out
    assert "500" in captured.out


def test_resend_emailer_swallows_network_error(monkeypatch, capsys):
    """requests raising ConnectionError is logged but does not propagate."""
    monkeypatch.setattr(settings, "resend_api_key", "re_test_key")

    def _raise(*_a, **_kw):
        raise requests.exceptions.ConnectionError("offline")

    monkeypatch.setattr("requests.post", _raise)

    ResendEmailer().send(to_email="foo@bar.com", magic_link_url="https://x.test/m")

    captured = capsys.readouterr()
    assert "send raised" in captured.out
    assert "offline" in captured.out
