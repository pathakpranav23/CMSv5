import os
import sys
from sqlalchemy import text

# Ensure project root is on sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from cms_app import create_app, db

def column_exists(conn, table: str, column: str) -> bool:
    res = conn.execute(text(f"PRAGMA table_info('{table}')")).fetchall()
    return any(row[1] == column for row in res)

def main():
    app = create_app()
    with app.app_context():
        conn = db.session.connection()
        added = []

        # Users
        if not column_exists(conn, "users", "email"):
            conn.execute(text("ALTER TABLE users ADD COLUMN email VARCHAR(128)"))
            added.append("users.email")
        if not column_exists(conn, "users", "is_active"):
            conn.execute(text("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT 1"))
            added.append("users.is_active")
        if not column_exists(conn, "users", "program_id_fk"):
            conn.execute(text("ALTER TABLE users ADD COLUMN program_id_fk INTEGER REFERENCES programs(program_id)"))
            added.append("users.program_id_fk")

        # CourseAssignment
        if not column_exists(conn, "course_assignments", "is_active"):
            conn.execute(text("ALTER TABLE course_assignments ADD COLUMN is_active BOOLEAN DEFAULT 1"))
            conn.execute(text("UPDATE course_assignments SET is_active=1 WHERE is_active IS NULL"))
            added.append("course_assignments.is_active")
        if not column_exists(conn, "course_assignments", "role"):
            conn.execute(text("ALTER TABLE course_assignments ADD COLUMN role VARCHAR(16) DEFAULT 'primary'"))
            added.append("course_assignments.role")
        if not column_exists(conn, "course_assignments", "academic_year"):
            conn.execute(text("ALTER TABLE course_assignments ADD COLUMN academic_year VARCHAR(16)"))
            added.append("course_assignments.academic_year")

        # Faculty
        if not column_exists(conn, "faculty", "emp_id"):
            conn.execute(text("ALTER TABLE faculty ADD COLUMN emp_id VARCHAR(32)"))
            added.append("faculty.emp_id")
        if not column_exists(conn, "faculty", "date_of_joining"):
            conn.execute(text("ALTER TABLE faculty ADD COLUMN date_of_joining DATE"))
            added.append("faculty.date_of_joining")
        if not column_exists(conn, "faculty", "highest_qualification"):
            conn.execute(text("ALTER TABLE faculty ADD COLUMN highest_qualification VARCHAR(64)"))
            added.append("faculty.highest_qualification")
        if not column_exists(conn, "faculty", "experience_years"):
            conn.execute(text("ALTER TABLE faculty ADD COLUMN experience_years FLOAT"))
            added.append("faculty.experience_years")
        if not column_exists(conn, "faculty", "specialization"):
            conn.execute(text("ALTER TABLE faculty ADD COLUMN specialization VARCHAR(255)"))
            added.append("faculty.specialization")
        if not column_exists(conn, "faculty", "extra_data"):
            conn.execute(text("ALTER TABLE faculty ADD COLUMN extra_data TEXT"))
            added.append("faculty.extra_data")

        # Students
        if not column_exists(conn, "students", "email"):
            conn.execute(text("ALTER TABLE students ADD COLUMN email VARCHAR(128)"))
            added.append("students.email")
        if not column_exists(conn, "students", "gender"):
            conn.execute(text("ALTER TABLE students ADD COLUMN gender VARCHAR(16)"))
            added.append("students.gender")
        if not column_exists(conn, "students", "photo_url"):
            conn.execute(text("ALTER TABLE students ADD COLUMN photo_url VARCHAR(255)"))
            added.append("students.photo_url")
        if not column_exists(conn, "students", "permanent_address"):
            conn.execute(text("ALTER TABLE students ADD COLUMN permanent_address VARCHAR(255)"))
            added.append("students.permanent_address")
        if not column_exists(conn, "students", "current_semester"):
            conn.execute(text("ALTER TABLE students ADD COLUMN current_semester INTEGER"))
            added.append("students.current_semester")
        if not column_exists(conn, "students", "medium_tag"):
            conn.execute(text("ALTER TABLE students ADD COLUMN medium_tag VARCHAR(32)"))
            added.append("students.medium_tag")
        
        # Subjects
        if not column_exists(conn, "subjects", "medium_tag"):
            conn.execute(text("ALTER TABLE subjects ADD COLUMN medium_tag VARCHAR(32)"))
            added.append("subjects.medium_tag")

        # Attendance
        if not column_exists(conn, "attendance", "period_no"):
            conn.execute(text("ALTER TABLE attendance ADD COLUMN period_no INTEGER"))
            added.append("attendance.period_no")

        # Announcements
        if not column_exists(conn, "announcements", "updated_at"):
            conn.execute(text("ALTER TABLE announcements ADD COLUMN updated_at DATETIME"))
            # Set default value for existing rows to current timestamp or created_at
            conn.execute(text("UPDATE announcements SET updated_at = created_at WHERE updated_at IS NULL"))
            added.append("announcements.updated_at")

        # FeePayments
        if not column_exists(conn, "fee_payments", "payment_date"):
            conn.execute(text("ALTER TABLE fee_payments ADD COLUMN payment_date DATE"))
            # Set default value for existing rows to created_at date
            conn.execute(text("UPDATE fee_payments SET payment_date = date(created_at) WHERE payment_date IS NULL"))
            added.append("fee_payments.payment_date")
            
        if not column_exists(conn, "announcements", "actor_user_id_fk"):
            conn.execute(text("ALTER TABLE announcements ADD COLUMN actor_user_id_fk INTEGER REFERENCES users(user_id)"))
            # Try to migrate data from created_by if it exists
            if column_exists(conn, "announcements", "created_by"):
                conn.execute(text("UPDATE announcements SET actor_user_id_fk = created_by WHERE created_by IS NOT NULL"))
            added.append("announcements.actor_user_id_fk")

        db.session.commit()
        print("Migration completed. Added:", ", ".join(added) if added else "none")

if __name__ == "__main__":
    main()
