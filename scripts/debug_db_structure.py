
import sqlite3
conn = sqlite3.connect('cms.db')
cursor = conn.cursor()

print("--- Programs ---")
cursor.execute("SELECT program_id, program_name, trust_id_fk FROM programs")
for row in cursor.fetchall():
    print(row)

print("\n--- Divisions for BCA ---")
# Assuming BCA is program_id 1 from previous knowledge, but let's be sure
cursor.execute("SELECT division_id, division_code, semester, program_id_fk FROM divisions")
for row in cursor.fetchall():
    print(row)

conn.close()
