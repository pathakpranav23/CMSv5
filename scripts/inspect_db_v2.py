
import sqlite3
import os

db_path = r"c:\project\CMSv5\cms.db"
if not os.path.exists(db_path):
    print(f"DB not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("--- Columns in students table ---")
cursor.execute("PRAGMA table_info(students)")
columns = cursor.fetchall()
col_names = []
for col in columns:
    print(col)
    col_names.append(col[1])

print("\n--- First 5 rows (raw) ---")
cursor.execute("SELECT * FROM students LIMIT 5")
rows = cursor.fetchall()
for row in rows:
    print(row)

# Check if old columns exist
if 'student_name' in col_names:
    print("\nWARNING: 'student_name' column exists!")
if 'surname' in col_names:
    print("\nWARNING: 'surname' column exists!")

# Check if new columns are empty
if 'first_name' in col_names:
    cursor.execute("SELECT count(*) FROM students WHERE first_name IS NULL OR first_name = ''")
    empty_first = cursor.fetchone()[0]
    print(f"\nEmpty first_name count: {empty_first}")

if 'last_name' in col_names:
    cursor.execute("SELECT count(*) FROM students WHERE last_name IS NULL OR last_name = ''")
    empty_last = cursor.fetchone()[0]
    print(f"\nEmpty last_name count: {empty_last}")

conn.close()
