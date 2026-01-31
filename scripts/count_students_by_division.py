
import os
import sys
from sqlalchemy import select, func, text

# Add project root to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from cms_app import create_app, db
from cms_app.models import Student, Program, Division

def main():
    app = create_app()
    with app.app_context():
        print(f"{'Program':<20} | {'Sem':<5} | {'Div':<5} | {'Count':<5}")
        print("-" * 45)
        
        # Query to group by Program, Semester, Division
        # We use Student.current_semester for the semester grouping
        stmt = (
            select(
                Program.program_name,
                Student.current_semester,
                Division.division_code,
                func.count(Student.enrollment_no).label('count')
            )
            .join(Program, Student.program_id_fk == Program.program_id)
            .outerjoin(Division, Student.division_id_fk == Division.division_id)
            .group_by(
                Program.program_name,
                Student.current_semester,
                Division.division_code
            )
            .order_by(
                Program.program_name,
                Student.current_semester,
                Division.division_code
            )
        )
        
        results = db.session.execute(stmt).all()
        
        current_program = None
        
        for program_name, semester, div_code, count in results:
            # Add a separator line between programs for better readability
            if current_program != program_name:
                if current_program is not None:
                    print("-" * 45)
                current_program = program_name
                
            div_display = div_code if div_code else "None"
            print(f"{program_name:<20} | {semester:<5} | {div_display:<5} | {count:<5}")

if __name__ == "__main__":
    main()
