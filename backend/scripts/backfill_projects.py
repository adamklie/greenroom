"""Backfill v2 projects from the legacy `project` string (Phase 3a).

Creates one Project per distinct legacy project string (owned by the admin via
a role='owner' membership), then assigns project_id on every content row:

  songs              -> project for songs.project   ('ideas'/NULL -> Solo)
  practice_sessions  -> project for practice_sessions.project
  audio_files        -> its song's project, else its session's, else Solo
  takes              -> its session's project (takes always have a session)
  setlists           -> Solo (no per-setlist project concept)

"ideas" is treated as a song *type*, not a project, so ideas-songs land in the
owner's Solo project (the owner re-assigns later). Idempotent: projects are
get-or-created by name and only NULL project_id values are filled, so re-running
is safe. Run AFTER the f1a2b3c4d5e6 migration and BEFORE enabling GREENROOM_MULTI_PROJECT
(Phase 3b) — once project-scoping is active, an unscoped re-run could see fewer
rows and under-backfill. Requires at least one user (the owner) — on prod that's
the admin (local dev often has none; seed one with create_admin.py). Refuses to
commit if any project_id is still NULL afterward.

Usage:
    cd backend
    python scripts/backfill_projects.py --dry-run
    python scripts/backfill_projects.py            # interactive confirm
    python scripts/backfill_projects.py --yes
"""
from __future__ import annotations

import argparse
import sys

from app.database import SessionLocal
from app.models import (
    AudioFile, PracticeSession, Project, ProjectMember, Setlist, Song, Take, User,
)

SOLO_NAME = "Solo"


def _display_name(legacy: str) -> str:
    return legacy.replace("_", " ").title()


def main(dry_run: bool, assume_yes: bool) -> int:
    db = SessionLocal()
    try:
        owner = (
            db.query(User).filter(User.role == "admin").order_by(User.id).first()
            or db.query(User).order_by(User.id).first()
        )
        if owner is None:
            print("No users exist — create an admin first (scripts/create_admin.py). Aborting.")
            return 1
        print(f"Owner: {owner.email} (id={owner.id})")

        cache: dict[str, Project] = {}

        def get_project(name: str) -> Project:
            if name in cache:
                return cache[name]
            proj = db.query(Project).filter(Project.name == name).first()
            if proj is None:
                proj = Project(name=name)
                db.add(proj)
                db.flush()  # assign id
            if db.query(ProjectMember).filter_by(project_id=proj.id, user_id=owner.id).first() is None:
                db.add(ProjectMember(project_id=proj.id, user_id=owner.id, role="owner"))
            cache[name] = proj
            return proj

        solo = get_project(SOLO_NAME)

        def project_for_legacy(legacy: str | None) -> Project:
            # 'ideas' is a type, not a project; null/blank -> Solo.
            if not legacy or legacy == "ideas":
                return solo
            return get_project(_display_name(legacy))

        changes = {"songs": 0, "practice_sessions": 0, "audio_files": 0, "takes": 0, "setlists": 0}

        for s in db.query(Song).filter(Song.project_id.is_(None)).all():
            s.project_id = project_for_legacy(s.project).id
            changes["songs"] += 1

        for ps in db.query(PracticeSession).filter(PracticeSession.project_id.is_(None)).all():
            ps.project_id = project_for_legacy(ps.project).id
            changes["practice_sessions"] += 1

        db.flush()  # so song/session project_id is visible to the joins below

        song_proj = dict(db.query(Song.id, Song.project_id).all())
        sess_proj = dict(db.query(PracticeSession.id, PracticeSession.project_id).all())

        for af in db.query(AudioFile).filter(AudioFile.project_id.is_(None)).all():
            pid = song_proj.get(af.song_id) if af.song_id else None
            if pid is None and af.session_id:
                pid = sess_proj.get(af.session_id)
            af.project_id = pid or solo.id
            changes["audio_files"] += 1

        for t in db.query(Take).filter(Take.project_id.is_(None)).all():
            pid = sess_proj.get(t.session_id) if t.session_id else None
            if pid is None and t.song_id:
                pid = song_proj.get(t.song_id)
            t.project_id = pid or solo.id
            changes["takes"] += 1

        for sl in db.query(Setlist).filter(Setlist.project_id.is_(None)).all():
            sl.project_id = solo.id
            changes["setlists"] += 1

        db.flush()

        nulls = {}
        for model, name in [
            (Song, "songs"), (PracticeSession, "practice_sessions"),
            (AudioFile, "audio_files"), (Take, "takes"), (Setlist, "setlists"),
        ]:
            n = db.query(model).filter(model.project_id.is_(None)).count()
            if n:
                nulls[name] = n

        print("Projects:", sorted(p.name for p in db.query(Project).all()))
        print("Rows assigned this run:", changes)
        if nulls:
            print("WARNING — still NULL project_id after assignment:", nulls)

        if dry_run:
            db.rollback()
            print("DRY RUN — rolled back, nothing committed.")
            return 0
        if nulls:
            db.rollback()
            print("Refusing to commit with NULL project_id remaining.")
            return 1
        if not assume_yes:
            if input("Commit? [y/N] ").strip().lower() not in ("y", "yes"):
                db.rollback()
                print("Aborted.")
                return 1
        db.commit()
        print("Committed.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--dry-run", action="store_true", help="Show what would change, commit nothing.")
    p.add_argument("--yes", action="store_true", help="Skip the confirmation prompt.")
    args = p.parse_args()
    sys.exit(main(args.dry_run, args.yes))
