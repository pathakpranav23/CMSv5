import sqlite3
import os
import sys

# Ensure project root is on sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from contextlib import closing
from cms_app import create_app, db
from sqlalchemy import text

def table_exists(conn, table_name):
    res = conn.execute(text(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")).fetchone()
    return res is not None

def column_exists(conn, table, column):
    try:
        res = conn.execute(text(f"PRAGMA table_info('{table}')")).fetchall()
        # row structure: (cid, name, type, notnull, dflt_value, pk)
        return any(row[1] == column for row in res)
    except Exception as e:
        print(f"Error checking column {column} in {table}: {e}")
        return False

def main():
    app = create_app()
    with app.app_context():
        conn = db.session.connection()
        
        print("Starting schema synchronization...")

        # 1. Faculty table updates
        if not column_exists(conn, "faculty", "emp_id"):
            print("Adding emp_id to faculty...")
            conn.execute(text("ALTER TABLE faculty ADD COLUMN emp_id TEXT"))
        
        if not column_exists(conn, "faculty", "extra_data"):
            print("Adding extra_data to faculty...")
            conn.execute(text("ALTER TABLE faculty ADD COLUMN extra_data TEXT"))

        # 2. FeesRecord table
        if not table_exists(conn, "fees_records"):
            print("Creating fees_records table...")
            conn.execute(text("""
                CREATE TABLE fees_records (
                    fee_id INTEGER PRIMARY KEY,
                    student_id_fk VARCHAR(32) NOT NULL,
                    amount_due FLOAT DEFAULT 0.0,
                    amount_paid FLOAT DEFAULT 0.0,
                    date_paid DATE,
                    semester INTEGER,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(student_id_fk) REFERENCES students(enrollment_no)
                )
            """))
        else:
            if not column_exists(conn, "fees_records", "created_at"):
                print("Adding created_at to fees_records...")
                conn.execute(text("ALTER TABLE fees_records ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP"))

        # 3. Timetable tables
        if not table_exists(conn, "timetable_settings"):
            print("Creating timetable_settings table...")
            conn.execute(text("""
                CREATE TABLE timetable_settings (
                    setting_id INTEGER PRIMARY KEY,
                    program_id_fk INTEGER NOT NULL,
                    academic_year VARCHAR(16) NOT NULL,
                    start_time TIME,
                    slot_duration_mins INTEGER DEFAULT 55,
                    FOREIGN KEY(program_id_fk) REFERENCES programs(program_id),
                    CONSTRAINT uq_timetable_settings UNIQUE (program_id_fk, academic_year)
                )
            """))

        if not table_exists(conn, "timetable_slots"):
            print("Creating timetable_slots table...")
            conn.execute(text("""
                CREATE TABLE timetable_slots (
                    slot_id INTEGER PRIMARY KEY,
                    division_id_fk INTEGER NOT NULL,
                    subject_id_fk INTEGER NOT NULL,
                    day_of_week VARCHAR(10) NOT NULL,
                    period_no INTEGER NOT NULL,
                    FOREIGN KEY(division_id_fk) REFERENCES divisions(division_id),
                    FOREIGN KEY(subject_id_fk) REFERENCES subjects(subject_id),
                    CONSTRAINT uq_timetable_slot_div_day_period UNIQUE (division_id_fk, day_of_week, period_no)
                )
            """))

        # 4. FeePayment table updates (ensure new columns exist if table exists)
        if table_exists(conn, "fee_payments"):
             if not column_exists(conn, "fee_payments", "payment_mode"):
                 print("Adding payment_mode to fee_payments...")
                 conn.execute(text("ALTER TABLE fee_payments ADD COLUMN payment_mode VARCHAR(32)"))
             if not column_exists(conn, "fee_payments", "reference_no"):
                 print("Adding reference_no to fee_payments...")
                 conn.execute(text("ALTER TABLE fee_payments ADD COLUMN reference_no VARCHAR(64)"))
             if not column_exists(conn, "fee_payments", "receipt_no"):
                 print("Adding receipt_no to fee_payments...")
                 conn.execute(text("ALTER TABLE fee_payments ADD COLUMN receipt_no VARCHAR(64)"))
             if not column_exists(conn, "fee_payments", "remarks"):
                 print("Adding remarks to fee_payments...")
                 conn.execute(text("ALTER TABLE fee_payments ADD COLUMN remarks TEXT"))
             if not column_exists(conn, "fee_payments", "created_by_user_id"):
                 print("Adding created_by_user_id to fee_payments...")
                 conn.execute(text("ALTER TABLE fee_payments ADD COLUMN created_by_user_id INTEGER REFERENCES users(user_id)"))
             if not column_exists(conn, "fee_payments", "verified_at"):
                 print("Adding verified_at to fee_payments...")
                 conn.execute(text("ALTER TABLE fee_payments ADD COLUMN verified_at DATETIME"))
             if not column_exists(conn, "fee_payments", "verified_by_user_id"):
                 print("Adding verified_by_user_id to fee_payments...")
                 conn.execute(text("ALTER TABLE fee_payments ADD COLUMN verified_by_user_id INTEGER REFERENCES users(user_id)"))

        db.session.commit()
        print("Schema synchronization completed.")

if __name__ == "__main__":
    main()
