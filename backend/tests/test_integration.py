"""Integration tests for greenroom MVP 1.0.

Cover the load-bearing flows: song CRUD, lyrics versioning, tag attach/detach,
upload happy-path, session detail shape, and the vault service primitives.

Where the router contract was different than the implementation plan assumed,
the test was adjusted to match the real behavior — those mismatches are
called out in inline comments so the next reader can find them quickly.
"""

from __future__ import annotations

from datetime import date

from app.config import settings
from app.models import AudioFile, PracticeSession, Song
from app.services import vault as vault_service


# --- Helper factories ---


def _make_song(db, **overrides) -> Song:
    """Insert a Song row directly via the session. Sensible defaults."""
    fields = dict(title="Test Song", type="idea", project="solo", status="idea")
    fields.update(overrides)
    song = Song(**fields)
    db.add(song)
    db.commit()
    db.refresh(song)
    return song


def _make_session(db, **overrides) -> PracticeSession:
    fields = dict(date=date(2026, 1, 1), project="solo", folder_path="/tmp/session")
    fields.update(overrides)
    sess = PracticeSession(**fields)
    db.add(sess)
    db.commit()
    db.refresh(sess)
    return sess


def _make_audio_file(db, **overrides) -> AudioFile:
    fields = dict(file_path="legacy/path.m4a", file_type="m4a", identifier="AFTEST0001")
    fields.update(overrides)
    af = AudioFile(**fields)
    db.add(af)
    db.commit()
    db.refresh(af)
    return af


# --- Tests ---


def test_song_crud_round_trip(client, db):
    """POST → GET → PATCH → GET (sees update) → DELETE → list excludes it."""
    # Create
    r = client.post("/api/songs", json={"title": "Roundtrip Song", "type": "idea"})
    assert r.status_code == 200, r.text
    song = r.json()
    song_id = song["id"]
    assert song["title"] == "Roundtrip Song"

    # Read
    r = client.get(f"/api/songs/{song_id}")
    assert r.status_code == 200
    assert r.json()["title"] == "Roundtrip Song"

    # Update
    r = client.patch(f"/api/songs/{song_id}", json={"title": "Renamed"})
    assert r.status_code == 200
    assert r.json()["title"] == "Renamed"

    # Read again — change persisted
    r = client.get(f"/api/songs/{song_id}")
    assert r.status_code == 200
    assert r.json()["title"] == "Renamed"

    # Delete (soft delete: status="deleted")
    r = client.delete(f"/api/songs/{song_id}")
    assert r.status_code == 200
    assert r.json().get("soft_deleted") is True

    # List excludes deleted songs by default
    r = client.get("/api/songs")
    assert r.status_code == 200
    assert all(s["id"] != song_id for s in r.json())

    # Including deleted shows it back
    r = client.get("/api/songs?include_deleted=true")
    assert r.status_code == 200
    assert any(s["id"] == song_id for s in r.json())


def test_song_lyrics_versioning(client, db):
    """Two PUTs to /lyrics → one prior version recorded.

    Contract (from routers/songs.py): the OLD lyrics get versioned before
    being replaced. So first PUT writes lyrics but versions nothing (no prior).
    Second PUT versions the first set. Third PUT versions the second set.
    """
    song = _make_song(db, title="Lyrics Song")

    r = client.put(f"/api/songs/{song.id}/lyrics", json={"lyrics": "verse one"})
    assert r.status_code == 200

    r = client.get(f"/api/songs/{song.id}/lyrics/versions")
    assert r.status_code == 200
    assert r.json() == []  # nothing prior to version

    r = client.put(f"/api/songs/{song.id}/lyrics", json={"lyrics": "verse two"})
    assert r.status_code == 200

    r = client.get(f"/api/songs/{song.id}/lyrics/versions")
    assert r.status_code == 200
    versions = r.json()
    assert len(versions) == 1
    assert versions[0]["lyrics_text"] == "verse one"
    assert versions[0]["version_number"] == 1


