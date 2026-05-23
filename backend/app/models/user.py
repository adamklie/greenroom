"""Auth models — user accounts and single-use magic-link tokens.

The auth model is admin-invite-only: users must be pre-added to the `users`
table (via scripts/create_admin.py or the future admin UI). There is no
self-signup flow. Login is via magic link only; passwords are not supported.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    # One of 'viewer', 'editor', 'admin'. Enforced in app/auth/deps.py rather
    # than as a DB CHECK constraint to keep migrations simple on SQLite.
    role: Mapped[str] = mapped_column(String, nullable=False)
    invited_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class MagicToken(Base):
    __tablename__ = "magic_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    # sha256 hex of the raw urlsafe token that was put in the magic-link URL.
    # The raw token is never stored — only its hash — so a DB leak can't be
    # turned into active sessions.
    token_hash: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
