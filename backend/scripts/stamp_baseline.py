"""Stamp an existing greenroom.db as already-at-baseline for Alembic.

Run this ONCE per machine after merging the Alembic baseline branch.

Before this branch, the DB schema was created by `Base.metadata.create_all`
on startup. Every table already exists in your live greenroom.db. The first
time the new lifespan runs `alembic upgrade head`, Alembic would try to
re-create those tables (because there's no alembic_version row yet) and
fail with "table already exists".

Stamping inserts the baseline revision into alembic_version without running
any DDL, so the next startup is a no-op upgrade and the live DB keeps every
row intact.

Usage (from the backend/ directory):
    python scripts/stamp_baseline.py

You only need to run this once per DB. New machines, fresh DBs, and the
test fixtures don't need it — they go through `alembic upgrade head` from
empty and create everything cleanly.
"""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config


def main() -> None:
    alembic_ini = Path(__file__).resolve().parent.parent / "alembic.ini"
    cfg = Config(str(alembic_ini))
    command.stamp(cfg, "head")
    print("Stamped existing DB at head. Future `alembic upgrade head` runs are no-ops until you add a new migration.")


if __name__ == "__main__":
    main()
