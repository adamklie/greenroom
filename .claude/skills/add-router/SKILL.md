---
description: Scaffold a new FastAPI router, Pydantic schemas, optional SQLAlchemy model, App registration, and a smoke test. Triggers on "add a new router for X", "scaffold a /api/X endpoint", "I need a backend endpoint for ...". Usage: /add-router <name>
---

# /add-router

Scaffold a new backend resource end-to-end: router file, schemas, optional model, App registration, smoke test. Follow the conventions in `backend/app/routers/songs.py` and `backend/app/schemas/song.py` — do not reinvent.

## Instructions

### 1. Gather the inputs

Ask the user (don't guess):

1. **Resource name.** Convention: `Song` (singular, PascalCase) for the model, `/api/songs` (plural, kebab-case) for the URL. If the argument was `gigs`, model = `Gig`, URL = `/api/gigs`, file = `gigs.py`. If you can't infer a clean plural, ask.
2. **Does this need a new SQLAlchemy model?** (yes / no — many routers just compose existing models.)
3. **Should the frontend `api/client.ts` get a typed client function?** (yes / no — defer if no UI yet.)

Confirm the four computed names before writing files:

- Model class: `<Name>` (e.g. `Gig`)
- File name: `<plural-lower>.py` (e.g. `gigs.py`)
- URL prefix: `/api/<plural-lower>` (e.g. `/api/gigs`)
- Tag: `<plural-lower>` (e.g. `gigs`)

### 2. Create `backend/app/routers/<name>.py`

Use this template literally (substituting `<name>` and `<Name>`). It mirrors `songs.py`: single-item tag list, `Depends(get_db)`, raises `HTTPException(404, "...")` with a message.

```python
"""<Name> router — <one-line purpose>."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.<name> import <Name>Create, <Name>Read, <Name>Update

router = APIRouter(prefix="/api/<plural-lower>", tags=["<plural-lower>"])


@router.get("", response_model=list[<Name>Read])
def list_<plural-lower>(db: Session = Depends(get_db)):
    # TODO: query the DB once the model exists. Empty list keeps this honest for now.
    return []


@router.get("/{item_id}", response_model=<Name>Read)
def get_<name>(item_id: int, db: Session = Depends(get_db)):
    # TODO: replace with real lookup against app.models.<Name>
    raise HTTPException(404, "<Name> not found")
```

### 3. Create `backend/app/schemas/<name>.py`

Pydantic v2 — match `backend/app/schemas/song.py`. `<Name>Read` is the only one that needs `model_config = {"from_attributes": True}` (it's the one constructed from ORM rows).

```python
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class <Name>Base(BaseModel):
    # TODO: add real fields once you know the shape
    name: str | None = None


class <Name>Create(<Name>Base):
    pass


class <Name>Update(BaseModel):
    # All fields optional — PATCH semantics
    name: str | None = None


class <Name>Read(<Name>Base):
    id: int
    created_at: datetime | None = None

    model_config = {"from_attributes": True}
```

### 4. (Optional) Create the SQLAlchemy model

Only if step 1 answered "yes" to a new model. Create `backend/app/models/<name>.py`:

```python
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from app.database import Base


class <Name>(Base):
    __tablename__ = "<plural-lower>"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

Then add it to `backend/app/models/__init__.py` so `Base.metadata.create_all()` picks it up. Read the existing `__init__.py` first and follow the same `from .x import X` pattern — don't reorder unrelated entries.

### 5. Register the router in `backend/app/main.py`

Two surgical edits:

1. Add `<plural-lower>` to the existing `from app.routers import ...` line (keep alphabetical order).
2. Add `app.include_router(<plural-lower>.router)` to the `app.include_router(...)` block (also alphabetical).

Don't reformat the rest of the imports. Don't move other routers around.

### 6. Add `backend/tests/test_<plural-lower>.py`

This may be the **first** test file in the repo — structure it for easy extension. Use FastAPI's `TestClient`. Don't pull in pytest fixtures that don't exist yet.

```python
"""Smoke test for the <plural-lower> router."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_<plural-lower>_returns_200():
    response = client.get("/api/<plural-lower>")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
```

### 7. (Optional) Add a typed client function to `frontend/src/api/client.ts`

Only if step 1 answered "yes". Read `frontend/src/api/client.ts` first and follow the existing pattern — don't invent a new style.

### 8. Verify

Run a syntax check on each new Python file:

```bash
python3 -m py_compile backend/app/routers/<name>.py backend/app/schemas/<name>.py
```

And run the smoke test:

```bash
cd backend && pytest tests/test_<plural-lower>.py -v
```

If the test fails because pytest isn't installed yet, surface that — don't try to install it silently.

## Rules

- **Don't** add CRUD endpoints (POST/PATCH/DELETE) speculatively. Only what the user asked for. They can always re-run this skill or add manually.
- **Don't** invent fields. The schema starts minimal (`name`) and the user adds real fields after.
- **Don't** modify existing routers. Surgical means the only files that change are the new ones plus the two-line edit to `main.py` (and `models/__init__.py` if a new model).
- Match `songs.py` style for `HTTPException` calls: `HTTPException(404, "<Name> not found")` — short message, no extra detail dict.
- Tag in `APIRouter(tags=...)` is a one-element list like songs.py: `tags=["<plural-lower>"]`.
