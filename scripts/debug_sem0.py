import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cms.db")

def check_db():
    print(f"Connecting to database at {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        print("\n--- Semester Distribution ---")
        cursor.execute("SELECT current_semester, count(*) FROM students GROUP BY current_semester")
        for row in cursor.fetchall():
            print(f"Semester {row[0]}: {row[1]} students")
            
        print("\n--- Bad Enrollment '0' ---")
        cursor.execute("SELECT enrollment_no, student_name, surname, roll_no, current_semester FROM students WHERE enrollment_no = '0'")
        bad = cursor.fetchall()
        print(bad)

        print("\n--- Sample Semester 0 Students ---")
        cursor.execute("SELECT enrollment_no, student_name, surname, roll_no FROM students WHERE current_semester = 0 LIMIT 5")
        print(cursor.fetchall())

        print("\n--- NULL Semester Students ---")
        cursor.execute("SELECT enrollment_no, student_name, surname, roll_no FROM students WHERE current_semester IS NULL LIMIT 5")
        print(cursor.fetchall())

        print("\n--- Check BHOJANI ---")
        cursor.execute("SELECT enrollment_no, student_name, surname, current_semester, roll_no FROM students WHERE surname LIKE '%BHOJANI%'")
        print(cursor.fetchall())
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_db()
