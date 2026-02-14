import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cms_app import create_app, db
from cms_app.models import StudentSubjectEnrollment, Student
from sqlalchemy import select

def check_enrollments():
    app = create_app()
    with app.app_context():
        # Check a sample student
        sample_enroll = '5034240094'
        enrolls = db.session.execute(
            select(StudentSubjectEnrollment).filter_by(student_id_fk=sample_enroll, academic_year='2025-26')
        ).scalars().all()
        
        print(f"Enrollments for student {sample_enroll}: {len(enrolls)}")
        for e in enrolls:
            print(f"Subject ID: {e.subject_id_fk}, Semester: {e.semester}, Active: {e.is_active}")

if __name__ == "__main__":
    check_enrollments()
