
import sys
import os

# Ensure project root is on sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from cms_app import create_app, db
from cms_app.models import Program, Student, Faculty, Subject, Division
from sqlalchemy import func

def analyze_data():
    app = create_app()
    with app.app_context():
        print("--- Data Sufficiency Analysis ---\n")
        
        programs = Program.query.all()
        if not programs:
            print("No programs found in database.")
            return

        print(f"{'Program Name':<30} | {'Code':<10} | {'Medium':<10} | {'Students':<10} | {'Faculty':<10} | {'Subjects':<10} | {'Divisions':<10}")
        print("-" * 110)

        for p in programs:
            s_count = Student.query.filter_by(program_id_fk=p.program_id).count()
            f_count = Faculty.query.filter_by(program_id_fk=p.program_id).count()
            sub_count = Subject.query.filter_by(program_id_fk=p.program_id).count()
            div_count = Division.query.filter_by(program_id_fk=p.program_id).count()
            
            p_code = p.program_code if p.program_code else "-"
            p_medium = p.medium if p.medium else "English" # Default assumption if None

            print(f"{p.program_name:<30} | {p_code:<10} | {p_medium:<10} | {s_count:<10} | {f_count:<10} | {sub_count:<10} | {div_count:<10}")

        print("\n--- End of Analysis ---")

if __name__ == "__main__":
    analyze_data()
