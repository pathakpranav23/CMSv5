
from cms_app import create_app, db
from cms_app.models import Program, Student, Division
from sqlalchemy import select

app = create_app()

def find_roll_1():
    with app.app_context():
        # Find BCA Program
        bca = db.session.execute(select(Program).filter(Program.program_name.ilike('%BCA%'))).scalars().first()
        if not bca:
            print("BCA Program not found")
            return

        print(f"Program: {bca.program_name} (ID: {bca.program_id})")

        # Find students in Sem 6
        students = db.session.execute(
            select(Student)
            .filter_by(program_id_fk=bca.program_id, current_semester=6)
        ).scalars().all()

        print(f"Total Students in Sem 6: {len(students)}")

        # Check for Roll No 1
        roll_1_students = [s for s in students if str(s.roll_no).strip() == '1']
        
        if roll_1_students:
            for s in roll_1_students:
                print(f"FOUND ROLL NO 1: {s.full_name} (Enrollment: {s.enrollment_no}, Div: {s.division_id_fk})")
        else:
            print("No student found with Roll No 1.")
            
        # List first 10 students sorted by current default (Enrollment)
        print("\n--- First 10 Students (Sorted by Enrollment) ---")
        students_by_enrollment = sorted(students, key=lambda x: x.enrollment_no)
        for s in students_by_enrollment[:10]:
            print(f"Roll: {s.roll_no} | Enr: {s.enrollment_no} | Name: {s.full_name}")

        # List first 10 students sorted by Roll No (Numeric)
        print("\n--- First 10 Students (Sorted by Roll No) ---")
        def get_roll_int(s):
            try:
                return int(s.roll_no)
            except:
                return 999999
        
        students_by_roll = sorted(students, key=get_roll_int)
        for s in students_by_roll[:10]:
            print(f"Roll: {s.roll_no} | Enr: {s.enrollment_no} | Name: {s.full_name}")

if __name__ == "__main__":
    find_roll_1()
