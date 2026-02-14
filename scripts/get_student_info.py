
import sqlite3
conn = sqlite3.connect('cms.db')
cursor = conn.cursor()

# Get BCA program ID
cursor.execute("SELECT program_id FROM programs WHERE program_name LIKE '%BCA%'")
bca_program_id = cursor.fetchone()[0]

# Get Division ID for Semester 4, Division A
# Using division_code instead of division_name
cursor.execute("SELECT division_id FROM divisions WHERE program_id_fk = ? AND semester = 4 AND division_code = 'A'", (bca_program_id,))
division_row = cursor.fetchone()

if division_row:
    division_id = division_row[0]
    # Get student with roll number 1 in that division
    cursor.execute("SELECT student_name, surname FROM students WHERE division_id_fk = ? AND roll_no = '1'", (division_id,))
    student = cursor.fetchone()
    if student:
        print(f"Student: {student[0]} {student[1]}")
    else:
        # Try roll_no as integer just in case
        cursor.execute("SELECT student_name, surname FROM students WHERE division_id_fk = ? AND roll_no = 1", (division_id,))
        student = cursor.fetchone()
        if student:
            print(f"Student: {student[0]} {student[1]}")
        else:
            print("Student with roll number 1 not found in Division A.")
else:
    print("Division A for BCA Semester 4 not found.")

conn.close()
