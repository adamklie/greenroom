from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class SetlistItemCreate(BaseModel):
    song_id: int
    position: int
    duration_minutes: int = 4
    notes: str | None = None


class SetlistItemRead(BaseModel):
    id: int
    song_id: int
    position: int
    duration_minutes: int
    notes: str | None = None
    song_title: str | None = None
    song_artist: str | None = None
    song_status: str | None = None

    model_config = {"from_attributes": True}


class SetlistCreate(BaseModel):
    name: str
    description: str | None = None
    config: str = "full_band"
    items: list[SetlistItemCreate] = []


class SetlistRead(BaseModel):
    id: int
    name: str
    description: str | None = None
    config: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    items: list[SetlistItemRead] = []
    total_minutes: int = 0
    song_count: int = 0

    model_config = {"from_attributes": True}


class SetlistUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    config: str | None = None
    items: list[SetlistItemCreate] | None = None
