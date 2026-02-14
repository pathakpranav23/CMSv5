import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cms_app import create_app, db
from cms_app.models import Subject
from sqlalchemy import select

def check_subjects():
    app = create_app()
    with app.app_context():
        subjects = db.session.execute(
            select(Subject).where(Subject.program_id_fk == 1, Subject.semester == 4)
        ).scalars().all()
        print(f"Found {len(subjects)} subjects for BCA Semester 4")
        for s in subjects:
            print(f"ID: {s.subject_id}, Name: {s.subject_name}, Active: {s.is_active}")

if __name__ == "__main__":
    check_subjects()
