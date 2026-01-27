
import sys
import os
import json

# Add the project root to the python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cms_app import create_app, db
from cms_app.models import Student

app = create_app()

def import_rolls():
    json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'roll_numbers.json')
    
    if not os.path.exists(json_path):
        print("roll_numbers.json not found!")
        return

    with open(json_path, 'r') as f:
        data = json.load(f)

    print(f"Loaded {len(data)} roll numbers from JSON.")

    with app.app_context():
        count = 0
        missing_students = 0
        
        # specific check for the student mentioned
        target_enrollment = "5034250004"
        
        for enrollment, roll_no in data.items():
            enrollment = str(enrollment).strip()
            student = db.session.get(Student, enrollment)
            
            if student:
                current_roll = getattr(student, 'roll_no', None)
                if str(current_roll) != str(roll_no):
                    print(f"Updating {enrollment}: {current_roll} -> {roll_no}")
                    student.roll_no = str(roll_no)
                    count += 1
            else:
                missing_students += 1
        
        try:
            db.session.commit()
            print(f"Successfully updated roll numbers for {count} students.")
            print(f"Skipped {missing_students} students (not found in DB).")
            
            # Verify the target student
            s = db.session.get(Student, target_enrollment)
            if s:
                print(f"VERIFICATION: Student {target_enrollment} has Roll No: {s.roll_no}")
            else:
                print(f"VERIFICATION: Student {target_enrollment} NOT FOUND in DB.")
                
        except Exception as e:
            db.session.rollback()
            print(f"Error committing changes: {e}")

if __name__ == '__main__':
    import_rolls()
