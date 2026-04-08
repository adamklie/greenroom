from __future__ import annotations

from pydantic import BaseModel

from app.schemas.roadmap import RoadmapPhase


class DashboardStats(BaseModel):
    total_songs: int
    total_sessions: int
    total_takes: int
    total_audio_files: int
    songs_by_status: dict[str, int]
    songs_by_project: dict[str, int]
    gig_ready_songs: int
    unrated_takes: int


class DashboardResponse(BaseModel):
    stats: DashboardStats
    roadmap: list[RoadmapPhase]
