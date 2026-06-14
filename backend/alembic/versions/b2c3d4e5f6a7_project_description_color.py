"""add description + color to projects

v2 — project metadata for the Settings editor. Additive, nullable, idempotent.

Revision ID: b2c3d4e5f6a7
Revises: f1a2b3c4d5e6
Create Date: 2026-06-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("projects")}
    to_add = [name for name in ("description", "color") if name not in cols]
    if to_add:
        with op.batch_alter_table("projects") as batch:
            for name in to_add:
                batch.add_column(sa.Column(name, sa.String(), nullable=True))


def downgrade() -> None:
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("projects")}
    to_drop = [name for name in ("color", "description") if name in cols]
    if to_drop:
        with op.batch_alter_table("projects") as batch:
            for name in to_drop:
                batch.drop_column(name)
