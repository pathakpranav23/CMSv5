
import sys
import os
from sqlalchemy import select, func

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cms_app import create_app, db
from cms_app.models import Subject, Program

def check_bca_subjects():
    app = create_app()
    with app.app_context():
        # Find BCA Program
        bca = db.session.execute(select(Program).filter_by(program_name="BCA")).scalars().first()
        if not bca:
            print("BCA Program not found!")
            return

        print(f"Checking subjects for BCA (ID: {bca.program_id})...")
        
        # Check semesters 2, 4, 6
        for sem in [2, 4, 6]:
            subjects = db.session.execute(
                select(Subject)
                .filter_by(program_id_fk=bca.program_id, semester=sem)
            ).scalars().all()
            
            print(f"Semester {sem}: Found {len(subjects)} subjects.")
            for s in subjects:
                print(f"  - [{s.subject_code}] {s.subject_name}")

if __name__ == "__main__":
    check_bca_subjects()
