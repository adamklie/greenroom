"""FastAPI dependency helpers for auth + role gating.

Four public deps:
    current_user(request, db) -> User | None
        Reads the session cookie, decodes the JWT, loads the user. Returns
        None on any failure. Does NOT raise. Use this when you want to know
        who's signed in but don't want to gate the endpoint.

    require_viewer / require_editor / require_admin
        Use as FastAPI Depends() on a route to require at least that role.
        Raises 401 if there's no session, 403 if the session has a role
        below the requirement.

Dev bypass:
    When settings.auth_required is False (default), all three require_* deps
    return a synthetic admin User (id=0, email='dev@local', role='admin').
    This preserves the existing ./dev.sh workflow — no login needed in dev.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app import scoping
from app.auth.jwt import decode_token
from app.config import settings
from app.database import get_db
from app.models import ProjectMember, User

# Header the frontend sends to name the active project (Phase 3b). It also
# mirrors the value into a same-named cookie so native browser requests
# (<audio src>, downloads, the AlphaTab fetch) — which can't set custom headers
# — are still scoped; the gate falls back to the cookie when the header is
# absent. The cookie only *narrows* scope: membership is still verified, so a
# forged value can't reach a project the user doesn't belong to.
PROJECT_HEADER = "X-Greenroom-Project"
PROJECT_COOKIE = "greenroom_project"

# Avoid an `from app.auth.router import COOKIE_NAME` cycle (router imports
# from this module too). Keep the cookie name canonical here and re-use it
# from router via a single import.
COOKIE_NAME = "greenroom_session"

# Role priority — higher number means more access.
_ROLE_RANK = {"viewer": 1, "editor": 2, "admin": 3}


def _synthetic_admin() -> User:
    """Return a non-persisted User object representing the dev-bypass admin.

    id=0 is a sentinel — no real user can have id 0 because SQLite primary
    keys start at 1.
    """
    u = User()
    u.id = 0
    u.email = "dev@local"
    u.role = "admin"
    return u


def _read_cookie_user(request: Request, db: Session) -> User | None:
    """Decode the session cookie into a User row. Returns None on any failure.

    Shared by current_user and the require_* deps so cookie parsing lives in
    one place.
    """
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    payload = decode_token(token)
    if payload is None:
        return None
    user_id = payload.get("user_id")
    if user_id is None:
        return None
    return db.query(User).filter(User.id == user_id).first()


def current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User | None:
    """Look up the signed-in user from the session cookie. Never raises.

    In bypass mode (auth_required=False) returns the synthetic admin so any
    code path that calls this gets a stable shape.
    """
    if not settings.auth_required:
        return _synthetic_admin()
    return _read_cookie_user(request, db)


def _require_role(min_role: str):
    """Build a Depends() callable that requires at least `min_role`.

    Factored out so the three public deps share one implementation. Returned
    callable raises 401 if there's no session, 403 if role is insufficient.
    """
    required = _ROLE_RANK[min_role]

    def dep(
        request: Request,
        db: Session = Depends(get_db),
    ) -> User:
        if not settings.auth_required:
            return _synthetic_admin()

        user = _read_cookie_user(request, db)
        if user is None:
            raise HTTPException(status_code=401, detail="Not authenticated")
        if _ROLE_RANK.get(user.role, 0) < required:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return user

    return dep


require_viewer = _require_role("viewer")
require_editor = _require_role("editor")
require_admin = _require_role("admin")


# Per-project role priority. owner outranks editor outranks viewer. (The global
# _ROLE_RANK above is a different ladder — viewer/editor/admin — used when the
# multi_project flag is off or for the global admin bypass.)
_PROJECT_RANK = {"viewer": 1, "editor": 2, "owner": 3}


def _active_project_id(request: Request) -> int:
    """Resolve the active project from the X-Greenroom-Project header, falling
    back to the greenroom_project cookie (for native requests that can't set the
    header). Raises 400 if neither is present or the value isn't an integer.
    Existence/membership is checked by the caller."""
    raw = request.headers.get(PROJECT_HEADER) or request.cookies.get(PROJECT_COOKIE)
    if not raw:
        raise HTTPException(status_code=400, detail=f"Missing {PROJECT_HEADER} header")
    try:
        return int(raw)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid {PROJECT_HEADER} header")


def require_project_role(min_role: str):
    """Project-scoped role gate — the v2 replacement for require_viewer/editor on
    data routes. As a side effect it sets the request's read scope (the
    do_orm_execute filter in database.py) so reads see only the active project.

    Behavior matrix (resolved in this order):
      - dev bypass (auth_required=False): synthetic admin, UNSCOPED (project
        isolation is a documented no-op in dev).
      - flag off (multi_project=False): gate on the global User.role exactly like
        the old require_* deps; no scope set → V1 behavior.
      - flag on, global admin: allowed and UNSCOPED (admin sees every project).
      - flag on, non-admin: require the X-Greenroom-Project header, a
        project_members row in that project, and a per-project role >= min_role;
        scope the request to {project_id} and reset on teardown.

    Implemented as an ASYNC generator dependency on purpose: an async dep runs
    in the request's event-loop context, so the contextvar it sets propagates to
    the sync endpoint (Starlette copies the context into the threadpool worker)
    and the teardown reset runs in the same context. A *sync* yield-dep would set
    and reset the var in two different threadpool contexts — the scope wouldn't
    reach the endpoint and reset() would raise.
    """
    project_required = _PROJECT_RANK[min_role]
    global_required = _ROLE_RANK[min_role]

    async def dep(request: Request, db: Session = Depends(get_db)):
        if not settings.auth_required:
            yield _synthetic_admin()
            return

        user = _read_cookie_user(request, db)
        if user is None:
            raise HTTPException(status_code=401, detail="Not authenticated")

        if not settings.multi_project:
            if _ROLE_RANK.get(user.role, 0) < global_required:
                raise HTTPException(status_code=403, detail="Insufficient role")
            yield user
            return

        if user.role == "admin":
            yield user  # unscoped: a global admin sees every project
            return

        project_id = _active_project_id(request)
        member = (
            db.query(ProjectMember)
            .filter_by(project_id=project_id, user_id=user.id)
            .first()
        )
        if member is None:
            raise HTTPException(status_code=403, detail="Not a member of this project")
        if _PROJECT_RANK.get(member.role, 0) < project_required:
            raise HTTPException(status_code=403, detail="Insufficient project role")

        token = scoping.set_scope({project_id})
        try:
            yield user
        finally:
            scoping.reset_scope(token)

    return dep


# Module-level singletons for the data routes (mirror require_viewer/editor).
project_viewer = require_project_role("viewer")
project_editor = require_project_role("editor")
