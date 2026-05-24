"""Tests for the feedback router (GitHub issues via REST API).

The previous implementation shelled out to the `gh` CLI which is not
present in the Fly container. These tests pin the new REST-based flow:
required headers, payload shape, error swallowing, and the PR filter on
the list endpoint. Nothing here actually hits GitHub — requests is
monkey-patched at module scope inside `app.routers.feedback`.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import requests

from app.config import settings


def test_feedback_post_creates_issue(client, monkeypatch):
    """A configured token + 201 from GitHub yields ok=True with the html_url."""
    monkeypatch.setattr(settings, "github_token", "fake_token_xyz")
    monkeypatch.setattr(settings, "github_repo", "adamklie/greenroom")

    fake_response = MagicMock(status_code=201)
    fake_response.json.return_value = {
        "html_url": "https://github.com/adamklie/greenroom/issues/123",
    }
    post_mock = MagicMock(return_value=fake_response)
    monkeypatch.setattr("app.routers.feedback.requests.post", post_mock)

    r = client.post(
        "/api/feedback",
        json={
            "title": "Crash when uploading FLAC",
            "description": "Steps to reproduce: ...",
            "category": "bug",
            "priority": "high",
        },
    )

    assert r.status_code == 200
    assert r.json() == {
        "ok": True,
        "url": "https://github.com/adamklie/greenroom/issues/123",
    }

    # One call, to the right URL, with the right shape.
    post_mock.assert_called_once()
    args, kwargs = post_mock.call_args
    assert args[0] == "https://api.github.com/repos/adamklie/greenroom/issues"
    assert kwargs["headers"]["Authorization"] == "token fake_token_xyz"
    assert kwargs["headers"]["Accept"] == "application/vnd.github+json"

    payload = kwargs["json"]
    assert payload["title"] == "Crash when uploading FLAC"
    # Body suffix preserved verbatim — frontend + downstream tools rely on it.
    assert "Steps to reproduce: ..." in payload["body"]
    assert "_Submitted via Greenroom app (high priority)_" in payload["body"]
    # bug -> ["bug"], priority=high adds "priority:high".
    assert set(payload["labels"]) == {"bug", "priority:high"}


def test_feedback_post_no_token(client, monkeypatch):
    """Empty github_token → clean error response, no requests call made."""
    monkeypatch.setattr(settings, "github_token", "")

    # If feedback tries to call requests.post with no token, fail loudly.
    def _boom(*_a, **_kw):  # pragma: no cover - assertion-by-side-effect
        raise AssertionError("requests.post should not be called when token is empty")

    monkeypatch.setattr("app.routers.feedback.requests.post", _boom)

    r = client.post(
        "/api/feedback",
        json={
            "title": "x",
            "description": "y",
            "category": "feedback",
            "priority": "normal",
        },
    )

    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is False
    assert "GREENROOM_GITHUB_TOKEN" in body["error"]


def test_feedback_post_github_error(client, monkeypatch):
    """A non-201 response is surfaced as ok=False with the status + body snippet."""
    monkeypatch.setattr(settings, "github_token", "fake_token_xyz")

    fake_response = MagicMock(status_code=422, text='{"message": "Validation Failed"}')
    monkeypatch.setattr(
        "app.routers.feedback.requests.post",
        MagicMock(return_value=fake_response),
    )

    r = client.post(
        "/api/feedback",
        json={
            "title": "x",
            "description": "y",
            "category": "feedback",
            "priority": "normal",
        },
    )

    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is False
    assert "422" in body["error"]
    assert "Validation Failed" in body["error"]


def test_feedback_post_network_error(client, monkeypatch):
    """A RequestException from requests is logged but not raised."""
    monkeypatch.setattr(settings, "github_token", "fake_token_xyz")

    def _raise(*_a, **_kw):
        raise requests.exceptions.ConnectionError("offline")

    monkeypatch.setattr("app.routers.feedback.requests.post", _raise)

    r = client.post(
        "/api/feedback",
        json={
            "title": "x",
            "description": "y",
            "category": "feedback",
            "priority": "normal",
        },
    )

    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is False
    assert "Network error" in body["error"]
    assert "offline" in body["error"]


def test_feedback_list_issues(client, monkeypatch):
    """The list endpoint hits GET /issues and filters out pull requests."""
    monkeypatch.setattr(settings, "github_token", "fake_token_xyz")
    monkeypatch.setattr(settings, "github_repo", "adamklie/greenroom")

    fake_response = MagicMock(status_code=200)
    fake_response.json.return_value = [
        {
            "number": 1,
            "title": "First issue",
            "labels": [{"name": "bug"}, {"name": "priority:high"}],
            "created_at": "2026-05-01T00:00:00Z",
            "html_url": "https://github.com/adamklie/greenroom/issues/1",
        },
        {
            # This one is a PR — must be filtered out.
            "number": 2,
            "title": "Some PR",
            "labels": [],
            "created_at": "2026-05-02T00:00:00Z",
            "html_url": "https://github.com/adamklie/greenroom/pull/2",
            "pull_request": {"url": "..."},
        },
        {
            "number": 3,
            "title": "Second issue",
            "labels": [{"name": "enhancement"}],
            "created_at": "2026-05-03T00:00:00Z",
            "html_url": "https://github.com/adamklie/greenroom/issues/3",
        },
    ]
    get_mock = MagicMock(return_value=fake_response)
    monkeypatch.setattr("app.routers.feedback.requests.get", get_mock)

    r = client.get("/api/feedback/issues")
    assert r.status_code == 200
    body = r.json()

    # PRs gone; the two real issues remain in order.
    assert [i["number"] for i in body["issues"]] == [1, 3]
    assert body["issues"][0]["labels"] == ["bug", "priority:high"]
    assert body["issues"][0]["url"].endswith("/issues/1")
    assert body["issues"][1]["title"] == "Second issue"

    # Auth header + query params shaped right.
    args, kwargs = get_mock.call_args
    assert args[0] == "https://api.github.com/repos/adamklie/greenroom/issues"
    assert kwargs["headers"]["Authorization"] == "token fake_token_xyz"
    assert kwargs["params"] == {"state": "open", "per_page": 20}
