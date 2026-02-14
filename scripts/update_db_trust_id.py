import sqlite3
import os

DB_PATH = "cms.db"

def check_and_update_schema():
    if not os.path.exists(DB_PATH):
        print(f"Error: {DB_PATH} not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Tables and columns to check/add
    updates = {
        "students": ["trust_id_fk"],
        "users": ["trust_id_fk"],
        "faculty": ["trust_id_fk", "is_active"]
    }

    column_types = {
        "trust_id_fk": "INTEGER",
        "is_active": "BOOLEAN DEFAULT 1"
    }

    for table, columns in updates.items():
        cursor.execute(f"PRAGMA table_info({table})")
        existing_columns = [row[1] for row in cursor.fetchall()]
        
        for column in columns:
            if column not in existing_columns:
                print(f"Adding column '{column}' to table '{table}'...")
                col_type = column_types.get(column, "INTEGER")
                try:
                    cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
                    print(f"Successfully added '{column}' to '{table}'.")
                except sqlite3.OperationalError as e:
                    print(f"Error adding column: {e}")
            else:
                print(f"Column '{column}' already exists in table '{table}'.")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    check_and_update_schema()
