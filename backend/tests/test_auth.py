"""Phase 3a auth tests.

The existing 22 tests run with AUTH_REQUIRED=false (the default), which
makes all require_* deps return a synthetic admin. These tests flip the
flag on per-test via monkeypatch so they can actually exercise the cookie
+ role logic.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.auth.jwt import encode_token
from app.auth.router import COOKIE_NAME, _hash_token
from app.config import settings
from app.models import MagicToken, User


# ---------- fixtures ----------


@pytest.fixture
def auth_required(monkeypatch):
    """Flip GREENROOM_AUTH_REQUIRED on for this test."""
    monkeypatch.setattr(settings, "auth_required", True)


def _make_user(db, *, email: str, role: str) -> User:
    user = User(email=email, role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _attach_cookie(client, *, user: User) -> None:
    """Pre-set the session cookie on a TestClient so subsequent requests are
    authed as `user`. encode_token signs whatever we hand it, so this works
    even if the DB row is fresh."""
    token = encode_token(user_id=user.id, role=user.role)
    client.cookies.set(COOKIE_NAME, token)


@pytest.fixture
def as_viewer(client, db):
    user = _make_user(db, email="viewer@test", role="viewer")
    _attach_cookie(client, user=user)
    return client


@pytest.fixture
def as_editor(client, db):
    user = _make_user(db, email="editor@test", role="editor")
    _attach_cookie(client, user=user)
    return client


@pytest.fixture
def as_admin(client, db):
    user = _make_user(db, email="admin@test", role="admin")
    _attach_cookie(client, user=user)
    return client


# ---------- /api/auth/request ----------


def test_request_unknown_email_returns_200(client, auth_required):
    """Unknown email: still 200, so the endpoint can't be used to enumerate users."""
    res = client.post("/api/auth/request", json={"email": "nobody@example.com"})
    assert res.status_code == 200
    assert res.json()["ok"] is True


def test_request_known_email_creates_token(client, db, auth_required, monkeypatch, capsys):
    """Known email: creates a magic_tokens row + dispatches via the emailer."""
    _make_user(db, email="real@user", role="editor")

    sent: list[tuple[str, str]] = []

    class _SpyEmailer:
        def send(self, *, to_email, magic_link_url):
            sent.append((to_email, magic_link_url))

    monkeypatch.setattr("app.auth.router.get_emailer", lambda: _SpyEmailer())

    res = client.post("/api/auth/request", json={"email": "real@user"})
    assert res.status_code == 200
    # Row exists
    tokens = db.query(MagicToken).all()
    assert len(tokens) == 1
    assert tokens[0].user_id is not None
    assert tokens[0].used_at is None
    # Emailer was called
    assert len(sent) == 1
    assert sent[0][0] == "real@user"
    assert "/api/auth/exchange?token=" in sent[0][1]


# ---------- /api/auth/exchange ----------


def test_exchange_valid_token_sets_cookie_and_reaches_viewer_route(client, db, auth_required):
    user = _make_user(db, email="x@y", role="viewer")
    raw_token = "raw-test-token-aaa"
    db.add(MagicToken(
        user_id=user.id,
        token_hash=_hash_token(raw_token),
        expires_at=datetime.utcnow() + timedelta(minutes=15),
    ))
    db.commit()

    res = client.get(f"/api/auth/exchange?token={raw_token}", follow_redirects=False)
    assert res.status_code == 303
    # httpx stores cookies on the client
    assert COOKIE_NAME in client.cookies
    # And the cookie actually works on a viewer-gated route
    songs_res = client.get("/api/songs")
    assert songs_res.status_code == 200


def test_exchange_reused_token_401(client, db, auth_required):
    user = _make_user(db, email="x@y", role="viewer")
    raw_token = "raw-reused-aaa"
    db.add(MagicToken(
        user_id=user.id,
        token_hash=_hash_token(raw_token),
        expires_at=datetime.utcnow() + timedelta(minutes=15),
        used_at=datetime.utcnow(),  # already used
    ))
    db.commit()

    res = client.get(f"/api/auth/exchange?token={raw_token}", follow_redirects=False)
    assert res.status_code == 401


def test_exchange_expired_token_401(client, db, auth_required):
    user = _make_user(db, email="x@y", role="viewer")
    raw_token = "raw-expired-aaa"
    db.add(MagicToken(
        user_id=user.id,
        token_hash=_hash_token(raw_token),
        expires_at=datetime.utcnow() - timedelta(minutes=1),  # already expired
    ))
    db.commit()

    res = client.get(f"/api/auth/exchange?token={raw_token}", follow_redirects=False)
    assert res.status_code == 401


# ---------- role gating ----------


def test_mutate_unauthed_401(client, auth_required):
    """No cookie + AUTH_REQUIRED=true → 401 on a mutation."""
    res = client.post("/api/songs", json={"title": "Test"})
    assert res.status_code == 401


def test_mutate_viewer_403(as_viewer, auth_required):
    """Viewer hits a mutate route → 403 (authed, just under-privileged)."""
    res = as_viewer.post("/api/songs", json={"title": "Test"})
    assert res.status_code == 403


def test_mutate_editor_200(as_editor, auth_required):
    """Editor can create a song."""
    res = as_editor.post("/api/songs", json={"title": "Editor song"})
    assert res.status_code == 200
    assert res.json()["title"] == "Editor song"


def test_read_viewer_200(as_viewer, auth_required):
    """Viewer can read."""
    res = as_viewer.get("/api/songs")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


# ---------- bypass + logout ----------


def test_auth_required_false_bypasses(client):
    """Default state (AUTH_REQUIRED=false): mutations succeed without a cookie."""
    # No monkeypatch — settings.auth_required is False by default.
    assert settings.auth_required is False
    res = client.post("/api/songs", json={"title": "Bypass song"})
    assert res.status_code == 200


def test_logout_clears_cookie(as_editor, auth_required):
    # Pre-condition: cookie is set
    assert COOKIE_NAME in as_editor.cookies
    res = as_editor.post("/api/auth/logout")
    assert res.status_code == 200
    # Server tells the client to clear the cookie
    set_cookie = res.headers.get("set-cookie", "")
    assert COOKIE_NAME in set_cookie
    # Either Max-Age=0 or an expired date — both work
    assert ("max-age=0" in set_cookie.lower()) or ("expires=" in set_cookie.lower())
