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
    """Sends magic-link emails via the Resend HTTP API.

    All failure modes (no API key, HTTP error, network error) are caught and
    logged rather than raised — the auth router treats `.send()` as best-effort
    and the caller already returns 200 to avoid leaking whether the email
    exists, so propagating an exception would only manifest as a 500 to the
    user without any useful recovery path.
    """

    def send(self, *, to_email: str, magic_link_url: str) -> None:
        if not settings.resend_api_key:
            # No API key configured — degrade to StubEmailer behavior so the
            # link is still recoverable from the server log during early
            # bring-up of a fresh deploy.
            print(f"[resend] no API key; falling back to stdout for {to_email}")
            print(f"[resend] MAGIC LINK: {magic_link_url}", flush=True)
            return

        import requests  # lazy: not needed for the stub-emailer dev path

        html = (
            "<p>Click below to sign in to Greenroom. Link expires in 15 minutes.</p>"
            f'<p><a href="{magic_link_url}">Sign in to Greenroom</a></p>'
            "<p>If you did not request this, you can ignore this email.</p>"
        )

        try:
            r = requests.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                json={
                    "from": settings.resend_from_email,
                    "to": [to_email],
                    "subject": "Sign in to Greenroom",
                    "html": html,
                },
                timeout=10,
            )
            if r.status_code >= 400:
                print(f"[resend] send failed for {to_email}: {r.status_code} {r.text}")
        except requests.RequestException as e:
            print(f"[resend] send raised for {to_email}: {e}")


def get_emailer() -> MagicLinkEmailer:
    if settings.email_backend == "resend":
        return ResendEmailer()
    return StubEmailer()
