"""Migrate Takes into AudioFiles — unifying all audio into one table.

Run: python -m app.services.migrate_takes
"""

from sqlalchemy import text

from app.database import SessionLocal, engine


def migrate():
    """Add session columns to audio_files, copy takes data, update references."""
    print("Migrating Takes → AudioFiles")

    with engine.connect() as conn:
        # 1. Add session columns to audio_files (if not exist)
        new_cols = {
            "session_id": "INTEGER REFERENCES practice_sessions(id)",
            "clip_name": "TEXT",
            "source_video": "TEXT",
            "start_time": "TEXT",
            "end_time": "TEXT",
            "video_path": "TEXT",
        }
        for col, col_type in new_cols.items():
            try:
                conn.execute(text(f"ALTER TABLE audio_files ADD COLUMN {col} {col_type}"))
                print(f"  Added audio_files.{col}")
            except Exception:
                print(f"  audio_files.{col} already exists")

        conn.commit()

        # 2. Copy takes into audio_files
        takes = conn.execute(text("SELECT * FROM takes")).fetchall()
        cols = [desc[0] for desc in conn.execute(text("SELECT * FROM takes LIMIT 0")).cursor.description]
        print(f"  Found {len(takes)} takes to migrate")

        migrated = 0
        skipped = 0
        for take in takes:
            row = dict(zip(cols, take))

            # Use audio_path as file_path, or video_path if no audio
            file_path = row.get("audio_path") or row.get("video_path")
            if not file_path:
                skipped += 1
                continue

            # Check if already in audio_files
            existing = conn.execute(
                text("SELECT id FROM audio_files WHERE file_path = :fp"),
                {"fp": file_path},
            ).first()

            if existing:
                # Update existing record with session context
                conn.execute(text("""
                    UPDATE audio_files SET
                        session_id = :session_id,
                        clip_name = :clip_name,
                        source_video = :source_video,
                        start_time = :start_time,
                        end_time = :end_time,
                        video_path = :video_path,
                        song_id = COALESCE(song_id, :song_id),
                        rating_overall = COALESCE(rating_overall, :rating_overall),
                        rating_vocals = COALESCE(rating_vocals, :rating_vocals),
                        rating_guitar = COALESCE(rating_guitar, :rating_guitar),
                        rating_drums = COALESCE(rating_drums, :rating_drums),
                        rating_tone = COALESCE(rating_tone, :rating_tone),
                        rating_timing = COALESCE(rating_timing, :rating_timing),
                        rating_energy = COALESCE(rating_energy, :rating_energy),
                        notes = COALESCE(notes, :notes)
                    WHERE file_path = :fp
                """), {
                    "session_id": row.get("session_id"),
                    "clip_name": row.get("clip_name"),
                    "source_video": row.get("source_video"),
                    "start_time": row.get("start_time"),
                    "end_time": row.get("end_time"),
                    "video_path": row.get("video_path"),
                    "song_id": row.get("song_id"),
                    "rating_overall": row.get("rating_overall"),
                    "rating_vocals": row.get("rating_vocals"),
                    "rating_guitar": row.get("rating_guitar"),
                    "rating_drums": row.get("rating_drums"),
                    "rating_tone": row.get("rating_tone"),
                    "rating_timing": row.get("rating_timing"),
                    "rating_energy": row.get("rating_energy"),
                    "notes": row.get("notes"),
                    "fp": file_path,
                })
                skipped += 1
            else:
                # Insert new record
                conn.execute(text("""
                    INSERT INTO audio_files (
                        song_id, file_path, file_type, source, role, is_stem,
                        session_id, clip_name, source_video, start_time, end_time, video_path,
                        rating_overall, rating_vocals, rating_guitar, rating_drums,
                        rating_tone, rating_timing, rating_energy, notes
                    ) VALUES (
                        :song_id, :file_path, :file_type, :source, :role, 0,
                        :session_id, :clip_name, :source_video, :start_time, :end_time, :video_path,
                        :rating_overall, :rating_vocals, :rating_guitar, :rating_drums,
                        :rating_tone, :rating_timing, :rating_energy, :notes
                    )
                """), {
                    "song_id": row.get("song_id"),
                    "file_path": file_path,
                    "file_type": "m4a" if file_path.endswith(".m4a") else "mp4",
                    "source": "gopro",
                    "role": "recording",
                    "session_id": row.get("session_id"),
                    "clip_name": row.get("clip_name"),
                    "source_video": row.get("source_video"),
                    "start_time": row.get("start_time"),
                    "end_time": row.get("end_time"),
                    "video_path": row.get("video_path"),
                    "rating_overall": row.get("rating_overall"),
                    "rating_vocals": row.get("rating_vocals"),
                    "rating_guitar": row.get("rating_guitar"),
                    "rating_drums": row.get("rating_drums"),
                    "rating_tone": row.get("rating_tone"),
                    "rating_timing": row.get("rating_timing"),
                    "rating_energy": row.get("rating_energy"),
                    "notes": row.get("notes"),
                })
                migrated += 1

        conn.commit()
        print(f"  Migrated: {migrated} new, {skipped} updated/skipped")

        # 3. Migrate take_tags to reference audio_files
        # (We'd need to map take_id → audio_file_id, skip for now)

        total = conn.execute(text("SELECT COUNT(*) FROM audio_files")).scalar()
        sessions = conn.execute(
            text("SELECT COUNT(*) FROM audio_files WHERE session_id IS NOT NULL")
        ).scalar()
        print(f"\n  Total audio files: {total}")
        print(f"  With session context: {sessions}")
        print(f"  Without session: {total - sessions}")

    print("\nMigration complete!")


if __name__ == "__main__":
    migrate()
