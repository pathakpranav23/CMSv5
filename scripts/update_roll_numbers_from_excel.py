import pandas as pd
import sys
import os
from sqlalchemy import select

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from cms_app import create_app, db
from cms_app.models import Student

def update_roll_numbers():
    file_path = r"c:\project\CMSv5\DATA FOR IMPORT EXPORT\BCA\BCA Sem 2 Bulk Student Data 2026.xlsx"
    
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    print("Reading Excel file...")
    try:
        df = pd.read_excel(file_path)
    except Exception as e:
        print(f"Error reading Excel: {e}")
        return

    # Check required columns
    required_cols = ['Enrollment Number', 'RollNo']
    for col in required_cols:
        if col not in df.columns:
            print(f"Missing required column: {col}")
            return

    app = create_app()
    with app.app_context():
        updated_count = 0
        not_found_count = 0
        
        print("Starting update...")
        for index, row in df.iterrows():
            enrollment_no = str(row['Enrollment Number']).strip()
            # Handle potential float/int conversion for roll no
            try:
                roll_no_val = row['RollNo']
                if pd.isna(roll_no_val):
                    continue
                roll_no = str(int(roll_no_val))
            except ValueError:
                roll_no = str(row['RollNo']).strip()

            student = db.session.get(Student, enrollment_no)
            
            if student:
                if student.roll_no != roll_no:
                    student.roll_no = roll_no
                    updated_count += 1
            else:
                not_found_count += 1
                # print(f"Student not found: {enrollment_no}")

        try:
            db.session.commit()
            print(f"Successfully updated {updated_count} students.")
            if not_found_count > 0:
                print(f"Warning: {not_found_count} students from Excel were not found in the database.")
        except Exception as e:
            db.session.rollback()
            print(f"Error committing changes: {e}")

if __name__ == "__main__":
    update_roll_numbers()
