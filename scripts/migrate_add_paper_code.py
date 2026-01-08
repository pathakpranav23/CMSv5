import sqlite3
import os
from contextlib import closing


def column_exists(conn, table, column):
    with closing(conn.cursor()) as cur:
        cur.execute(f"PRAGMA table_info({table})")
        columns = [row[1] for row in cur.fetchall()]
        return column in columns


def migrate(db_path="cms.db"):
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database file not found: {db_path}")

    with closing(sqlite3.connect(db_path)) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        if column_exists(conn, "subjects", "paper_code"):
            print("Column 'paper_code' already exists on 'subjects'. Skipping.")
            return

        print("Adding 'paper_code' column to 'subjects' table...")
        with closing(conn.cursor()) as cur:
            cur.execute("ALTER TABLE subjects ADD COLUMN paper_code TEXT")
        conn.commit()
        print("Migration completed: 'paper_code' added.")


if __name__ == "__main__":
    migrate()