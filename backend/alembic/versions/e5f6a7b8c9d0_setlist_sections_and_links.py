"""add songs.links, setlist_items.section and setlist_items.links

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-10-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ADDS = {
    "songs": [("links", sa.JSON())],
    "setlist_items": [("section", sa.String()), ("links", sa.JSON())],
}


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    for table, columns in _ADDS.items():
        existing = {c["name"] for c in insp.get_columns(table)}
        missing = [(n, t) for n, t in columns if n not in existing]
        if missing:
            with op.batch_alter_table(table) as batch:
                for name, type_ in missing:
                    batch.add_column(sa.Column(name, type_, nullable=True))


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())
    for table, columns in _ADDS.items():
        existing = {c["name"] for c in insp.get_columns(table)}
        present = [n for n, _ in columns if n in existing]
        if present:
            with op.batch_alter_table(table) as batch:
                for name in present:
                    batch.drop_column(name)
