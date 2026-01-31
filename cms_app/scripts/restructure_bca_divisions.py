import sys
import os
import logging
from sqlalchemy import text

# Add parent directory to path to import app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from cms_app import create_app, db
from cms_app.models import (
    Program, Student, Division, Attendance, ExamMark, 
    StudentSemesterResult, FeesRecord, FeePayment, 
    StudentSubjectEnrollment, Grade, StudentCreditLog,
    CourseAssignment, Subject
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def cleanup_non_bca_students():
    """
    Removes all student information from all programs EXCEPT BCA.
    """
    logger.info("Starting cleanup of non-BCA students...")
    
    # 1. Identify Non-BCA Programs
    bca_program = Program.query.filter_by(program_name="BCA").first()
    if not bca_program:
        logger.error("BCA Program not found! Aborting.")
        return

    non_bca_programs = Program.query.filter(Program.program_name != "BCA").all()
    non_bca_program_ids = [p.program_id for p in non_bca_programs]
    
    if not non_bca_program_ids:
        logger.info("No non-BCA programs found.")
    else:
        logger.info(f"Found non-BCA programs: {[p.program_name for p in non_bca_programs]}")

        # Get all students in these programs
        students_to_delete = Student.query.filter(Student.program_id_fk.in_(non_bca_program_ids)).all()
        student_enrollments = [s.enrollment_no for s in students_to_delete]
        
        if not students_to_delete:
            logger.info("No students found in non-BCA programs.")
        else:
            logger.info(f"Found {len(students_to_delete)} students to remove.")

            # Chunk deletion to avoid massive transactions if necessary, but for now do all
            # Delete related records
            logger.info("Deleting related records (Attendance, Marks, Fees, etc.)...")
            
            Attendance.query.filter(Attendance.student_id_fk.in_(student_enrollments)).delete(synchronize_session=False)
            ExamMark.query.filter(ExamMark.student_id_fk.in_(student_enrollments)).delete(synchronize_session=False)
            StudentSemesterResult.query.filter(StudentSemesterResult.student_id_fk.in_(student_enrollments)).delete(synchronize_session=False)
            FeesRecord.query.filter(FeesRecord.student_id_fk.in_(student_enrollments)).delete(synchronize_session=False)
            FeePayment.query.filter(FeePayment.enrollment_no.in_(student_enrollments)).delete(synchronize_session=False)
            StudentSubjectEnrollment.query.filter(StudentSubjectEnrollment.student_id_fk.in_(student_enrollments)).delete(synchronize_session=False)
            Grade.query.filter(Grade.student_id_fk.in_(student_enrollments)).delete(synchronize_session=False)
            StudentCreditLog.query.filter(StudentCreditLog.student_id_fk.in_(student_enrollments)).delete(synchronize_session=False)
            
            # Finally delete students
            Student.query.filter(Student.program_id_fk.in_(non_bca_program_ids)).delete(synchronize_session=False)
            
            db.session.commit()
            logger.info("Non-BCA students removed successfully.")

def restructure_bca_divisions():
    """
    Restructures BCA divisions for Sem 2, 4, 6 and assigns continuous roll numbers.
    Sem 2: 2 Divisions (A, B)
    Sem 4: 3 Divisions (A, B, C)
    Sem 6: 3 Divisions (A, B, C)
    Max Capacity: 66
    """
    logger.info("Restructuring BCA divisions...")
    
    bca_program = Program.query.filter_by(program_name="BCA").first()
    if not bca_program:
        return

    # Configuration: Semester -> Number of Divisions
    config = {
        2: 2,
        4: 3,
        6: 3
    }
    
    MAX_CAPACITY = 66
    
    for semester, num_divs in config.items():
        logger.info(f"Processing Semester {semester} (Target Divisions: {num_divs})...")
        
        # 1. Manage Divisions
        # Find existing divisions for this semester/program
        existing_divs = Division.query.filter_by(
            program_id_fk=bca_program.program_id,
            semester=semester
        ).order_by(Division.division_code).all()
        
        # Create mapping of Code -> Div Object
        div_map = {d.division_code: d for d in existing_divs}
        
        # Ensure we have A, B, C... up to num_divs
        final_divs = []
        for i in range(num_divs):
            code = chr(65 + i) # A, B, C...
            if code in div_map:
                div = div_map[code]
                div.capacity = MAX_CAPACITY
                final_divs.append(div)
            else:
                new_div = Division(
                    program_id_fk=bca_program.program_id,
                    semester=semester,
                    division_code=code,
                    capacity=MAX_CAPACITY
                )
                db.session.add(new_div)
                final_divs.append(new_div)
        
        db.session.commit() # Commit to get IDs for new divisions
        
        # Reload final_divs to ensure bound to session
        # (Actually the list objects might be detached if we aren't careful, better to re-query or use the ones we have)
        
        # 2. Assign Students
        # Fetch all students for this semester in BCA
        students = Student.query.filter_by(
            program_id_fk=bca_program.program_id,
            current_semester=semester
        ).order_by(Student.enrollment_no).all() # Sort by Enrollment No
        
        logger.info(f"Found {len(students)} students in Sem {semester}.")
        
        # Assign
        roll_counter = 1
        
        for student in students:
            # Determine Division Index: (roll_counter - 1) // 66
            div_idx = (roll_counter - 1) // MAX_CAPACITY
            
            if div_idx < len(final_divs):
                target_div = final_divs[div_idx]
            else:
                # Overflow handling: Put in the last division or create new?
                # User specified fixed number of divisions. 
                # If we exceed 3 * 66 = 198 students in Sem 4/6, or 132 in Sem 2, we have a problem.
                # For now, put in the LAST division available.
                target_div = final_divs[-1]
                logger.warning(f"Student {student.enrollment_no} overflowed max capacity. Assigning to last division {target_div.division_code}.")

            student.division_id_fk = target_div.division_id
            student.roll_no = str(roll_counter)
            
            roll_counter += 1
        
        db.session.commit()
        logger.info(f"Semester {semester} restructuring complete.")

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        try:
            cleanup_non_bca_students()
            restructure_bca_divisions()
            logger.info("All tasks completed successfully.")
        except Exception as e:
            logger.error(f"An error occurred: {e}")
            db.session.rollback()
