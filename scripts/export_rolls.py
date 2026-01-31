
import sys
import os
import json

# Add the project root to the python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cms_app import create_app, db
from cms_app.models import Student
from sqlalchemy import select

app = create_app()

def export_rolls():
    with app.app_context():
        # Get all students with roll numbers
        students = db.session.execute(select(Student).where(Student.roll_no != None)).scalars().all()
        
        data = {}
        for s in students:
            data[str(s.enrollment_no)] = s.roll_no
            
        with open('roll_numbers.json', 'w') as f:
            json.dump(data, f)
            
        print(f"Exported {len(data)} roll numbers to roll_numbers.json")

if __name__ == '__main__':
    export_rolls()
