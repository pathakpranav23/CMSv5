import sys
import os
import random
import json
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.getcwd())

from cms_app import create_app, db
from cms_app.models import (
    Program, Subject, Student, ExamScheme, ExamMark, StudentSemesterResult
)

def seed_bca_exam_data():
    app = create_app()
    with app.app_context():
        print("--- Seeding BCA Exam Data ---")
        
        # 1. Get Program and Semester
        prog = Program.query.filter(Program.program_name.ilike("BCA")).first()
        if not prog:
            print("Error: BCA Program not found!")
            return

        semester = 4
        academic_year = "2024-2025"
        
        print(f"Target: {prog.program_name} Sem {semester} ({academic_year})")

        # 2. Create Exam Scheme
        scheme_name = f"BCA Sem {semester} Regular Exam April 2025"
        scheme = ExamScheme.query.filter_by(
            program_id_fk=prog.program_id,
            semester=semester,
            academic_year=academic_year
        ).first()

        if not scheme:
            print(f"Creating new ExamScheme: {scheme_name}")
            grading_logic = {
                "passing_marks_internal": 12,
                "passing_marks_external": 28,
                "passing_marks_total": 40
            }
            scheme = ExamScheme(
                program_id_fk=prog.program_id,
                semester=semester,
                academic_year=academic_year,
                name=scheme_name,
                max_internal_marks=30.0,
                max_external_marks=70.0,
                min_internal_marks=12.0,
                min_external_marks=28.0,
                min_total_marks=40.0,
                max_total_marks=100.0,
                grading_scheme_json=json.dumps(grading_logic),
                is_active=True
            )
            db.session.add(scheme)
            db.session.commit()
        else:
            print(f"Using existing ExamScheme: {scheme.name} (ID: {scheme.scheme_id})")

        # 3. Get Subjects
        subjects = Subject.query.filter_by(
            program_id_fk=prog.program_id, 
            semester=semester
        ).all()
        
        if not subjects:
            print("Error: No subjects found for this semester!")
            return
            
        print(f"Found {len(subjects)} subjects.")

        # 4. Get Students (limit to 5 for testing)
        students = Student.query.filter_by(
            program_id_fk=prog.program_id,
            current_semester=semester
        ).limit(5).all()
        
        if not students:
            print("Error: No students found in this semester!")
            return

        print(f"Seeding marks for {len(students)} students...")

        # 5. Generate Marks and Results
        for student in students:
            print(f"Processing: {student.first_name} {student.last_name} ({student.enrollment_no})")
            
            total_obtained = 0
            total_max = 0
            failed_subjects = []
            
            # Assumptions for credits
            credits_per_subject = 4
            total_credits = len(subjects) * credits_per_subject
            earned_credits = 0
            
            for subject in subjects:
                # Check if mark already exists
                mark = ExamMark.query.filter_by(
                    scheme_id_fk=scheme.scheme_id,
                    student_id_fk=student.enrollment_no,
                    subject_id_fk=subject.subject_id
                ).first()

                if not mark:
                    # Generate random marks
                    is_absent = random.random() < 0.05
                    
                    if is_absent:
                        internal = 0
                        external = 0
                        grade = "Ab"
                    else:
                        internal = round(random.uniform(5, 28), 1)
                        external = round(random.uniform(15, 65), 1)
                        if random.random() > 0.2:
                            internal = max(internal, 12.0)
                            external = max(external, 28.0)
                            
                    total = internal + external
                    
                    if is_absent:
                        grade = "Ab"
                        gp = 0.0
                    elif internal < 12 or external < 28:
                        grade = "F"
                        gp = 0.0
                        failed_subjects.append(subject.subject_code or subject.subject_name)
                    else:
                        if total >= 90: grade, gp = "A+", 10.0
                        elif total >= 80: grade, gp = "A", 9.0
                        elif total >= 70: grade, gp = "B+", 8.0
                        elif total >= 60: grade, gp = "B", 7.0
                        elif total >= 50: grade, gp = "C", 6.0
                        elif total >= 40: grade, gp = "D", 5.0
                        else: grade, gp = "F", 0.0
                        
                        earned_credits += credits_per_subject
                    
                    mark = ExamMark(
                        student_id_fk=student.enrollment_no,
                        subject_id_fk=subject.subject_id,
                        scheme_id_fk=scheme.scheme_id,
                        semester=semester,
                        academic_year=academic_year,
                        internal_marks=internal,
                        external_marks=external,
                        total_marks=total,
                        grade_point=gp,
                        grade_letter=grade,
                        is_absent=is_absent
                    )
                    db.session.add(mark)
                    
                    total_obtained += total
                    total_max += 100
                else:
                    total_obtained += mark.total_marks
                    total_max += 100
                    if mark.grade_letter not in ['F', 'Ab']:
                         earned_credits += credits_per_subject
                    else:
                         failed_subjects.append(subject.subject_code or subject.subject_name)

            # Create/Update Semester Result
            result_status = "FAIL" if failed_subjects else "PASS"
            sgpa = (total_obtained / total_max) * 10.0 if total_max > 0 else 0.0 
            
            sem_result = StudentSemesterResult.query.filter_by(
                student_id_fk=student.enrollment_no,
                scheme_id_fk=scheme.scheme_id
            ).first()
            
            if not sem_result:
                sem_result = StudentSemesterResult(
                    student_id_fk=student.enrollment_no,
                    program_id_fk=prog.program_id,
                    scheme_id_fk=scheme.scheme_id,
                    semester=semester,
                    academic_year=academic_year,
                    total_credits_registered=total_credits,
                    total_credits_earned=earned_credits,
                    sgpa=round(sgpa, 2),
                    cgpa=round(sgpa, 2), # Simplified
                    result_status=result_status,
                    remarks=f"Failed in: {', '.join(failed_subjects)}" if failed_subjects else "Congratulations"
                )
                db.session.add(sem_result)
            
        db.session.commit()
        print("--- Seeding Completed Successfully ---")

if __name__ == "__main__":
    seed_bca_exam_data()
