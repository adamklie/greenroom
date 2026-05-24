"""Feedback API — creates GitHub issues from user feedback.

Talks to GitHub's REST API directly via `requests`. The previous version
shelled out to the `gh` CLI which isn't present in the Fly container
(python:3.11-slim + ffmpeg + litestream only), so production submissions
hit FileNotFoundError. This module has no system dependencies.

Auth model: token is a personal access token with `repo` (private) or
`public_repo` (public) scope, read from GREENROOM_GITHUB_TOKEN. When the
token is empty the endpoints return a clean error shape instead of trying
to call GitHub.
"""

from __future__ import annotations

import logging

import requests
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth.deps import require_editor, require_viewer
from app.config import settings

router = APIRouter(prefix="/api/feedback", tags=["feedback"])

log = logging.getLogger(__name__)

# Map UI categories to labels that exist in the repo. "feedback" has no direct
# label equivalent — leave it unlabeled. "feature" maps to the standard
# "enhancement" label.
CATEGORY_LABELS = {
    "feedback": [],
    "bug": ["bug"],
    "feature": ["enhancement"],
    "question": ["question"],
}

# Short timeout — the frontend waits on this synchronously. GitHub is fast
# but a hung connection would block the request loop.
_HTTP_TIMEOUT = 15


class FeedbackCreate(BaseModel):
    title: str
    description: str
    category: str = "feedback"  # feedback, bug, feature, question
    priority: str = "normal"   # low, normal, high


def _issues_url() -> str:
    return f"https://api.github.com/repos/{settings.github_repo}/issues"


def _auth_headers() -> dict[str, str]:
    return {
        "Authorization": f"token {settings.github_token}",
        "Accept": "application/vnd.github+json",
    }


@router.post("")
def create_feedback(data: FeedbackCreate, _user=Depends(require_editor)):
    """Create a GitHub issue from user feedback via the REST API."""
    if not settings.github_token:
        log.warning("feedback POST attempted without GREENROOM_GITHUB_TOKEN configured")
        return {
            "ok": False,
            "error": "GitHub feedback not configured (set GREENROOM_GITHUB_TOKEN)",
        }

    labels = list(CATEGORY_LABELS.get(data.category, []))
    if data.priority == "high":
        labels.append("priority:high")

    body = (
        f"{data.description}\n\n---\n"
        f"_Submitted via Greenroom app ({data.priority} priority)_"
    )

    payload: dict = {"title": data.title, "body": body}
    if labels:
        payload["labels"] = labels

    try:
        resp = requests.post(
            _issues_url(),
            headers=_auth_headers(),
            json=payload,
            timeout=_HTTP_TIMEOUT,
        )
    except requests.RequestException as e:
        log.warning("feedback POST network error: %s", e)
        return {"ok": False, "error": f"Network error contacting GitHub: {e}"}

    if resp.status_code == 201:
        return {"ok": True, "url": resp.json().get("html_url", "")}

    return {
        "ok": False,
        "error": f"GitHub API {resp.status_code}: {resp.text[:200]}",
    }


@router.get("/issues")
def list_issues(_user=Depends(require_viewer)):
    """List open GitHub issues for the repo via the REST API.

    GitHub returns issues AND pull requests in the same endpoint — PRs are
    issues with a `pull_request` key set. Filter those out so the UI only
    sees real issues.
    """
    if not settings.github_token:
        return {
            "issues": [],
            "error": "GitHub feedback not configured (set GREENROOM_GITHUB_TOKEN)",
        }

    try:
        resp = requests.get(
            _issues_url(),
            headers=_auth_headers(),
            params={"state": "open", "per_page": 20},
            timeout=_HTTP_TIMEOUT,
        )
    except requests.RequestException as e:
        log.warning("feedback list network error: %s", e)
        return {"issues": [], "error": f"Network error contacting GitHub: {e}"}

    if resp.status_code != 200:
        return {
            "issues": [],
            "error": f"GitHub API {resp.status_code}: {resp.text[:200]}",
        }

    raw = resp.json()
    issues = []
    for it in raw:
        # Skip pull requests — they show up in the issues endpoint with a
        # `pull_request` sub-object. Real issues have it as None / missing.
        if it.get("pull_request") is not None:
            continue
        issues.append(
            {
                "number": it.get("number"),
                "title": it.get("title"),
                "labels": [lbl.get("name") for lbl in it.get("labels", [])],
                "createdAt": it.get("created_at"),
                "url": it.get("html_url"),
            }
        )
    return {"issues": issues}
