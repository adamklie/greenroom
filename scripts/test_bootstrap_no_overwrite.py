"""Regression test: bootstrap_songs must not overwrite user-edited Song fields.

Creates a temp SQLite DB + a synthetic REPERTOIRE.md that declares a song as
'original'. Writes the same song into the DB with a user-edit value of
'cover'. Runs bootstrap_songs() and asserts the DB value is still 'cover'.

Run with:  python -m scripts.test_bootstrap_no_overwrite
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# Build throwaway vault + DB before importing app modules (env vars steer settings).
_test_dir = Path(tempfile.mkdtemp(prefix="bootstrap_test_"))
_test_music = _test_dir / "music"
_test_music.mkdir()
_test_vault = _test_dir / "vault"
_test_db = _test_dir / "greenroom.db"

os.environ["GREENROOM_MUSIC_DIR"] = str(_test_music)
os.environ["GREENROOM_VAULT_DIR"] = str(_test_vault)
os.environ["GREENROOM_DB_PATH"] = str(_test_db)

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.models import Song  # noqa: E402
from app.services.bootstrap import bootstrap_songs  # noqa: E402


# Minimal REPERTOIRE.md that the parser recognizes.
REPERTOIRE = """# Repertoire

## Solo

### Covers
| Song | Artist | Status | Times |
|------|--------|--------|-------|
| Test Song | Some Artist | idea | 0 |
"""


def main() -> int:
    (_test_music / "REPERTOIRE.md").write_text(REPERTOIRE)

    Base.metadata.create_all(bind=engine)

    # Seed the DB with a user-edited Song: title matches REPERTOIRE.md but
    # type is 'cover' + status 'polished' (user's corrections).
    with SessionLocal() as db:
        db.add(Song(
            title="Test Song",
            artist="USER-EDITED ARTIST",
            project="solo",
            is_original=False,
            type="cover",
            status="polished",
            notes="user notes",
        ))
        db.commit()

    # Run bootstrap_songs — the function under test.
    with SessionLocal() as db:
        bootstrap_songs(db)
        db.commit()

    # Assert all user edits survived.
    with SessionLocal() as db:
        song = db.query(Song).filter_by(title="Test Song", project="solo").first()
        assert song is not None, "song vanished after bootstrap"
        assert song.type == "cover", f"type overwritten: expected 'cover', got {song.type!r}"
        assert song.status == "polished", f"status overwritten: expected 'polished', got {song.status!r}"
        assert song.artist == "USER-EDITED ARTIST", f"artist overwritten: got {song.artist!r}"
        assert song.is_original is False, f"is_original overwritten: got {song.is_original!r}"
        assert song.notes == "user notes", f"notes overwritten: got {song.notes!r}"

    print("bootstrap_songs preserves user-edited fields on existing rows. ✓")

    # Cleanup
    import shutil
    shutil.rmtree(_test_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
