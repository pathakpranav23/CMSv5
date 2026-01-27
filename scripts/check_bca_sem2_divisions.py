
import sys
import os

# Add the project root to the python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cms_app import create_app, db
from cms_app.models import Division, Program, Student
from sqlalchemy import select

app = create_app()

def check_divisions():
    with app.app_context():
        # Find BCA program
        bca = db.session.execute(select(Program).filter(Program.program_name.like('%BCA%'))).scalars().first()
        if not bca:
            print("BCA program not found")
            return

        print(f"Program: {bca.program_name} (ID: {bca.program_id})")
        
        # Check Semester 2 Divisions
        divisions = db.session.execute(
            select(Division)
            .filter_by(program_id_fk=bca.program_id, semester=2)
            .order_by(Division.division_code)
        ).scalars().all()

        print("\nDivisions for Semester 2:")
        for d in divisions:
            # Count students in this division
            count = db.session.execute(
                select(db.func.count(Student.enrollment_no))
                .filter_by(division_id_fk=d.division_id)
            ).scalar()
            print(f"  Division {d.division_code}: Capacity={d.capacity}, Students={count}, ID={d.division_id}")

if __name__ == '__main__':
    check_divisions()
