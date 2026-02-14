import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cms_app import create_app, db
from cms_app.models import User, Student, Faculty
from sqlalchemy import select, func

def verify_trust_isolation():
    app = create_app()
    with app.app_context():
        # Check Students
        student_no_trust = db.session.execute(
            select(func.count(Student.enrollment_no)).where(
                Student.program_id_fk == 1,
                Student.current_semester == 4,
                Student.is_active == True,
                Student.trust_id_fk == None
            )
        ).scalar()
        
        # Check Faculty
        faculty_no_trust = db.session.execute(
            select(func.count(Faculty.faculty_id)).where(
                Faculty.program_id_fk == 1,
                Faculty.is_active == True,
                Faculty.trust_id_fk == None
            )
        ).scalar()
        
        # Check Users (associated with these students/faculty)
        # We'll just check all users who have a trust_id_fk=None and are not super admin
        users_no_trust = db.session.execute(
            select(User).where(
                User.trust_id_fk == None,
                User.is_super_admin == False
            )
        ).scalars().all()

        print(f"BCA Students without Trust ID: {student_no_trust}")
        print(f"BCA Faculty without Trust ID: {faculty_no_trust}")
        print(f"Non-SuperAdmin Users without Trust ID: {len(users_no_trust)}")
        for u in users_no_trust:
            print(f" - User: {u.username}, Role: {u.role}")

        faculty_no_trust_list = db.session.execute(
            select(Faculty).where(
                Faculty.program_id_fk == 1,
                Faculty.is_active == True,
                Faculty.trust_id_fk == None
            )
        ).scalars().all()
        for f in faculty_no_trust_list:
            print(f" - Faculty: {f.full_name}, EmpId: {f.emp_id}")

        # Sample check
        student = db.session.execute(
            select(Student).where(Student.program_id_fk == 1, Student.is_active == True).limit(1)
        ).scalars().first()
        if student:
            print(f"Sample Student {student.enrollment_no}: Trust ID {student.trust_id_fk}")
            user = db.session.execute(select(User).filter_by(user_id=student.user_id_fk)).scalars().first()
            if user:
                print(f"Associated User {user.username}: Trust ID {user.trust_id_fk}")

        faculty = db.session.execute(
            select(Faculty).where(Faculty.program_id_fk == 1, Faculty.is_active == True).limit(1)
        ).scalars().first()
        if faculty:
            print(f"Sample Faculty {faculty.emp_id}: Trust ID {faculty.trust_id_fk}")
            user = db.session.execute(select(User).filter_by(user_id=faculty.user_id_fk)).scalars().first()
            if user:
                print(f"Associated User {user.username}: Trust ID {user.trust_id_fk}")

if __name__ == "__main__":
    verify_trust_isolation()
