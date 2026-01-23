
import sqlite3
import os

# Adjust path if needed
db_path = r"c:\project\CMSv5\instance\cms_app.db"
if not os.path.exists(db_path):
    print(f"DB not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("--- Columns in students table ---")
cursor.execute("PRAGMA table_info(students)")
columns = cursor.fetchall()
for col in columns:
    print(col)

print("\n--- First 5 rows (raw) ---")
cursor.execute("SELECT * FROM students LIMIT 5")
rows = cursor.fetchall()
for row in rows:
    print(row)

conn.close()
