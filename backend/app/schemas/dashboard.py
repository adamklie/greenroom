from __future__ import annotations

from pydantic import BaseModel


class DashboardStats(BaseModel):
    total_songs: int
    total_sessions: int
    total_takes: int
    total_audio_files: int
    songs_by_type: dict[str, int]
    songs_by_status: dict[str, int]
    songs_by_project: dict[str, int]
    unrated_takes: int
    triage_pending: int


class DashboardResponse(BaseModel):
    stats: DashboardStats
