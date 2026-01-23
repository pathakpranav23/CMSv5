
import sqlite3
import os

DB_PATH = os.path.join(os.getcwd(), 'cms.db')

def add_column_if_not_exists(cursor, table, column, definition):
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        print(f"Added column {column} to {table}")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print(f"Column {column} already exists in {table}")
        else:
            print(f"Error adding column {column} to {table}: {e}")

def fix_database():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Add created_at to fees_records
    add_column_if_not_exists(cursor, "fees_records", "created_at", "DATETIME")
    
    # Add other potentially missing columns for Phase 1 models if needed
    # (Timetable tables should be created by db.create_all() if they don't exist, which verify_startup.py does)
    
    conn.commit()
    conn.close()
    print("Database schema update complete.")

if __name__ == "__main__":
    fix_database()
