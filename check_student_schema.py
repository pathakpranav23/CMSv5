import sqlite3

def check_schema():
    try:
        conn = sqlite3.connect('cms.db')
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(students)")
        columns = cursor.fetchall()
        print("Columns in students table:")
        for col in columns:
            print(col)
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_schema()