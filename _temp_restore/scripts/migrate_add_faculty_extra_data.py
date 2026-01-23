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

        # faculty.extra_data
        if not column_exists(conn, "faculty", "extra_data"):
            conn.execute(text("ALTER TABLE faculty ADD COLUMN extra_data TEXT"))
            added.append("faculty.extra_data")

        db.session.commit()
        print("Migration completed. Added columns:", ", ".join(added) if added else "none")


if __name__ == "__main__":
    main()