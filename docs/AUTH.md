# Authentication

Magic-link login with three roles (`viewer`, `editor`, `admin`). No passwords, no signup — users are admin-invite-only.

## Dev mode (the default)

`GREENROOM_AUTH_REQUIRED=false` (the default) makes the backend's role gates return a synthetic admin (`id=0`, `email=dev@local`). Every route works without a cookie, the frontend renders as if you were signed in, and there's nothing extra to set up. This is what `./dev.sh` runs.

## Real auth (prod)

Flip `GREENROOM_AUTH_REQUIRED=true` and restart the backend. From that point on:

- `/api/auth/*` is the only public surface (plus `/api/health`).
- Every other endpoint requires a `greenroom_session` cookie.
- Mutations require role ≥ editor; admin-only routes require role admin.

### Environment variables

| Var | Default | Purpose |
|---|---|---|
| `GREENROOM_AUTH_REQUIRED` | `false` | Master switch. `true` enables cookie checks. |
| `GREENROOM_AUTH_SECRET` | (random per process) | HS256 signing key for the session JWT. Set this in prod or every restart logs everyone out. |
| `GREENROOM_EMAIL_BACKEND` | `stub` | `stub` prints magic links to stdout. `resend` will hit Resend in Phase 3d (not wired yet). |
| `GREENROOM_PUBLIC_URL` | `http://localhost:5175` | Origin used to build the magic-link URL emailed to the user. |

## Flow

1. User visits the app → frontend calls `GET /api/auth/me` → 401 → renders `/login`.
2. User enters email → `POST /api/auth/request {email}`.
3. Backend always returns 200 (anti-enumeration). If the email exists in `users`, it creates a `magic_tokens` row (sha256 of a 32-byte urlsafe token, 15-min expiry) and the configured emailer dispatches the link.
4. User clicks the link → `GET /api/auth/exchange?token=...` → backend hashes the token, looks up the row, checks expiry + that it's unused, marks it used, sets the `greenroom_session` httpOnly cookie (HS256 JWT, 7-day expiry), 303-redirects to `/`.
5. Subsequent requests carry the cookie; `Depends(require_viewer/editor/admin)` enforces role.
6. `POST /api/auth/logout` clears the cookie.

## Roles

| Role | Allowed |
|---|---|
| `viewer` | All `GET` endpoints |
| `editor` | `viewer` + all mutations (POST/PATCH/PUT/DELETE on songs, audio_files, sessions, tags, setlists, tabs, options, upload, backup, etc.) |
| `admin` | `editor` + user management (admin endpoints arrive in a later phase) |

Role rank is centralized in `backend/app/auth/deps.py` (`_ROLE_RANK`). Adding a role is one dict entry.

## Adding a user

There is no signup flow. To add the first admin:

```bash
cd backend
python scripts/create_admin.py aklie@ucsd.edu
```

If the email already exists in `users`, its role is promoted to admin. Otherwise the script inserts a new row.

To add other users in the current phase, insert into `users` directly:

```sql
INSERT INTO users (email, role) VALUES ('teammate@example.com', 'editor');
```

A proper admin UI for managing users arrives in a later phase.

## Stub emailer

While `GREENROOM_EMAIL_BACKEND=stub` (the default for Phase 3a), the magic link is printed to the backend's stdout:

```
=== MAGIC LINK for aklie@ucsd.edu ===
http://localhost:5175/api/auth/exchange?token=...
=== expires in 15 minutes ===
```

Copy the URL, paste in the browser, you're in. Resend wires up in Phase 3d.

## Files

- `backend/app/auth/jwt.py` — encode/decode the session JWT.
- `backend/app/auth/email.py` — `MagicLinkEmailer` Protocol + `StubEmailer`.
- `backend/app/auth/router.py` — the four endpoints.
- `backend/app/auth/deps.py` — `current_user`, `require_viewer/editor/admin`.
- `backend/app/models/user.py` — `User`, `MagicToken`.
- `backend/scripts/create_admin.py` — bootstrap the first admin.
- `frontend/src/auth/` — `useCurrentUser`, `RoleGate`, `Login`.
