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

from app.auth.jwt import decode_token
from app.config import settings
from app.database import get_db
from app.models import User

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
