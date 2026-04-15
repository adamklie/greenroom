"""Ingest music/Early Days/<Song>/<files> into greenroom.

- Each subfolder becomes (or matches) a Song (title=folder name, type=cover,
  project=solo, status=rehearsed).
- Each audio/video file in the folder becomes an AudioFile linked to that song.
- recorded_at is file mtime.

Idempotent: re-running skips songs/files already in the DB (matched by
file_path for audio files, case-insensitive title for songs).

Usage:
    python -m scripts.ingest_early_days [--dry-run]
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import AudioFile, Song
from app.models.audio_file import generate_identifier


ROOT_REL = "Early Days"
AUDIO_EXTS = {".m4a", ".mp3", ".wav", ".aif", ".aiff", ".flac", ".ogg"}
VIDEO_EXTS = {".mp4", ".mov", ".m4v"}
ALL_EXTS = AUDIO_EXTS | VIDEO_EXTS


def _find_song(db: Session, title: str) -> Song | None:
    t = title.strip()
    return (
        db.query(Song)
        .filter(Song.title.ilike(t))
        .filter(Song.status != "deleted")
        .first()
    )


def _ftype_for(ext: str) -> str:
    e = ext.lower().lstrip(".")
    return "mp4" if e == "m4v" else e


def ingest(db: Session, dry_run: bool = False) -> dict:
    root = settings.music_dir / ROOT_REL
    if not root.is_dir():
        raise RuntimeError(f"Not a directory: {root}")

    songs_created = 0
    songs_matched = 0
    files_added = 0
    files_skipped = 0

    for song_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        title = song_dir.name
        song = _find_song(db, title)
        if song:
            songs_matched += 1
        else:
            song = Song(
                title=title,
                artist=None,
                type="cover",
                project="solo",
                status="rehearsed",
            )
            db.add(song)
            db.flush()
            songs_created += 1

        for f in sorted(song_dir.iterdir()):
            if not f.is_file() or f.suffix.lower() not in ALL_EXTS:
                continue
            rel = str(f.relative_to(settings.music_dir))
            if db.query(AudioFile).filter_by(file_path=rel).first():
                files_skipped += 1
                continue

            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            ftype = _ftype_for(f.suffix)
            af = AudioFile(
                song_id=song.id,
                file_path=rel,
                file_type=ftype,
                identifier=generate_identifier(f.name, mtime.isoformat()),
                source="phone",
                role="practice_clip",
                is_stem=False,
                recorded_at=mtime,
                uploaded_at=datetime.now(),
                clip_name=f.stem,
            )
            db.add(af)
            files_added += 1

    if dry_run:
        db.rollback()
    else:
        db.commit()

    return {
        "root": str(root),
        "songs_created": songs_created,
        "songs_matched_existing": songs_matched,
        "files_added": files_added,
        "files_skipped_already_in_db": files_skipped,
        "dry_run": dry_run,
    }


def _cli():
    dry = "--dry-run" in sys.argv
    with SessionLocal() as db:
        result = ingest(db, dry_run=dry)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    _cli()
