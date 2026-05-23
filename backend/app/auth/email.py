"""Magic-link delivery.

Phase 3a stubs this out: StubEmailer just prints the URL to stdout so the
dev workflow is 'request magic link → copy URL from server log → paste in
browser'. ResendEmailer is a placeholder that raises until Phase 3d wires
the real provider.
"""

from __future__ import annotations

from typing import Protocol

from app.config import settings


class MagicLinkEmailer(Protocol):
    def send(self, *, to_email: str, magic_link_url: str) -> None: ...


class StubEmailer:
    """Logs the magic link to stdout. Default backend in dev."""

    def send(self, *, to_email: str, magic_link_url: str) -> None:
        print(
            f"\n=== MAGIC LINK for {to_email} ===\n{magic_link_url}\n"
            "=== expires in 15 minutes ===\n",
            flush=True,
        )


class ResendEmailer:
    """Placeholder. Real wiring lands in Phase 3d."""

    def send(self, *, to_email: str, magic_link_url: str) -> None:  # noqa: D401
        raise NotImplementedError(
            "Resend not wired yet — set GREENROOM_EMAIL_BACKEND=stub or "
            "implement in Phase 3d."
        )


def get_emailer() -> MagicLinkEmailer:
    if settings.email_backend == "resend":
        return ResendEmailer()
    return StubEmailer()
