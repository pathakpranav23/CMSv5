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
        progs = Program.query.filter(Program.program_name.ilike('%BCA%')).all()
        prog_ids = [p.program_id for p in progs]
        users = User.query.filter(User.role == 'Clerk', User.program_id_fk.in_(prog_ids)).all()
        for u in users:
            f = Faculty.query.filter_by(user_id_fk=u.user_id).first()
            name = f.full_name if f else ''
            email = f.email if f else ''
            print(f"{u.user_id}|{u.username}|{u.program_id_fk}|{name}|{email}")


if __name__ == "__main__":
    main()