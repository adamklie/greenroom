"""Smoke tests: every survivor router's primary GET returns 200 on an empty DB.

Routers whose primary GET requires a path param (analytics endpoints, media,
gopro, etc.) or a state-changing call (backup, upload, feedback, trim,
filebrowser, files) are intentionally skipped here — those are covered (or
will be covered) by integration tests.
"""

import pytest


SMOKE_ROUTES = [
    "/api/dashboard",
    "/api/songs",
    "/api/audio-files",
    "/api/sessions",
    "/api/tags",
    "/api/setlists",
    "/api/options",
    "/api/tabs",
    "/api/trash",
    "/api/health",
]


@pytest.mark.parametrize("path", SMOKE_ROUTES)
def test_router_get_smoke(client, path):
    """GET each surviving router; expect 200 against an empty in-memory DB."""
    response = client.get(path)
    assert response.status_code == 200, f"{path} -> {response.status_code}: {response.text}"
