"""Request-scoped project access control (v2 Phase 3b).

A contextvar holds the set of project_ids the current request is allowed to
touch — or None for "unscoped" (admin, background/system work, and the dev
auth-bypass). The ``do_orm_execute`` listener in ``database.py`` reads this and
restricts every query against the scoped content models to that set.

Everything here is inert unless ``settings.multi_project`` is True, so with the
flag off the app behaves exactly like V1.

The scope is set per-request by the auth dependency (Phase 3b) after it has
validated the caller's membership in the active project — so a request can only
ever be scoped to projects the user actually belongs to. Code that runs outside
a request (migrations, backfills, the auto-backup thread) never sets a scope and
is therefore unscoped, which is correct for system-level work.
"""

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterable

# None  => unscoped: see everything (admin / system / dev-bypass).
# frozenset => restrict reads to exactly these project_ids.
_scope: ContextVar["frozenset[int] | None"] = ContextVar("project_scope", default=None)


def set_scope(project_ids: Iterable[int] | None):
    """Set the active scope; returns a token to pass to reset_scope()."""
    return _scope.set(frozenset(project_ids) if project_ids is not None else None)


def reset_scope(token) -> None:
    _scope.reset(token)


def get_scope() -> "frozenset[int] | None":
    return _scope.get()


@contextmanager
def scoped(project_ids: Iterable[int] | None):
    """Temporarily apply a scope (handy in tests and scripts)."""
    token = set_scope(project_ids)
    try:
        yield
    finally:
        reset_scope(token)
