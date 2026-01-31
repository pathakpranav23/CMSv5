import sys
import os
import sqlite3

# Add parent directory to path to import app (if needed, but here we use raw sqlite for migration)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../cms.db"))

def update_default_trust():
    print(f"Connecting to database at: {DB_PATH}")
    if not os.path.exists(DB_PATH):
        print("Database file not found!")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Update the Trust Information
    print("Updating Trust Information...")
    trust_name = "Shree Balvant Parekh Education Trust - Mahuva"
    trust_code = "SBPET-MAHUVA"
    logo_path = "logo.png" 
    # Refined Slogan: "Believe to Progress" (B & P for Balvant Parekh)
    slogan = "Believe to Progress" 
    
    # Update the first trust found
    cursor.execute("SELECT trust_id FROM trusts LIMIT 1")
    row = cursor.fetchone()
    
    if row:
        trust_id = row[0]
        cursor.execute("""
            UPDATE trusts 
            SET trust_name = ?, 
                trust_code = ?, 
                logo_path = ?,
                slogan = ?
            WHERE trust_id = ?
        """, (trust_name, trust_code, logo_path, slogan, trust_id))
        print(f"Updated Trust ID {trust_id} with new slogan '{slogan}'.")
    else:
        cursor.execute("""
            INSERT INTO trusts (trust_name, trust_code, logo_path, slogan) 
            VALUES (?, ?, ?, ?)
        """, (trust_name, trust_code, logo_path, slogan))
        print("Created new Trust record.")

    # 2. Update the Institute Information
    # Refined Name: "The Group of Parekh Colleges" (User Request)
    institute_name = "The Group of Parekh Colleges"
    institute_code = "PAREKH-GRP"

    # Update the first institute found (previously 'Parekh College' or 'Default Institute')
    cursor.execute("SELECT institute_id FROM institutes LIMIT 1")
    inst_row = cursor.fetchone()
    if inst_row:
         cursor.execute("""
            UPDATE institutes 
            SET institute_name = ?, 
                institute_code = ?
            WHERE institute_id = ?
        """, (institute_name, institute_code, inst_row[0]))
         print(f"Updated Institute to '{institute_name}'.")

    conn.commit()
    conn.close()
    print("Trust and Institute Information Update complete.")

if __name__ == "__main__":
    update_default_trust()
