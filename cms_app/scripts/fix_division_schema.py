
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

    # Get existing columns in divisions table
    cursor.execute("PRAGMA table_info(divisions)")
    columns = [row[1] for row in cursor.fetchall()]
    print(f"Current columns in 'divisions': {columns}")

    # Add 'medium_tag' column if missing
    if "medium_tag" not in columns:
        print("Adding 'medium_tag' column...")
        try:
            cursor.execute("ALTER TABLE divisions ADD COLUMN medium_tag TEXT")
            print("Added 'medium_tag' column successfully.")
        except Exception as e:
            print(f"Error adding 'medium_tag': {e}")
    else:
        print("'medium_tag' column already exists.")

    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate_db()
