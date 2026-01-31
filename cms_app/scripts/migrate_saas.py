import sys
import os
import sqlite3

# Add parent directory to path to import app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../cms.db"))

def migrate_saas_architecture():
    print(f"Connecting to database at: {DB_PATH}")
    if not os.path.exists(DB_PATH):
        print("Database file not found!")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # 1. Create Trusts Table
        print("Creating 'trusts' table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trusts (
                trust_id INTEGER PRIMARY KEY,
                trust_name VARCHAR(128) NOT NULL,
                trust_code VARCHAR(32) UNIQUE,
                address TEXT,
                contact_email VARCHAR(128),
                contact_phone VARCHAR(32),
                website VARCHAR(128),
                logo_path VARCHAR(255),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 2. Create Institutes Table
        print("Creating 'institutes' table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS institutes (
                institute_id INTEGER PRIMARY KEY,
                trust_id_fk INTEGER,
                institute_name VARCHAR(128) NOT NULL,
                institute_code VARCHAR(32) UNIQUE,
                address TEXT,
                contact_email VARCHAR(128),
                contact_phone VARCHAR(32),
                website VARCHAR(128),
                logo_path VARCHAR(255),
                affiliation_body VARCHAR(64),
                aicte_code VARCHAR(32),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(trust_id_fk) REFERENCES trusts(trust_id)
            )
        """)

        # 3. Add institute_id_fk to Programs Table
        # Check if column exists
        cursor.execute("PRAGMA table_info(programs)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if "institute_id_fk" not in columns:
            print("Adding 'institute_id_fk' to 'programs' table...")
            cursor.execute("ALTER TABLE programs ADD COLUMN institute_id_fk INTEGER REFERENCES institutes(institute_id)")
        else:
            print("'institute_id_fk' already exists in 'programs'.")

        # 4. Create Default Data (Migration Logic)
        # Create a default Trust and Institute for existing data
        print("Checking for existing data...")
        cursor.execute("SELECT count(*) FROM trusts")
        if cursor.fetchone()[0] == 0:
            print("Creating default Trust and Institute...")
            cursor.execute("INSERT INTO trusts (trust_name, trust_code) VALUES ('Default Trust', 'DEFAULT')")
            trust_id = cursor.lastrowid
            
            cursor.execute("INSERT INTO institutes (trust_id_fk, institute_name, institute_code) VALUES (?, 'Main Campus', 'MAIN')", (trust_id,))
            institute_id = cursor.lastrowid
            
            # Link existing programs to this institute
            print(f"Linking all existing programs to Institute ID {institute_id}...")
            cursor.execute("UPDATE programs SET institute_id_fk = ? WHERE institute_id_fk IS NULL", (institute_id,))
            
        conn.commit()
        print("Migration successful.")

    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_saas_architecture()
