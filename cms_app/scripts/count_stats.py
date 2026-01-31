import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from cms_app import create_app, db
from cms_app.models import Institute, Program, Student, Faculty, Subject

app = create_app()

def count_stats():
    with app.app_context():
        # Find "The Group of Parekh Colleges"
        # We know from previous context it's likely Institute ID 1 or we can search by name
        institute = Institute.query.filter(Institute.institute_name.ilike("%Parekh%")).first()
        
        if not institute:
            print("Institute 'The Group of Parekh Colleges' not found.")
            # Fallback to ID 1 if name doesn't match exactly
            institute = db.session.get(Institute, 1)
            if institute:
                print(f"Fallback: Found Institute ID 1: {institute.institute_name}")
            else:
                return

        print(f"Stats for Institute: {institute.institute_name} (ID: {institute.institute_id})")
        
        # Get Programs
        programs = institute.programs
        program_ids = [p.program_id for p in programs]
        
        print(f"Programs ({len(programs)}):")
        for p in programs:
            print(f" - {p.program_name} (ID: {p.program_id})")
            
        if not program_ids:
            print("No programs found for this institute.")
            return

        # Count Students
        student_count = Student.query.filter(Student.program_id_fk.in_(program_ids)).count()
        
        # Count Staff (Faculty)
        # Note: Faculty might be linked via program_id_fk or other means. 
        # Checking model definition in memory: Faculty.program_id_fk exists.
        staff_count = Faculty.query.filter(Faculty.program_id_fk.in_(program_ids)).count()
        
        # Count Subjects
        subject_count = Subject.query.filter(Subject.program_id_fk.in_(program_ids)).count()
        
        print("\nCounts:")
        print(f"Students: {student_count}")
        print(f"Staff: {staff_count}")
        print(f"Subjects: {subject_count}")

if __name__ == "__main__":
    count_stats()
