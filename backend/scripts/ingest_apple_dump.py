"""Ingest an Apple Media Services data-export into greenroom.

Designed to be re-runnable: future dumps from Apple will only add new plays
and refresh track/playlist metadata. No duplicates.

Usage (CLI):
    python -m scripts.ingest_apple_dump /path/to/Apple_Media_Services.zip
    python -m scripts.ingest_apple_dump /path/to/extracted/dir --wipe

Also called from the /api/apple-music/ingest-dump endpoint.
"""

from __future__ import annotations

import csv
import io
import json
import sys
import zipfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine
from app.models.listening import (
    ApplePlaylist,
    ApplePlaylistTrack,
    ListeningHistory,
    ListeningPlay,
)

# --- Locating files inside the dump --------------------------------------------------

TRACK_HISTORY_CSV = "Apple Music Activity/Apple Music Play Activity.csv"
LIB_TRACKS_JSON_ZIP = "Apple Music Activity/Apple Music Library Tracks.json.zip"
LIB_PLAYLISTS_JSON_ZIP = "Apple Music Activity/Apple Music Library Playlists.json.zip"


class DumpReader:
    """Transparent access to files in a zip OR an extracted dir."""

    def __init__(self, src: Path):
        self.src = src
        if src.is_file() and src.suffix == ".zip":
            self._zf = zipfile.ZipFile(src)
            # Detect prefix (e.g. "Apple_Media_Services/")
            names = self._zf.namelist()
            self._prefix = ""
            for n in names:
                if n.endswith(TRACK_HISTORY_CSV):
                    self._prefix = n[: -len(TRACK_HISTORY_CSV)]
                    break
        elif src.is_dir():
            self._zf = None
            # Find the dir containing "Apple Music Activity/..."
            self._root = self._find_root(src)
        else:
            raise ValueError(f"Not a zip or directory: {src}")

    @staticmethod
    def _find_root(d: Path) -> Path:
        for p in [d, *d.rglob("Apple Music Activity")]:
            if (p / "Apple Music Activity").exists() or p.name == "Apple Music Activity":
                return p if p.name != "Apple Music Activity" else p.parent
        return d

    def close(self):
        if self._zf:
            self._zf.close()

    @contextmanager
    def open_text(self, relpath: str):
        """Open a UTF-8 text file from the dump."""
        if self._zf:
            full = self._prefix + relpath
            with self._zf.open(full) as raw:
                yield io.TextIOWrapper(raw, encoding="utf-8", newline="")
        else:
            with open(self._root / relpath, "r", encoding="utf-8", newline="") as f:
                yield f

    @contextmanager
    def open_inner_json(self, zip_relpath: str, inner_name: str | None = None):
        """Read a .json.zip (either from the outer zip or from an extracted dir)."""
        if self._zf:
            inner_bytes = self._zf.read(self._prefix + zip_relpath)
            inner_zf = zipfile.ZipFile(io.BytesIO(inner_bytes))
        else:
            inner_zf = zipfile.ZipFile(self._root / zip_relpath)
        try:
            name = inner_name or inner_zf.namelist()[0]
            with inner_zf.open(name) as f:
                yield f
        finally:
            inner_zf.close()


# --- Helpers -------------------------------------------------------------------------

def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    s = s.rstrip("Z")
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _parse_epoch_ms(v) -> datetime | None:
    try:
        ms = int(v)
    except (TypeError, ValueError):
        return None
    if ms <= 0:
        return None
    return datetime.utcfromtimestamp(ms / 1000.0)


def _truthy(v) -> bool:
    return str(v).strip().lower() in ("true", "1", "yes")


# --- Ingest stages -------------------------------------------------------------------

def _wipe(db: Session) -> None:
    db.execute(delete(ApplePlaylistTrack))
    db.execute(delete(ApplePlaylist))
    db.execute(delete(ListeningPlay))
    db.execute(delete(ListeningHistory))
    db.commit()


