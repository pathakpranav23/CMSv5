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
        # Find all BCom-related programs (generic or variants like English/Gujarati)
        bcom_programs = (
            Program.query
            .filter(Program.program_name.ilike('%BCOM%'))
            .order_by(Program.program_name)
            .all()
        )
        if not bcom_programs:
            print("No BCom programs found.")
            return

        prog_ids = [p.program_id for p in bcom_programs]

        def count_medium(tag: str) -> int:
            return (
                Student.query
                .filter(Student.program_id_fk.in_(prog_ids), Student.medium_tag == tag)
                .count()
            )

        gujarati_count = count_medium('Gujarati')
        english_count = count_medium('English')
        # Also report students with 'General' or empty/None medium for awareness
        general_count = (
            Student.query
            .filter(Student.program_id_fk.in_(prog_ids))
            .filter((Student.medium_tag == 'General') | (Student.medium_tag == '') | (Student.medium_tag.is_(None)))
            .count()
        )

        total_bcom_students = (
            Student.query
            .filter(Student.program_id_fk.in_(prog_ids))
            .count()
        )

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