"""Magic-link auth endpoints.

Flow:
    POST /api/auth/request {email}  → always 200 (don't leak whether the
                                       email is registered). If registered,
                                       creates a 15-minute magic_tokens row
                                       and dispatches the link via the
                                       configured emailer.
    GET  /api/auth/exchange?token=… → validates the raw token (sha256 it,
                                       look up the row, check expiry + that
                                       it hasn't been used), marks it used,
                                       sets the greenroom_session cookie,
                                       redirects to /.
    POST /api/auth/logout           → clears the cookie.
    GET  /api/auth/me               → returns {id, email, role} from the
                                       cookie or 401.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.deps import COOKIE_NAME
from app.auth.email import get_emailer
from app.auth.jwt import encode_token
from app.config import settings
from app.database import get_db
from app.models import MagicToken, User

router = APIRouter(prefix="/api/auth", tags=["auth"])

TOKEN_TTL = timedelta(minutes=15)
SESSION_COOKIE_MAX_AGE = 7 * 24 * 60 * 60  # 7 days, matches JWT exp


class RequestMagicLink(BaseModel):
    # Plain str rather than pydantic.EmailStr — that would pull in
    # email-validator as a hard dep, and we already trust the users table
    # as the source of truth (unknown emails are simply not found).
    email: str


class MeResponse(BaseModel):
    id: int
    email: str
    role: str


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _set_session_cookie(response: Response, token: str, *, secure: bool) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=SESSION_COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=secure,
        path="/",
    )


@router.post("/request")
def request_magic_link(
    payload: RequestMagicLink,
    db: Session = Depends(get_db),
):
    """Send a magic link if the email is registered. Always 200.

    The response shape is identical whether or not the email exists in the
    users table — that's deliberate, so this endpoint can't be used to
    enumerate accounts.
    """
    user = db.query(User).filter(User.email == payload.email).first()
    if user is not None:
        raw_token = secrets.token_urlsafe(32)
        token_row = MagicToken(
            user_id=user.id,
            token_hash=_hash_token(raw_token),
            expires_at=datetime.utcnow() + TOKEN_TTL,
        )
        db.add(token_row)
        db.commit()

        link = f"{settings.public_url.rstrip('/')}/api/auth/exchange?token={raw_token}"
        get_emailer().send(to_email=user.email, magic_link_url=link)

    return {"ok": True, "message": "If that email is registered, a magic link has been sent."}


@router.get("/exchange")
def exchange_magic_link(token: str, request: Request, db: Session = Depends(get_db)):
    """Trade a raw magic-link token for a session cookie + redirect to /.

    Single-use semantics: setting used_at on the row means a stolen link
    that's already been clicked can't be re-used.
    """
    token_hash = _hash_token(token)
    row = db.query(MagicToken).filter(MagicToken.token_hash == token_hash).first()
    if row is None:
        raise HTTPException(status_code=401, detail="Invalid or expired link")
    if row.used_at is not None:
        raise HTTPException(status_code=401, detail="Invalid or expired link")
    if row.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Invalid or expired link")

    user = db.query(User).filter(User.id == row.user_id).first()
    if user is None:
        # Shouldn't happen (FK), but guard anyway.
        raise HTTPException(status_code=401, detail="Invalid or expired link")

    row.used_at = datetime.utcnow()
    user.last_login_at = datetime.utcnow()
    db.commit()

    jwt_token = encode_token(user_id=user.id, role=user.role)

    redirect_to = settings.public_url.rstrip("/") + "/"
    response = RedirectResponse(url=redirect_to, status_code=303)
    _set_session_cookie(
        response, jwt_token, secure=(request.url.scheme == "https")
    )
    return response


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/me", response_model=MeResponse)
def me(request: Request, db: Session = Depends(get_db)):
    """Return the current user, or 401 if no valid session.

    When AUTH_REQUIRED=false (dev default), returns a synthetic admin so
    the frontend has a stable shape to render against in local dev.
    """
    # Imported locally to break the deps→router→deps cycle (router defines
    # COOKIE_NAME which deps imports).
    from app.auth.deps import _read_cookie_user

    user = _read_cookie_user(request=request, db=db)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return MeResponse(id=user.id, email=user.email, role=user.role)
