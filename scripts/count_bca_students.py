import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cms_app import create_app, db
from cms_app.models import Student
from sqlalchemy import select, func

def count_students():
    app = create_app()
    with app.app_context():
        count = db.session.execute(
            select(func.count(Student.enrollment_no)).where(
                Student.program_id_fk == 1,
                Student.current_semester == 4,
                Student.is_active == True
            )
        ).scalar()
        print(f"Total active BCA Semester 4 students: {count}")

if __name__ == "__main__":
    count_students()
