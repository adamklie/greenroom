"""Backfill audio_files rows from takes rows where missing.

The AudioFile unification (Phases 1-3 per docs/AUDIOFILE_UNIFICATION.md)
ported the *read* side of practice sessions to audio_files, but the
*ingestion* side (Phase 4: bootstrap creating audio_files for session
clips) is still pending. As a result, sessions ingested via bootstrap
end up with take rows but no parallel audio_file rows, and the Sessions
page (which reads audio_files only) shows them as empty.

This script backfills the gap: for every take with a `video_path` set,
create a matching audio_file row with source='gopro', role='practice_clip',
a generated AF{hash} identifier, and the same session/song/ratings/notes
as the take.

Idempotent: if an audio_file row already exists with the same file_path,
the take is skipped.

Usage:
    cd backend
    python scripts/backfill_audio_files_from_takes.py [--dry-run]
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

# Make `app` importable regardless of cwd
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal
from app.models import AudioFile, PracticeSession, Take
from app.models.audio_file import generate_identifier


def file_type_from_path(p: str) -> str:
    """Return the lowercased extension without the dot, e.g. 'mp4'."""
    return Path(p).suffix.lstrip(".").lower() or "mp4"


def source_for_session(session: PracticeSession) -> str:
    """Map a session's project to an audio_files.source value.

    Mirrors what existing 2026-2-1-style rows use: 'gopro' or the project name.
    Default to 'gopro' since that's how every Ozone Destructors clip got there.
    """
    return "gopro"


def backfill(dry_run: bool = False) -> tuple[int, int, int]:
    """Returns (created_count, skipped_existing, skipped_no_path)."""
    db = SessionLocal()
    created = 0
    skipped_existing = 0
    skipped_no_path = 0

    try:
        takes = db.query(Take).all()
        print(f"Inspecting {len(takes)} takes...")

        for t in takes:
            # No video_path means no extracted file exists yet — nothing to point at
            if not t.video_path:
                skipped_no_path += 1
                continue

            existing = db.query(AudioFile).filter_by(file_path=t.video_path).first()
            if existing:
                # Patch session_id when it disagrees with the take. The take is the
                # source of truth here because its session was derived from the
                # cuts.txt parent folder. Existing audio_files sometimes ended up
                # linked to the wrong session via earlier bootstrap/upload paths.
                if t.session_id is not None and existing.session_id != t.session_id:
                    old_sid = existing.session_id
                    if not dry_run:
                        existing.session_id = t.session_id
                    print(f"  patch session_id  ->  af:{existing.id}  was:{old_sid} now:{t.session_id}  ({t.clip_name})")
                skipped_existing += 1
                continue

            session = db.query(PracticeSession).filter_by(id=t.session_id).first()
            if session is None:
                # Orphan take — skip
                continue

            file_type = file_type_from_path(t.video_path)
            identifier = generate_identifier(
                Path(t.video_path).name,
                datetime.utcnow().isoformat(),
            )

            af = AudioFile(
                song_id=t.song_id,
                file_path=t.video_path,
                file_type=file_type,
                identifier=identifier,
                source=source_for_session(session),
                role="practice_clip",
                session_id=t.session_id,
                clip_name=t.clip_name,
                source_file=t.source_video,
                start_time=t.start_time,
                end_time=t.end_time,
                video_path=t.video_path,
                rating_overall=t.rating_overall,
                rating_vocals=t.rating_vocals,
                rating_guitar=t.rating_guitar,
                rating_drums=t.rating_drums,
                rating_tone=t.rating_tone,
                rating_timing=t.rating_timing,
                rating_energy=t.rating_energy,
                notes=t.notes,
            )

            if not dry_run:
                db.add(af)
                db.flush()

            created += 1
            print(f"  create  ->  af:{af.id if not dry_run else '?'}  session:{t.session_id}  {t.clip_name}  ({t.video_path})")

        if not dry_run:
            db.commit()
            print(f"\nCommitted. created={created} skipped_existing={skipped_existing} skipped_no_path={skipped_no_path}")
        else:
            db.rollback()
            print(f"\nDRY RUN. Would create={created} skipped_existing={skipped_existing} skipped_no_path={skipped_no_path}")

    finally:
        db.close()

    return created, skipped_existing, skipped_no_path


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    backfill(dry_run=dry_run)
