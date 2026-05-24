"""Tests for the cloud-backend 307-redirect path in the media router.

The local backend returns None from url_for() and the router falls through
to range-aware streaming; that path is already covered by the broader
integration tests. Here we just verify the cloud branch.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

from app.config import settings
from app.models import AudioFile, PracticeSession


def test_media_audio_redirects_to_presigned_url(client, db, monkeypatch):
    """When the active backend returns a signed URL, the route 307s to it."""
    # Flip the setting on so the route believes it's running in cloud mode.
    monkeypatch.setattr(settings, "media_backend", "r2")

    # Insert a session + audio file row so the DB lookup succeeds.
    sess = PracticeSession(date=date(2026, 1, 1), project="solo", folder_path="/tmp/s")
    db.add(sess)
    db.commit()
    db.refresh(sess)

    af = AudioFile(
        file_path="legacy/path.m4a",
        file_type="m4a",
        identifier="AFTESTREDIR",
        session_id=sess.id,
    )
    db.add(af)
    db.commit()
    db.refresh(af)

    # Stub out get_backend so we don't need real boto3 credentials.
    fake_backend = MagicMock()
    fake_backend.url_for.return_value = "https://example.r2.dev/test.m4a?sig=xyz"
    monkeypatch.setattr("app.routers.media.get_backend", lambda: fake_backend)

    response = client.get(f"/api/media/audio/{af.id}", follow_redirects=False)

    assert response.status_code == 307
    assert "example.r2.dev/test.m4a" in response.headers["location"]
    fake_backend.url_for.assert_called_once()
