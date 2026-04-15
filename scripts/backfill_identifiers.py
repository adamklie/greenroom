"""One-time migration: add identifier, submitted_file_name, and new rating columns to audio_files."""

import sqlite3
import sys
from pathlib import Path

# Find the database
GREENROOM_DIR = Path(__file__).resolve().parent.parent
DB_PATH = GREENROOM_DIR / "greenroom.db"

if not DB_PATH.exists():
    print(f"Database not found at {DB_PATH}")
    sys.exit(1)

# Import identifier generator
sys.path.insert(0, str(GREENROOM_DIR / "backend"))
from app.models.audio_file import generate_identifier

conn = sqlite3.connect(str(DB_PATH))
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# --- Step 1: Add new columns (ignore if already exist) ---
new_columns = [
    ("identifier", "TEXT"),
    ("submitted_file_name", "TEXT"),
    ("rating_keys", "INTEGER"),
    ("rating_bass", "INTEGER"),
    ("rating_mix", "INTEGER"),
    ("rating_other", "INTEGER"),
]

for col_name, col_type in new_columns:
    try:
        cur.execute(f"ALTER TABLE audio_files ADD COLUMN {col_name} {col_type}")
        print(f"  Added column: {col_name}")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print(f"  Column already exists: {col_name}")
        else:
            raise

conn.commit()

# --- Step 2: Backfill identifier and submitted_file_name ---
rows = cur.execute(
    "SELECT id, file_path, created_at FROM audio_files WHERE identifier IS NULL"
).fetchall()

print(f"\nBackfilling {len(rows)} rows...")

updated = 0
for row in rows:
    file_path = row["file_path"]
    created_at = row["created_at"] or ""
    filename = Path(file_path).name

    identifier = generate_identifier(filename, created_at)

    # Handle unlikely collision
    existing = cur.execute(
        "SELECT id FROM audio_files WHERE identifier = ?", (identifier,)
    ).fetchone()
    if existing:
        # Add row id as salt
        identifier = generate_identifier(f"{filename}:{row['id']}", created_at)

    cur.execute(
        "UPDATE audio_files SET identifier = ?, submitted_file_name = ? WHERE id = ?",
        (identifier, filename, row["id"]),
    )
    updated += 1

conn.commit()
print(f"  Updated {updated} rows")

# --- Step 3: Create unique index on identifier ---
try:
    cur.execute(
        "CREATE UNIQUE INDEX ix_audio_files_identifier ON audio_files(identifier)"
    )
    print("  Created unique index on identifier")
except sqlite3.OperationalError as e:
    if "already exists" in str(e).lower():
        print("  Index already exists")
    else:
        raise

conn.commit()
conn.close()

print("\nBackfill complete!")
