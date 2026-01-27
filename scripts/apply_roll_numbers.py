
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

    with app.app_context():
        count = 0
        for enrollment, roll_no in data.items():
            # Ensure enrollment is integer if DB expects it (model usually uses BigInteger/String depending on schema)
            # Student.enrollment_no is BigInteger in many setups, but let's check model.
            # Usually safe to pass as is if SQLAlchemy handles it.
            student = db.session.get(Student, enrollment)
            if student:
                if student.roll_no != roll_no:
                    student.roll_no = roll_no
                    count += 1
        
        db.session.commit()
        print(f"Updated roll numbers for {count} students.")

if __name__ == '__main__':
    import_rolls()
