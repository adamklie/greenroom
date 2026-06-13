from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings


DEFAULT_VAULT_DIR = (
    Path.home()
    / "Library"
    / "Mobile Documents"
    / "com~apple~CloudDocs"
    / "greenroom"
)


class Settings(BaseSettings):
    """Application settings. Override via environment variables or .env file."""

    # Canonical home for imported music files, DB backups, and annotation
    # exports. Lives in iCloud so it's synced across devices; the app itself
    # (code + live DB) lives elsewhere and is only backed up via git.
    vault_dir: Path = DEFAULT_VAULT_DIR

    # Legacy: pre-vault, files were scattered through a music directory.
    # Kept so (a) old DB rows still resolve while we migrate, (b) the
    # migration script has a place to look for source files. Once every
    # AudioFile row has been migrated into the vault, this is unused.
    music_dir: Path = Path(__file__).resolve().parents[3]

    # Live SQLite database (next to the app, not in the vault).
    db_path: Path = Path(__file__).resolve().parents[2] / "greenroom.db"

    # Storage backend selection. "local" uses the iCloud vault on disk;
    # "r2" is a stub for future Cloudflare R2 hosting (not yet wired).
    media_backend: Literal["local", "r2"] = "local"

    # R2 (S3-compatible) backend config. Unused while media_backend == "local".
    # Populated from env vars when cloud hosting is enabled.
    r2_account_id: str = ""           # GREENROOM_R2_ACCOUNT_ID
    r2_access_key_id: str = ""        # GREENROOM_R2_ACCESS_KEY_ID
    r2_secret_access_key: str = ""    # GREENROOM_R2_SECRET_ACCESS_KEY
    r2_bucket: str = ""               # GREENROOM_R2_BUCKET (media bucket)
    # Full endpoint URL with scheme (e.g. https://<account>.r2.cloudflarestorage.com).
    r2_endpoint_url: str = ""         # GREENROOM_R2_ENDPOINT_URL
    # Separate bucket for Litestream DB replicas. Kept apart so a media-only
    # API token can be issued for bulk-upload scripts without DB access.
    r2_db_backup_bucket: str = ""     # GREENROOM_R2_DB_BACKUP_BUCKET
    # TTL for presigned media URLs handed to the browser. Default 1 hour —
    # long enough to play a track without spamming the signing endpoint,
    # short enough that a leaked URL expires quickly.
    r2_presign_ttl_seconds: int = 3600  # GREENROOM_R2_PRESIGN_TTL_SECONDS

    # --- Feedback / GitHub issues ---
    # Personal access token for the feedback endpoint. Empty disables real
    # issue creation — the endpoint returns a clean error without hitting
    # the network. Set GREENROOM_GITHUB_TOKEN on the deploy to enable.
    github_token: str = ""            # GREENROOM_GITHUB_TOKEN
    # Repo that feedback issues are filed into. Overridable so a fork or
    # test repo can be targeted without a code change.
    github_repo: str = "adamklie/greenroom"  # GREENROOM_GITHUB_REPO

    # --- Email (Phase 3d) ---
    # Resend API key. Empty disables real sends — ResendEmailer falls back
    # to printing the magic link to stdout (same behavior as StubEmailer).
    resend_api_key: str = ""          # GREENROOM_RESEND_API_KEY
    # The `from` header for outbound mail. Defaults to the Resend sandbox
    # sender so the deploy works out-of-the-box without a verified domain;
    # override per-deploy once a custom domain is verified in Resend.
    resend_from_email: str = "Greenroom <onboarding@resend.dev>"  # GREENROOM_RESEND_FROM_EMAIL

    # --- Auth (Phase 3a) ---
    # Master switch. When False (default), all role-guarded routes return a
    # synthetic admin so the local dev flow (./dev.sh) keeps working without
    # any login step. Flip to True for real cookie-based enforcement.
    auth_required: bool = False

    # HS256 signing key for the greenroom_session JWT. Empty string triggers
    # a random key generated at startup with a warning (non-persistent — every
    # restart logs everyone out). Set GREENROOM_AUTH_SECRET in prod.
    auth_secret: str = ""

    # Which MagicLinkEmailer to use. "stub" prints to stdout (good for dev +
    # for Phase 3a). "resend" is Phase 3d.
    email_backend: Literal["stub", "resend"] = "stub"

    # Used to construct the magic-link URL in /api/auth/request. Should be the
    # public-facing origin the frontend is served from.
    public_url: str = "http://localhost:5175"

    # --- Deployment (Phase 3b) ---
    # Directory of pre-built React static assets to serve at `/`. Empty (the
    # default) skips the static mount — local dev runs Vite separately on
    # :5173/:5175, so the backend doesn't need to serve the SPA. In the
    # container image this points at /app/static (set by the Dockerfile).
    static_dir: str = ""

    # Comma-separated allow-list of origins for CORS. Default covers the
    # ports `dev.sh` and the Makefile spin up. In production deployments
    # this is overridden via GREENROOM_ALLOWED_ORIGINS to include the
    # public domain (e.g. https://greenroom.example.com).
    allowed_origins: str = "http://localhost:5173,http://localhost:5175,http://localhost:5176"

    # --- Multi-project (v2, Phase 3) ---
    # Master switch for project-scoped access control. When False (default),
    # the app behaves exactly like V1 — no query scoping, global roles, and the
    # new project_id columns are inert. Flipped to True in Phase 3b, after the
    # schema + backfill are live and verified, to enforce per-project access.
    multi_project: bool = False

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.db_path}"

    @property
    def vault_files_dir(self) -> Path:
        return self.vault_dir / "files"

    @property
    def vault_backups_dir(self) -> Path:
        return self.vault_dir / "backups"

    @property
    def vault_exports_dir(self) -> Path:
        return self.vault_dir / "exports"

    def ensure_vault_layout(self) -> None:
        """Create vault subdirectories if missing. Safe to call repeatedly."""
        for d in (self.vault_files_dir, self.vault_backups_dir, self.vault_exports_dir):
            d.mkdir(parents=True, exist_ok=True)

    model_config = {"env_prefix": "GREENROOM_", "env_file": ".env", "extra": "ignore"}


settings = Settings()