def _ingest_library_tracks(db: Session, reader: DumpReader) -> dict[str, int]:
    """Upsert ListeningHistory rows from the library tracks JSON.

    Returns a map apple_track_id -> listening_history.id for later joining.
    """
    with reader.open_inner_json(LIB_TRACKS_JSON_ZIP) as f:
        tracks = json.load(f)

    # Existing rows keyed by apple_track_id
    existing = {
        r.apple_track_id: r
        for r in db.query(ListeningHistory).filter(ListeningHistory.apple_track_id.isnot(None)).all()
    }

    id_map: dict[str, int] = {}
    added = 0
    updated = 0
    seen_in_pass: set[str] = set()
    pending_new: dict[str, ListeningHistory] = {}

    for t in tracks:
        track_id = t.get("Apple Music Track Identifier") or t.get("Track Identifier")
        if track_id is None:
            continue
        track_id_str = str(track_id)
        if track_id_str in seen_in_pass:
            continue
        seen_in_pass.add(track_id_str)

        duration_ms = t.get("Track Duration") or 0
        row = existing.get(track_id_str) or pending_new.get(track_id_str)
        if row:
            row.title = t.get("Title") or row.title
            row.artist = t.get("Artist") or row.artist or ""
            row.album = t.get("Album")
            row.genre = t.get("Genre")
            row.duration_seconds = int(duration_ms / 1000) if duration_ms else row.duration_seconds
            row.media_type = t.get("Content Type")
            row.last_played_at = _parse_iso(t.get("Last Played Date")) or row.last_played_at
            updated += 1
        else:
            row = ListeningHistory(
                apple_track_id=track_id_str,
                title=t.get("Title") or "",
                artist=t.get("Artist") or "",
                album=t.get("Album"),
                genre=t.get("Genre"),
                duration_seconds=int(duration_ms / 1000) if duration_ms else None,
                media_type=t.get("Content Type"),
                play_count=0,
                total_play_ms=0,
                last_played_at=_parse_iso(t.get("Last Played Date")),
            )
            db.add(row)
            pending_new[track_id_str] = row
            added += 1
        # Flush periodically so we can get IDs
        if (added + updated) % 2000 == 0:
            db.flush()

    db.flush()
    for row in db.query(ListeningHistory).filter(ListeningHistory.apple_track_id.isnot(None)).all():
        id_map[row.apple_track_id] = row.id

    db.commit()
    return {"added": added, "updated": updated, "id_map": id_map}


def _ingest_play_activity(
    db: Session, reader: DumpReader, id_map: dict[str, int]
) -> dict[str, int]:
    """Stream Play Activity CSV, insert ListeningPlay rows, aggregate into
    ListeningHistory.

    Play Activity CSV has Song Name + Album Name but NO artist or track ID,
    so we match back to library tracks by (title, album) first, then by title.
    """
    seen_events = {
        ev for (ev,) in db.query(ListeningPlay.event_id)
        .filter(ListeningPlay.event_id.isnot(None)).yield_per(5000)
    }

    # Build in-memory match indexes from existing library tracks
    title_album_idx: dict[tuple[str, str], int] = {}
    title_only_idx: dict[str, int] = {}  # only for rows where title is unambiguous
    title_collisions: set[str] = set()
    for r in db.query(ListeningHistory).all():
        if not r.title:
            continue
        t_key = r.title.lower().strip()
        a_key = (r.album or "").lower().strip()
        title_album_idx[(t_key, a_key)] = r.id
        if t_key in title_only_idx and title_only_idx[t_key] != r.id:
            title_collisions.add(t_key)
        else:
            title_only_idx[t_key] = r.id
    for t in title_collisions:
        title_only_idx.pop(t, None)

    agg: dict[int, dict] = {}
    plays_added = 0
    plays_skipped_dup = 0
    plays_skipped_no_title = 0
    orphan_rows_created = 0

    with reader.open_text(TRACK_HISTORY_CSV) as f:
        rd = csv.DictReader(f)
        batch: list[ListeningPlay] = []
        for row in rd:
            event_id = row.get("Event ID") or None
            if event_id and event_id in seen_events:
                plays_skipped_dup += 1
                continue

            track_name = (row.get("Song Name") or "").strip()
            if not track_name:
                plays_skipped_no_title += 1
                continue
            album_name = (row.get("Album Name") or "").strip()

            t_key = track_name.lower()
            a_key = album_name.lower()

            lh_id = title_album_idx.get((t_key, a_key))
            if lh_id is None:
                lh_id = title_only_idx.get(t_key)

            if lh_id is None:
                # Orphan — play of a track not in the library JSON
                new_row = ListeningHistory(
                    apple_track_id=None,
                    title=track_name,
                    artist="",
                    album=album_name or None,
                    media_type=row.get("Media Type"),
                )
                db.add(new_row)
                db.flush()
                lh_id = new_row.id
                title_album_idx[(t_key, a_key)] = lh_id
                if t_key not in title_collisions:
                    title_only_idx[t_key] = lh_id
                orphan_rows_created += 1

            ts = _parse_epoch_ms(row.get("Event Timestamp") or row.get("Event Start Timestamp"))
            duration_ms_raw = row.get("Play Duration Milliseconds") or "0"
            try:
                duration_ms = int(float(duration_ms_raw))
            except ValueError:
                duration_ms = 0

            batch.append(ListeningPlay(
                listening_history_id=lh_id,
                event_id=event_id,
                event_timestamp=ts,
                play_duration_ms=duration_ms if duration_ms > 0 else None,
                end_reason=row.get("End Reason Type"),
                event_type=row.get("Event Type"),
                container_type=row.get("Container Type"),
                container_name=row.get("Container Name"),
                device_type=row.get("Device Type") or row.get("Client Device Name"),
                country=row.get("ISO Country") or row.get("IP Country Code"),
            ))
            if event_id:
                seen_events.add(event_id)

            a = agg.setdefault(lh_id, {"plays": 0, "ms": 0, "first": None, "last": None})
            a["plays"] += 1
            a["ms"] += max(duration_ms, 0)
            if ts:
                if a["first"] is None or ts < a["first"]:
                    a["first"] = ts
                if a["last"] is None or ts > a["last"]:
                    a["last"] = ts

            if len(batch) >= 1000:
                db.bulk_save_objects(batch)
                plays_added += len(batch)
                batch.clear()
                db.commit()

        if batch:
            db.bulk_save_objects(batch)
            plays_added += len(batch)
            batch.clear()
            db.commit()

    # Apply aggregates
    for lh_id_int, a in agg.items():
        row = db.get(ListeningHistory, lh_id_int)
        if not row:
            continue
        row.play_count = (row.play_count or 0) + a["plays"]
        row.total_play_ms = (row.total_play_ms or 0) + a["ms"]
        if a["first"] and (row.first_played_at is None or a["first"] < row.first_played_at):
            row.first_played_at = a["first"]
        if a["last"] and (row.last_played_at is None or a["last"] > row.last_played_at):
            row.last_played_at = a["last"]
    db.commit()

    return {
        "plays_added": plays_added,
        "plays_skipped_dup": plays_skipped_dup,
        "plays_skipped_no_title": plays_skipped_no_title,
        "orphan_tracks_created": orphan_rows_created,
    }


