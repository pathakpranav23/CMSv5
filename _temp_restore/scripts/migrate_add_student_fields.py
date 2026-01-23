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

        # students.gender
        if not column_exists(conn, "students", "gender"):
            conn.execute(text("ALTER TABLE students ADD COLUMN gender TEXT"))
            added.append("students.gender")

        # students.photo_url
        if not column_exists(conn, "students", "photo_url"):
            conn.execute(text("ALTER TABLE students ADD COLUMN photo_url TEXT"))
            added.append("students.photo_url")

        # students.permanent_address
        if not column_exists(conn, "students", "permanent_address"):
            conn.execute(text("ALTER TABLE students ADD COLUMN permanent_address TEXT"))
            added.append("students.permanent_address")

        db.session.commit()
        print("Migration completed. Added columns:", ", ".join(added) if added else "none")


if __name__ == "__main__":
    main()