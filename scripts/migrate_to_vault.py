"""One-time migration: move every AudioFile into the vault.

For each row in audio_files:
  1. Resolve the current on-disk location (legacy: music_dir + file_path, or absolute).
  2. Ensure the row has an identifier + file_type (generate/infer if missing).
  3. Copy the source file to vault/files/{identifier}.{ext}.
  4. Update file_path to the new flat filename.

The original source file is left alone — the user can move/delete it
afterward, since the vault copy is now canonical.

Usage:
    python -m scripts.migrate_to_vault             # dry-run (default)
    python -m scripts.migrate_to_vault --execute   # actually copy + update DB

A DB backup is written before any changes when --execute is passed.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

# Make the backend package importable when invoked from the repo root.
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.config import settings  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models import AudioFile  # noqa: E402
from app.models.audio_file import generate_identifier  # noqa: E402
from app.services.backup import backup_database  # noqa: E402
from app.services.vault import vault_path_for  # noqa: E402


@dataclass
class Plan:
    af_id: int
    source: Path
    target: Path
    identifier: str
    file_type: str
    note: str = ""


def _resolve_source(af: AudioFile) -> Path:
    p = Path(af.file_path)
    if p.is_absolute():
        return p
    return settings.music_dir / af.file_path


def _infer_file_type(af: AudioFile, source: Path) -> str:
    if af.file_type:
        return af.file_type.lstrip(".").lower()
    return source.suffix.lstrip(".").lower()


def _ensure_identifier(af: AudioFile) -> str:
    if af.identifier:
        return af.identifier
    seed = af.submitted_file_name or Path(af.file_path).name
    return generate_identifier(seed)


def plan_migration() -> tuple[list[Plan], list[tuple[int, str]]]:
    """Return (plans, skipped). Skipped entries note why each was skipped."""
    plans: list[Plan] = []
    skipped: list[tuple[int, str]] = []

    with SessionLocal() as db:
        for af in db.query(AudioFile).order_by(AudioFile.id).all():
            if not af.file_path:
                skipped.append((af.id, "no file_path"))
                continue

            source = _resolve_source(af)
            if not source.exists():
                skipped.append((af.id, f"source missing: {source}"))
                continue

            file_type = _infer_file_type(af, source)
            identifier = _ensure_identifier(af)
            target = vault_path_for(identifier, file_type)

            if source.resolve() == target.resolve():
                skipped.append((af.id, "already in vault at canonical path"))
                continue

            note = ""
            if target.exists():
                note = "target exists (will keep existing vault copy, just update DB)"

            plans.append(Plan(
                af_id=af.id, source=source, target=target,
                identifier=identifier, file_type=file_type, note=note,
            ))

    return plans, skipped


def execute(plans: list[Plan]) -> tuple[int, int, list[str]]:
    """Returns (copied, db_updated, errors)."""
    settings.ensure_vault_layout()

    copied = 0
    updated = 0
    errors: list[str] = []

    with SessionLocal() as db:
        for plan in plans:
            af = db.query(AudioFile).get(plan.af_id)
            if af is None:
                errors.append(f"AF{plan.af_id}: row disappeared mid-migration")
                continue

            try:
                if not plan.target.exists():
                    shutil.copy2(plan.source, plan.target)
                    copied += 1

                af.identifier = plan.identifier
                af.file_type = plan.file_type
                af.file_path = plan.target.name
                db.add(af)
                updated += 1
            except Exception as e:  # noqa: BLE001
                errors.append(f"AF{plan.af_id}: {e}")
                db.rollback()
                continue

        db.commit()

    return copied, updated, errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true",
                        help="Actually copy files and update DB. Default is dry-run.")
    args = parser.parse_args()

    plans, skipped = plan_migration()

    print(f"Vault:     {settings.vault_dir}")
    print(f"Music dir: {settings.music_dir}")
    print(f"DB:        {settings.db_path}")
    print()
    print(f"Planned migrations: {len(plans)}")
    print(f"Skipped:            {len(skipped)}")

    if skipped:
        print("\nSkipped rows (first 20):")
        for af_id, reason in skipped[:20]:
            print(f"  AF id={af_id}: {reason}")
        if len(skipped) > 20:
            print(f"  ... and {len(skipped) - 20} more")

    if plans:
        print("\nFirst 10 planned moves:")
        for plan in plans[:10]:
            suffix = f" ({plan.note})" if plan.note else ""
            print(f"  AF id={plan.af_id}: {plan.source.name} -> {plan.target.name}{suffix}")
        if len(plans) > 10:
            print(f"  ... and {len(plans) - 10} more")

    if not args.execute:
        print("\nDry-run only. Re-run with --execute to apply.")
        return 0

    if not plans:
        print("\nNothing to do.")
        return 0

    print("\nBacking up DB before migration...")
    backup_path = backup_database()
    print(f"  DB backup: {backup_path}")

    print("Applying migration...")
    copied, updated, errors = execute(plans)
    print(f"  Copied to vault: {copied}")
    print(f"  DB rows updated: {updated}")
    if errors:
        print(f"  Errors ({len(errors)}):")
        for err in errors:
            print(f"    {err}")

    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
