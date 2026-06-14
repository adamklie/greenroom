"""HTTP-level project isolation tests (v2 Phase 3b).

The ORM-level spec lives in test_scoping.py; this is the end-to-end proof that
the request stack — require_project_role gate + X-Greenroom-Project header +
do_orm_execute filter + before_flush stamp — keeps one project's data away from
another project's members over real HTTP, while admin and the dev-bypass see
everything.

All tests run with auth_required=True AND multi_project=True (the prod-on
config). Two projects, each owned by a different user, plus a viewer to exercise
per-project role gating.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.auth.jwt import encode_token
from app.auth.router import COOKIE_NAME
from app.config import settings
from app.models import AudioFile, Project, ProjectMember, Song, User

PROJECT_HEADER = "X-Greenroom-Project"


@pytest.fixture
def iso(db, monkeypatch):
    """Flag-on, auth-on world: users A (owner of PA), B (owner of PB), C (viewer
    of PA), plus a global admin. Each project has one song + one audio file.

    Everything is exposed as plain ids and then `expunge_all()`'d, so the shared
    test session starts each request with an empty identity map — matching prod,
    where each request gets a fresh session and a PK `.get()` therefore issues a
    SELECT that the scope filter can act on (a cached object would bypass it)."""
    monkeypatch.setattr(settings, "auth_required", True)
    monkeypatch.setattr(settings, "multi_project", True)

    admin = User(email="admin@t", role="admin")
    ua = User(email="a@t", role="editor")
    ub = User(email="b@t", role="editor")
    uc = User(email="c@t", role="editor")  # global editor, but only a VIEWER of PA
    db.add_all([admin, ua, ub, uc])
    db.flush()

    pa, pb = Project(name="PA"), Project(name="PB")
    db.add_all([pa, pb])
    db.flush()
    db.add_all([
        ProjectMember(project_id=pa.id, user_id=ua.id, role="owner"),
        ProjectMember(project_id=pb.id, user_id=ub.id, role="owner"),
        ProjectMember(project_id=pa.id, user_id=uc.id, role="viewer"),
    ])

    sa = Song(title="SongA", type="cover", status="idea", project="x", project_id=pa.id)
    sb = Song(title="SongB", type="cover", status="idea", project="x", project_id=pb.id)
    db.add_all([sa, sb])
    db.flush()
    afa = AudioFile(file_path="a.mp3", file_type="mp3", project_id=pa.id, song_id=sa.id)
    afb = AudioFile(file_path="b.mp3", file_type="mp3", project_id=pb.id, song_id=sb.id)
    db.add_all([afa, afb])
    db.commit()

    ns = SimpleNamespace(
        admin=(admin.id, admin.role), ua=(ua.id, ua.role),
        ub=(ub.id, ub.role), uc=(uc.id, uc.role),
        pa=pa.id, pb=pb.id, sa=sa.id, sb=sb.id, afa=afa.id, afb=afb.id,
    )
    db.expunge_all()
    return ns


def _as(client, user: tuple[int, str]):
    uid, role = user
    client.cookies.set(COOKIE_NAME, encode_token(user_id=uid, role=role))


def _h(project_id: int) -> dict:
    return {PROJECT_HEADER: str(project_id)}


# ---------- read isolation ----------

def test_list_songs_scoped_to_active_project(client, iso):
    _as(client, iso.ua)
    res = client.get("/api/songs", headers=_h(iso.pa))
    assert res.status_code == 200
    assert {s["title"] for s in res.json()} == {"SongA"}


def test_get_other_projects_song_is_404(client, iso):
    _as(client, iso.ua)
    res = client.get(f"/api/songs/{iso.sb}", headers=_h(iso.pa))
    assert res.status_code == 404


def test_patch_other_projects_song_is_404(client, iso):
    _as(client, iso.ua)
    res = client.patch(f"/api/songs/{iso.sb}", json={"title": "hax"}, headers=_h(iso.pa))
    assert res.status_code == 404


def test_delete_other_projects_song_is_404(client, iso):
    _as(client, iso.ua)
    res = client.delete(f"/api/songs/{iso.sb}", headers=_h(iso.pa))
    assert res.status_code == 404


def test_stream_other_projects_audio_is_404(client, iso):
    _as(client, iso.ua)
    res = client.get(f"/api/media/audio/{iso.afb}", headers=_h(iso.pa))
    assert res.status_code == 404


# ---------- gate behavior ----------

def test_missing_project_header_is_400(client, iso):
    _as(client, iso.ua)
    res = client.get("/api/songs")  # no X-Greenroom-Project
    assert res.status_code == 400


def test_header_for_unjoined_project_is_403(client, iso):
    _as(client, iso.ua)  # A is not a member of PB
    res = client.get("/api/songs", headers=_h(iso.pb))
    assert res.status_code == 403


def test_viewer_cannot_write(client, iso):
    _as(client, iso.uc)  # C is only a viewer of PA
    res = client.patch(f"/api/songs/{iso.sa}", json={"title": "nope"}, headers=_h(iso.pa))
    assert res.status_code == 403


def test_viewer_can_read(client, iso):
    _as(client, iso.uc)
    res = client.get(f"/api/songs/{iso.sa}", headers=_h(iso.pa))
    assert res.status_code == 200


# ---------- project cookie fallback (native requests) ----------

def test_cookie_scopes_request_without_header(client, iso):
    _as(client, iso.ua)
    # Native requests (audio/tab/download) can't set the header; the cookie does.
    client.cookies.set("greenroom_project", str(iso.pa))
    res = client.get("/api/songs")  # no X-Greenroom-Project header
    assert res.status_code == 200
    assert {s["title"] for s in res.json()} == {"SongA"}


def test_header_takes_precedence_over_cookie(client, iso):
    _as(client, iso.ua)
    # Cookie names PA (a project A belongs to) but the header names PB (it
    # doesn't) — the header wins, so membership fails → 403, proving precedence.
    client.cookies.set("greenroom_project", str(iso.pa))
    res = client.get("/api/songs", headers=_h(iso.pb))
    assert res.status_code == 403


# ---------- cross-project write validation ----------

def test_cannot_reassign_audio_to_other_projects_song(client, iso):
    _as(client, iso.ua)
    # A owns afa + sa; try to point afa at SongB (project PB) → rejected.
    res = client.patch(
        f"/api/audio-files/{iso.afa}",
        json={"song_id": iso.sb},
        headers=_h(iso.pa),
    )
    assert res.status_code == 400


def test_cannot_trim_other_projects_audio(client, iso):
    _as(client, iso.ua)
    # afb belongs to PB; the scoped .get() returns None → 404 before any ffmpeg.
    res = client.post(
        f"/api/audio-files/{iso.afb}/trim",
        json={"start_time": 0.0, "end_time": 1.0},
        headers=_h(iso.pa),
    )
    assert res.status_code == 404


# ---------- write stamping ----------

def test_created_song_inherits_active_project(client, iso, db):
    _as(client, iso.ua)
    res = client.post("/api/songs", json={"title": "Fresh"}, headers=_h(iso.pa))
    assert res.status_code == 200
    new_id = res.json()["id"]
    created = db.query(Song).get(new_id)
    assert created.project_id == iso.pa


# ---------- aggregates respect scope ----------

def test_dashboard_counts_are_scoped(client, iso):
    _as(client, iso.ua)
    res = client.get("/api/dashboard", headers=_h(iso.pa))
    assert res.status_code == 200
    stats = res.json()["stats"]
    # PA has exactly one song and one audio file; PB's are invisible.
    assert stats["total_songs"] == 1
    assert stats["total_audio_files"] == 1


# ---------- admin + dev bypass ----------

def test_admin_unscoped_without_a_project_sees_all(client, iso):
    _as(client, iso.admin)
    # No project selected → admin is unscoped → sees every project's songs.
    res = client.get("/api/songs")
    assert res.status_code == 200
    assert {s["title"] for s in res.json()} == {"SongA", "SongB"}


def test_admin_is_scoped_to_active_project(client, iso):
    _as(client, iso.admin)
    # With a project selected, the admin's view is scoped like anyone else's —
    # so the switcher actually filters for admins.
    res = client.get("/api/songs", headers=_h(iso.pa))
    assert res.status_code == 200
    assert {s["title"] for s in res.json()} == {"SongA"}


def test_admin_can_reach_any_project_without_membership(client, iso):
    _as(client, iso.admin)
    # Admin has no membership row in PB, but can still switch into it.
    res = client.get(f"/api/songs/{iso.sb}", headers=_h(iso.pb))
    assert res.status_code == 200


def test_dev_bypass_is_unscoped(client, iso, monkeypatch):
    monkeypatch.setattr(settings, "auth_required", False)  # dev: synthetic admin
    res = client.get("/api/songs")  # no auth, no header
    assert res.status_code == 200
    assert {s["title"] for s in res.json()} == {"SongA", "SongB"}


# ---------- projects API ----------

def test_list_projects_returns_only_memberships(client, iso):
    _as(client, iso.ua)
    res = client.get("/api/projects")
    assert res.status_code == 200
    assert [p["name"] for p in res.json()] == ["PA"]
    assert res.json()[0]["role"] == "owner"


def test_admin_lists_all_projects(client, iso):
    _as(client, iso.admin)
    res = client.get("/api/projects")
    assert {p["name"] for p in res.json()} == {"PA", "PB"}


def test_create_project_makes_creator_owner(client, iso, db):
    _as(client, iso.ub)
    res = client.post("/api/projects", json={"name": "New Band"})
    assert res.status_code == 201
    assert res.json()["role"] == "owner"
    pid = res.json()["id"]
    m = db.query(ProjectMember).filter_by(project_id=pid, user_id=iso.ub[0]).first()
    assert m is not None and m.role == "owner"


def test_owner_can_add_existing_member(client, iso, db):
    _as(client, iso.ua)
    res = client.post(
        f"/api/projects/{iso.pa}/members",
        json={"email": "b@t", "role": "editor"},
    )
    assert res.status_code == 201
    assert res.json()["role"] == "editor"


def test_add_unknown_email_is_404(client, iso):
    _as(client, iso.ua)
    res = client.post(
        f"/api/projects/{iso.pa}/members",
        json={"email": "nobody@nowhere", "role": "editor"},
    )
    assert res.status_code == 404


def test_non_owner_cannot_add_member(client, iso):
    _as(client, iso.uc)  # viewer of PA, not owner
    res = client.post(
        f"/api/projects/{iso.pa}/members",
        json={"email": "b@t", "role": "editor"},
    )
    assert res.status_code == 403


# ---------- move items between projects ----------

def test_move_song_cascades_recordings(client, iso, db):
    _as(client, iso.admin)  # admin can edit any target
    res = client.post(
        "/api/projects/move",
        json={"kind": "song", "ids": [iso.sa], "target_project_id": iso.pb},
        headers=_h(iso.pa),  # source = PA
    )
    assert res.status_code == 200
    assert res.json()["moved"] == 1
    db.expire_all()
    assert db.query(Song).get(iso.sa).project_id == iso.pb
    # The song's recording moves with it.
    assert db.query(AudioFile).get(iso.afa).project_id == iso.pb


def test_split_recording_creates_song_copy(client, iso, db):
    _as(client, iso.admin)
    # create_song: copy the source song into PB and link the recording there; the
    # source song stays in PA.
    res = client.post(
        "/api/projects/move-recordings",
        json={"audio_file_ids": [iso.afa], "target_project_id": iso.pb, "create_song": True},
        headers=_h(iso.pa),
    )
    assert res.status_code == 200
    new_song_id = res.json()["song_id"]
    db.expire_all()
    afa = db.query(AudioFile).get(iso.afa)
    assert afa.project_id == iso.pb
    assert afa.song_id == new_song_id and new_song_id != iso.sa
    assert db.query(Song).get(iso.sa).project_id == iso.pa  # source song untouched
    copy = db.query(Song).get(new_song_id)
    assert copy.project_id == iso.pb and copy.title == "SongA"


def test_split_recording_links_existing_song(client, iso, db):
    _as(client, iso.admin)
    res = client.post(
        "/api/projects/move-recordings",
        json={"audio_file_ids": [iso.afa], "target_project_id": iso.pb, "song_id": iso.sb},
        headers=_h(iso.pa),
    )
    assert res.status_code == 200
    db.expire_all()
    afa = db.query(AudioFile).get(iso.afa)
    assert afa.project_id == iso.pb and afa.song_id == iso.sb


def test_bulk_split_recordings_auto_match(client, iso, db):
    _as(client, iso.admin)
    # No song_id / create_song → auto-match by title+artist (creates "SongA" in PB).
    res = client.post(
        "/api/projects/move-recordings",
        json={"audio_file_ids": [iso.afa], "target_project_id": iso.pb},
        headers=_h(iso.pa),
    )
    assert res.status_code == 200
    assert res.json()["moved"] == 1
    db.expire_all()
    assert db.query(AudioFile).get(iso.afa).project_id == iso.pb
    assert db.query(Song).get(iso.sa).project_id == iso.pa  # source song stays


def test_list_project_songs_for_picker(client, iso):
    _as(client, iso.admin)
    res = client.get(f"/api/projects/{iso.pb}/songs")
    assert res.status_code == 200
    assert {s["title"] for s in res.json()} == {"SongB"}


def test_cannot_move_into_uneditable_project(client, iso):
    _as(client, iso.ua)  # owner of PA, not a member of PB
    res = client.post(
        "/api/projects/move",
        json={"kind": "song", "ids": [iso.sa], "target_project_id": iso.pb},
        headers=_h(iso.pa),
    )
    assert res.status_code == 403


def test_move_ignores_items_outside_source_scope(client, iso, db):
    _as(client, iso.ua)  # scoped to PA; can edit PA
    # Try to pull PB's song into PA — it isn't visible in PA scope, so nothing moves.
    res = client.post(
        "/api/projects/move",
        json={"kind": "song", "ids": [iso.sb], "target_project_id": iso.pa},
        headers=_h(iso.pa),
    )
    assert res.status_code == 200
    assert res.json()["moved"] == 0
    db.expire_all()
    assert db.query(Song).get(iso.sb).project_id == iso.pb  # unchanged


def test_owner_can_rename_project(client, iso, db):
    _as(client, iso.ua)  # owner of PA
    res = client.patch(f"/api/projects/{iso.pa}", json={"name": "Solo Stuff"})
    assert res.status_code == 200
    assert res.json()["name"] == "Solo Stuff"


def test_non_owner_cannot_rename_project(client, iso):
    _as(client, iso.uc)  # viewer of PA
    res = client.patch(f"/api/projects/{iso.pa}", json={"name": "Nope"})
    assert res.status_code == 403


def test_update_project_description_and_color(client, iso):
    _as(client, iso.ua)
    res = client.patch(f"/api/projects/{iso.pa}", json={"description": "My solo stuff", "color": "#10b981"})
    assert res.status_code == 200
    assert res.json()["description"] == "My solo stuff"
    assert res.json()["color"] == "#10b981"


def test_reorder_projects(client, iso):
    _as(client, iso.admin)
    client.post("/api/projects/reorder", json={"ordered_ids": [iso.pb, iso.pa]})
    res = client.get("/api/projects")
    order = [p["id"] for p in res.json()]
    assert order.index(iso.pb) < order.index(iso.pa)


def test_cannot_delete_nonempty_project(client, iso):
    _as(client, iso.ua)  # PA has SongA
    res = client.delete(f"/api/projects/{iso.pa}")
    assert res.status_code == 409


def test_delete_empty_project(client, iso, db):
    _as(client, iso.admin)
    pid = client.post("/api/projects", json={"name": "Temp"}).json()["id"]
    res = client.delete(f"/api/projects/{pid}")
    assert res.status_code == 204
    db.expire_all()
    assert db.query(Project).get(pid) is None


# ---------- ops endpoints are admin-only ----------

def test_filebrowser_forbidden_for_non_admin(client, iso):
    _as(client, iso.ua)
    res = client.get("/api/browse", headers=_h(iso.pa))
    assert res.status_code == 403
