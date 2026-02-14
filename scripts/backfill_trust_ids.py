import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cms_app import create_app, db
from cms_app.models import User, Student, Faculty, Program
from sqlalchemy import select

def backfill_trust_ids():
    app = create_app()
    with app.app_context():
        print("--- Backfilling Trust IDs ---")
        
        # 1. Backfill Users
        users = db.session.execute(
            select(User).where(User.trust_id_fk == None, User.is_super_admin == False)
        ).scalars().all()
        for user in users:
            if user.program_id_fk:
                program = db.session.get(Program, user.program_id_fk)
                if program:
                    user.trust_id_fk = program.institute.trust_id_fk
                    print(f"Updated User {user.username} to Trust {user.trust_id_fk}")
            elif user.username in ['Principal', 'Admin']:
                # Assign default users to Trust 1 / Program 1
                user.trust_id_fk = 1
                user.program_id_fk = 1
                print(f"Updated Default User {user.username} to Trust 1, Program 1")
            else:
                # If no program, check if linked to a student or faculty
                student = db.session.execute(select(Student).filter_by(user_id_fk=user.user_id)).scalars().first()
                if student and student.trust_id_fk:
                    user.trust_id_fk = student.trust_id_fk
                    print(f"Updated User {user.username} (from Student) to Trust {user.trust_id_fk}")
                else:
                    faculty = db.session.execute(select(Faculty).filter_by(user_id_fk=user.user_id)).scalars().first()
                    if faculty and faculty.trust_id_fk:
                        user.trust_id_fk = faculty.trust_id_fk
                        print(f"Updated User {user.username} (from Faculty) to Trust {user.trust_id_fk}")

        # 2. Backfill Students
        students = db.session.execute(
            select(Student).where(Student.trust_id_fk == None)
        ).scalars().all()
        for student in students:
            if student.program_id_fk:
                program = db.session.get(Program, student.program_id_fk)
                if program:
                    student.trust_id_fk = program.institute.trust_id_fk
                    print(f"Updated Student {student.enrollment_no} to Trust {student.trust_id_fk}")

        # 3. Backfill Faculty
        faculty_list = db.session.execute(
            select(Faculty).where(Faculty.trust_id_fk == None)
        ).scalars().all()
        for faculty in faculty_list:
            if faculty.program_id_fk:
                program = db.session.get(Program, faculty.program_id_fk)
                if program:
                    faculty.trust_id_fk = program.institute.trust_id_fk
                    print(f"Updated Faculty {faculty.full_name} to Trust {faculty.trust_id_fk}")

        try:
            db.session.commit()
            print("--- SUCCESS ---")
        except Exception as e:
            db.session.rollback()
            print(f"--- ERROR: {e} ---")

if __name__ == "__main__":
    backfill_trust_ids()
