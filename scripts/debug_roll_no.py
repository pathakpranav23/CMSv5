
import sys
import os

# Add the project root to the python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cms_app import create_app, db
from cms_app.models import Student
from sqlalchemy import select

app = create_app()

def check_student_roll():
    with app.app_context():
        # Check specific student mentioned by user
        enrollment = "5034250004"
        student = db.session.get(Student, enrollment)
        
        if student:
            print(f"Student: {student.first_name} {student.last_name}")
            print(f"Enrollment: {student.enrollment_no}")
            print(f"Roll No in DB: {student.roll_no}")
            print(f"Division ID: {student.division_id_fk}")
        else:
            print(f"Student with enrollment {enrollment} not found!")

if __name__ == '__main__':
    check_student_roll()
