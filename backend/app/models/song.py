from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Song(Base):
    __tablename__ = "songs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    artist: Mapped[str | None] = mapped_column(String, nullable=True)

    # Three pillars: cover, original, idea (all optional)
    type: Mapped[str | None] = mapped_column(String, nullable=True)

    # Status progression (optional)
    status: Mapped[str | None] = mapped_column(String, nullable=True)

    # Project / band context (optional)
    project: Mapped[str | None] = mapped_column(String, nullable=True)

    # Structured music fields
    key: Mapped[str | None] = mapped_column(String, nullable=True)
    tempo_bpm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tuning: Mapped[str | None] = mapped_column(String, nullable=True, default="standard")
    vibe: Mapped[str | None] = mapped_column(String, nullable=True)

    # Lyrics (current version)
    lyrics: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Reference recording for covers
    reference_audio_file_id: Mapped[int | None] = mapped_column(
        ForeignKey("audio_files.id", use_alter=True), nullable=True
    )

    # If an idea was promoted to an original
    promoted_from_id: Mapped[int | None] = mapped_column(
        ForeignKey("songs.id"), nullable=True
    )

    # Song-level ratings (overall impression of the song, not a specific recording)
    rating_overall: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating_vocals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating_guitar: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating_drums: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating_tone: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating_timing: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating_energy: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Legacy / carry-forward
    is_original: Mapped[bool] = mapped_column(Boolean, default=False)
    times_practiced: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    takes: Mapped[list["Take"]] = relationship(back_populates="song")  # noqa: F821
    audio_files: Mapped[list["AudioFile"]] = relationship(  # noqa: F821
        back_populates="song", foreign_keys="AudioFile.song_id"
    )
    lyrics_versions: Mapped[list["LyricsVersion"]] = relationship(  # noqa: F821
        back_populates="song", cascade="all, delete-orphan"
    )
    tags: Mapped[list["Tag"]] = relationship(  # noqa: F821
        secondary="song_tags", back_populates="songs"
    )
