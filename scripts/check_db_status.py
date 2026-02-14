
import sqlite3
import os

# Look for cms.db in the parent directory (project root)
db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "cms.db"))
if not os.path.exists(db_path):
    # Fallback to current working directory
    db_path = os.path.abspath("cms.db")
    
if not os.path.exists(db_path):
    print(f"Error: {db_path} not found")
    exit(1)

print(f"Using database at: {db_path}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

tables = ["users", "students", "faculty"]
for table in tables:
    print(f"\nChecking table: {table}")
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    print(f"Columns: {columns}")
    
    if "trust_id_fk" in columns:
        print("✅ trust_id_fk exists")
    else:
        print("❌ trust_id_fk MISSING")

cursor.execute("SELECT COUNT(*) FROM trusts")
trusts_count = cursor.fetchone()[0]
print(f"\nTrusts count: {trusts_count}")

cursor.execute("SELECT COUNT(*) FROM institutes")
institutes_count = cursor.fetchone()[0]
print(f"Institutes count: {institutes_count}")

conn.close()
