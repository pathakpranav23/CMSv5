import sys
import os
import sqlite3

# Add parent directory to path to import app (if needed, but here we use raw sqlite for migration)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../cms.db"))

def add_branding_columns():
    print(f"Connecting to database at: {DB_PATH}")
    if not os.path.exists(DB_PATH):
        print("Database file not found!")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Add columns to 'trusts' table
    print("Checking 'trusts' table columns...")
    cursor.execute("PRAGMA table_info(trusts)")
    columns = [row[1] for row in cursor.fetchall()]
    
    new_cols = ['slogan', 'vision', 'mission']
    for col in new_cols:
        if col not in columns:
            print(f"Adding '{col}' to trusts...")
            try:
                cursor.execute(f"ALTER TABLE trusts ADD COLUMN {col} TEXT")
            except Exception as e:
                print(f"Error adding {col}: {e}")
        else:
             print(f"'{col}' already exists in trusts.")

    # 2. Add columns to 'institutes' table
    print("Checking 'institutes' table columns...")
    cursor.execute("PRAGMA table_info(institutes)")
    columns = [row[1] for row in cursor.fetchall()]
    
    for col in new_cols:
        if col not in columns:
            print(f"Adding '{col}' to institutes...")
            try:
                cursor.execute(f"ALTER TABLE institutes ADD COLUMN {col} TEXT")
            except Exception as e:
                print(f"Error adding {col}: {e}")
        else:
             print(f"'{col}' already exists in institutes.")

    conn.commit()
    conn.close()
    print("Branding columns migration complete.")

if __name__ == "__main__":
    add_branding_columns()
