"""Restore song-level annotations from a JSON export.

For each song in the export, match the DB row by (title, project) and
restore these fields from the export: artist, is_original, type, status,
notes. Other tables (audio_files, takes, setlists, etc.) are untouched.

Rules:
  - Match by (title, project). If there's no matching DB row, skip — we
    don't create songs that no longer exist.
  - Never overwrite a DB value with an empty/null export value. (So if
    you deleted a note in the UI intentionally, the restore won't bring
    it back.)
  - Dry-run by default: prints per-song diffs + a summary.
  - --apply to actually write. Backs up the DB first.

Usage:
    python -m scripts.restore_song_annotations <path/to/export.json>
    python -m scripts.restore_song_annotations <path/to/export.json> --apply
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.config import settings  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models import Song  # noqa: E402
from app.services.backup import backup_database  # noqa: E402


RESTORE_FIELDS = ("artist", "is_original", "type", "status", "notes")


@dataclass
class Diff:
    song_id: int
    title: str
    project: str
    changes: dict  # field -> (current_value, export_value)


def _is_empty(v):
    return v is None or (isinstance(v, str) and v.strip() == "")


def plan_restore(export_path: Path) -> tuple[list[Diff], list[str]]:
    """Return (diffs, misses). Diffs are DB rows that would change; misses
    are (title, project) pairs in the export that have no DB match."""
    data = json.loads(export_path.read_text())
    export_songs = data.get("songs", [])

    diffs: list[Diff] = []
    misses: list[str] = []

    with SessionLocal() as db:
        for es in export_songs:
            title = es.get("title")
            project = es.get("project")
            if not title or not project:
                continue
            song = db.query(Song).filter_by(title=title, project=project).first()
            if song is None:
                misses.append(f"{title} [{project}]")
                continue

            changes = {}
            for field in RESTORE_FIELDS:
                export_val = es.get(field)
                if _is_empty(export_val):
                    continue  # never overwrite with nothing
                current_val = getattr(song, field)
                if current_val != export_val:
                    changes[field] = (current_val, export_val)

            if changes:
                diffs.append(Diff(
                    song_id=song.id, title=title, project=project, changes=changes,
                ))

    return diffs, misses


def execute(diffs: list[Diff]) -> int:
    """Apply all diffs. Returns count of rows updated."""
    updated = 0
    with SessionLocal() as db:
        for diff in diffs:
            song = db.query(Song).get(diff.song_id)
            if song is None:
                continue
            for field, (_current, new_val) in diff.changes.items():
                setattr(song, field, new_val)
            db.add(song)
            db.commit()
            updated += 1
    return updated


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("export", type=Path, help="Path to annotations JSON file")
    parser.add_argument("--apply", action="store_true",
                        help="Actually write changes. Default is dry-run.")
    args = parser.parse_args()

    if not args.export.exists():
        print(f"Export not found: {args.export}", file=sys.stderr)
        return 1

    diffs, misses = plan_restore(args.export)

    print(f"Export:    {args.export}")
    print(f"DB:        {settings.db_path}")
    print()
    print(f"Songs with proposed changes: {len(diffs)}")
    print(f"Songs in export not in DB:   {len(misses)}")
    print()

    if diffs:
        print("Proposed changes:")
        for d in diffs:
            fields = ", ".join(
                f"{f}: {current!r} -> {new!r}"
                for f, (current, new) in d.changes.items()
            )
            print(f"  [{d.project}] {d.title!r} (AF id={d.song_id}):")
            for f, (current, new) in d.changes.items():
                print(f"    {f}: {current!r} -> {new!r}")

    if misses and len(misses) <= 20:
        print("\nIn export but not in DB (not restored):")
        for m in misses:
            print(f"  {m}")
    elif misses:
        print(f"\nIn export but not in DB: {len(misses)} songs (not shown; not restored)")

    if not args.apply:
        print("\nDry-run. Re-run with --apply to write these changes.")
        return 0

    if not diffs:
        print("\nNothing to do.")
        return 0

    print("\nBacking up DB before restore...")
    backup_path = backup_database()
    print(f"  DB backup: {backup_path}")

    print("Applying restore...")
    updated = execute(diffs)
    print(f"  Rows updated: {updated}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
