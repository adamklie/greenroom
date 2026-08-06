"""Dedup is project-scoped (v2).

Song deduplication must only ever group and merge songs within the active
project — never across projects — and it must display the authoritative project
(from project_id), not the legacy free-text `Song.project` string, which can be
stale. Runs in the prod-on config (auth + multi_project).
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
def dup(db, monkeypatch):
    """Flag-on world with a duplicate title straddling two projects.

    PA has two "Fast Car" songs (a genuine in-project duplicate); one carries a
    STALE legacy string ("solo") that disagrees with its project_id. PB has its
    own "Fast Car". Ids are expunged so the shared session starts each request
    with an empty identity map (matching prod's fresh-session-per-request)."""
    monkeypatch.setattr(settings, "auth_required", True)
    monkeypatch.setattr(settings, "multi_project", True)

    admin = User(email="admin@t", role="admin")
    db.add(admin)
    db.flush()

    pa, pb = Project(name="PA"), Project(name="PB")
    db.add_all([pa, pb])
    db.flush()
    db.add(ProjectMember(project_id=pa.id, user_id=admin.id, role="owner"))

    # PA duplicates. s1's legacy string is stale ("solo"), s2's happens to match.
    s1 = Song(title="Fast Car", artist="Tracy Chapman", type="cover", status="idea",
              project="solo", project_id=pa.id)
    s2 = Song(title="Fast Car", artist="Tracy Chapman", type="cover", status="idea",
              project="PA", project_id=pa.id)
    # PB's own "Fast Car" — same title+artist but a different project.
    s3 = Song(title="Fast Car", artist="Tracy Chapman", type="cover", status="idea",
              project="PB", project_id=pb.id)
    db.add_all([s1, s2, s3])
    db.flush()
    af = AudioFile(file_path="fc.mp4", file_type="mp4", project_id=pa.id, song_id=s1.id)
    db.add(af)
    db.commit()

    ns = SimpleNamespace(
        admin=(admin.id, admin.role),
        pa=pa.id, pb=pb.id, s1=s1.id, s2=s2.id, s3=s3.id, af=af.id,
    )
    db.expunge_all()
    return ns


def _as(client, user: tuple[int, str]):
    uid, role = user
    client.cookies.set(COOKIE_NAME, encode_token(user_id=uid, role=role))


def _h(project_id: int) -> dict:
    return {PROJECT_HEADER: str(project_id)}


def test_duplicates_scoped_to_active_project(client, dup):
    _as(client, dup.admin)
    res = client.get("/api/dedup/duplicates", headers=_h(dup.pa))
    assert res.status_code == 200
    ids = {e["id"] for g in res.json() for e in g["entries"]}
    # Only PA's two Fast Cars group; PB's is out of scope and never appears.
    assert ids == {dup.s1, dup.s2}
    assert dup.s3 not in ids


def test_duplicates_show_authoritative_project(client, dup):
    _as(client, dup.admin)
    res = client.get("/api/dedup/duplicates", headers=_h(dup.pa))
    projects = {e["project"] for g in res.json() for e in g["entries"]}
    # s1's stale legacy "solo" string must NOT leak through — both show "PA".
    assert projects == {"PA"}


def test_merge_within_project(client, dup, db):
    _as(client, dup.admin)
    res = client.post(
        "/api/dedup/merge",
        json={"keep_id": dup.s2, "merge_ids": [dup.s1]},
        headers=_h(dup.pa),
    )
    assert res.status_code == 200, res.text
    assert res.json()["merged_audio"] == 1
    db.expire_all()
    assert db.query(AudioFile).get(dup.af).song_id == dup.s2  # audio moved
    assert db.query(Song).get(dup.s1).status == "deleted"     # source tombstoned


def test_merge_keep_in_other_project_is_404(client, dup):
    _as(client, dup.admin)
    # keep_id is PB's song, but we're scoped to PA → scoped lookup can't see it.
    res = client.post(
        "/api/dedup/merge",
        json={"keep_id": dup.s3, "merge_ids": [dup.s1]},
        headers=_h(dup.pa),
    )
    assert res.status_code == 404


def test_merge_skips_cross_project_source(client, dup, db):
    _as(client, dup.admin)
    # keep is PA's s2; a cross-project source (PB's s3) is silently skipped, not
    # merged/deleted — merges never reach across projects.
    res = client.post(
        "/api/dedup/merge",
        json={"keep_id": dup.s2, "merge_ids": [dup.s3]},
        headers=_h(dup.pa),
    )
    assert res.status_code == 200
    assert res.json()["deleted_songs"] == []
    db.expire_all()
    s3 = db.query(Song).get(dup.s3)
    assert s3.status == "idea" and s3.project_id == dup.pb  # untouched
