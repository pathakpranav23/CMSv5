import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'cms.db')

def inspect_db():
    print(f"Connecting to: {DB_PATH}")
    if not os.path.exists(DB_PATH):
        print("DB file does not exist!")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("Tables found:", [t[0] for t in tables])
    
    conn.close()

if __name__ == "__main__":
    inspect_db()
