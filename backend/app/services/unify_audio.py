"""Unify Takes into AudioFiles — Phase 1 of the AudioFile unification plan.

Run: python -m app.services.unify_audio

Does:
  1. Rebuild audio_files with correct types (Float ratings, DATETIME recorded_at)
     and rename source_video -> source_file.
  2. Create audio_file_tags junction.
  3. Migrate remaining Take rows into audio_files (idempotent on file_path).
     Sets recorded_at = session.date, role = 'practice_clip', source = project.
  4. Migrate take_tags -> audio_file_tags.

Takes table is NOT dropped yet — routers still read from it. Phase 3 retires it.
"""

from sqlalchemy import text

from app.database import engine


def rebuild_audio_files(conn) -> None:
    """SQLite can't ALTER column types or rename in place, so rebuild the table."""
    existing = conn.execute(text("PRAGMA table_info(audio_files_new)")).fetchall()
    if existing:
        conn.execute(text("DROP TABLE audio_files_new"))

    conn.execute(text("""
        CREATE TABLE audio_files_new (
            id INTEGER PRIMARY KEY,
            song_id INTEGER REFERENCES songs(id),
            file_path VARCHAR NOT NULL UNIQUE,
            file_type VARCHAR,
            identifier VARCHAR UNIQUE,
            submitted_file_name VARCHAR,
            source VARCHAR,
            role VARCHAR DEFAULT 'recording',
            version VARCHAR,
            is_stem INTEGER NOT NULL DEFAULT 0,
            session_id INTEGER REFERENCES practice_sessions(id),
            clip_name TEXT,
            source_file TEXT,
            start_time TEXT,
            end_time TEXT,
            video_path TEXT,
            rating_overall REAL,
            rating_vocals REAL,
            rating_guitar REAL,
            rating_drums REAL,
            rating_tone REAL,
            rating_timing REAL,
            rating_energy REAL,
            rating_keys REAL,
            rating_bass REAL,
            rating_mix REAL,
            rating_other REAL,
            notes TEXT,
            content_hash TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
            uploaded_at DATETIME,
            recorded_at DATETIME
        )
    """))

    conn.execute(text("""
        INSERT INTO audio_files_new (
            id, song_id, file_path, file_type, identifier, submitted_file_name,
            source, role, version, is_stem,
            session_id, clip_name, source_file, start_time, end_time, video_path,
            rating_overall, rating_vocals, rating_guitar, rating_drums,
            rating_tone, rating_timing, rating_energy,
            rating_keys, rating_bass, rating_mix, rating_other,
            notes, content_hash, created_at, uploaded_at, recorded_at
        )
        SELECT
            id, song_id, file_path, file_type, identifier, submitted_file_name,
            source, role, version, is_stem,
            session_id, clip_name, source_video, start_time, end_time, video_path,
            CAST(rating_overall AS REAL), CAST(rating_vocals AS REAL),
            CAST(rating_guitar AS REAL), CAST(rating_drums AS REAL),
            CAST(rating_tone AS REAL), CAST(rating_timing AS REAL),
            CAST(rating_energy AS REAL),
            CAST(rating_keys AS REAL), CAST(rating_bass AS REAL),
            CAST(rating_mix AS REAL), CAST(rating_other AS REAL),
            notes, content_hash, created_at, uploaded_at, recorded_at
        FROM audio_files
    """))

    conn.execute(text("DROP TABLE audio_files"))
    conn.execute(text("ALTER TABLE audio_files_new RENAME TO audio_files"))
    conn.execute(text("CREATE UNIQUE INDEX ix_audio_files_identifier ON audio_files(identifier)"))
    print("  Rebuilt audio_files (Float ratings, DATETIME recorded_at, source_file).")


