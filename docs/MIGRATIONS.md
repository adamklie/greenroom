# Database Migrations

Last updated: 2026-05-23

How Greenroom evolves the SQLite schema with [Alembic](https://alembic.sqlalchemy.org/).

## What Alembic does here

Before this was wired up, the FastAPI startup called `Base.metadata.create_all` — fine for a fresh DB but unable to alter an existing one (add a column, rename a table, change a constraint). Alembic stores ordered migration scripts in `backend/alembic/versions/` and tracks which ones have been applied via the `alembic_version` table inside the DB.

Configuration lives in `backend/alembic.ini` + `backend/alembic/env.py`. The DB URL is sourced from `app.config.settings.database_url`, so the live app and migrations always agree on which file to touch.

## One-time setup on an existing machine

If you have a `greenroom.db` that pre-dates this branch (built by the old `Base.metadata.create_all`), stamp it as already-at-baseline so the first startup is a no-op:

```bash
cd ~/code/greenroom/backend
python scripts/stamp_baseline.py
```

This inserts the baseline revision into `alembic_version` without running any DDL — every row is preserved. **Skip this step on a brand-new DB**; the first `alembic upgrade head` on startup will create every table cleanly.

## Adding a new migration

When you change a model (new column, new table, renamed field, new index):

1. Edit the model under `backend/app/models/`.
2. Generate a migration:
   ```bash
   cd ~/code/greenroom/backend
   alembic revision --autogenerate -m "<short subject>"
   ```
3. **Inspect** the generated file in `alembic/versions/`. Autogenerate is good at adds/drops but cannot tell a rename from a drop-and-add, and may miss server-side defaults or check constraints. Edit by hand if needed.
4. Apply it. Startup will do this automatically next time the backend boots, or run manually:
   ```bash
   alembic upgrade head
   ```
5. Commit both the model change and the migration in the same PR.

## Applying migrations

Three triggers:

| Trigger | When | Command |
|---|---|---|
| **Automatic** | Every backend startup | `command.upgrade(cfg, "head")` in `app/main.py` lifespan |
| **Manual** | After pulling a branch with new migrations, before booting | `cd backend && alembic upgrade head` |
| **Stamp** | First time on a pre-Alembic DB | `cd backend && python scripts/stamp_baseline.py` |

Useful inspection commands:

```bash
alembic current   # what revision is the DB at
alembic history   # ordered list of migrations
alembic show <revision>   # print a specific migration
```

## Common pitfalls

- **Autogenerate doesn't catch column renames.** It sees `old_col` dropped + `new_col` added. Inspect the diff; replace with `op.alter_column(..., new_column_name=...)`.
- **SQLite ALTER TABLE limitations.** `env.py` enables `render_as_batch=True`, which makes Alembic emit copy-rebuild-rename instead of `ALTER COLUMN`. Most cases work transparently; complex multi-constraint changes may still need manual scripting.
- **Server-side defaults.** If a model sets `server_default=text("...")`, double-check the generated migration carries it; sometimes autogenerate omits defaults on existing-column changes.
- **Don't edit a migration after it has been applied to any DB.** Add a new follow-up migration instead. The applied revision is recorded in `alembic_version`; editing in-place desyncs every existing DB.
- **Backups before structural changes.** A backup is automatically scheduled on commit (see [STORAGE.md](STORAGE.md)). For a hand-edited migration, also trigger a manual backup via the Sync page before running `alembic upgrade head`.

## Recovery

Migration broke the live DB? The rolling backups in `vault/backups/` (last 10) are the recovery path:

```bash
cp ~/Library/Mobile\ Documents/com~apple~CloudDocs/greenroom/backups/greenroom_<latest>.db \
   ~/code/greenroom/greenroom.db
```

Then either fix the migration and re-run `alembic upgrade head`, or revert the branch and re-stamp.
