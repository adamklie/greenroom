"""rename practice_sessions -> sessions; add nullable name

Renames the table to match what the API/UI already call these ("sessions"),
and adds an optional user-provided session title (the UI falls back to the
date when null). The Python model class stays PracticeSession to avoid
colliding with sqlalchemy.orm.Session.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-06-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "practice_sessions" in tables and "sessions" not in tables:
        # legacy_alter_table=OFF makes SQLite rewrite child FK references
        # (audio_files.session_id, takes.session_id) to point at the new name.
        # Alembic leaves it ON, which would dangle them at "practice_sessions".
        bind.exec_driver_sql("PRAGMA legacy_alter_table=OFF")
        bind.exec_driver_sql("ALTER TABLE practice_sessions RENAME TO sessions")

    cols = {c["name"] for c in sa.inspect(bind).get_columns("sessions")}
    if "name" not in cols:
        # Native ADD COLUMN (no table recreate) — safe with the inbound FKs.
        op.add_column("sessions", sa.Column("name", sa.String(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    cols = {c["name"] for c in sa.inspect(bind).get_columns("sessions")}
    if "name" in cols:
        with op.batch_alter_table("sessions") as batch:
            batch.drop_column("name")

    tables = set(sa.inspect(bind).get_table_names())
    if "sessions" in tables and "practice_sessions" not in tables:
        bind.exec_driver_sql("PRAGMA legacy_alter_table=OFF")
        bind.exec_driver_sql("ALTER TABLE sessions RENAME TO practice_sessions")
