import os
import sys
from datetime import datetime

# Ensure project root is on sys.path when running from scripts/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from cms_app import create_app, db
from cms_app.models import Program, FeeStructure
from cms_app.main.routes import FEE_COMPONENTS, _slugify_component
from sqlalchemy import select


def main():
    app = create_app()
    with app.app_context():
        programs = db.session.execute(
            select(Program).order_by(Program.program_name.asc())
        ).scalars().all()
        total_created = 0
        for p in programs:
            # Assume up to 8 semesters (2 per year) unless program specifies fewer
            try:
                years = int(getattr(p, "program_duration_years", 3) or 3)
            except Exception:
                years = 3
            max_sem = max(2 * years, 2)

            for s in range(1, max_sem + 1):
                existing_rows = db.session.execute(
                    select(FeeStructure).filter_by(program_id_fk=p.program_id, semester=s)
                ).scalars().all()
                existing_norms = { _slugify_component((r.component_name or "").strip()) for r in existing_rows }
                for comp in FEE_COMPONENTS:
                    norm = _slugify_component(comp)
                    if norm not in existing_norms:
                        row = FeeStructure(
                            program_id_fk=p.program_id,
                            semester=s,
                            component_name=comp,
                            amount=0.0,
                            is_active=True,
                            updated_at=datetime.utcnow(),
                        )
                        db.session.add(row)
                        total_created += 1
        db.session.commit()
        print(f"Seeded fee heads across programs/semesters. created={total_created}")


if __name__ == "__main__":
    main()
