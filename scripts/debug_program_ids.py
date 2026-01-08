import os
import sys

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from cms_app import create_app
from cms_app.models import Program


def main():
    app = create_app()
    with app.app_context():
        progs = Program.query.order_by(Program.program_name).all()
        for p in progs:
            print(f"{p.program_id}: {p.program_name}")


if __name__ == "__main__":
    main()