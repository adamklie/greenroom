from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class SongBase(BaseModel):
    title: str
    artist: str | None = None
    type: str = "cover"
    project: str = "solo"
    status: str = "idea"
    key: str | None = None
    tempo_bpm: int | None = None
    tuning: str | None = "standard"
    vibe: str | None = None
    lyrics: str | None = None
    notes: str | None = None


class SongCreate(SongBase):
    pass


class SongRead(SongBase):
    id: int
    times_practiced: int = 0
    reference_audio_file_id: int | None = None
    promoted_from_id: int | None = None
    rating_overall: int | None = None
    rating_vocals: int | None = None
    rating_guitar: int | None = None
    rating_drums: int | None = None
    rating_tone: int | None = None
    rating_timing: int | None = None
    rating_energy: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    has_audio: bool = False
    take_count: int = 0
    tags: list[str] = []

    model_config = {"from_attributes": True}


class SongUpdate(BaseModel):
    title: str | None = None
    artist: str | None = None
    type: str | None = None
    status: str | None = None
    project: str | None = None
    key: str | None = None
    tempo_bpm: int | None = None
    tuning: str | None = None
    vibe: str | None = None
    lyrics: str | None = None
    notes: str | None = None
    reference_audio_file_id: int | None = None
    rating_overall: int | None = None
    rating_vocals: int | None = None
    rating_guitar: int | None = None
    rating_drums: int | None = None
    rating_tone: int | None = None
    rating_timing: int | None = None
    rating_energy: int | None = None


class SongDetail(SongRead):
    takes: list[TakeRead] = []
    audio_files: list[AudioFileRead] = []
    lyrics_versions: list[LyricsVersionRead] = []


# Avoid circular imports
from app.schemas.take import TakeRead  # noqa: E402
from app.schemas.audio_file import AudioFileRead  # noqa: E402
from app.schemas.lyrics_version import LyricsVersionRead  # noqa: E402

SongDetail.model_rebuild()
