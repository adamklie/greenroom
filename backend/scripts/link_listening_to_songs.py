"""Match catalog Songs to ListeningHistory rows so song detail pages can show
'you've played this X times on Apple Music'.

Matching:
  1. exact (title, artist) case-insensitive
  2. title-only if unambiguous in both catalog and listening history

Run:
    python -m scripts.link_listening_to_songs
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Song
from app.models.listening import ListeningHistory


_PAREN_RE = re.compile(r"\s*[\(\[][^()\[\]]*[\)\]]\s*")
_PUNCT_RE = re.compile(r"[^\w\s]")


def _norm(s: str | None) -> str:
    if not s:
        return ""
    s = s.lower()
    s = _PAREN_RE.sub(" ", s)  # drop "(feat. X)", "[Remastered]", etc.
    s = _PUNCT_RE.sub(" ", s)
    return " ".join(s.split())


def link(db: Session) -> dict:
    songs = db.query(Song).all()

    # Index catalog
    by_title_artist: dict[tuple[str, str], list[int]] = defaultdict(list)
    by_title: dict[str, list[int]] = defaultdict(list)
    for s in songs:
        t = _norm(s.title)
        a = _norm(s.artist)
        if t:
            by_title_artist[(t, a)].append(s.id)
            by_title[t].append(s.id)

    # Candidate listening rows (exclude already-linked, own recordings)
    rows = (
        db.query(ListeningHistory)
        .filter(ListeningHistory.linked_song_id.is_(None))
        .filter(ListeningHistory.is_own_recording == False)  # noqa: E712
        .all()
    )

    exact_matches = 0
    title_matches = 0
    ambiguous = 0

    for r in rows:
        t = _norm(r.title)
        a = _norm(r.artist)
        if not t:
            continue

        ids = by_title_artist.get((t, a))
        if ids and len(ids) == 1:
            r.linked_song_id = ids[0]
            exact_matches += 1
            continue

        ids = by_title.get(t)
        if ids and len(ids) == 1:
            r.linked_song_id = ids[0]
            title_matches += 1
        elif ids:
            ambiguous += 1

    db.commit()

    total_linked = (
        db.query(ListeningHistory)
        .filter(ListeningHistory.linked_song_id.isnot(None))
        .count()
    )
    unlinked_songs = [
        s.id for s in songs
        if not db.query(ListeningHistory)
        .filter(ListeningHistory.linked_song_id == s.id).first()
    ]

    return {
        "catalog_songs": len(songs),
        "listening_rows_checked": len(rows),
        "exact_matches_added": exact_matches,
        "title_only_matches_added": title_matches,
        "ambiguous_skipped": ambiguous,
        "total_listening_rows_linked": total_linked,
        "catalog_songs_with_no_link": len(unlinked_songs),
    }


def _cli():
    with SessionLocal() as db:
        result = link(db)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    _cli()
