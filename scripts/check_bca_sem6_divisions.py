import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cms_app import create_app, db
from cms_app.models import Division, Program, Student
from sqlalchemy import select

app = create_app()


def check_sem6_divisions():
    with app.app_context():
        bca = db.session.execute(
            select(Program).filter(Program.program_name.like('%BCA%'))
        ).scalars().first()
        if not bca:
            print("BCA program not found")
            return

        print(f"Program: {bca.program_name} (ID: {bca.program_id})")

        divisions = db.session.execute(
            select(Division)
            .filter_by(program_id_fk=bca.program_id, semester=6)
            .order_by(Division.division_code)
        ).scalars().all()

        print("\nDivisions for Semester 6:")
        for d in divisions:
            count = db.session.execute(
                select(db.func.count(Student.enrollment_no))
                .filter(
                    Student.division_id_fk == d.division_id,
                    Student.current_semester == 6,
                    Student.is_active == True
                )
            ).scalar()
            print(f"  Division {d.division_code}: Capacity={d.capacity}, Students={count}, ID={d.division_id}")

        print("\nSample students per division (first 5 by roll_no):")
        for d in divisions:
            students = db.session.execute(
                select(Student)
                .filter(
                    Student.division_id_fk == d.division_id,
                    Student.current_semester == 6,
                    Student.is_active == True
                )
                .order_by(Student.roll_no)
                .limit(5)
            ).scalars().all()
            print(f"\nDivision {d.division_code}:")
            for s in students:
                print(f"  Roll {s.roll_no}: {s.full_name} ({s.enrollment_no})")


if __name__ == "__main__":
    check_sem6_divisions()

