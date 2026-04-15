"""Listening history + Apple Music dump models."""

from datetime import datetime

from sqlalchemy import (
    BigInteger, Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ListeningHistory(Base):
    """One row per unique Apple Music track, aggregated across all plays."""
    __tablename__ = "listening_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    apple_track_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    artist: Mapped[str] = mapped_column(String, nullable=False, default="")
    album: Mapped[str | None] = mapped_column(String, nullable=True)
    genre: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    media_type: Mapped[str | None] = mapped_column(String, nullable=True)

    play_count: Mapped[int] = mapped_column(Integer, default=0)
    total_play_ms: Mapped[int] = mapped_column(BigInteger, default=0)
    first_played_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_played_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)

    is_own_recording: Mapped[bool] = mapped_column(Boolean, default=False)
    linked_song_id: Mapped[int | None] = mapped_column(ForeignKey("songs.id"), nullable=True)

    imported_at: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("apple_track_id", name="uq_listening_apple_track"),
    )


class ListeningPlay(Base):
    """Individual play event from the Apple Music Play Activity CSV."""
    __tablename__ = "listening_plays"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    listening_history_id: Mapped[int] = mapped_column(
        ForeignKey("listening_history.id"), nullable=False, index=True
    )
    event_id: Mapped[str | None] = mapped_column(String, nullable=True, unique=True, index=True)
    event_timestamp: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)

    play_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    event_type: Mapped[str | None] = mapped_column(String, nullable=True)

    container_type: Mapped[str | None] = mapped_column(String, nullable=True)
    container_name: Mapped[str | None] = mapped_column(String, nullable=True)

    device_type: Mapped[str | None] = mapped_column(String, nullable=True)
    country: Mapped[str | None] = mapped_column(String, nullable=True)

    source: Mapped[str] = mapped_column(String, default="apple_music")


class ApplePlaylist(Base):
    """Apple Music playlist metadata (potential setlist source)."""
    __tablename__ = "apple_playlists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    apple_playlist_id: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    is_collaborative: Mapped[bool] = mapped_column(Boolean, default=False)
    track_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    linked_setlist_id: Mapped[int | None] = mapped_column(ForeignKey("setlists.id"), nullable=True)
    imported_at: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.utcnow)


class ApplePlaylistTrack(Base):
    """Tracks within an Apple Music playlist (ordered)."""
    __tablename__ = "apple_playlist_tracks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    playlist_id: Mapped[int] = mapped_column(
        ForeignKey("apple_playlists.id"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    apple_track_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    artist: Mapped[str | None] = mapped_column(String, nullable=True)
    album: Mapped[str | None] = mapped_column(String, nullable=True)
