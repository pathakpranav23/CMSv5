
import sys
import os
import sqlite3

# Add project root to path
sys.path.append(os.getcwd())

def migrate_subject_types():
    db_path = os.path.join(os.getcwd(), "cms.db")
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check columns
        cursor.execute("PRAGMA table_info(subject_types)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if "type_code" in columns and "type_name" in columns:
            print("Found both type_code and type_name columns. Migrating data...")
            
            # Update type_name from type_code where type_name is NULL
            cursor.execute("UPDATE subject_types SET type_name = type_code WHERE type_name IS NULL")
            affected = cursor.rowcount
            print(f"Migrated {affected} rows.")
            
            conn.commit()
        else:
            print("Columns missing. Available:", columns)

    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_subject_types()
