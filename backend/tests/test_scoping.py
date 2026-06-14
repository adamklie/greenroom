"""Isolation tests for v2 project scoping (Phase 3b core).

These are the spec for the do_orm_execute filter: with the flag on and a scope
set, a session must see ONLY its project's rows — including through lazy
relationship loads — while flag-off and unscoped both behave like V1.
"""

import pytest

from app import scoping
from app.config import settings
from app.models import AudioFile, Project, Song


@pytest.fixture
def projects(db):
    """Two projects, each with a song + audio file, plus a 'rogue' audio file
    linked to project A's song but tagged to project B (to catch leaks)."""
    pa, pb = Project(name="A"), Project(name="B")
    db.add_all([pa, pb])
    db.flush()
    sa = Song(title="SongA", type="cover", status="idea", project="x", project_id=pa.id)
    sb = Song(title="SongB", type="cover", status="idea", project="x", project_id=pb.id)
    db.add_all([sa, sb])
    db.flush()
    db.add_all([
        AudioFile(file_path="a.mp3", project_id=pa.id, song_id=sa.id),
        AudioFile(file_path="b.mp3", project_id=pb.id, song_id=sb.id),
        AudioFile(file_path="rogue.mp3", project_id=pb.id, song_id=sa.id),
    ])
    db.commit()
    return pa, pb, sa, sb


def test_flag_off_means_no_scoping(db, projects, monkeypatch):
    monkeypatch.setattr(settings, "multi_project", False)
    pa, *_ = projects
    with scoping.scoped({pa.id}):  # scope is ignored while the flag is off
        assert db.query(Song).count() == 2
        assert db.query(AudioFile).count() == 3


def test_flag_on_but_unscoped_sees_everything(db, projects, monkeypatch):
    monkeypatch.setattr(settings, "multi_project", True)
    # No scope set → admin/system context → unfiltered.
    assert db.query(Song).count() == 2
    assert db.query(AudioFile).count() == 3


def test_scoped_to_one_project(db, projects, monkeypatch):
    monkeypatch.setattr(settings, "multi_project", True)
    pa, pb, sa, sb = projects
    with scoping.scoped({pa.id}):
        assert {s.title for s in db.query(Song).all()} == {"SongA"}
        assert {a.file_path for a in db.query(AudioFile).all()} == {"a.mp3"}
        # Direct fetch-by-id of another project's row returns nothing (→ 404).
        assert db.query(Song).filter(Song.id == sb.id).first() is None
        assert db.query(AudioFile).filter(AudioFile.file_path == "b.mp3").first() is None


def test_relationship_load_does_not_leak(db, projects, monkeypatch):
    monkeypatch.setattr(settings, "multi_project", True)
    pa, pb, sa, sb = projects
    with scoping.scoped({pa.id}):
        song = db.query(Song).filter(Song.id == sa.id).first()
        assert song is not None
        # SongA has a.mp3 (project A) and rogue.mp3 (project B). The lazy
        # relationship load must drop the cross-project row.
        assert {af.file_path for af in song.audio_files} == {"a.mp3"}
