"""Defensive tests for cloud-mode (settings.media_backend='r2').

`CloudVaultBackend.resolve()` returns a `PurePosixPath` (an R2 object key,
not a filesystem Path). Any route that touches `.exists()`, `.stat()`, or
`.parent.mkdir()` on that value crashes with AttributeError in cloud mode.
These tests pin down the contract for every route that was patched to
branch on `is_cloud_backend()`.

Setup pattern: monkeypatch `settings.media_backend = "r2"`, then either
- monkeypatch `get_backend()` in the relevant module to return a Mock
  (avoids needing real boto3 credentials), or
- just rely on the branch in route code (where `get_backend()` isn't called).
"""

from __future__ import annotations

from datetime import date
from pathlib import PurePosixPath
from unittest.mock import MagicMock

from app.config import settings
from app.models import AudioFile, PracticeSession, Song, SongTab


def _make_session(db) -> PracticeSession:
    sess = PracticeSession(date=date(2026, 1, 1), project="solo", folder_path="/tmp/s")
    db.add(sess)
    db.commit()
    db.refresh(sess)
    return sess


def _make_audio_file(db, **overrides) -> AudioFile:
    fields = dict(
        file_path="AFTEST0001.m4a",
        file_type="m4a",
        identifier="AFTEST0001",
    )
    fields.update(overrides)
    af = AudioFile(**fields)
    db.add(af)
    db.commit()
    db.refresh(af)
    return af


# --- LIST endpoint ---


def test_list_audio_files_does_not_crash_in_cloud_mode(client, db, monkeypatch):
    """Regression: GET /api/audio-files used to crash in cloud mode because
    `_af_to_read` called .exists() on the PurePosixPath returned by
    CloudVaultBackend.resolve()."""
    monkeypatch.setattr(settings, "media_backend", "r2")

    # Stub the backend so we don't need real boto3 credentials.
    fake_backend = MagicMock()
    fake_backend.resolve.return_value = PurePosixPath("files/AFTEST0001.m4a")
    fake_backend.url_for.return_value = "https://example.r2.dev/AFTEST0001.m4a?sig=x"
    monkeypatch.setattr("app.services.vault.get_backend", lambda: fake_backend)

    sess = _make_session(db)
    _make_audio_file(db, session_id=sess.id)

    response = client.get("/api/audio-files")
    assert response.status_code == 200, response.text
    rows = response.json()
    assert len(rows) == 1
    # In cloud mode we trust the backend has the file (file_exists is True
    # when abs_path is non-None and doesn't expose .exists()).
    assert rows[0]["identifier"] == "AFTEST0001"
    assert rows[0]["file_exists"] is True


# --- DELETE endpoint ---


def test_delete_audio_file_in_cloud_mode_is_db_only(client, db, monkeypatch, tmp_path):
    """DELETE /api/audio-files/{id} in cloud mode flips role='deleted' in the
    DB without touching the filesystem (no _trash/ creation, no shutil.move)."""
    monkeypatch.setattr(settings, "media_backend", "r2")

    af = _make_audio_file(db)
    af_id = af.id

    # Sentinel: trash dir does not exist before, must not exist after.
    trash_dir = settings.music_dir / "_trash"
    assert not trash_dir.exists()

    response = client.delete(f"/api/audio-files/{af_id}")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ok"] is True
    assert body["mode"] == "cloud-soft-delete"

    # No filesystem side effects.
    assert not trash_dir.exists()

    # DB row flipped to deleted.
    db.expire_all()
    refreshed = db.query(AudioFile).get(af_id)
    assert refreshed.role == "deleted"


# --- EXTRACT-AUDIO endpoint ---


def test_extract_audio_in_cloud_mode_returns_501(client, db, monkeypatch):
    """POST /api/audio-files/{id}/extract-audio is 501 in cloud mode (needs
    local ffmpeg + filesystem access)."""
    monkeypatch.setattr(settings, "media_backend", "r2")
    af = _make_audio_file(db, file_type="mp4")

    response = client.post(f"/api/audio-files/{af.id}/extract-audio")
    assert response.status_code == 501
    assert "cloud" in response.json()["detail"].lower()


# --- TRIM endpoint ---


def test_trim_in_cloud_mode_returns_501(client, db, monkeypatch):
    """POST /api/audio-files/{id}/trim is 501 in cloud mode."""
    monkeypatch.setattr(settings, "media_backend", "r2")
    af = _make_audio_file(db)

    response = client.post(
        f"/api/audio-files/{af.id}/trim",
        json={"start_time": 0.0, "end_time": 5.0},
    )
    assert response.status_code == 501
    assert "cloud" in response.json()["detail"].lower()


# --- TABS endpoints ---


