"""Configurable options for dropdowns (sources, roles, projects, statuses, etc.)."""

from sqlalchemy import Integer, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Option(Base):
    __tablename__ = "options"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category: Mapped[str] = mapped_column(String, nullable=False)  # source, role, project, status, tuning
    value: Mapped[str] = mapped_column(String, nullable=False)
    label: Mapped[str | None] = mapped_column(String, nullable=True)  # human-readable, defaults to value
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)  # seeded options


# Seed data
DEFAULT_OPTIONS = [
    # Sources
    {"category": "source", "value": "phone", "label": "Phone Recording"},
    {"category": "source", "value": "logic_pro", "label": "Logic Pro"},
    {"category": "source", "value": "garageband", "label": "GarageBand"},
    {"category": "source", "value": "suno_ai", "label": "Suno AI"},
    {"category": "source", "value": "gopro", "label": "GoPro"},
    {"category": "source", "value": "collaborator", "label": "Collaborator"},
    {"category": "source", "value": "download", "label": "Download"},
    {"category": "source", "value": "unknown", "label": "Unknown"},
    # Roles
    {"category": "role", "value": "recording", "label": "Recording"},
    {"category": "role", "value": "demo", "label": "Demo"},
    {"category": "role", "value": "reference", "label": "Reference (Original)"},
    {"category": "role", "value": "backing_track", "label": "Backing Track"},
    {"category": "role", "value": "final_mix", "label": "Final Mix"},
    {"category": "role", "value": "stem", "label": "Stem"},
    # Projects
    {"category": "project", "value": "solo", "label": "Solo"},
    {"category": "project", "value": "ozone_destructors", "label": "Ozone Destructors"},
    {"category": "project", "value": "sural", "label": "Sural"},
    {"category": "project", "value": "joe", "label": "Joe"},
    # Tunings
    {"category": "tuning", "value": "standard", "label": "Standard"},
    {"category": "tuning", "value": "drop_d", "label": "Drop D"},
    {"category": "tuning", "value": "open_g", "label": "Open G"},
    {"category": "tuning", "value": "open_d", "label": "Open D"},
    {"category": "tuning", "value": "half_step_down", "label": "Half Step Down"},
    {"category": "tuning", "value": "dadgad", "label": "DADGAD"},
]
