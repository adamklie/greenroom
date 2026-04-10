from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AudioFile(Base):
    """The fundamental unit — a single audio or video recording.

    This table holds ALL audio: solo recordings, practice session clips,
    Sural collabs, Suno AI, references, demos, everything. Practice session
    clips have session_id + timestamps filled in; other recordings don't.
    """
    __tablename__ = "audio_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    song_id: Mapped[int | None] = mapped_column(ForeignKey("songs.id"), nullable=True)
    file_path: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    file_type: Mapped[str | None] = mapped_column(String, nullable=True)

    # Source & role
    source: Mapped[str | None] = mapped_column(String, nullable=True)
    role: Mapped[str | None] = mapped_column(String, nullable=True, default="recording")
    version: Mapped[str | None] = mapped_column(String, nullable=True)
    is_stem: Mapped[bool] = mapped_column(Integer, nullable=False, default=False)

    # Practice session context (null for non-session recordings)
    session_id: Mapped[int | None] = mapped_column(
        ForeignKey("practice_sessions.id"), nullable=True
    )
    clip_name: Mapped[str | None] = mapped_column(String, nullable=True)
    source_video: Mapped[str | None] = mapped_column(String, nullable=True)
    start_time: Mapped[str | None] = mapped_column(String, nullable=True)
    end_time: Mapped[str | None] = mapped_column(String, nullable=True)
    video_path: Mapped[str | None] = mapped_column(String, nullable=True)

    # Ratings (7 dimensions, all 1-5)
    rating_overall: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating_vocals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating_guitar: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating_drums: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating_tone: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating_timing: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating_energy: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # when imported into Greenroom
    recorded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # when the recording was made

    song: Mapped["Song | None"] = relationship(  # noqa: F821
        back_populates="audio_files", foreign_keys=[song_id]
    )
    session: Mapped["PracticeSession | None"] = relationship(  # noqa: F821
        foreign_keys=[session_id]
    )
    # TODO: add audio_file_tags junction table for tags on audio files
