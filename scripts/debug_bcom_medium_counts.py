import os
import sys

# Ensure project root is on sys.path when running from scripts/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from cms_app import create_app, db
from cms_app.models import Program, Student
from sqlalchemy import select, func


def main():
    app = create_app()
    with app.app_context():
        # Find all BCom-related programs (generic or variants like English/Gujarati)
        bcom_programs = db.session.execute(
            select(Program)
            .where(Program.program_name.ilike('%BCOM%'))
            .order_by(Program.program_name)
        ).scalars().all()
        if not bcom_programs:
            print("No BCom programs found.")
            return

        prog_ids = [p.program_id for p in bcom_programs]

        def count_medium(tag: str) -> int:
            return db.session.execute(
                select(func.count()).select_from(Student).where(
                    Student.program_id_fk.in_(prog_ids),
                    Student.medium_tag == tag,
                )
            ).scalar_one()

        gujarati_count = count_medium('Gujarati')
        english_count = count_medium('English')
        # Also report students with 'General' or empty/None medium for awareness
        general_count = db.session.execute(
            select(func.count()).select_from(Student).where(
                Student.program_id_fk.in_(prog_ids),
                (Student.medium_tag == 'General') | (Student.medium_tag == '') | (Student.medium_tag.is_(None)),
            )
        ).scalar_one()

        total_bcom_students = db.session.execute(
            select(func.count()).select_from(Student).where(
                Student.program_id_fk.in_(prog_ids),
            )
        ).scalar_one()

        print("BCom Medium Counts")
        print("Programs considered:")
        for p in bcom_programs:
            print(f"- {p.program_id}: {p.program_name}")
        print("")
        print(f"Gujarati: {gujarati_count}")
        print(f"English: {english_count}")
        print(f"General/Unspecified: {general_count}")
        print(f"Total BCom students: {total_bcom_students}")


if __name__ == "__main__":
    main()
