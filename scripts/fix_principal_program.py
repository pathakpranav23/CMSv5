import os
import sys

# Ensure project root is on sys.path when running from scripts/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from cms_app import create_app, db
from cms_app.models import User, Program
from sqlalchemy import select


def main():
    username = sys.argv[1] if len(sys.argv) > 1 else 'principal'
    target_program_name = 'BCom (English)'

    app = create_app()
    with app.app_context():
        user = db.session.execute(
            select(User).filter_by(username=username)
        ).scalars().first()
        if not user:
            print(f"No user found with username '{username}'.")
            return
        target_program = db.session.execute(
            select(Program).filter_by(program_name=target_program_name)
        ).scalars().first()
        if not target_program:
            print(f"Program '{target_program_name}' not found.")
            return
        before_pid = user.program_id_fk
        user.program_id_fk = target_program.program_id
        db.session.commit()
        print(f"Updated principal '{username}' program_id from {before_pid} to {user.program_id_fk} ({target_program.program_name}).")


if __name__ == "__main__":
    main()
