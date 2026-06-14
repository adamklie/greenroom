"""add position to projects (custom switcher order)

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-06-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("projects")}
    if "position" not in cols:
        with op.batch_alter_table("projects") as batch:
            batch.add_column(sa.Column("position", sa.Integer(), nullable=True))


def downgrade() -> None:
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("projects")}
    if "position" in cols:
        with op.batch_alter_table("projects") as batch:
            batch.drop_column("position")
