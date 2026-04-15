"""Song deduplication — find and merge duplicate songs."""

import re
from collections import defaultdict
from difflib import SequenceMatcher

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AudioFile, Song, Take

router = APIRouter(prefix="/api/dedup", tags=["dedup"])


class DuplicateEntry(BaseModel):
    id: int
    title: str
    artist: str | None
    type: str | None
    status: str | None
    project: str | None
    audio_count: int
    take_count: int
    notes: str | None


class DuplicateGroup(BaseModel):
    key: str
    entries: list[DuplicateEntry]


class MergeRequest(BaseModel):
    keep_id: int
    merge_ids: list[int]


def _normalize(s: str) -> str:
    """Normalize a string for comparison: lowercase, strip punctuation, collapse whitespace."""
    s = s.strip().lower()
    s = re.sub(r"[''`]", "", s)  # remove apostrophes
    s = re.sub(r"[^a-z0-9\s]", " ", s)  # punctuation to spaces
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


@router.get("/duplicates", response_model=list[DuplicateGroup])
def find_duplicates(fuzzy: bool = Query(False), threshold: float = Query(0.8), db: Session = Depends(get_db)):
    """Find songs with matching title+artist. Set fuzzy=true for approximate matching."""
    songs = db.query(Song).filter(Song.status != "deleted").all()

    def _make_entry(s: Song) -> DuplicateEntry:
        af_count = db.query(func.count(AudioFile.id)).filter(AudioFile.song_id == s.id).scalar()
        take_count = db.query(func.count(Take.id)).filter(Take.song_id == s.id).scalar()
        return DuplicateEntry(
            id=s.id, title=s.title, artist=s.artist, type=s.type,
            status=s.status, project=s.project, audio_count=af_count,
            take_count=take_count, notes=s.notes,
        )

    if not fuzzy:
        # Exact match (case-insensitive). Group by title; within a title,
        # songs with a blank artist merge into any populated-artist group.
        title_groups: dict[str, list[Song]] = defaultdict(list)
        for s in songs:
            title_groups[s.title.strip().lower()].append(s)

        results = []
        for title_key, songs_with_title in sorted(title_groups.items()):
            by_artist: dict[str, list[Song]] = defaultdict(list)
            for s in songs_with_title:
                by_artist[(s.artist or "").strip().lower()].append(s)

            blanks = by_artist.pop("", [])
            if by_artist:
                # Attach blank-artist songs to every populated group (likely dupes)
                for artist_key, group in by_artist.items():
                    merged = group + blanks
                    if len(merged) < 2:
                        continue
                    results.append(DuplicateGroup(
                        key=f"{title_key}||{artist_key}",
                        entries=[_make_entry(s) for s in merged],
                    ))
            elif len(blanks) >= 2:
                results.append(DuplicateGroup(
                    key=f"{title_key}||",
                    entries=[_make_entry(s) for s in blanks],
                ))
        return results

    # Fuzzy matching — compare all pairs
    merged_into: dict[int, int] = {}  # song_id -> group representative id
    fuzzy_groups: dict[int, list[Song]] = {}  # representative id -> songs

    for i, a in enumerate(songs):
        if a.id in merged_into:
            continue
        norm_a = _normalize(a.title)
        artist_a = _normalize(a.artist or "")

        for b in songs[i + 1:]:
            if b.id in merged_into:
                continue
            norm_b = _normalize(b.title)
            artist_b = _normalize(b.artist or "")

            title_sim = _similarity(norm_a, norm_b)
            # If artists both exist, require they're similar too
            if artist_a and artist_b:
                artist_sim = _similarity(artist_a, artist_b)
                if title_sim >= threshold and artist_sim >= 0.6:
                    pass  # match
                else:
                    continue
            elif title_sim < threshold:
                continue

            # Found a fuzzy match
            rep = merged_into.get(a.id, a.id)
            if rep not in fuzzy_groups:
                fuzzy_groups[rep] = [a]
            if b not in fuzzy_groups[rep]:
                fuzzy_groups[rep].append(b)
            merged_into[b.id] = rep

    results = []
    for rep_id, group_songs in sorted(fuzzy_groups.items()):
        if len(group_songs) < 2:
            continue
        key = f"fuzzy||{group_songs[0].title.lower()}"
        results.append(DuplicateGroup(
            key=key,
            entries=[_make_entry(s) for s in group_songs],
        ))

    return results


@router.post("/merge")
def merge_songs(req: MergeRequest, db: Session = Depends(get_db)):
    """Merge duplicate songs: move all audio files and takes to keep_id, delete the rest."""
    keep = db.query(Song).get(req.keep_id)
    if not keep:
        raise HTTPException(404, f"Song {req.keep_id} not found")

    merged_audio = 0
    merged_takes = 0
    deleted_songs = []

    for merge_id in req.merge_ids:
        if merge_id == req.keep_id:
            continue
        source = db.query(Song).get(merge_id)
        if not source:
            continue

        # Move audio files
        afs = db.query(AudioFile).filter(AudioFile.song_id == merge_id).all()
        for af in afs:
            af.song_id = req.keep_id
            merged_audio += 1

        # Move takes
        takes = db.query(Take).filter(Take.song_id == merge_id).all()
        for t in takes:
            t.song_id = req.keep_id
            merged_takes += 1

        # Update reference_audio_file_id if the source had one and keep doesn't
        if source.reference_audio_file_id and not keep.reference_audio_file_id:
            keep.reference_audio_file_id = source.reference_audio_file_id

        # Merge notes
        if source.notes:
            keep.notes = ((keep.notes or "") + "\n" + source.notes).strip()

        # Preserve higher practice count
        keep.times_practiced = max(keep.times_practiced or 0, source.times_practiced or 0)

        # Preserve lyrics if keep has none
        if not keep.lyrics and source.lyrics:
            keep.lyrics = source.lyrics

        # Preserve key/tempo/tuning/vibe if keep has none
        for field in ("key", "tempo_bpm", "tuning", "vibe"):
            if not getattr(keep, field) and getattr(source, field):
                setattr(keep, field, getattr(source, field))

        # Delete the source song
        db.delete(source)
        deleted_songs.append({"id": merge_id, "title": source.title})

    db.commit()

    return {
        "ok": True,
        "kept": {"id": keep.id, "title": keep.title},
        "merged_audio": merged_audio,
        "merged_takes": merged_takes,
        "deleted_songs": deleted_songs,
    }
