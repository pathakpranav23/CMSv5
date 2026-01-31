
import sqlite3
import os

# Path to the database
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../cms.db"))

def migrate_db():
    print(f"Connecting to database at: {DB_PATH}")
    if not os.path.exists(DB_PATH):
        print("Database file not found!")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get existing columns in programs table
    cursor.execute("PRAGMA table_info(programs)")
    columns = [row[1] for row in cursor.fetchall()]
    print(f"Current columns in 'programs': {columns}")

    # Add 'medium' column if missing
    if "medium" not in columns:
        print("Adding 'medium' column...")
        try:
            cursor.execute("ALTER TABLE programs ADD COLUMN medium TEXT DEFAULT 'English'")
            print("Added 'medium' column successfully.")
        except Exception as e:
            print(f"Error adding 'medium': {e}")
    else:
        print("'medium' column already exists.")

    # Add 'program_code' column if missing
    if "program_code" not in columns:
        print("Adding 'program_code' column...")
        try:
            cursor.execute("ALTER TABLE programs ADD COLUMN program_code TEXT")
            print("Added 'program_code' column successfully.")
        except Exception as e:
            print(f"Error adding 'program_code': {e}")
    else:
        print("'program_code' column already exists.")

    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate_db()
