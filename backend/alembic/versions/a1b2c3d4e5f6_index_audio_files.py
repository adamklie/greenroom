"""add indexes on audio_files filter/sort columns

Speeds up the library list query (filter by song_id/source/role, sort by
created_at). Idempotent: some deployments already have a subset of these
indexes (e.g. song_id), so we inspect first and only create what's missing.

Revision ID: a1b2c3d4e5f6
Revises: 0da88e30addd
Create Date: 2026-05-31

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "0da88e30addd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_INDEXES = {
    "ix_audio_files_song_id": "song_id",
    "ix_audio_files_source": "source",
    "ix_audio_files_role": "role",
    "ix_audio_files_created_at": "created_at",
}


def upgrade() -> None:
    existing = {ix["name"] for ix in sa.inspect(op.get_bind()).get_indexes("audio_files")}
    for name, column in _INDEXES.items():
        if name not in existing:
            op.create_index(name, "audio_files", [column])


def downgrade() -> None:
    existing = {ix["name"] for ix in sa.inspect(op.get_bind()).get_indexes("audio_files")}
    for name in _INDEXES:
        if name in existing:
            op.drop_index(name, table_name="audio_files")
