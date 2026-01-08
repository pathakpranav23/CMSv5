import os
import sys
import argparse

# Ensure project root is on sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from cms_app import create_app, db
from cms_app.models import User


def set_role(username: str, role: str) -> None:
    app = create_app()
    with app.app_context():
        u = User.query.filter_by(username=username).first()
        if not u:
            print(f"User '{username}' not found.")
            return
        old_role = u.role
        u.role = role
        db.session.commit()
        print(f"Updated role for '{username}' from '{old_role}' to '{role}'.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Set a user's role by username.")
    parser.add_argument("--username", required=True, help="Username (often email) of the user")
    parser.add_argument("--role", required=True, help="Role to assign (e.g., Admin, Principal, Faculty, Clerk, Student)")
    args = parser.parse_args()

    set_role(args.username, args.role)