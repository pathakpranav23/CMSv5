
import pandas as pd
from cms_app import create_app, db
from cms_app.models import Student
from sqlalchemy import select

app = create_app()

file_path = r"c:\project\CMSv5\DATA FOR IMPORT EXPORT\BCA\BCA Sem 6 Bulk Student Data 2026.xlsx"

def update_roll_numbers():
    print(f"Reading Excel: {file_path}")
    try:
        df = pd.read_excel(file_path)
    except Exception as e:
        print(f"Failed to read Excel: {e}")
        return

    # Normalize columns
    df.columns = [c.strip().lower() for c in df.columns]
    
    # Identify key columns
    roll_col = next((c for c in df.columns if 'roll' in c), None)
    enr_col = next((c for c in df.columns if 'enrollment' in c), None)
    
    if not roll_col or not enr_col:
        print(f"Missing columns! Found: {df.columns.tolist()}")
        return

    print(f"Using columns: Roll='{roll_col}', Enrollment='{enr_col}'")
    
    updates = 0
    not_found = 0
    
    with app.app_context():
        for index, row in df.iterrows():
            raw_enr = row[enr_col]
            raw_roll = row[roll_col]
            
            # Clean Enrollment (handle float/scientific from Excel)
            try:
                enrollment_str = str(int(float(raw_enr)))
            except:
                enrollment_str = str(raw_enr).strip()
                
            # Clean Roll No
            try:
                roll_str = str(int(float(raw_roll)))
            except:
                roll_str = str(raw_roll).strip()
            
            # Find Student
            student = db.session.get(Student, enrollment_str)
            
            if student:
                if student.roll_no != roll_str:
                    # print(f"Updating {student.full_name} ({enrollment_str}): {student.roll_no} -> {roll_str}")
                    student.roll_no = roll_str
                    updates += 1
            else:
                # print(f"Student not found: {enrollment_str}")
                not_found += 1
        
        try:
            db.session.commit()
            print(f"\nSUCCESS: Updated {updates} student roll numbers.")
            print(f"WARNING: {not_found} students from Excel were not found in DB.")
        except Exception as e:
            db.session.rollback()
            print(f"ERROR: Commit failed: {e}")

        # Verify Roll No 1
        print("\n--- Verification: Who is Roll No 1? ---")
        roll1 = db.session.execute(
            select(Student)
            .filter(Student.roll_no == '1')
            .filter(Student.current_semester == 6) # Assuming Sem 6 context
        ).scalars().first()
        
        if roll1:
            print(f"Roll No 1 is: {roll1.full_name} ({roll1.enrollment_no})")
        else:
            print("No student found with Roll No 1 in Sem 6.")

if __name__ == "__main__":
    update_roll_numbers()
