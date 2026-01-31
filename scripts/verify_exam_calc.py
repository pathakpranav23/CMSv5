import sys
import os

# Add the parent directory to the path so we can import the app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cms_app import create_app, db
from cms_app.models import ExamScheme, ExamMark, StudentSemesterResult, Student
from cms_app.exams.services import calculate_exam_results

app = create_app()

def verify_calculation():
    with app.app_context():
        print("--- Verifying Exam Calculation ---")
        
        # 1. Find a scheme that has marks
        # We join ExamScheme with ExamMark to find schemes with data
        scheme_with_marks = db.session.query(ExamScheme).join(ExamMark).first()
        
        if not scheme_with_marks:
            print("No Exam Schemes with marks found. Cannot verify calculation without data.")
            # Optional: Check if any scheme exists at all
            scheme = db.session.query(ExamScheme).first()
            if scheme:
                print(f"Found Scheme ID {scheme.id} ({scheme.name}) but it has no marks.")
            else:
                print("No Exam Schemes found at all.")
            return

        print(f"Found Scheme with marks: ID={scheme_with_marks.scheme_id}, Name='{scheme_with_marks.name}'")
        
        # 2. Check existing results for this scheme (if any)
        existing_results_count = StudentSemesterResult.query.filter_by(scheme_id_fk=scheme_with_marks.scheme_id).count()
        print(f"Existing StudentSemesterResult entries for this scheme: {existing_results_count}")
        
        # 3. Run Calculation
        print("\nRunning calculate_exam_results()...")
        success, message, count = calculate_exam_results(scheme_with_marks.scheme_id)
        
        print(f"Calculation returned: Success={success}, Message='{message}', Count={count}")
        
        if success:
            # 4. Inspect a few results
            results = StudentSemesterResult.query.filter_by(scheme_id_fk=scheme_with_marks.scheme_id).limit(5).all()
            print("\nSample Results:")
            print(f"{'Student ID':<10} | {'SGPA':<6} | {'Grade':<6} | {'Credits':<10} | {'Total Marks':<12}")
            print("-" * 60)
            for res in results:
                student = db.session.get(Student, res.student_id_fk)
                student_name = student.first_name if student else "Unknown"
                # StudentSemesterResult doesn't seem to have 'grade' or 'result_status' fields directly in the model definition I saw
                # It has sgpa, total_credits_earned
                # Let me check the model definition again.
                print(f"{res.student_id_fk:<10} | {res.sgpa:<6} | {res.total_credits_earned:<10} | {res.total_credits_earned:<10}")
        else:
            print("Calculation failed.")

if __name__ == "__main__":
    verify_calculation()
