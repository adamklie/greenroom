"""One-off: drop tables for features removed by feat/simplify-v2.

When to run: once, after merging feat/simplify-v2. The SQLAlchemy models
for these features are gone, so `Base.metadata.create_all` will not
recreate them. The tables linger as orphans until this script drops
them. Idempotent — safe to re-run; missing tables are skipped silently.

Tables dropped:
  - content_posts          (Content Planner)
  - listening_history      (Apple Music ingest)
  - listening_plays        (Apple Music ingest)
  - apple_playlists        (Apple Music ingest)
  - apple_playlist_tracks  (Apple Music ingest)
  - roadmap_tasks          (dead-code Roadmap model)
  - triage_queue           (Triage page)

Usage:
  python scripts/drop_simplified_tables.py

The DB path is read from the same source the app uses: the env var
GREENROOM_DB_PATH if set, otherwise the live `greenroom.db` next to
this repo. No backup is taken; run `make backend` (or the Sync page)
first if you want a fresh backup in the vault before dropping.
"""

import os
import sqlite3
import sys
from pathlib import Path


TABLES_TO_DROP = [
    "content_posts",
    "listening_history",
    "listening_plays",
    "apple_playlists",
    "apple_playlist_tracks",
    "roadmap_tasks",
    "triage_queue",
]


def _resolve_db_path() -> Path:
    env = os.environ.get("GREENROOM_DB_PATH")
    if env:
        return Path(env).expanduser()
    return Path(__file__).resolve().parent.parent / "greenroom.db"


def main() -> int:
    db_path = _resolve_db_path()
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return 1

    print(f"Database: {db_path}")
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    existing = {
        row[0]
        for row in cur.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }

    dropped = 0
    skipped = 0
    for table in TABLES_TO_DROP:
        if table in existing:
            cur.execute(f"DROP TABLE {table}")
            print(f"  dropped: {table}")
            dropped += 1
        else:
            print(f"  skipped (not present): {table}")
            skipped += 1

    conn.commit()
    conn.close()
    print(f"Done. Dropped {dropped}, skipped {skipped}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
