from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class AudioFileRead(BaseModel):
    id: int
    song_id: int | None = None
    file_path: str
    file_type: str | None = None
    identifier: str | None = None
    submitted_file_name: str | None = None
    source: str | None = None
    role: str | None = None
    version: str | None = None
    # Session context (for practice clips)
    session_id: int | None = None
    clip_name: str | None = None
    source_file: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    video_path: str | None = None
    # Ratings
    rating_overall: float | None = None
    rating_vocals: float | None = None
    rating_guitar: float | None = None
    rating_drums: float | None = None
    rating_tone: float | None = None
    rating_timing: float | None = None
    rating_energy: float | None = None
    rating_keys: float | None = None
    rating_bass: float | None = None
    rating_mix: float | None = None
    rating_other: float | None = None
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
    # Computed
    file_exists: bool | None = None

    model_config = {"from_attributes": True}


class AudioFileUpdate(BaseModel):
    song_id: int | None = None
    session_id: int | None = None
    source: str | None = None
    role: str | None = None
    version: str | None = None
    clip_name: str | None = None
    rating_overall: float | None = None
    rating_vocals: float | None = None
    rating_guitar: float | None = None
    rating_drums: float | None = None
    rating_tone: float | None = None
    rating_timing: float | None = None
    rating_energy: float | None = None
    rating_keys: float | None = None
    rating_bass: float | None = None
    rating_mix: float | None = None
    rating_other: float | None = None
    notes: str | None = None
    uploaded_at: datetime | None = None
    recorded_at: datetime | None = None
