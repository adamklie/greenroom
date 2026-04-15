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
    unrated_audio_files: int
    triage_pending: int


class RecentSong(BaseModel):
    id: int
    title: str
    artist: str | None
    type: str
    status: str
    created_at: str | None


class RecentAudioFile(BaseModel):
    id: int
    identifier: str | None
    file_path: str
    file_type: str
    song_id: int | None
    song_title: str | None
    session_id: int | None
    session_date: str | None
    created_at: str | None
    uploaded_at: str | None
    recorded_at: str | None


class RecentSession(BaseModel):
    id: int
    date: str
    folder_path: str
    clip_count: int
    created_at: str | None


class DashboardResponse(BaseModel):
    stats: DashboardStats
    recent_songs: list[RecentSong] = []
    recent_audio_files: list[RecentAudioFile] = []
    recent_sessions: list[RecentSession] = []
