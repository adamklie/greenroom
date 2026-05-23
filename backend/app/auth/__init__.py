"""Magic-link auth + role gating for greenroom.

Layout:
    jwt.py    — HS256 encode/decode of the session payload
    email.py  — MagicLinkEmailer protocol + StubEmailer (logs URLs to stdout)
    router.py — /api/auth/{request,exchange,logout,me}
    deps.py   — current_user, require_viewer, require_editor, require_admin

When settings.auth_required is False, the require_* deps return a synthetic
admin so the existing local dev flow works without login. Flip to True
(GREENROOM_AUTH_REQUIRED=true) to enforce real cookies.
"""
