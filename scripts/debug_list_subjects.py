import os
import sys

# Ensure project root is on sys.path when running from scripts/
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from cms_app import create_app
from cms_app.models import Program, Subject


def list_subjects(program_name: str, semester: int):
    app = create_app()
    with app.app_context():
        prog = Program.query.filter_by(program_name=program_name).first()
        if not prog:
            print(f"Program not found: {program_name}")
            return
        subs = (
            Subject.query
            .filter_by(program_id_fk=prog.program_id, semester=semester)
            .order_by(Subject.subject_name)
            .all()
        )
        print(f"Subjects for {program_name} Sem {semester}: count={len(subs)}")
        for s in subs:
            print(f"- {s.subject_name} (code={s.subject_code or '-'}, paper={s.paper_code or '-'})")


if __name__ == "__main__":
    list_subjects("BCom (English)", 3)
    list_subjects("BCom (English)", 5)
    list_subjects("BCom (Gujarati)", 3)
    list_subjects("BCom (Gujarati)", 5)