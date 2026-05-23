"""JWT encode/decode for the greenroom_session cookie.

HS256 with a 7-day expiry. The secret comes from settings.auth_secret; if
empty (the default in dev), a random key is generated once per process and
a warning is logged — fine for dev, but means every backend restart logs
everyone out. Set GREENROOM_AUTH_SECRET in any environment where you want
sessions to survive restarts.
"""

from __future__ import annotations

import secrets
import warnings
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt as _jwt

from app.config import settings

_ALGORITHM = "HS256"
_SESSION_LIFETIME = timedelta(days=7)

# Cached random key for the empty-secret case. Computed lazily on first use
# so import-time has no side effects.
_random_secret: str | None = None


def _get_secret() -> str:
    global _random_secret
    if settings.auth_secret:
        return settings.auth_secret
    if _random_secret is None:
        _random_secret = secrets.token_urlsafe(48)
        warnings.warn(
            "GREENROOM_AUTH_SECRET is empty — generated a random one for this "
            "process. Sessions will not survive restarts. Set the env var in prod.",
            stacklevel=2,
        )
    return _random_secret


def encode_token(*, user_id: int, role: str) -> str:
    """Encode a 7-day session JWT. Carries user_id + role; that's it."""
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "user_id": user_id,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + _SESSION_LIFETIME).timestamp()),
    }
    return _jwt.encode(payload, _get_secret(), algorithm=_ALGORITHM)


def decode_token(token: str) -> dict[str, Any] | None:
    """Decode + validate a session JWT. Returns the payload or None on any error.

    Callers should treat None as 'no valid session' — expired, bad signature,
    malformed, doesn't matter, they all fold to the same outcome.
    """
    try:
        return _jwt.decode(token, _get_secret(), algorithms=[_ALGORITHM])
    except _jwt.PyJWTError:
        return None
