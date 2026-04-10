from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class AudioFileRead(BaseModel):
    id: int
    song_id: int | None = None
    file_path: str
    file_type: str | None = None
    source: str | None = None
    role: str | None = None
    version: str | None = None
    # Session context (for practice clips)
    session_id: int | None = None
    clip_name: str | None = None
    source_video: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    video_path: str | None = None
    # Ratings
    rating_overall: int | None = None
    rating_vocals: int | None = None
    rating_guitar: int | None = None
    rating_drums: int | None = None
    rating_tone: int | None = None
    rating_timing: int | None = None
    rating_energy: int | None = None
    notes: str | None = None
    created_at: datetime | None = None
    uploaded_at: datetime | None = None
    recorded_at: datetime | None = None
    # Joined from Song
    song_title: str | None = None
    song_artist: str | None = None
    song_type: str | None = None
    # Joined from Session
    session_date: str | None = None

    model_config = {"from_attributes": True}


class AudioFileUpdate(BaseModel):
    song_id: int | None = None
    source: str | None = None
    role: str | None = None
    version: str | None = None
    clip_name: str | None = None
    rating_overall: int | None = None
    rating_vocals: int | None = None
    rating_guitar: int | None = None
    rating_drums: int | None = None
    rating_tone: int | None = None
    rating_timing: int | None = None
    rating_energy: int | None = None
    notes: str | None = None
    uploaded_at: datetime | None = None
    recorded_at: datetime | None = None
