import os
import sys
from werkzeug.security import generate_password_hash

# Ensure project root is on sys.path when running from scripts/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from cms_app import create_app, db
from cms_app.models import User, Program
from sqlalchemy import select


def ensure_user(username: str, password: str, role: str, program_id: int = None):
    user = db.session.execute(
        select(User).filter_by(username=username)
    ).scalars().first()
    if user is None:
        user = User(
            username=username,
            password_hash=generate_password_hash(password),
            role=role,
            program_id_fk=program_id,
        )
        db.session.add(user)
        db.session.commit()
        return user, True, False
    # Update existing user's password and role/program to ensure known credentials
    user.password_hash = generate_password_hash(password)
    user.role = role
    if program_id is not None:
        user.program_id_fk = program_id
    db.session.commit()
    return user, False, True


def main():
    app = create_app()
    with app.app_context():
        # Prefer scoping principal to BCom (English); fallback to BCA
        bcom_eng = db.session.execute(
            select(Program).filter_by(program_name="BCom (English)")
        ).scalars().first()
        target_prog = bcom_eng or db.session.execute(
            select(Program).filter_by(program_name="BCA")
        ).scalars().first()
        target_pid = target_prog.program_id if target_prog else None

        admin_user, admin_created, admin_updated = ensure_user(
            username="admin",
            password="admin123",
            role="admin",
        )
        principal_user, principal_created, principal_updated = ensure_user(
            username="principal",
            password="principal123",
            role="principal",
            program_id=target_pid,
        )

        print(
            f"Admin -> username: admin, password: admin123, created={admin_created}, updated={admin_updated}"
        )
        print(
            f"Principal -> username: principal, password: principal123, program_id={target_pid}, created={principal_created}, updated={principal_updated}"
        )


if __name__ == "__main__":
    main()
