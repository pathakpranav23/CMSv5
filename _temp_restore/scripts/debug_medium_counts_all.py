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
        programs = db.session.execute(
            select(Program).order_by(Program.program_name)
        ).scalars().all()
        if not programs:
            print("No programs found.")
            return

        overall = {
            "English": 0,
            "Gujarati": 0,
            "General": 0,
            "Unspecified": 0,  # empty string or NULL
            "Total": 0,
        }

        print("Medium Counts — All Programs")
        for p in programs:
            pid = p.program_id
            name = p.program_name
            english = db.session.execute(
                select(func.count()).select_from(Student).where(
                    Student.program_id_fk == pid,
                    Student.medium_tag == 'English',
                )
            ).scalar_one()
            gujarati = db.session.execute(
                select(func.count()).select_from(Student).where(
                    Student.program_id_fk == pid,
                    Student.medium_tag == 'Gujarati',
                )
            ).scalar_one()
            general = db.session.execute(
                select(func.count()).select_from(Student).where(
                    Student.program_id_fk == pid,
                    Student.medium_tag == 'General',
                )
            ).scalar_one()
            unspecified = db.session.execute(
                select(func.count()).select_from(Student).where(
                    Student.program_id_fk == pid,
                    (Student.medium_tag == '') | (Student.medium_tag.is_(None)),
                )
            ).scalar_one()
            total = db.session.execute(
                select(func.count()).select_from(Student).where(
                    Student.program_id_fk == pid,
                )
            ).scalar_one()

            print(f"- {name}: English={english}, Gujarati={gujarati}, General={general}, Unspecified={unspecified}, Total={total}")

            overall["English"] += english
            overall["Gujarati"] += gujarati
            overall["General"] += general
            overall["Unspecified"] += unspecified
            overall["Total"] += total

        print("")
        print("Overall Totals:")
        print(f"English: {overall['English']}")
        print(f"Gujarati: {overall['Gujarati']}")
        print(f"General: {overall['General']}")
        print(f"Unspecified: {overall['Unspecified']}")
        print(f"Total: {overall['Total']}")


if __name__ == "__main__":
    main()
