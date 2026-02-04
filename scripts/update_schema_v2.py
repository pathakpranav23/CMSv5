
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "cms.db")

def upgrade():
    print(f"Connecting to {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Add must_change_password to users
    try:
        # 1 = True in SQLite
        cursor.execute("ALTER TABLE users ADD COLUMN must_change_password BOOLEAN DEFAULT 0")
        print("Added must_change_password to users.")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("Column must_change_password already exists.")
        else:
            print(f"Error adding must_change_password: {e}")

    # 2. Add photo_url to faculty
    try:
        cursor.execute("ALTER TABLE faculty ADD COLUMN photo_url VARCHAR(255)")
        print("Added photo_url to faculty.")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("Column photo_url already exists.")
        else:
            print(f"Error adding photo_url: {e}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    upgrade()
