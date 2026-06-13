"""Multi-project models (v2).

A Project groups a user's songs, sessions, setlists, and recordings.
ProjectMember grants a user access to a project with a role
('owner' | 'editor' | 'viewer'). Ownership is just a `role='owner'` membership
row — there is no separate `owner_id` on the project, so there's a single
source of truth for who can do what.

Phase 3a adds these tables plus a nullable `project_id` on the content tables,
backfilled from the legacy `project` string. Query scoping (restricting every
read/write to the caller's accessible projects) lands in Phase 3b, behind the
GREENROOM_MULTI_PROJECT flag — so until that flips, these columns are inert and
the app behaves exactly like V1.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Intentionally NOT globally unique: in the multi-tenant model two different
    # users may each have a project named e.g. "Solo". Per-owner name uniqueness
    # is enforced in the app layer when project creation lands (Phase 3b), not as
    # a DB constraint. The Phase 3a backfill stays dup-free via get-or-create.
    name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class ProjectMember(Base):
    __tablename__ = "project_members"
    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uq_project_members_project_user"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    # One of 'owner', 'editor', 'viewer'. Enforced in app code (Phase 3b),
    # not as a DB CHECK constraint — keeps SQLite migrations simple.
    role: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
