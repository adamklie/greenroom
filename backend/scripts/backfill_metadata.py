"""Backfill derivable AudioFile metadata where it's safely inferable.

Only fills fields from deterministic, existing sources — never guesses:

  recorded_at  <- linked session's date         (when the clip was recorded)
  uploaded_at  <- row created_at                 (proxy: when it entered Greenroom)
  clip_name    <- filename stem, but ONLY for rows that have start_time/end_time
                  set (i.e. genuine trimmed clips, not full recordings)

Each pass is opt-in via a flag; with no pass flags, ALL passes run. Nothing is
overwritten — only NULL/blank fields are touched. Soft-deleted and stem rows
are skipped.

Usage
-----
    cd backend
    python scripts/backfill_metadata.py --dry-run          # show what would change
    python scripts/backfill_metadata.py                    # interactive confirm, all passes
    python scripts/backfill_metadata.py --recorded --yes   # only recorded_at, no prompt
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime

from app.database import SessionLocal
from app.models import AudioFile, PracticeSession


def _stem(path: str) -> str:
    return os.path.splitext(os.path.basename(path))[0]


def _parse_filename_date(name: str) -> datetime | None:
    """Extract a recording date from common filename patterns. Conservative:
    returns None unless a pattern matches with in-range values.

      2025_01_25_... or 2025-01-25-...        -> Y M D
      Audio_04_11_2025_22_41_35 (voice memo)  -> M D Y H M S
      20250125_...                            -> Y M D (8-digit run)
    """
    def _mk(y, mo, d, h=0, mi=0, s=0):
        if not (2000 <= y <= 2099 and 1 <= mo <= 12 and 1 <= d <= 31):
            return None
        try:
            return datetime(y, mo, d, h, mi, s)
        except ValueError:
            return None

    m = re.match(r"^(\d{4})[_-](\d{1,2})[_-](\d{1,2})", name)
    if m:
        return _mk(int(m[1]), int(m[2]), int(m[3]))
    m = re.search(r"[Aa]udio[_-](\d{2})[_-](\d{2})[_-](\d{4})[_-](\d{2})[_-](\d{2})[_-](\d{2})", name)
    if m:
        return _mk(int(m[3]), int(m[1]), int(m[2]), int(m[4]), int(m[5]), int(m[6]))
    m = re.match(r"^(\d{4})(\d{2})(\d{2})(?:\D|$)", name)
    if m:
        return _mk(int(m[1]), int(m[2]), int(m[3]))
    return None


def plan_changes(db, do_recorded: bool, do_filename: bool, do_uploaded: bool, do_clip: bool):
    """Return a list of (audio_file, {field: new_value}) for rows to update."""
    rows = (
        db.query(AudioFile)
        .filter(AudioFile.is_stem == False)  # noqa: E712
        .filter((AudioFile.role != "deleted") | (AudioFile.role.is_(None)))
        .all()
    )
    sessions = {s.id: s for s in db.query(PracticeSession).all()}
    changes = []
    for af in rows:
        new: dict = {}

        # recorded_at: prefer the linked session's date; otherwise parse the
        # filename. Only fills when currently null.
        if af.recorded_at is None:
            if do_recorded and af.session_id in sessions and sessions[af.session_id].date is not None:
                new["recorded_at"] = datetime.combine(sessions[af.session_id].date, datetime.min.time())
            elif do_filename:
                parsed = _parse_filename_date(_stem(af.file_path))
                if parsed is not None:
                    new["recorded_at"] = parsed

        if do_uploaded and af.uploaded_at is None and af.created_at is not None:
            new["uploaded_at"] = af.created_at

        if do_clip and not af.clip_name and (af.start_time or af.end_time):
            stem = _stem(af.file_path)
            if stem:
                new["clip_name"] = stem

        if new:
            changes.append((af, new))
    return changes


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--recorded", action="store_true", help="Backfill recorded_at from session date.")
    p.add_argument("--filename", action="store_true", help="Backfill recorded_at from a date in the filename (no-session files).")
    p.add_argument("--uploaded", action="store_true", help="Backfill uploaded_at from created_at.")
    p.add_argument("--clip", action="store_true", help="Backfill clip_name from filename (trimmed clips only).")
    p.add_argument("--dry-run", action="store_true", help="Show changes, commit nothing.")
    p.add_argument("--yes", action="store_true", help="Skip the confirmation prompt.")
    args = p.parse_args()

    # No pass flags -> run all passes.
    if not (args.recorded or args.filename or args.uploaded or args.clip):
        args.recorded = args.filename = args.uploaded = args.clip = True

    db = SessionLocal()
    try:
        changes = plan_changes(db, args.recorded, args.filename, args.uploaded, args.clip)

        by_field: dict[str, int] = {}
        for _af, new in changes:
            for f in new:
                by_field[f] = by_field.get(f, 0) + 1

        print(f"Rows to update: {len(changes)}")
        for f, n in sorted(by_field.items()):
            print(f"  {f}: {n}")
        print()
        for af, new in changes[:40]:
            desc = ", ".join(f"{k}={v}" for k, v in new.items())
            print(f"  id={af.id}  {_stem(af.file_path)}  ->  {desc}")
        if len(changes) > 40:
            print(f"  … and {len(changes) - 40} more")

        if not changes:
            print("Nothing to backfill.")
            return 0
        if args.dry_run:
            print("\nDRY RUN — no changes committed.")
            return 0
        if not args.yes:
            reply = input(f"\nApply {len(changes)} update(s)? [y/N] ").strip().lower()
            if reply not in ("y", "yes"):
                print("Aborted.")
                return 1

        for af, new in changes:
            for field, value in new.items():
                setattr(af, field, value)
        db.commit()
        print(f"Updated {len(changes)} row(s).")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
