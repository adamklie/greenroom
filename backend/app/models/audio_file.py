from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AudioFile(Base):
    __tablename__ = "audio_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    song_id: Mapped[int | None] = mapped_column(ForeignKey("songs.id"), nullable=True)
    file_path: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    file_type: Mapped[str | None] = mapped_column(String, nullable=True)

    # Expanded source taxonomy
    source: Mapped[str | None] = mapped_column(String, nullable=True)
    # gopro, phone, logic_pro, garageband, suno_ai, backing_track,
    # collaborator, download, apple_notes, unknown

    # What role does this file play?
    role: Mapped[str] = mapped_column(String, nullable=False, default="recording")
    # recording, reference, backing_track, stem, demo, final_mix

    version: Mapped[str | None] = mapped_column(String, nullable=True)
    is_stem: Mapped[bool] = mapped_column(Integer, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    song: Mapped["Song | None"] = relationship(  # noqa: F821
        back_populates="audio_files", foreign_keys=[song_id]
    )
