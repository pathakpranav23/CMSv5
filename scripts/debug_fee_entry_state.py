import os
import sys

# Ensure project root is on sys.path when running from scripts/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from cms_app import create_app, db
from cms_app.models import Program, FeeStructure
from cms_app.main.routes import FEE_COMPONENTS


def main():
    app = create_app()
    with app.app_context():
        print("db_uri=", app.config.get("SQLALCHEMY_DATABASE_URI"))
        prog = Program.query.filter(Program.program_name.ilike("%BCA%")).first()
        print("bca_program_id=", prog.program_id if prog else None)
        if not prog:
            print("BCA program not found")
            return
        rows = FeeStructure.query.filter_by(program_id_fk=prog.program_id, semester=1).all()
        print("rows_count=", len(rows))
        for r in rows:
            print("row:", (r.component_name or "").strip(), "amount=", float(r.amount or 0.0), "frozen=", bool(getattr(r, "is_frozen", False)))

        existing_map = { (r.component_name or "").strip(): float(r.amount or 0.0) for r in rows }
        print("component_check:")
        for comp in FEE_COMPONENTS:
            print(comp, "->", existing_map.get(comp, "MISSING"))


if __name__ == "__main__":
    main()