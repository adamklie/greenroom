"""Create or update a user with a role.

There is no signup flow in greenroom — users are added by an admin from the CLI:

    cd backend
    python scripts/create_admin.py aklie@ucsd.edu                  # admin (default)
    python scripts/create_admin.py bandmate@gmail.com --role viewer
    python scripts/create_admin.py editor@gmail.com   --role editor

Roles: viewer (read-only) < editor (can modify) < admin (full). If the email
already exists, its role is updated; otherwise a new row is inserted. Defaults
to admin so the original bootstrap usage still works.
"""

import argparse
import sys
from datetime import datetime

from app.database import SessionLocal
from app.models import User

ROLES = ("viewer", "editor", "admin")


def _valid_email(email: str) -> bool:
    return email.count("@") == 1 and "." in email.split("@")[1] and " " not in email


def main(email: str, role: str) -> int:
    if not _valid_email(email):
        print(f"'{email}' doesn't look like a valid email address.")
        return 1
    db = SessionLocal()
    try:
        existing = db.query(User).filter_by(email=email).first()
        if existing:
            existing.role = role
            print(f"Updated {email} -> {role}.")
        else:
            db.add(User(email=email, role=role, created_at=datetime.utcnow()))
            print(f"Created {role} user: {email}")
        db.commit()
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Create or update a greenroom user with a role.")
    p.add_argument("email")
    p.add_argument("--role", default="admin", choices=ROLES, help="Role to grant (default: admin).")
    args = p.parse_args()
    sys.exit(main(args.email, args.role))
