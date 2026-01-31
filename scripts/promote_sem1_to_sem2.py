
import os
import sys
from sqlalchemy import select

# Add project root to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from cms_app import create_app, db
from cms_app.models import Student, Division

def main():
    app = create_app()
    with app.app_context():
        print("Starting promotion of Semester 1 students to Semester 2...")
        
        # 1. Fetch all students currently in Semester 1
        students = db.session.execute(
            select(Student).filter_by(current_semester=1)
        ).scalars().all()
        
        if not students:
            print("No students found in Semester 1.")
            return

        print(f"Found {len(students)} students in Semester 1. Processing...")
        
        # 2. Fetch all target divisions (Semester 2) for lookup
        # Map: (program_id, division_code) -> division_id
        sem2_divisions = db.session.execute(
            select(Division).filter_by(semester=2)
        ).scalars().all()
        
        # Create a lookup dictionary for fast access
        # Key: (program_id, division_code)
        # Value: division_id
        sem2_div_map = {
            (d.program_id_fk, d.division_code): d.division_id 
            for d in sem2_divisions
        }
        
        count_promoted = 0
        count_div_updated = 0
        count_div_cleared = 0
        
        for student in students:
            # Check for current division info before update
            current_div = None
            if student.division_id_fk:
                current_div = db.session.get(Division, student.division_id_fk)
            
            # Promote Semester
            student.current_semester = 2
            count_promoted += 1
            
            # Handle Division Mapping
            if current_div:
                # Try to find corresponding division in Sem 2
                target_key = (student.program_id_fk, current_div.division_code)
                new_div_id = sem2_div_map.get(target_key)
                
                if new_div_id:
                    student.division_id_fk = new_div_id
                    count_div_updated += 1
                else:
                    # No corresponding division found in Sem 2, clear it to prevent mismatch
                    # Log this as it might be important for the user
                    print(f"Warning: Student {student.enrollment_no} (Prog {student.program_id_fk}) promoted but lost division {current_div.division_code} (no Sem 2 equivalent).")
                    student.division_id_fk = None
                    count_div_cleared += 1
            else:
                # Student had no division, stays with no division
                pass

        db.session.commit()
        
        print("\nPromotion Summary:")
        print("-" * 30)
        print(f"Total Students Promoted: {count_promoted}")
        print(f"Divisions Updated (Mapped): {count_div_updated}")
        print(f"Divisions Cleared (No Match): {count_div_cleared}")
        print("-" * 30)
        print("Done.")

if __name__ == "__main__":
    main()