def create_audio_file_tags(conn) -> None:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS audio_file_tags (
            audio_file_id INTEGER NOT NULL REFERENCES audio_files(id) ON DELETE CASCADE,
            tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
            PRIMARY KEY (audio_file_id, tag_id)
        )
    """))
    print("  Created audio_file_tags junction.")


def migrate_takes_to_audio_files(conn) -> None:
    takes = conn.execute(text("""
        SELECT t.*, s.date AS session_date, s.project AS session_project
        FROM takes t
        LEFT JOIN practice_sessions s ON s.id = t.session_id
    """)).mappings().all()

    if not takes:
        print("  No takes to migrate.")
        return

    inserted = 0
    updated = 0
    skipped = 0

    for t in takes:
        file_path = t["audio_path"] or t["video_path"]
        if not file_path:
            skipped += 1
            continue

        existing = conn.execute(
            text("SELECT id FROM audio_files WHERE file_path = :fp"),
            {"fp": file_path},
        ).first()

        payload = {
            "song_id": t["song_id"],
            "file_path": file_path,
            "file_type": "m4a" if file_path.endswith(".m4a") else "mp4",
            "source": t["session_project"] or "gopro",
            "role": "practice_clip",
            "session_id": t["session_id"],
            "clip_name": t["clip_name"],
            "source_file": t["source_video"],
            "start_time": t["start_time"],
            "end_time": t["end_time"],
            "video_path": t["video_path"],
            "rating_overall": float(t["rating_overall"]) if t["rating_overall"] is not None else None,
            "rating_vocals": float(t["rating_vocals"]) if t["rating_vocals"] is not None else None,
            "rating_guitar": float(t["rating_guitar"]) if t["rating_guitar"] is not None else None,
            "rating_drums": float(t["rating_drums"]) if t["rating_drums"] is not None else None,
            "rating_tone": float(t["rating_tone"]) if t["rating_tone"] is not None else None,
            "rating_timing": float(t["rating_timing"]) if t["rating_timing"] is not None else None,
            "rating_energy": float(t["rating_energy"]) if t["rating_energy"] is not None else None,
            "notes": t["notes"],
            "created_at": t["created_at"],
            "recorded_at": t["session_date"],
        }

        if existing:
            conn.execute(text("""
                UPDATE audio_files SET
                    session_id = COALESCE(:session_id, session_id),
                    clip_name = COALESCE(:clip_name, clip_name),
                    source_file = COALESCE(:source_file, source_file),
                    start_time = COALESCE(:start_time, start_time),
                    end_time = COALESCE(:end_time, end_time),
                    video_path = COALESCE(:video_path, video_path),
                    song_id = COALESCE(song_id, :song_id),
                    source = COALESCE(source, :source),
                    role = COALESCE(NULLIF(role, 'recording'), :role),
                    recorded_at = COALESCE(recorded_at, :recorded_at),
                    rating_overall = COALESCE(rating_overall, :rating_overall),
                    rating_vocals = COALESCE(rating_vocals, :rating_vocals),
                    rating_guitar = COALESCE(rating_guitar, :rating_guitar),
                    rating_drums = COALESCE(rating_drums, :rating_drums),
                    rating_tone = COALESCE(rating_tone, :rating_tone),
                    rating_timing = COALESCE(rating_timing, :rating_timing),
                    rating_energy = COALESCE(rating_energy, :rating_energy),
                    notes = COALESCE(notes, :notes)
                WHERE file_path = :file_path
            """), payload)
            updated += 1
        else:
            conn.execute(text("""
                INSERT INTO audio_files (
                    song_id, file_path, file_type, source, role, is_stem,
                    session_id, clip_name, source_file, start_time, end_time, video_path,
                    rating_overall, rating_vocals, rating_guitar, rating_drums,
                    rating_tone, rating_timing, rating_energy,
                    notes, created_at, recorded_at
                ) VALUES (
                    :song_id, :file_path, :file_type, :source, :role, 0,
                    :session_id, :clip_name, :source_file, :start_time, :end_time, :video_path,
                    :rating_overall, :rating_vocals, :rating_guitar, :rating_drums,
                    :rating_tone, :rating_timing, :rating_energy,
                    :notes, :created_at, :recorded_at
                )
            """), payload)
            inserted += 1

    print(f"  Takes migrated: {inserted} inserted, {updated} updated, {skipped} skipped (no path).")


def migrate_take_tags(conn) -> None:
    rows = conn.execute(text("""
        SELECT af.id AS audio_file_id, tt.tag_id
        FROM take_tags tt
        JOIN takes t ON t.id = tt.take_id
        JOIN audio_files af
          ON af.file_path = COALESCE(t.audio_path, t.video_path)
    """)).fetchall()

    inserted = 0
    for audio_file_id, tag_id in rows:
        result = conn.execute(text("""
            INSERT OR IGNORE INTO audio_file_tags (audio_file_id, tag_id)
            VALUES (:af, :tag)
        """), {"af": audio_file_id, "tag": tag_id})
        inserted += result.rowcount or 0
    print(f"  Tag links migrated: {inserted} inserted ({len(rows)} source rows).")


def backfill_recorded_at_for_existing(conn) -> None:
    """Some pre-existing AudioFile rows with session_id may be missing recorded_at."""
    result = conn.execute(text("""
        UPDATE audio_files
        SET recorded_at = (
            SELECT date FROM practice_sessions WHERE id = audio_files.session_id
        )
        WHERE recorded_at IS NULL AND session_id IS NOT NULL
    """))
    print(f"  Backfilled recorded_at on {result.rowcount} rows.")


def backfill_role_and_source(conn) -> None:
    result = conn.execute(text("""
        UPDATE audio_files
        SET role = 'practice_clip'
        WHERE session_id IS NOT NULL AND (role IS NULL OR role = 'recording')
    """))
    print(f"  Set role='practice_clip' on {result.rowcount} rows.")

    result = conn.execute(text("""
        UPDATE audio_files
        SET source = (
            SELECT project FROM practice_sessions WHERE id = audio_files.session_id
        )
        WHERE session_id IS NOT NULL AND source IS NULL
    """))
    print(f"  Set source=<project> on {result.rowcount} rows.")


def migrate() -> None:
    print("Unifying Takes → AudioFiles")
    with engine.begin() as conn:
        rebuild_audio_files(conn)
        create_audio_file_tags(conn)
        migrate_takes_to_audio_files(conn)
        migrate_take_tags(conn)
        backfill_recorded_at_for_existing(conn)
        backfill_role_and_source(conn)

        total = conn.execute(text("SELECT COUNT(*) FROM audio_files")).scalar()
        with_session = conn.execute(text(
            "SELECT COUNT(*) FROM audio_files WHERE session_id IS NOT NULL"
        )).scalar()
        print(f"\n  Total audio_files: {total}")
        print(f"  With session_id:   {with_session}")
        print(f"  Standalone:        {total - with_session}")
    print("Done.")


if __name__ == "__main__":
    migrate()
