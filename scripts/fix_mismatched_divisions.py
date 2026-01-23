import os
import sys
from sqlalchemy import select

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from cms_app import create_app, db
from cms_app.models import Student, Division

def main():
    app = create_app()
    with app.app_context():
        print("Checking for mismatched divisions...")
        
        # Select students with divisions
        stmt = select(Student, Division).join(Division, Student.division_id_fk == Division.division_id)
        results = db.session.execute(stmt).all()
        
        count = 0
        for student, division in results:
            if student.current_semester != division.semester:
                print(f"Mismatch: Student {student.enrollment_no} (Sem {student.current_semester}) in Division {division.division_code} (Sem {division.semester}). Unassigning.")
                student.division_id_fk = None
                count += 1
                
        if count > 0:
            db.session.commit()
            print(f"Fixed {count} students.")
        else:
            print("No mismatches found.")

if __name__ == "__main__":
    main()