def test_tag_attach_detach(client, db):
    """POST tag to song auto-creates the tag and links it; DELETE detaches."""
    song = _make_song(db, title="Tagged Song")

    # Attach a fresh tag (validates the auto-create branch)
    r = client.post(f"/api/songs/{song.id}/tags", params={"tag_name": "new-tag"})
    assert r.status_code == 200
    assert "new-tag" in r.json()["tags"]

    # Confirm via GET /api/songs
    r = client.get("/api/songs")
    songs = r.json()
    s = next(x for x in songs if x["id"] == song.id)
    assert "new-tag" in s["tags"]

    # Detach
    r = client.delete(f"/api/songs/{song.id}/tags/new-tag")
    assert r.status_code == 200
    assert "new-tag" not in r.json()["tags"]


def test_upload_happy_path(client, db, sample_audio_file_path):
    """POST /api/upload with sample.m4a + create_song_title → AF row + vault file."""
    with sample_audio_file_path.open("rb") as fh:
        r = client.post(
            "/api/upload",
            files={"file": ("sample.m4a", fh, "audio/mp4")},
            data={"create_song_title": "Upload Test Song", "source": "test"},
        )
    assert r.status_code == 200, r.text
    payload = r.json()
    assert payload["ok"] is True
    assert payload["audio_file_id"] is not None
    assert payload["song_id"] is not None
    assert payload["identifier"].startswith("AF")
    assert payload["filename"].endswith(".m4a")
    assert payload["is_video"] is False  # m4a, not a video

    # Row landed in DB
    af = db.get(AudioFile, payload["audio_file_id"])
    assert af is not None
    assert af.file_path == payload["filename"]
    assert af.identifier == payload["identifier"]
    assert af.song_id == payload["song_id"]

    # File landed in the vault under {identifier}.m4a
    vault_path = settings.vault_files_dir / payload["filename"]
    assert vault_path.exists()
    assert vault_path.stat().st_size > 0


def test_session_detail_shape(client, db):
    """GET /api/sessions/{id} returns linked audio_files with song_title populated.

    Pins the N+1 fix in sessions.get_session: each AudioFile in the response
    must carry the joined song title (or None) without a separate API call.
    """
    sess = _make_session(db, folder_path="/tmp/sess1")
    song = _make_song(db, title="Linked Song")

    af_linked = _make_audio_file(
        db,
        file_path="legacy/linked.m4a",
        identifier="AFLINKED001",
        session_id=sess.id,
        song_id=song.id,
    )
    af_unlinked = _make_audio_file(
        db,
        file_path="legacy/unlinked.m4a",
        identifier="AFUNLINK001",
        session_id=sess.id,
    )

    r = client.get(f"/api/sessions/{sess.id}")
    assert r.status_code == 200, r.text
    body = r.json()

    afs = body["audio_files"]
    assert len(afs) == 2

    by_id = {af["id"]: af for af in afs}
    assert by_id[af_linked.id]["song_title"] == "Linked Song"
    assert by_id[af_unlinked.id]["song_title"] is None


def test_vault_basics(tmp_path, monkeypatch):
    """Vault path resolution + idempotent ingest_into_vault."""
    monkeypatch.setattr(settings, "music_dir", tmp_path)
    monkeypatch.setattr(settings, "vault_dir", tmp_path / "vault")
    settings.ensure_vault_layout()

    # 1) vault_path_for builds the canonical {identifier}.{ext} path
    p = vault_service.vault_path_for("AF12AB34CD", "m4a")
    assert p == settings.vault_files_dir / "AF12AB34CD.m4a"

    # 2) resolve_audio_path falls back to music_dir / file_path when there's
    #    no vault file (e.g. legacy row pre-vault migration).
    af = AudioFile(
        file_path="legacy/song.m4a",
        file_type="m4a",
        identifier="AFLEGACY01",
    )
    legacy_target = tmp_path / "legacy" / "song.m4a"
    legacy_target.parent.mkdir(parents=True, exist_ok=True)
    legacy_target.write_bytes(b"audio-bytes")
    resolved = vault_service.resolve_audio_path(af)
    assert resolved == legacy_target

    # 3) ingest_into_vault is idempotent — second call returns the same path
    #    and doesn't error.
    src = tmp_path / "source.m4a"
    src.write_bytes(b"audio-source")
    dest1 = vault_service.ingest_into_vault(src, "AFINGEST01", "m4a")
    assert dest1.exists()
    contents1 = dest1.read_bytes()
    dest2 = vault_service.ingest_into_vault(src, "AFINGEST01", "m4a")
    assert dest1 == dest2
    assert dest2.read_bytes() == contents1
