from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class TakeRead(BaseModel):
    id: int
    session_id: int
    song_id: int | None = None
    clip_name: str
    source_video: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    video_path: str | None = None
    audio_path: str | None = None
    rating: int | None = None
    notes: str | None = None
    created_at: datetime | None = None
    song_title: str | None = None
    session_date: str | None = None

    model_config = {"from_attributes": True}


class TakeUpdate(BaseModel):
    rating: int | None = None
    notes: str | None = None
