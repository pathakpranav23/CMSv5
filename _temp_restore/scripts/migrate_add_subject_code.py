from cms_app import create_app, db
from sqlalchemy import text


def column_exists(conn, table: str, column: str) -> bool:
    res = conn.execute(text(f"PRAGMA table_info('{table}')")).fetchall()
    return any(row[1] == column for row in res)


def main():
    app = create_app()
    with app.app_context():
        conn = db.session.connection()
        added = []

        # subjects.subject_code
        if not column_exists(conn, "subjects", "subject_code"):
            conn.execute(text("ALTER TABLE subjects ADD COLUMN subject_code TEXT"))
            added.append("subjects.subject_code")

        db.session.commit()
        print("Migration completed. Added columns:", ", ".join(added) if added else "none")


if __name__ == "__main__":
    main()