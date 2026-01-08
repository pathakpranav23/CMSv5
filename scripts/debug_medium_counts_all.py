import os
import sys

# Ensure project root is on sys.path when running from scripts/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from cms_app import create_app
from cms_app.models import Program, Student


def main():
    app = create_app()
    with app.app_context():
        programs = Program.query.order_by(Program.program_name).all()
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
            english = Student.query.filter(Student.program_id_fk == pid, Student.medium_tag == 'English').count()
            gujarati = Student.query.filter(Student.program_id_fk == pid, Student.medium_tag == 'Gujarati').count()
            general = Student.query.filter(Student.program_id_fk == pid, Student.medium_tag == 'General').count()
            unspecified = Student.query.filter(Student.program_id_fk == pid).filter((Student.medium_tag == '') | (Student.medium_tag.is_(None))).count()
            total = Student.query.filter(Student.program_id_fk == pid).count()

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