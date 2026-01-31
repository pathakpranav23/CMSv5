
from cms_app import create_app, db
from cms_app.models import Student, Program
from sqlalchemy import select, or_

app = create_app()

def find_mahida():
    with app.app_context():
        # Find BCA Program
        bca = db.session.execute(select(Program).filter(Program.program_name.ilike('%BCA%'))).scalars().first()
        if not bca:
            print("BCA Program not found")
            return

        print(f"Searching in Program: {bca.program_name}")

        # Search for Mahida in First Name or Last Name
        students = db.session.execute(
            select(Student)
            .filter(Student.program_id_fk == bca.program_id)
            .filter(
                or_(
                    Student.first_name.ilike('%Mahida%'),
                    Student.last_name.ilike('%Mahida%'),
                    Student.father_name.ilike('%Mahida%')
                )
            )
        ).scalars().all()
        
        if students:
            print(f"\nFound {len(students)} student(s) matching 'Mahida':")
            for s in students:
                print(f"- {s.full_name} (Roll: {s.roll_no}, Enr: {s.enrollment_no}, Sem: {s.current_semester}, DivID: {s.division_id_fk})")
        else:
            print("No student found matching 'Mahida' in BCA.")

if __name__ == "__main__":
    find_mahida()
