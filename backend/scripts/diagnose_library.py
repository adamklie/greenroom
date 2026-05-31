"""Triage library data problems into actionable buckets (read-only report).

Classifies the things that make songs "not play" or "have no files":

  RECOVERABLE   a soft-deleted audio file whose actual file is still on disk
                (often at a different path than the DB records). Re-point
                file_path + clear role='deleted' to restore it.
  LOST          a soft-deleted/active row whose file is not found anywhere on
                disk. Nothing to recover -> reconcile or hard-delete the row.
  EMPTY_IDEA    a song with no audio files at all (idea captured by name only).
                Leave, link a file, or delete the song.

Read-only. Pairs with reconcile_recordings.py / the Settings integrity check.

Usage:
    cd backend
    python scripts/diagnose_library.py
"""

from __future__ import annotations

import os
import sys
from collections import defaultdict

from app.config import settings
from app.database import SessionLocal
from app.models import AudioFile, Song
from app.services.vault import is_cloud_backend, resolve_audio_path


def _disk_index() -> dict[str, list[str]]:
    """basename(lower) -> [relative paths] for every file under music_dir."""
    idx: dict[str, list[str]] = defaultdict(list)
    root = settings.music_dir
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            full = os.path.join(dirpath, f)
            idx[f.lower()].append(os.path.relpath(full, root))
    return idx


def main() -> int:
    if is_cloud_backend():
        print("This diagnostic walks the local filesystem; run it against the local vault.")
        return 1

    db = SessionLocal()
    try:
        disk = _disk_index()

        recoverable, lost = [], []
        afs = db.query(AudioFile).filter(AudioFile.is_stem == False).all()  # noqa: E712
        for af in afs:
            deleted = af.role == "deleted"
            p = resolve_audio_path(af)
            on_disk = hasattr(p, "exists") and p.exists()
            if on_disk and not deleted:
                continue  # healthy
            base = os.path.basename(af.file_path).lower()
            found = disk.get(base, [])
            if on_disk and deleted:
                recoverable.append((af, [af.file_path], "marked deleted, file present"))
            elif found:
                recoverable.append((af, found, "file found at different path"))
            else:
                lost.append(af)

        # Songs with no audio files at all
        empty = []
        for s in db.query(Song).filter(Song.status != "deleted").all():
            if db.query(AudioFile).filter(AudioFile.song_id == s.id).count() == 0:
                empty.append(s)

        print(f"RECOVERABLE audio files: {len(recoverable)}")
        for af, paths, why in recoverable:
            print(f"  af id={af.id} song_id={af.song_id} role={af.role}  ({why})")
            print(f"     db path : {af.file_path}")
            for fp in paths[:3]:
                print(f"     on disk : {fp}")

        print(f"\nLOST audio files (no copy on disk): {len(lost)}")
        for af in lost:
            print(f"  af id={af.id} song_id={af.song_id} role={af.role}  {af.file_path}")

        print(f"\nEMPTY_IDEA songs (no audio files at all): {len(empty)}")
        for s in empty:
            print(f"  song id={s.id} {s.title!r} ({s.artist}) status={s.status}")

        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
