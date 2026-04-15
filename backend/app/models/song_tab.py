from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SongTab(Base):
    """Guitar Pro tab attached to a song. One song can have many tabs
    (rhythm/solo/bass, different versions, different instruments)."""
    __tablename__ = "song_tabs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    song_id: Mapped[int] = mapped_column(ForeignKey("songs.id"), nullable=False)
    label: Mapped[str | None] = mapped_column(String, nullable=True)  # e.g. "rhythm", "solo", "v2"
    instrument: Mapped[str | None] = mapped_column(String, nullable=True)  # guitar, bass, vocals, drums
    file_path: Mapped[str] = mapped_column(String, nullable=False)  # relative to music_dir
    file_format: Mapped[str | None] = mapped_column(String, nullable=True)  # gp, gp5, gpx, gp3, gp4
    original_filename: Mapped[str | None] = mapped_column(String, nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    song = relationship("Song", foreign_keys=[song_id])
