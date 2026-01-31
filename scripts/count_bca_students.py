
import os
import sys
from sqlalchemy import select, func

# Add project root to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from cms_app import create_app, db
from cms_app.models import Student, Program

def main():
    app = create_app()
    with app.app_context():
        # Find BCA Program
        # Using ilike for case-insensitive partial match
        bca_prog = db.session.execute(
            select(Program).filter(Program.program_name.ilike("%BCA%"))
        ).scalars().first()
        
        if not bca_prog:
            print("Program 'BCA' not found.")
            return

        print(f"Found Program: {bca_prog.program_name} (ID: {bca_prog.program_id})")
        
        # Count students for Semesters 3, 4, 5, 6
        semesters = [3, 4, 5, 6]
        
        print("\nStudent Counts:")
        print("-" * 20)
        
        total = 0
        for sem in semesters:
            count = db.session.scalar(
                select(func.count(Student.enrollment_no))
                .filter_by(program_id_fk=bca_prog.program_id, current_semester=sem)
            )
            print(f"Semester {sem}: {count}")
            total += count
            
        print("-" * 20)
        print(f"Total:      {total}")

if __name__ == "__main__":
    main()
