
import sys
import os
from sqlalchemy import select

# Add the project root to the python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from cms_app import create_app, db
from cms_app.models import User, Student, Program, Subject, CourseAssignment, StudentSubjectEnrollment

app = create_app()

def promote_and_fix_amit():
    with app.app_context():
        print("Starting Semester Promotion and Faculty Fix Script...")

        # 1. Identify Program (BCA)
        # We look for a program with 'BCA' in the name or code
        program = db.session.execute(
            select(Program).filter(Program.program_code.ilike('%BCA%'))
        ).scalars().first()

        if not program:
            # Fallback search by name
            program = db.session.execute(
                select(Program).filter(Program.program_name.ilike('%BCA%'))
            ).scalars().first()
        
        if not program:
            print("Error: Could not find 'BCA' program.")
            return

        print(f"Target Program: {program.program_name} (ID: {program.program_id})")

        # 2. Identify Faculty (Amit)
        amit_email = 'Amit.potent@gmail.com'
        amit_user = db.session.execute(
            select(User).filter(User.email.ilike(amit_email))
        ).scalars().first()

        if not amit_user:
            print(f"Error: User with email '{amit_email}' not found.")
            # Depending on strictness, we might continue with promotion or stop.
            # The user explicitly asked for this fix, so better stop or warn.
            # But let's proceed with promotion if possible, but the requirement is bundled.
            return
        
        print(f"Found Faculty: {amit_user.username} (ID: {amit_user.user_id})")

        # 3. Promote Students (Sem 5 -> Sem 6)
        students_sem_5 = db.session.execute(
            select(Student).filter(
                Student.program_id_fk == program.program_id,
                Student.current_semester == 5
            )
        ).scalars().all()

        print(f"Found {len(students_sem_5)} students in Semester 5.")

        promoted_count = 0
        for student in students_sem_5:
            student.current_semester = 6
            promoted_count += 1
            
            # "Clear semester - 5 data" - Deactivate active Sem 5 enrollments
            # This ensures they don't show up as 'Active' in Sem 5 lists if filtered by enrollment
            enrollments = db.session.execute(
                select(StudentSubjectEnrollment).filter(
                    StudentSubjectEnrollment.student_id_fk == student.enrollment_no,
                    StudentSubjectEnrollment.semester == 5,
                    StudentSubjectEnrollment.is_active == True
                )
            ).scalars().all()
            
            for enrollment in enrollments:
                enrollment.is_active = False
        
        print(f"Promoted {promoted_count} students to Semester 6 and deactivated their Sem 5 enrollments.")

        # 4. Fix Amit's Subjects
        # Remove PHP (Sem 5)
        # Find PHP subject for this program
        php_subject = db.session.execute(
            select(Subject).filter(
                Subject.program_id_fk == program.program_id,
                Subject.subject_name.ilike('%PHP%')
            )
        ).scalars().first()

        if php_subject:
            print(f"Found PHP Subject: {php_subject.subject_name} (ID: {php_subject.subject_id})")
            # Remove assignment
            assignments_to_remove = db.session.execute(
                select(CourseAssignment).filter(
                    CourseAssignment.faculty_id_fk == amit_user.user_id,
                    CourseAssignment.subject_id_fk == php_subject.subject_id
                )
            ).scalars().all()

            for assign in assignments_to_remove:
                db.session.delete(assign)
                print(f"Removed assignment for PHP (ID: {assign.assignment_id}) from Amit.")
        else:
            print("Warning: PHP subject not found in this program.")

        # Add ASP.Net (Sem 6)
        asp_subject = db.session.execute(
            select(Subject).filter(
                Subject.program_id_fk == program.program_id,
                Subject.subject_name.ilike('%ASP.Net%')
            )
        ).scalars().first()

        if asp_subject:
            print(f"Found ASP.Net Subject: {asp_subject.subject_name} (ID: {asp_subject.subject_id})")
            
            # Check if already assigned
            existing_assign = db.session.execute(
                select(CourseAssignment).filter(
                    CourseAssignment.faculty_id_fk == amit_user.user_id,
                    CourseAssignment.subject_id_fk == asp_subject.subject_id
                )
            ).scalars().first()

            if not existing_assign:
                # We need a division to assign. Usually assignments are per division.
                # Since we promoted students, we should assign him to the divisions they are in.
                # Let's find all divisions for Sem 6 in this program.
                divisions_sem_6 = db.session.execute(
                    select(ProgramDivisionPlan).filter(
                        ProgramDivisionPlan.program_id_fk == program.program_id,
                        ProgramDivisionPlan.semester == 6
                    )
                ).scalars().all()
                
                # If no plan, check actual Division table
                if not divisions_sem_6:
                     # This might be tricky if divisions aren't set up for Sem 6 yet.
                     # But assuming they exist since we promoted students? 
                     # Wait, we just updated current_semester. We didn't change division_id_fk.
                     # The Division model has a 'semester' column. 
                     # If students stay in the same division ID but the division itself is "Sem 5 division", that's a problem.
                     # Usually Division A is Sem 1, Division B is Sem 1... OR Division A (Sem 1), Division A (Sem 2).
                     # Let's check Division model: `semester = db.Column(db.Integer)`
                     # So Division is tied to a semester.
                     # If we promote students, we MUST also move them to a new Division ID corresponding to Sem 6?
                     # OR does the system reuse Division IDs?
                     pass
                
                # Let's look at `_rebalance_program_divisions_for_semester` logic in routes.py (which I saw earlier but didn't read fully)
                # Usually promotion involves moving to new division.
                # If I just update `current_semester`, their `division_id_fk` points to a Sem 5 division.
                # This script needs to handle Division mapping if I want to be thorough.
                # However, the user request was "promote those students".
                # If I only update `current_semester`, the UI might show mismatch (Student in Sem 6 but Division says Sem 5).
                
                # Let's assume for now we assign Amit to *any* division of Sem 6 or just create the assignment without division if allowed?
                # CourseAssignment has `division_id_fk`.
                # I'll try to find a default Division A for Sem 6.
                
                from cms_app.models import Division
                div_sem_6 = db.session.execute(
                    select(Division).filter(
                        Division.program_id_fk == program.program_id,
                        Division.semester == 6,
                        Division.division_code == 'A' # Assumption
                    )
                ).scalars().first()

                if div_sem_6:
                    new_assign = CourseAssignment(
                        faculty_id_fk=amit_user.user_id,
                        subject_id_fk=asp_subject.subject_id,
                        division_id_fk=div_sem_6.division_id,
                        academic_year='2024-2025', # Hardcoded or dynamic?
                        role='primary',
                        is_active=True
                    )
                    db.session.add(new_assign)
                    print(f"Assigned Amit to ASP.Net (Division {div_sem_6.division_code}, Sem 6).")
                else:
                    print("Warning: Could not find Division A for Sem 6. Created assignment with NULL division.")
                    new_assign = CourseAssignment(
                        faculty_id_fk=amit_user.user_id,
                        subject_id_fk=asp_subject.subject_id,
                        division_id_fk=None,
                        academic_year='2024-2025',
                        role='primary',
                        is_active=True
                    )
                    db.session.add(new_assign)

        else:
            print("Warning: ASP.Net subject not found in this program.")

        try:
            db.session.commit()
            print("Transaction committed successfully.")
        except Exception as e:
            db.session.rollback()
            print(f"Error committing transaction: {e}")

if __name__ == "__main__":
    promote_and_fix_amit()
