"""Read-only DB <-> storage reconciliation — make sure no recordings were dropped.

Reports two directions, never modifies anything:

  1. DB rows (active, not soft-deleted) whose backing object is MISSING.
  2. Storage objects with NO DB row at all — the real "dropped recording"
     risk (e.g. a GoPro upload that landed in R2 but whose ingest never
     created an audio_files row).

This is the spot-check companion to the GET /api/integrity/recordings
endpoint and to cleanup_orphan_audio_files.py (which fixes direction 1).

Usage
-----
    cd backend
    python scripts/reconcile_recordings.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from app.config import settings
from app.database import SessionLocal
from app.models import AudioFile
from app.services.vault import get_backend, is_cloud_backend


def main() -> int:
    db = SessionLocal()
    backend = get_backend()
    cloud = is_cloud_backend()
    try:
        known = {ident for (ident,) in db.query(AudioFile.identifier).all() if ident}

        active = (
            db.query(AudioFile)
            .filter((AudioFile.role != "deleted") | (AudioFile.role.is_(None)))
            .filter(AudioFile.identifier.isnot(None))
            .all()
        )

        # Direction 1: active rows with a missing object.
        missing = []
        for af in active:
            if not af.file_type:
                continue
            if not backend.exists(af.identifier, af.file_type):
                missing.append(af)

        # Direction 2: objects with no DB row.
        orphans: list[str] = []
        if cloud and hasattr(backend, "list_keys"):
            for key in backend.list_keys():
                if Path(key).stem and Path(key).stem not in known:
                    orphans.append(key)
        elif not cloud:
            files_dir = settings.vault_files_dir
            if files_dir.exists():
                for f in files_dir.iterdir():
                    if f.is_file() and f.stem not in known:
                        orphans.append(f.name)

        print(f"Backend: {'r2' if cloud else 'local'}")
        print(f"Active rows checked: {len(active)}")
        print()
        print(f"DB rows with a MISSING object: {len(missing)}")
        for af in missing:
            print(f"  id={af.id}  identifier={af.identifier}  file_path={af.file_path}")
        print()
        print(f"Storage objects with NO DB row (possible dropped recordings): {len(orphans)}")
        for key in orphans:
            print(f"  {key}")

        if not missing and not orphans:
            print("\nAll recordings accounted for. ✓")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
