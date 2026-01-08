import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from cms_app import create_app
from cms_app.models import User, Program


def main():
    username = (sys.argv[1] if len(sys.argv) > 1 else "").strip()
    if not username:
        print("ERROR: Provide username/email as first argument")
        sys.exit(2)

    app = create_app()
    with app.app_context():
        u = User.query.filter_by(username=username).first()
        if not u:
            print(f"NOT_FOUND: {username}")
            return

        role = (u.role or "").strip()
        prog_id = u.program_id_fk
        prog_name = None
        if prog_id:
            try:
                p = Program.query.get(int(prog_id))
                prog_name = getattr(p, "program_name", None)
            except Exception:
                prog_name = None

        print(f"USERNAME: {u.username}")
        print(f"ROLE: {role}")
        print(f"PROGRAM_ID: {prog_id if prog_id is not None else ''}")
        print(f"PROGRAM_NAME: {prog_name or ''}")


if __name__ == "__main__":
    main()