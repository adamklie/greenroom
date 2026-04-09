from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class LyricsVersionRead(BaseModel):
    id: int
    song_id: int
    version_number: int
    lyrics_text: str
    change_note: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class LyricsUpdate(BaseModel):
    lyrics: str
    change_note: str | None = None
