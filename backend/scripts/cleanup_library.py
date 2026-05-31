"""Act on the library triage buckets from diagnose_library.py.

Passes (each opt-in; --dry-run previews, --yes skips the prompt):

  --recover       For soft-deleted rows whose file is present but ONLY this row
                  references it: re-point file_path to the real file and set
                  role='recording'. Files sitting in _trash/ are moved to
                  Recovered/ first so the 30-day purge can't reap them.
  --purge-dupes   Hard-delete soft-deleted rows whose file is ALSO held by an
                  active row (stale pre-reorg leftovers). The file is untouched.
  --delete-lost   Hard-delete soft-deleted rows with no file anywhere on disk.
  --match-ideas   Report only: pair each fileless ("empty idea") song with its
                  best-matching song that HAS files (typo covers), for reconcile.

Usage:
    cd backend
    python scripts/cleanup_library.py --recover --purge-dupes --delete-lost --match-ideas --dry-run
    python scripts/cleanup_library.py --recover --purge-dupes --delete-lost --yes
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
from collections import defaultdict
from difflib import SequenceMatcher

from sqlalchemy import update

from app.config import settings
from app.database import SessionLocal
from app.models import AudioFile, Song
from app.services.vault import is_cloud_backend, resolve_audio_path


def _disk_index() -> dict[str, list[str]]:
    idx: dict[str, list[str]] = defaultdict(list)
    root = settings.music_dir
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            idx[f.lower()].append(os.path.relpath(os.path.join(dirpath, f), root))
    return idx


def classify(db, disk):
    """-> (recover, dupes, lost) lists of AudioFile (non-stem, deleted)."""
    active_basenames = {
        os.path.basename(af.file_path).lower()
        for af in db.query(AudioFile).filter(
            AudioFile.is_stem == False,  # noqa: E712
            (AudioFile.role != "deleted") | (AudioFile.role.is_(None)),
        )
    }
    recover, dupes, lost = [], [], []
    for af in db.query(AudioFile).filter(AudioFile.is_stem == False, AudioFile.role == "deleted"):  # noqa: E712
        base = os.path.basename(af.file_path).lower()
        found = disk.get(base, [])
        if not found:
            lost.append(af)
        elif base in active_basenames:
            dupes.append(af)
        else:
            recover.append(af)
    return recover, dupes, lost


def _norm(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def match_ideas(db):
    """Pair each fileless song with its best song-that-has-files match."""
    with_files_ids = {
        af.song_id for af in db.query(AudioFile).filter(
            AudioFile.song_id.isnot(None),
            (AudioFile.role != "deleted") | (AudioFile.role.is_(None)),
        )
    }
    candidates = [s for s in db.query(Song).filter(Song.status != "deleted") if s.id in with_files_ids]
    empties = [
        s for s in db.query(Song).filter(Song.status != "deleted")
        if db.query(AudioFile).filter(AudioFile.song_id == s.id).count() == 0
    ]
    out = []
    for e in empties:
        ne = _norm(e.title)
        best, best_score = None, 0.0
        for c in candidates:
            nc = _norm(c.title)
            if not ne or not nc:
                continue
            if ne in nc or nc in ne:
                score = 0.95
            else:
                score = SequenceMatcher(None, ne, nc).ratio()
            if score > best_score:
                best, best_score = c, score
        out.append((e, best, best_score))
    return out


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--recover", action="store_true")
    p.add_argument("--purge-dupes", action="store_true")
    p.add_argument("--delete-lost", action="store_true")
    p.add_argument("--match-ideas", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--yes", action="store_true")
    args = p.parse_args()

    if is_cloud_backend():
        print("Run against the local vault (this walks the filesystem).")
        return 1

    db = SessionLocal()
    try:
        disk = _disk_index()
        recover, dupes, lost = classify(db, disk)
        print(f"recover={len(recover)}  purge-dupes={len(dupes)}  delete-lost={len(lost)}")

        if args.match_ideas:
            print("\n=== Empty-idea -> best match (reconcile candidates) ===")
            for e, best, score in sorted(match_ideas(db), key=lambda t: -t[2]):
                tag = "STRONG" if score >= 0.9 else ("maybe" if score >= 0.6 else "—")
                m = f"{best.title!r} (#{best.id}, {best.artist})" if best else "no candidate"
                print(f"  [{tag} {score:.2f}] {e.title!r} (#{e.id})  ->  {m}")

        planned = []  # (description, apply_fn)

        if args.recover:
            print("\n=== RECOVER ===")
            recovered_dir = settings.music_dir / "Recovered"
            for af in recover:
                base = os.path.basename(af.file_path)
                found = disk.get(base.lower(), [])
                # prefer an organized (non-_trash) location
                target_rel = next((f for f in found if not f.startswith("_trash")), found[0])
                in_trash = target_rel.startswith("_trash")
                print(f"  af {af.id} (song {af.song_id})  role deleted->recording")
                print(f"     -> file_path = {'Recovered/'+base if in_trash else target_rel}")

                def _apply(af=af, target_rel=target_rel, base=base, in_trash=in_trash):
                    if in_trash:
                        recovered_dir.mkdir(parents=True, exist_ok=True)
                        src = settings.music_dir / target_rel
                        dst = recovered_dir / base
                        if src.exists():
                            shutil.move(str(src), str(dst))
                        af.file_path = str(dst.relative_to(settings.music_dir))
                    else:
                        af.file_path = target_rel
                    af.role = "recording"
                planned.append(_apply)

        if args.purge_dupes:
            print(f"\n=== PURGE STALE DUPLICATES ({len(dupes)} rows) ===")
            ids = [af.id for af in dupes]
            def _apply_dupes(ids=ids):
                db.execute(update(Song).where(Song.reference_audio_file_id.in_(ids)).values(reference_audio_file_id=None))
                for af in dupes:
                    db.delete(af)
            if ids:
                planned.append(_apply_dupes)

        if args.delete_lost:
            print("\n=== DELETE LOST ===")
            for af in lost:
                print(f"  af {af.id}  {af.file_path}")
            ids = [af.id for af in lost]
            def _apply_lost(ids=ids):
                db.execute(update(Song).where(Song.reference_audio_file_id.in_(ids)).values(reference_audio_file_id=None))
                for af in lost:
                    db.delete(af)
            if ids:
                planned.append(_apply_lost)

        if not planned:
            print("\n(no mutating actions selected)")
            return 0
        if args.dry_run:
            print("\nDRY RUN — nothing committed.")
            return 0
        if not args.yes:
            if input(f"\nApply {len(planned)} action group(s)? [y/N] ").strip().lower() not in ("y", "yes"):
                print("Aborted.")
                return 1
        for fn in planned:
            fn()
        db.commit()
        print("Done.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
