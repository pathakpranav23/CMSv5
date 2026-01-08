import os
import sys

# Ensure project root is on sys.path when running from scripts/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from cms_app import create_app
from cms_app.models import User, Program, Faculty


def main():
    app = create_app()
    with app.app_context():
        principals = User.query.filter(User.role.ilike('%principal%')).all()
        if not principals:
            print("No principal users found.")
            return
        print("user_id | username | program_id | program_name | faculty_name | faculty_email")
        for u in principals:
            prog = Program.query.get(u.program_id_fk) if u.program_id_fk else None
            fac = Faculty.query.filter_by(user_id_fk=u.user_id).first()
            fac_name = fac.full_name if fac else ''
            fac_email = fac.email if fac else ''
            print(f"{u.user_id} | {u.username} | {u.program_id_fk or ''} | {(prog.program_name if prog else '')} | {fac_name} | {fac_email}")


if __name__ == "__main__":
    main()