from cms_app import create_app, db
from sqlalchemy import text


def column_exists(conn, table: str, column: str) -> bool:
    res = conn.execute(text(f"PRAGMA table_info('{table}')")).fetchall()
    return any(row[1] == column for row in res)


def table_exists(conn, table: str) -> bool:
    res = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name=:t"), {"t": table}).fetchone()
    return res is not None


def main():
    app = create_app()
    with app.app_context():
        conn = db.session.connection()
        added = []

        # Add elective-related columns to subjects
        if not column_exists(conn, "subjects", "is_elective"):
            conn.execute(text("ALTER TABLE subjects ADD COLUMN is_elective INTEGER DEFAULT 0"))
            added.append("subjects.is_elective")
        if not column_exists(conn, "subjects", "capacity"):
            conn.execute(text("ALTER TABLE subjects ADD COLUMN capacity INTEGER"))
            added.append("subjects.capacity")
        if not column_exists(conn, "subjects", "elective_group_id"):
            conn.execute(text("ALTER TABLE subjects ADD COLUMN elective_group_id TEXT"))
            added.append("subjects.elective_group_id")

        # Create student_subject_enrollments table if missing
        if not table_exists(conn, "student_subject_enrollments"):
            conn.execute(text(
                """
                CREATE TABLE student_subject_enrollments (
                    enrollment_id INTEGER PRIMARY KEY,
                    student_id_fk TEXT NOT NULL,
                    subject_id_fk INTEGER NOT NULL,
                    semester INTEGER,
                    division_id_fk INTEGER,
                    academic_year TEXT,
                    is_active INTEGER DEFAULT 1,
                    source TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
                """
            ))
            # Basic indexes for performance
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_sse_subject ON student_subject_enrollments(subject_id_fk)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_sse_student ON student_subject_enrollments(student_id_fk)"))
            added.append("student_subject_enrollments (table + indexes)")

        db.session.commit()
        print("Migration completed. Added:", ", ".join(added) if added else "none")


if __name__ == "__main__":
    main()