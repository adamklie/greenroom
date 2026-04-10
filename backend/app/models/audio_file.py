from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AudioFile(Base):
    __tablename__ = "audio_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    song_id: Mapped[int | None] = mapped_column(ForeignKey("songs.id"), nullable=True)
    file_path: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    file_type: Mapped[str | None] = mapped_column(String, nullable=True)

    # Source taxonomy
    source: Mapped[str | None] = mapped_column(String, nullable=True)
    role: Mapped[str] = mapped_column(String, nullable=False, default="recording")
    version: Mapped[str | None] = mapped_column(String, nullable=True)
    is_stem: Mapped[bool] = mapped_column(Integer, nullable=False, default=False)

    # Ratings (same 7 dimensions as takes — per individual track)
    rating_overall: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating_vocals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating_guitar: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating_drums: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating_tone: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating_timing: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating_energy: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    song: Mapped["Song | None"] = relationship(  # noqa: F821
        back_populates="audio_files", foreign_keys=[song_id]
    )
