"""Debounced auto-backup of the live DB into the vault.

Every SQLAlchemy session commit schedules a backup for 30s in the future,
canceling any previously-pending backup. A burst of writes (e.g. saving
ratings on ten takes in a row) produces one backup, 30s after the last
write lands.

The listener is installed in database.py on module import.
"""

from __future__ import annotations

import logging
import threading

from app.services.backup import backup_database

log = logging.getLogger(__name__)

DEBOUNCE_SECONDS = 30.0

_timer: threading.Timer | None = None
_lock = threading.Lock()


def schedule_backup(delay: float = DEBOUNCE_SECONDS) -> None:
    """Schedule a DB backup, canceling any pending one."""
    global _timer
    with _lock:
        if _timer is not None:
            _timer.cancel()
        _timer = threading.Timer(delay, _run_backup)
        _timer.daemon = True
        _timer.start()


def _run_backup() -> None:
    try:
        path = backup_database()
        log.info("auto_backup: wrote %s", path)
    except Exception:  # noqa: BLE001 — background thread, don't crash app
        log.exception("auto_backup: failed")
