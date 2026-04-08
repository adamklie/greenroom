from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class ContentPostCreate(BaseModel):
    title: str
    song_id: int | None = None
    take_id: int | None = None
    audio_file_id: int | None = None
    platform: str | None = None
    post_type: str | None = None
    scheduled_date: date | None = None
    status: str = "planned"
    caption: str | None = None
    notes: str | None = None


class ContentPostRead(ContentPostCreate):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None
    song_title: str | None = None

    model_config = {"from_attributes": True}


class ContentPostUpdate(BaseModel):
    title: str | None = None
    song_id: int | None = None
    take_id: int | None = None
    audio_file_id: int | None = None
    platform: str | None = None
    post_type: str | None = None
    scheduled_date: date | None = None
    status: str | None = None
    caption: str | None = None
    notes: str | None = None
