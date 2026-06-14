"""Re-unify songs with their media after cross-project splits.

A song and all its recordings/takes should share one project_id. An earlier
version of the "move" feature moved a recording without moving its song, which
could strand a recording in a different project than its song (it then shows as
"— link song" because the song isn't visible in that project's scope).

This heals every such split: for each song that has any recording or take in a
DIFFERENT project than the song, it moves the song + ALL its recordings + ALL
its takes into that project — i.e. it commits the move you intended (the media's
project is treated as the destination). If a song's stray media points at more
than one other project it's ambiguous, so the script skips it and reports it for
manual handling.

Usage:
    cd backend
    python scripts/heal_project_splits.py --dry-run
    python scripts/heal_project_splits.py --yes
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict

from app.database import SessionLocal
from app.models import AudioFile, Song, Take


def main(dry_run: bool, assume_yes: bool) -> int:
    db = SessionLocal()
    try:
        song_proj = dict(db.query(Song.id, Song.project_id).all())

        # For each song, collect the set of "other" projects its media sits in.
        stray: dict[int, set[int]] = defaultdict(set)
        for sid, pid in db.query(AudioFile.song_id, AudioFile.project_id).filter(AudioFile.song_id.isnot(None)).all():
            if sid in song_proj and pid is not None and pid != song_proj[sid]:
                stray[sid].add(pid)
        for sid, pid in db.query(Take.song_id, Take.project_id).filter(Take.song_id.isnot(None)).all():
            if sid in song_proj and pid is not None and pid != song_proj[sid]:
                stray[sid].add(pid)

        plan: dict[int, int] = {}      # song_id -> target project
        ambiguous: dict[int, set[int]] = {}
        for sid, projs in stray.items():
            if len(projs) == 1:
                plan[sid] = next(iter(projs))
            else:
                ambiguous[sid] = projs

        titles = dict(db.query(Song.id, Song.title).all())
        by_target: dict[int, list[int]] = defaultdict(list)
        for sid, tgt in plan.items():
            by_target[tgt].append(sid)
        print(f"Songs to re-unify: {len(plan)}  (ambiguous, skipped: {len(ambiguous)})")
        for tgt, sids in sorted(by_target.items()):
            print(f"  -> project {tgt}: {len(sids)} songs")
        for sid, projs in ambiguous.items():
            print(f"  AMBIGUOUS song {sid} ({titles.get(sid)}): media in projects {sorted(projs)} — skipped")

        if not plan:
            print("Nothing to heal.")
            return 0

        af_moved = tk_moved = 0
        for sid, tgt in plan.items():
            s = db.query(Song).get(sid)
            s.project_id = tgt
            for af in db.query(AudioFile).filter(AudioFile.song_id == sid).all():
                if af.project_id != tgt:
                    af.project_id = tgt; af_moved += 1
            for t in db.query(Take).filter(Take.song_id == sid).all():
                if t.project_id != tgt:
                    t.project_id = tgt; tk_moved += 1
        print(f"Will move {len(plan)} songs, {af_moved} recordings, {tk_moved} takes.")

        if dry_run:
            db.rollback()
            print("DRY RUN — nothing committed.")
            return 0
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
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--yes", action="store_true")
    args = p.parse_args()
    sys.exit(main(args.dry_run, args.yes))
