"""Soft-delete AudioFile rows whose underlying media file no longer exists.

What this does
--------------
Scans every non-stem ``audio_files`` row that has an ``identifier`` set,
asks the active vault backend whether the corresponding file actually
exists, and sets ``role='deleted'`` on the rows whose file is gone.

The check honors the configured storage backend:

* ``media_backend=local``  -> stat the resolved on-disk path.
* ``media_backend=r2``     -> R2 ``head_object`` via ``CloudVaultBackend.exists``.

When to run
-----------
After any of these:

* A bulk move/rename of vault files outside the app.
* A failed ingest that committed DB rows before copying media.
* A cloud migration where some local files never made it to R2.
* Any time the Library shows phantom rows that 404 on playback.

Run with ``--list-only`` first to see what would be touched, then with
``--dry-run`` to walk the full update path without committing, then for
real with ``--yes`` to skip the confirmation prompt in CI/cron contexts.

Soft-delete, not hard-delete
----------------------------
Orphans are marked ``role='deleted'``. Nothing else is changed --
``identifier``, ``file_path``, ratings, tags, session_id all stay put. The
rows remain queryable; the UI just filters them out. This is intentionally
recoverable.

Undo
----
If a sweep was wrong, restore the affected rows with::

    UPDATE audio_files
       SET role = 'recording'
     WHERE id IN (<ids printed by this script>);

The script prints every affected ``(id, identifier, file_path)`` tuple so
the undo set is reconstructable from the run log.

Usage
-----
    cd backend
    python scripts/cleanup_orphan_audio_files.py --list-only
    python scripts/cleanup_orphan_audio_files.py --dry-run
    python scripts/cleanup_orphan_audio_files.py            # interactive
    python scripts/cleanup_orphan_audio_files.py --yes      # non-interactive
"""

from __future__ import annotations

import argparse
import sys

from app.database import SessionLocal
from app.models import AudioFile
from app.services.vault import get_backend, is_cloud_backend, resolve_audio_path


def _list_r2_keys(backend) -> set[str]:
    """Single paginated list_objects_v2 of `files/` prefix — way faster
    than per-row head_object when there are hundreds of candidates."""
    paginator = backend._s3.get_paginator("list_objects_v2")
    keys: set[str] = set()
    for page in paginator.paginate(Bucket=backend._bucket, Prefix="files/"):
        for obj in page.get("Contents", []) or []:
            keys.add(obj["Key"])
    return keys


def find_orphans(db) -> list[AudioFile]:
    """Return non-stem AudioFile rows whose backing file is missing."""
    backend = get_backend()
    candidates = (
        db.query(AudioFile)
        .filter(AudioFile.is_stem == False)  # noqa: E712 -- SQLAlchemy needs ==
        .filter(AudioFile.identifier.isnot(None))
        .filter((AudioFile.role.is_(None)) | (AudioFile.role != "deleted"))
        .all()
    )

    # Cloud path: one listing instead of N head_objects (which would otherwise
    # take 600+ round-trips and bust the `fly machine exec` timeout).
    r2_keys: set[str] | None = None
    if is_cloud_backend():
        r2_keys = _list_r2_keys(backend)

    orphans: list[AudioFile] = []
    for af in candidates:
        if not af.file_type:
            # Without a file_type we can't ask the backend; skip rather
            # than guess and risk a false-positive delete.
            continue
        if is_cloud_backend():
            key = backend._key(af.identifier, af.file_type)
            present = key in r2_keys
        else:
            present = resolve_audio_path(af).exists()
        if not present:
            orphans.append(af)
    return orphans


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Find orphans and walk the update path, but rollback instead of commit.",
    )
    parser.add_argument(
        "--list-only",
        action="store_true",
        help="Print orphans and exit. No DB writes attempted.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip the interactive confirmation prompt.",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        orphans = find_orphans(db)
        backend_name = "r2" if is_cloud_backend() else "local"
        print(f"Backend: {backend_name}")
        print(f"Orphans found: {len(orphans)}")
        for af in orphans:
            print(f"  id={af.id}  identifier={af.identifier}  file_path={af.file_path}")

        if not orphans:
            return 0

        if args.list_only:
            return 0

        if not args.yes and not args.dry_run:
            reply = input(f"Soft-delete {len(orphans)} row(s)? [y/N] ").strip().lower()
            if reply not in ("y", "yes"):
                print("Aborted.")
                return 1

        for af in orphans:
            af.role = "deleted"

        if args.dry_run:
            db.rollback()
            print(f"DRY RUN: would have soft-deleted {len(orphans)} row(s). Rolled back.")
        else:
            db.commit()
            print(f"Soft-deleted {len(orphans)} row(s).")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
