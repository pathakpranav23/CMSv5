import os
import sys
from typing import List

# Ensure project root is on sys.path when running from scripts/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from cms_app import create_app, db
from cms_app.models import Program, FeeStructure
from sqlalchemy import select


FEE_COMPONENTS: List[str] = [
    "Tuition Fee",
    "Caution Money (Deposit)",
    "Gymkhana Cultural Activity Fee",
    "Library Fee",
    "Examination Fee",
    "Admission Fee",
    "Student Aid Fee",
    "University Sport Fee",
    "University Enrollment Fee",
    "Magazine Fee",
    "I Card Fee",
    "Laboratory Fee",
    "Campus Fund",
    "University Amenities Fee",
]

# Provided amounts for BCA Semester 1, in the same order as FEE_COMPONENTS
AMOUNTS: List[float] = [
    11500,
    500,
    150,
    200,
    500,
    50,
    200,
    50,
    100,
    0,
    100,
    600,
    300,
    0,
]


def upsert_bca_sem1_fees():
    app = create_app()
    with app.app_context():
        # Find or create BCA program
        prog = db.session.execute(
            select(Program).where(Program.program_name.ilike("BCA"))
        ).scalars().first()
        if not prog:
            prog = Program(program_name="BCA", program_duration_years=3)
            db.session.add(prog)
            db.session.flush()

        created = 0
        updated = 0

        for comp, amt in zip(FEE_COMPONENTS, AMOUNTS):
            row = db.session.execute(
                select(FeeStructure).filter_by(
                    program_id_fk=prog.program_id,
                    semester=1,
                    component_name=comp,
                )
            ).scalars().first()
            if not row:
                row = FeeStructure(
                    program_id_fk=prog.program_id,
                    semester=1,
                    component_name=comp,
                    amount=float(amt),
                )
                db.session.add(row)
                created += 1
            else:
                row.amount = float(amt)
                updated += 1
        db.session.commit()

        print(f"BCA Sem 1 fees upserted. created={created}, updated={updated}")


if __name__ == "__main__":
    upsert_bca_sem1_fees()
