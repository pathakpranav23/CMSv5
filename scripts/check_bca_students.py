
import sqlite3
conn = sqlite3.connect('cms.db')
cursor = conn.cursor()

print("--- Divisions ---")
cursor.execute("SELECT division_id, division_code, semester, program_id_fk FROM divisions")
for row in cursor.fetchall():
    print(row)

print("\n--- BCA Semester 4 Students in DB ---")
# Let's find the division_id for BCA (prog 1) Sem 4 Div A
cursor.execute("SELECT division_id FROM divisions WHERE program_id_fk = 1 AND semester = 4 AND division_code = 'A'")
div_row = cursor.fetchone()
if div_row:
    div_id = div_row[0]
    print(f"Division A ID: {div_id}")
    cursor.execute("SELECT roll_no, student_name, surname FROM students WHERE division_id_fk = ? ORDER BY roll_no ASC LIMIT 10", (div_id,))
    for row in cursor.fetchall():
        print(row)
else:
    print("Division A not found for BCA Sem 4")

conn.close()