def test_upload_tab_in_cloud_mode_returns_501(client, db, monkeypatch):
    """POST /api/tabs is 501 in cloud mode (no per-tab R2 integration yet)."""
    monkeypatch.setattr(settings, "media_backend", "r2")

    response = client.post(
        "/api/tabs",
        files={"file": ("test.gp", b"fake-gp-bytes", "application/octet-stream")},
        data={"song_id": "1"},
    )
    assert response.status_code == 501
    assert "cloud" in response.json()["detail"].lower()


def test_delete_tab_in_cloud_mode_returns_501(client, db, monkeypatch):
    """DELETE /api/tabs/{id} is 501 in cloud mode."""
    monkeypatch.setattr(settings, "media_backend", "r2")

    song = Song(title="X", type="idea", project="solo", status="idea")
    db.add(song)
    db.commit()
    db.refresh(song)
    tab = SongTab(song_id=song.id, file_path="tabs/foo.gp", file_format="gp")
    db.add(tab)
    db.commit()
    db.refresh(tab)

    response = client.delete(f"/api/tabs/{tab.id}")
    assert response.status_code == 501


# --- GOPRO endpoints ---


def test_gopro_analyze_in_cloud_mode_returns_501(client, monkeypatch):
    """POST /api/gopro/analyze is 501 in cloud mode (needs local ffmpeg)."""
    monkeypatch.setattr(settings, "media_backend", "r2")

    response = client.post(
        "/api/gopro/analyze",
        json={"video_path": "/tmp/whatever.mp4"},
    )
    assert response.status_code == 501


def test_gopro_process_in_cloud_mode_returns_501(client, monkeypatch):
    """POST /api/gopro/process is 501 in cloud mode."""
    monkeypatch.setattr(settings, "media_backend", "r2")

    response = client.post(
        "/api/gopro/process",
        json={
            "source_path": "/tmp/x.mp4",
            "session_date": "2026-01-01",
            "clips": [],
        },
    )
    assert response.status_code == 501


# --- FILES admin endpoints ---


def test_health_check_in_cloud_mode_returns_empty(client, db, monkeypatch):
    """GET /api/files/health returns an empty broken-link list in cloud mode
    (avoids calling .exists() on the PurePosixPath sentinel)."""
    monkeypatch.setattr(settings, "media_backend", "r2")
    # Insert an AF that *would* be flagged in local mode (vault is empty in tests).
    _make_audio_file(db)

    response = client.get("/api/files/health")
    assert response.status_code == 200
    body = response.json()
    assert body["total_broken"] == 0
    assert body["broken_links"] == []


def test_move_file_in_cloud_mode_returns_501(client, db, monkeypatch):
    """POST /api/files/audio/{id}/move is 501 in cloud mode."""
    monkeypatch.setattr(settings, "media_backend", "r2")
    af = _make_audio_file(db)

    response = client.post(
        f"/api/files/audio/{af.id}/move",
        json={"new_path": "elsewhere/file.m4a"},
    )
    assert response.status_code == 501


def test_consolidate_all_in_cloud_mode_returns_501(client, monkeypatch):
    """POST /api/files/consolidate-all is 501 in cloud mode."""
    monkeypatch.setattr(settings, "media_backend", "r2")
    response = client.post("/api/files/consolidate-all")
    assert response.status_code == 501


# --- Song soft-delete cloud path ---


def test_soft_delete_song_in_cloud_mode_marks_db_only(client, db, monkeypatch):
    """DELETE /api/songs/{id} in cloud mode flips song.status to 'deleted' and
    marks all child AudioFiles as role='deleted' without touching the disk."""
    monkeypatch.setattr(settings, "media_backend", "r2")

    song = Song(title="Doomed", type="idea", project="solo", status="idea")
    db.add(song)
    db.commit()
    db.refresh(song)
    af = _make_audio_file(db, song_id=song.id)

    trash_dir = settings.music_dir / "_trash"
    assert not trash_dir.exists()

    response = client.delete(f"/api/songs/{song.id}")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["soft_deleted"] is True
    assert body["files_trashed"] == 1

    # No filesystem side effects.
    assert not trash_dir.exists()

    db.expire_all()
    assert db.query(Song).get(song.id).status == "deleted"
    assert db.query(AudioFile).get(af.id).role == "deleted"


# --- Vault helper ---


def test_is_cloud_backend_helper(monkeypatch):
    """The single switch that every route branches on."""
    from app.services.vault import is_cloud_backend

    monkeypatch.setattr(settings, "media_backend", "local")
    assert is_cloud_backend() is False

    monkeypatch.setattr(settings, "media_backend", "r2")
    assert is_cloud_backend() is True
