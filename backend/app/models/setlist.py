from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Setlist(Base):
    __tablename__ = "setlists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    config: Mapped[str] = mapped_column(String, default="full_band")  # solo, duo, full_band
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    items: Mapped[list["SetlistItem"]] = relationship(
        back_populates="setlist", cascade="all, delete-orphan", order_by="SetlistItem.position"
    )


class SetlistItem(Base):
    __tablename__ = "setlist_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    setlist_id: Mapped[int] = mapped_column(ForeignKey("setlists.id"))
    song_id: Mapped[int] = mapped_column(ForeignKey("songs.id"))
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=4)  # estimated
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    setlist: Mapped["Setlist"] = relationship(back_populates="items")
    song: Mapped["Song"] = relationship()  # noqa: F821
