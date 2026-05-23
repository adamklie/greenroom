"""Create or promote the initial admin user.

There is no signup flow in greenroom — users are added by an admin. The
first admin has to be bootstrapped from the CLI:

    cd backend
    python scripts/create_admin.py aklie@ucsd.edu

If the email already exists, its role is upgraded to 'admin'. Otherwise a
new row is inserted.
"""

import sys
from datetime import datetime

from app.database import SessionLocal
from app.models import User


def main(email: str) -> None:
    db = SessionLocal()
    try:
        existing = db.query(User).filter_by(email=email).first()
        if existing:
            existing.role = "admin"
            print(f"Updated {email} to admin.")
        else:
            user = User(email=email, role="admin", created_at=datetime.utcnow())
            db.add(user)
            print(f"Created admin user: {email}")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/create_admin.py <email>")
        sys.exit(1)
    main(sys.argv[1])
