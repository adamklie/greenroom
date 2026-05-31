"""Copy organized files into the identifier-keyed vault when the vault copy is
missing.

Some files (recovered rows, recently-cut clips) live only at their organized
path (Covers/…, Ideas/…) and were never ingested into the canonical vault at
vault_files_dir/{identifier}.{ext}. Cloud (R2) playback keys off the vault name,
so those files 404 in prod. This copies each missing one into the vault; run a
normal `rclone copy` of the vault afterward to push them to R2.

Run LOCALLY (needs filesystem access to the iCloud music dir):
    cd backend
    python scripts/sync_to_vault.py            # dry-run (lists what it'd copy)
    python scripts/sync_to_vault.py --apply
"""

from __future__ import annotations

import shutil
import sys

from app.config import settings
from app.database import SessionLocal
from app.models import AudioFile


def main() -> int:
    apply = "--apply" in sys.argv
    db = SessionLocal()
    try:
        rows = (
            db.query(AudioFile)
            .filter(AudioFile.is_stem == False)  # noqa: E712
            .filter((AudioFile.role != "deleted") | (AudioFile.role.is_(None)))
            .filter(AudioFile.identifier.isnot(None), AudioFile.file_type.isnot(None))
            .all()
        )
        copied = missing = present = 0
        for af in rows:
            ext = af.file_type.lstrip(".").lower()
            vault_path = settings.vault_files_dir / f"{af.identifier}.{ext}"
            if vault_path.exists():
                present += 1
                continue
            src = settings.music_dir / af.file_path
            if not src.exists():
                print(f"  SOURCE MISSING  {af.identifier}  {af.file_path}")
                missing += 1
                continue
            print(f"  {'copy' if apply else 'would copy'}  {af.identifier}.{ext}  <-  {af.file_path}")
            if apply:
                settings.vault_files_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, vault_path)
                copied += 1
        print(f"\nin vault already: {present} | {'copied' if apply else 'to copy'}: "
              f"{copied if apply else sum(1 for _ in ()) or '(run with --apply)'} | source missing: {missing}")
        if not apply:
            print("Dry run — re-run with --apply, then: rclone copy <vault>/files greenroom-r2:greenroom-1-media/files")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
