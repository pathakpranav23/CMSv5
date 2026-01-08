import os
import sys

# Ensure project root is on sys.path when running from scripts/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from cms_app import create_app
from cms_app.models import User, Program


def main():
    username = sys.argv[1] if len(sys.argv) > 1 else 'principal'
    target_program_name = 'BCom (English)'

    app = create_app()
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if not user:
            print(f"No user found with username '{username}'.")
            return
        target_program = Program.query.filter_by(program_name=target_program_name).first()
        if not target_program:
            print(f"Program '{target_program_name}' not found.")
            return
        before_pid = user.program_id_fk
        user.program_id_fk = target_program.program_id
        from cms_app import db
        db.session.commit()
        print(f"Updated principal '{username}' program_id from {before_pid} to {user.program_id_fk} ({target_program.program_name}).")


if __name__ == "__main__":
    main()