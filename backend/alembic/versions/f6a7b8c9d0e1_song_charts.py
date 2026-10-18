"""add song_charts (uploaded chart PDFs / images per song)

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-10-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if "song_charts" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "song_charts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("song_id", sa.Integer(), sa.ForeignKey("songs.id"), nullable=False),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("identifier", sa.String(), nullable=False, unique=True),
        sa.Column("file_type", sa.String(), nullable=False),
        sa.Column("original_filename", sa.String(), nullable=True),
        sa.Column("label", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_song_charts_song_id", "song_charts", ["song_id"])
    op.create_index("ix_song_charts_project_id", "song_charts", ["project_id"])


def downgrade() -> None:
    if "song_charts" in sa.inspect(op.get_bind()).get_table_names():
        op.drop_index("ix_song_charts_project_id", table_name="song_charts")
        op.drop_index("ix_song_charts_song_id", table_name="song_charts")
        op.drop_table("song_charts")