def _ingest_playlists(db: Session, reader: DumpReader, id_map: dict[str, int]) -> dict[str, int]:
    with reader.open_inner_json(LIB_PLAYLISTS_JSON_ZIP) as f:
        playlists = json.load(f)

    existing = {p.apple_playlist_id: p for p in db.query(ApplePlaylist).all()}

    added = 0
    updated = 0
    tracks_linked = 0

    for p in playlists:
        pid = p.get("Container Identifier")
        if pid is None:
            continue
        pid_str = str(pid)
        items = p.get("Playlist Item Identifiers") or []

        row = existing.get(pid_str)
        if row:
            row.name = p.get("Title") or row.name
            row.description = p.get("Description") or row.description
            row.track_count = len(items)
            row.updated_at = _parse_iso(p.get("Playlist Items Modified Date")) or row.updated_at
            updated += 1
            # Re-populate tracks (simpler than diffing)
            db.execute(delete(ApplePlaylistTrack).where(ApplePlaylistTrack.playlist_id == row.id))
        else:
            row = ApplePlaylist(
                apple_playlist_id=pid_str,
                name=p.get("Title") or "(untitled)",
                description=p.get("Description"),
                is_collaborative=_truthy(p.get("Playlist Is Shared")),
                track_count=len(items),
                created_at=_parse_iso(p.get("Added Date")),
                updated_at=_parse_iso(p.get("Playlist Items Modified Date")),
            )
            db.add(row)
            db.flush()
            added += 1

        for i, track_id in enumerate(items):
            tid = str(track_id)
            lh_id = id_map.get(tid)
            title = ""
            artist = None
            album = None
            if lh_id:
                lh = db.query(ListeningHistory).get(lh_id)
                if lh:
                    title = lh.title
                    artist = lh.artist
                    album = lh.album
            db.add(ApplePlaylistTrack(
                playlist_id=row.id,
                position=i,
                apple_track_id=tid,
                title=title or f"(track {tid})",
                artist=artist,
                album=album,
            ))
            tracks_linked += 1

    db.commit()
    return {"playlists_added": added, "playlists_updated": updated, "tracks_linked": tracks_linked}


# --- Entry point ---------------------------------------------------------------------

def ingest(db: Session, src: Path, wipe: bool = False) -> dict:
    Base.metadata.create_all(bind=engine)  # ensure new tables exist

    if wipe:
        _wipe(db)

    reader = DumpReader(src)
    try:
        tracks_stats = _ingest_library_tracks(db, reader)
        id_map = tracks_stats.pop("id_map")
        plays_stats = _ingest_play_activity(db, reader, id_map)
        pl_stats = _ingest_playlists(db, reader, id_map)
    finally:
        reader.close()

    return {"source": str(src), "wiped": wipe, "tracks": tracks_stats,
            "plays": plays_stats, "playlists": pl_stats}


def _cli():
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.ingest_apple_dump <path> [--wipe]")
        sys.exit(1)
    src = Path(sys.argv[1])
    wipe = "--wipe" in sys.argv
    with SessionLocal() as db:
        result = ingest(db, src, wipe=wipe)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    _cli()
