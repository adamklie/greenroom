from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class TriageItemRead(BaseModel):
    id: int
    file_path: str
    file_type: str | None = None
    discovered_at: datetime | None = None
    suggested_song_id: int | None = None
    suggested_type: str | None = None
    suggested_source: str | None = None
    status: str = "pending"

    model_config = {"from_attributes": True}


class TriageClassify(BaseModel):
    song_id: int | None = None
    create_song_title: str | None = None  # If song_id is None, create a new song
    song_type: str = "cover"
    source: str = "unknown"
    role: str = "recording"
