import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from cms_app import create_app, db
from cms_app.models import Student
from sqlalchemy import select, func, update


def main():
    app = create_app()
    with app.app_context():
        before_s3 = db.session.scalar(
            select(func.count()).select_from(Student).filter_by(current_semester=3)
        ) or 0
        before_s5 = db.session.scalar(
            select(func.count()).select_from(Student).filter_by(current_semester=5)
        ) or 0
        print(f"Before update: sem3={before_s3}, sem5={before_s5}")

        if before_s3 or before_s5:
            db.session.execute(
                update(Student)
                .where(Student.current_semester == 3)
                .values(current_semester=4)
            )
            db.session.execute(
                update(Student)
                .where(Student.current_semester == 5)
                .values(current_semester=6)
            )
            db.session.commit()

        after_s3 = db.session.scalar(
            select(func.count()).select_from(Student).filter_by(current_semester=3)
        ) or 0
        after_s5 = db.session.scalar(
            select(func.count()).select_from(Student).filter_by(current_semester=5)
        ) or 0
        after_s4 = db.session.scalar(
            select(func.count()).select_from(Student).filter_by(current_semester=4)
        ) or 0
        after_s6 = db.session.scalar(
            select(func.count()).select_from(Student).filter_by(current_semester=6)
        ) or 0

        print(f"After update: sem3={after_s3}, sem4={after_s4}, sem5={after_s5}, sem6={after_s6}")


if __name__ == "__main__":
    main()
