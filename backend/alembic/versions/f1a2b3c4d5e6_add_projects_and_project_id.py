"""add projects + project_members tables and nullable project_id columns

v2 Phase 3a — additive only. Creates the project tables and adds a nullable
`project_id` (+ index) to each content table. Nothing is backfilled here (see
scripts/backfill_projects.py) and nothing is enforced yet — the columns stay
inert until GREENROOM_MULTI_PROJECT is flipped in Phase 3b.

Idempotent: inspects the live schema and only creates what's missing, so it
tolerates the known baseline/live drift in this repo.

Revision ID: f1a2b3c4d5e6
Revises: a1b2c3d4e5f6
Create Date: 2026-06-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Content tables that gain a nullable project_id + index.
_SCOPED_TABLES = ("audio_files", "songs", "practice_sessions", "setlists", "takes")


def _idx(table: str) -> str:
    return f"ix_{table}_project_id"


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    tables = set(insp.get_table_names())

    if "projects" not in tables:
        op.create_table(
            "projects",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )

    if "project_members" not in tables:
        op.create_table(
            "project_members",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("role", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("project_id", "user_id", name="uq_project_members_project_user"),
        )

    for table in _SCOPED_TABLES:
        cols = {c["name"] for c in insp.get_columns(table)}
        if "project_id" not in cols:
            # Plain nullable column — SQLite ADD COLUMN, no table rebuild. The
            # FK is declared at the ORM level; SQLite doesn't enforce it anyway.
            op.add_column(table, sa.Column("project_id", sa.Integer(), nullable=True))
        existing_idx = {ix["name"] for ix in insp.get_indexes(table)}
        if _idx(table) not in existing_idx:
            op.create_index(_idx(table), table, ["project_id"])


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())

    for table in _SCOPED_TABLES:
        existing_idx = {ix["name"] for ix in insp.get_indexes(table)}
        if _idx(table) in existing_idx:
            op.drop_index(_idx(table), table_name=table)
        cols = {c["name"] for c in insp.get_columns(table)}
        if "project_id" in cols:
            # DROP COLUMN needs batch mode (table rebuild) on SQLite.
            with op.batch_alter_table(table) as batch:
                batch.drop_column("project_id")

    tables = set(insp.get_table_names())
    if "project_members" in tables:
        op.drop_table("project_members")
    if "projects" in tables:
        op.drop_table("projects")
