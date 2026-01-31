import sys
import os
import sqlite3
from datetime import datetime

# Add parent directory to path to import app (if needed, but here we use raw sqlite for migration)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../cms.db"))

def migrate_db():
    print(f"Connecting to database at: {DB_PATH}")
    if not os.path.exists(DB_PATH):
        print("Database file not found!")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Create 'trusts' table
    print("Checking 'trusts' table...")
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
        slogan VARCHAR(255),
        vision TEXT,
        mission TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)
    print("'trusts' table ensured.")

    # 2. Create 'institutes' table
    print("Checking 'institutes' table...")
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
        slogan VARCHAR(255),
        vision TEXT,
        mission TEXT,
        affiliation_body VARCHAR(64),
        aicte_code VARCHAR(32),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(trust_id_fk) REFERENCES trusts(trust_id)
    );
    """)
    print("'institutes' table ensured.")

    # 3. Add 'institute_id_fk' to 'programs' table
    print("Checking 'programs' table for 'institute_id_fk'...")
    cursor.execute("PRAGMA table_info(programs)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if "institute_id_fk" not in columns:
        print("Adding 'institute_id_fk' column to 'programs'...")
        try:
            cursor.execute("ALTER TABLE programs ADD COLUMN institute_id_fk INTEGER REFERENCES institutes(institute_id)")
            print("Added 'institute_id_fk' successfully.")
            
            # OPTIONAL: Create a default Trust and Institute if none exist, and link existing programs
            print("Creating default Trust and Institute for migration...")
            cursor.execute("SELECT COUNT(*) FROM trusts")
            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                    INSERT INTO trusts (trust_name, trust_code) 
                    VALUES ('Default Trust', 'DEF-TRUST')
                """)
                trust_id = cursor.lastrowid
                
                cursor.execute("""
                    INSERT INTO institutes (trust_id_fk, institute_name, institute_code) 
                    VALUES (?, 'Default Institute', 'DEF-INST')
                """, (trust_id,))
                inst_id = cursor.lastrowid
                
                # Link existing programs to this institute
                cursor.execute("UPDATE programs SET institute_id_fk = ?", (inst_id,))
                print(f"Linked existing programs to Default Institute (ID: {inst_id})")
                
        except Exception as e:
            print(f"Error adding 'institute_id_fk': {e}")
    else:
        print("'institute_id_fk' already exists.")

    conn.commit()
    conn.close()
    print("SaaS Architecture Migration complete.")

if __name__ == "__main__":
    migrate_db()
