
import sqlite3
import os

DB_PATH = "cms.db"

def check_and_update_schema():
    if not os.path.exists(DB_PATH):
        print(f"Error: {DB_PATH} not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Tables and columns to check/add based on current models.py
    updates = {
        "users": [
            ("mobile", "VARCHAR(20)"),
            ("is_active", "BOOLEAN DEFAULT 1"),
            ("must_change_password", "BOOLEAN DEFAULT 0"),
            ("is_super_admin", "BOOLEAN DEFAULT 0"),
            ("trust_id_fk", "INTEGER"),
            ("preferred_lang", "VARCHAR(8)")
        ],
        "faculty": [
            ("photo_url", "VARCHAR(255)"),
            ("emp_id", "VARCHAR(32)"),
            ("date_of_joining", "DATE"),
            ("highest_qualification", "VARCHAR(64)"),
            ("experience_years", "FLOAT"),
            ("specialization", "VARCHAR(255)"),
            ("medium_expertise", "VARCHAR(32)"),
            ("extra_data", "TEXT"),
            ("trust_id_fk", "INTEGER"),
            ("is_active", "BOOLEAN DEFAULT 1")
        ],
        "students": [
            ("roll_no", "VARCHAR(20)"),
            ("gender", "VARCHAR(16)"),
            ("photo_url", "VARCHAR(255)"),
            ("permanent_address", "VARCHAR(255)"),
            ("current_semester", "INTEGER"),
            ("medium_tag", "VARCHAR(32)"),
            ("trust_id_fk", "INTEGER"),
            ("is_active", "BOOLEAN DEFAULT 1")
        ]
    }

    for table, columns in updates.items():
        print(f"\nChecking table '{table}'...")
        cursor.execute(f"PRAGMA table_info({table})")
        existing_columns = [row[1] for row in cursor.fetchall()]
        
        for col_name, col_type in columns:
            if col_name not in existing_columns:
                print(f"  Adding column '{col_name}' ({col_type})...")
                try:
                    cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}")
                    print(f"  ✅ Successfully added '{col_name}'.")
                except sqlite3.OperationalError as e:
                    print(f"  ❌ Error adding '{col_name}': {e}")
            else:
                print(f"  - Column '{col_name}' already exists.")

    conn.commit()
    conn.close()
    print("\nSchema update complete.")

if __name__ == "__main__":
    check_and_update_schema()
