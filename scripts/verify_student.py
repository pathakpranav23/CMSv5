import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cms_app import create_app, db
from cms_app.models import Student
from sqlalchemy import select

def check_student():
    app = create_app()
    with app.app_context():
        student = db.session.execute(
            select(Student).filter_by(enrollment_no='5034240094')
        ).scalars().first()
        
        if student:
            print(f"Enrollment: {student.enrollment_no}")
            print(f"Name: {student.student_name} {student.surname}")
            print(f"Current Semester: {student.current_semester}")
            print(f"Active: {student.is_active}")
            print(f"Trust ID: {student.trust_id_fk}")
        else:
            print("Student not found.")

if __name__ == "__main__":
    check_student()
