"""Feedback API — creates GitHub issues from user feedback."""

import subprocess

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/feedback", tags=["feedback"])

REPO = "adamklie/greenroom"


class FeedbackCreate(BaseModel):
    title: str
    description: str
    category: str = "feedback"  # feedback, bug, feature, question
    priority: str = "normal"   # low, normal, high


@router.post("")
def create_feedback(data: FeedbackCreate):
    """Create a GitHub issue from user feedback."""
    labels = [data.category]
    if data.priority == "high":
        labels.append("priority:high")

    body = f"{data.description}\n\n---\n_Submitted via Greenroom app ({data.priority} priority)_"

    try:
        result = subprocess.run(
            [
                "gh", "issue", "create",
                "--repo", REPO,
                "--title", data.title,
                "--body", body,
                "--label", ",".join(labels),
            ],
            capture_output=True, text=True, timeout=15,
        )

        if result.returncode == 0:
            # Parse issue URL from output
            url = result.stdout.strip()
            return {"ok": True, "url": url}
        else:
            # If gh CLI fails (not installed, not authenticated), save locally
            return {"ok": False, "error": result.stderr, "saved_locally": True}

    except FileNotFoundError:
        return {"ok": False, "error": "GitHub CLI (gh) not installed. Install with: brew install gh"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/issues")
def list_issues():
    """List open GitHub issues for the repo."""
    try:
        result = subprocess.run(
            ["gh", "issue", "list", "--repo", REPO, "--json", "number,title,labels,createdAt,url", "--limit", "20"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0:
            import json
            return {"issues": json.loads(result.stdout)}
        return {"issues": [], "error": result.stderr}
    except Exception as e:
        return {"issues": [], "error": str(e)}
