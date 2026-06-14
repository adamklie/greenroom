"""Projects API (v2 Phase 3b).

CRUD for projects and their membership. These endpoints operate on the
access-control tables (`projects`, `project_members`), which are deliberately
NOT query-scoped — they're what *determine* a request's scope — so they use the
plain auth deps, not require_project_role.

Authorization:
  - GET /api/projects          — any authenticated user (their memberships;
                                 global admin sees all projects).
  - POST /api/projects         — any authenticated user (becomes owner).
  - members sub-routes         — project owner or global admin only.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.deps import require_viewer
from app.database import get_db
from app.models import Project, ProjectMember, User

router = APIRouter(prefix="/api/projects", tags=["projects"])

_VALID_MEMBER_ROLES = {"owner", "editor", "viewer"}


class ProjectRead(BaseModel):
    id: int
    name: str
    role: str  # the caller's role in this project ('admin' for the global admin)
    model_config = {"from_attributes": True}


class ProjectCreate(BaseModel):
    name: str


class MemberRead(BaseModel):
    id: int
    user_id: int
    email: str
    role: str


class MemberAdd(BaseModel):
    email: str
    role: str = "viewer"


class MemberRoleUpdate(BaseModel):
    role: str


def _owns_or_admin(project_id: int, user: User, db: Session) -> None:
    """Raise 403 unless `user` is the project's owner or a global admin."""
    if user.role == "admin":
        return
    member = (
        db.query(ProjectMember)
        .filter_by(project_id=project_id, user_id=user.id, role="owner")
        .first()
    )
    if member is None:
        raise HTTPException(status_code=403, detail="Only the project owner can manage members")


def _get_project_or_404(project_id: int, db: Session) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("", response_model=list[ProjectRead])
def list_projects(db: Session = Depends(get_db), user: User = Depends(require_viewer)):
    """Projects the caller can switch to. A global admin sees every project."""
    if user.role == "admin":
        return [
            ProjectRead(id=p.id, name=p.name, role="admin")
            for p in db.query(Project).order_by(Project.name).all()
        ]
    rows = (
        db.query(Project, ProjectMember.role)
        .join(ProjectMember, ProjectMember.project_id == Project.id)
        .filter(ProjectMember.user_id == user.id)
        .order_by(Project.name)
        .all()
    )
    return [ProjectRead(id=p.id, name=p.name, role=role) for p, role in rows]


@router.post("", response_model=ProjectRead, status_code=201)
def create_project(
    data: ProjectCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_viewer),
):
    """Create a project; the creator becomes its owner. Project names are unique
    per owner (not globally — two users may both have a 'Solo')."""
    name = data.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Project name is required")

    # Per-owner uniqueness: does this user already own a project by this name?
    existing = (
        db.query(Project)
        .join(ProjectMember, ProjectMember.project_id == Project.id)
        .filter(
            ProjectMember.user_id == user.id,
            ProjectMember.role == "owner",
            Project.name == name,
        )
        .first()
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="You already have a project with that name")

    project = Project(name=name)
    db.add(project)
    db.flush()
    db.add(ProjectMember(project_id=project.id, user_id=user.id, role="owner"))
    db.commit()
    return ProjectRead(id=project.id, name=project.name, role="owner")


@router.get("/{project_id}/members", response_model=list[MemberRead])
def list_members(
    project_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_viewer),
):
    _get_project_or_404(project_id, db)
    _owns_or_admin(project_id, user, db)
    rows = (
        db.query(ProjectMember, User.email)
        .join(User, User.id == ProjectMember.user_id)
        .filter(ProjectMember.project_id == project_id)
        .all()
    )
    return [
        MemberRead(id=m.id, user_id=m.user_id, email=email, role=m.role)
        for m, email in rows
    ]


@router.post("/{project_id}/members", response_model=MemberRead, status_code=201)
def add_member(
    project_id: int,
    data: MemberAdd,
    db: Session = Depends(get_db),
    user: User = Depends(require_viewer),
):
    """Add an EXISTING user (by email) to the project. Invite-only: we never
    create accounts here."""
    _get_project_or_404(project_id, db)
    _owns_or_admin(project_id, user, db)
    if data.role not in _VALID_MEMBER_ROLES:
        raise HTTPException(status_code=400, detail="Invalid role")

    # Match the codebase's exact-match email lookup (auth/router.py, create_admin.py
    # don't normalize case) — lowercasing here would fail to find a mixed-case
    # account. Strip only, to forgive stray whitespace.
    target = db.query(User).filter(User.email == data.email.strip()).first()
    if target is None:
        raise HTTPException(status_code=404, detail="No account with that email")

    existing = (
        db.query(ProjectMember)
        .filter_by(project_id=project_id, user_id=target.id)
        .first()
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Already a member")

    member = ProjectMember(project_id=project_id, user_id=target.id, role=data.role)
    db.add(member)
    db.commit()
    db.refresh(member)
    return MemberRead(id=member.id, user_id=target.id, email=target.email, role=member.role)


@router.patch("/{project_id}/members/{member_id}", response_model=MemberRead)
def update_member_role(
    project_id: int,
    member_id: int,
    data: MemberRoleUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_viewer),
):
    _get_project_or_404(project_id, db)
    _owns_or_admin(project_id, user, db)
    if data.role not in _VALID_MEMBER_ROLES:
        raise HTTPException(status_code=400, detail="Invalid role")
    member = (
        db.query(ProjectMember)
        .filter_by(id=member_id, project_id=project_id)
        .first()
    )
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    # Don't let the last owner demote themselves into a project with no owner.
    if member.role == "owner" and data.role != "owner":
        owners = (
            db.query(ProjectMember)
            .filter_by(project_id=project_id, role="owner")
            .count()
        )
        if owners <= 1:
            raise HTTPException(status_code=400, detail="A project must keep at least one owner")
    member.role = data.role
    db.commit()
    target = db.query(User).filter(User.id == member.user_id).first()
    return MemberRead(id=member.id, user_id=member.user_id, email=target.email, role=member.role)


@router.delete("/{project_id}/members/{member_id}", status_code=204)
def remove_member(
    project_id: int,
    member_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_viewer),
):
    _get_project_or_404(project_id, db)
    _owns_or_admin(project_id, user, db)
    member = (
        db.query(ProjectMember)
        .filter_by(id=member_id, project_id=project_id)
        .first()
    )
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    if member.role == "owner":
        owners = (
            db.query(ProjectMember)
            .filter_by(project_id=project_id, role="owner")
            .count()
        )
        if owners <= 1:
            raise HTTPException(status_code=400, detail="A project must keep at least one owner")
    db.delete(member)
    db.commit()
