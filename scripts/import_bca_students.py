import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cms_app import create_app, db
from cms_app.models import User, Student, Program, Subject, StudentSubjectEnrollment, Division
from sqlalchemy import select, update
import pandas as pd
import os
import random
import string
import math
from datetime import datetime

def generate_random_password(length=8):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def parse_date(date_val):
    if pd.isna(date_val):
        return None
    if isinstance(date_val, (datetime, pd.Timestamp)):
        return date_val.date()
    if isinstance(date_val, str):
        # Try multiple formats
        for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y'):
            try:
                return datetime.strptime(date_val, fmt).date()
            except ValueError:
                continue
    return None

def import_bca_data():
    app = create_app()
    with app.app_context():
        file_path = r'c:\project\CMSv5\DATA FOR IMPORT EXPORT\BCA Semester 4 Updated Data 2026 Feb.xlsx'
        if not os.path.exists(file_path):
            print("Excel file not found.")
            return

        print("--- Step 1: Loading Excel Data ---")
        df = pd.read_excel(file_path, sheet_name='BCA Semester 4 Batch 2025-26')
        
        # 1. Identify Target Program
        bca_program = db.session.execute(
            select(Program).filter(Program.program_name.like('%BCA%'))
        ).scalars().first()
        
        if not bca_program:
            print("BCA Program not found in database.")
            return
            
        program_id = bca_program.program_id
        trust_id = bca_program.institute.trust_id_fk
        print(f"Target Program: {bca_program.program_name} (ID: {program_id}, Trust: {trust_id})")

        # 2. Deactivate Old Semester 4 Data
        print("--- Step 2: Deactivating existing BCA Semester 4 students ---")
        
        # Get subject IDs first to avoid subquery evaluation issues in update
        sem4_subject_ids = db.session.execute(
            select(Subject.subject_id).where(Subject.program_id_fk == program_id, Subject.semester == 4)
        ).scalars().all()

        if sem4_subject_ids:
            # Deactivate subject enrollments for Semester 4 BCA
            db.session.execute(
                update(StudentSubjectEnrollment)
                .where(
                    StudentSubjectEnrollment.semester == 4,
                    StudentSubjectEnrollment.subject_id_fk.in_(sem4_subject_ids)
                )
                .values(is_active=False)
                .execution_options(synchronize_session=False)
            )
        
        # Deactivate student records who are currently in Sem 4 BCA
        db.session.execute(
            update(Student)
            .where(
                Student.program_id_fk == program_id,
                Student.current_semester == 4
            )
            .values(is_active=False)
            .execution_options(synchronize_session=False)
        )
        db.session.flush()

        # 3. Import New Data
        print("--- Step 3: Importing New Students ---")
        stats = {"created_users": 0, "created_students": 0, "updated_students": 0, "enrollments": 0}

        # Pre-fetch subjects for Sem 4 BCA to avoid repeated queries
        subjects = db.session.execute(
            select(Subject).where(Subject.program_id_fk == program_id, Subject.semester == 4, Subject.is_active == True)
        ).scalars().all()
        
        if not subjects:
            print("Warning: No active subjects found for BCA Semester 4. Enrollments will be skipped.")

        for index, row in df.iterrows():
            # Clean enrollment number
            enroll_raw = row.get('Enrollment Number')
            if pd.isna(enroll_raw):
                print(f"Skipping row {index+2}: Missing Enrollment Number")
                continue
            try:
                enrollment_no = str(int(enroll_raw))
            except:
                print(f"Skipping row {index+2}: Invalid Enrollment Number {enroll_raw}")
                continue
            
            # 3.1 Handle User Account
            user = db.session.execute(select(User).filter_by(username=enrollment_no)).scalars().first()
            mobile_raw = row.get('Mobile')
            mobile = str(int(mobile_raw)) if pd.notnull(mobile_raw) and not isinstance(mobile_raw, str) else str(mobile_raw) if pd.notnull(mobile_raw) else None
            
            if not user:
                email = row.get('Email Id') if pd.notnull(row.get('Email Id')) else f"{enrollment_no}@cms.com"
                user = User(
                    username=enrollment_no,
                    email=email,
                    mobile=mobile,
                    role='student',
                    trust_id_fk=trust_id,
                    is_active=True,
                    must_change_password=True
                )
                # Password strategy: Mobile or Random
                password = mobile if mobile and len(mobile) >= 6 else generate_random_password()
                user.set_password(password)
                db.session.add(user)
                db.session.flush()
                stats["created_users"] += 1
            else:
                user.is_active = True
                user.trust_id_fk = trust_id # Ensure trust is set
                if mobile: user.mobile = mobile

            # 3.2 Handle Student Profile
            student = db.session.execute(select(Student).filter_by(enrollment_no=enrollment_no)).scalars().first()
            
            s_name = str(row.get('Student Name', '')).strip()
            s_surname = str(row.get('Surname', '')).strip()
            s_father = str(row.get('Father\'s Name', '')).strip()
            s_gender = str(row.get('Gender', 'Male')).strip()
            s_roll = str(int(row.get('RollNo'))) if pd.notnull(row.get('RollNo')) else None
            s_address = str(row.get('Permanent Address', ''))[:255] if pd.notnull(row.get('Permanent Address')) else None
            s_dob = parse_date(row.get('Date of Birth'))
            s_medium = str(row.get('Medium', 'English')).strip()

            if not student:
                student = Student(
                    enrollment_no=enrollment_no,
                    user_id_fk=user.user_id,
                    program_id_fk=program_id,
                    trust_id_fk=trust_id,
                    student_name=s_name,
                    surname=s_surname,
                    father_name=s_father,
                    gender=s_gender,
                    roll_no=s_roll,
                    mobile=mobile,
                    email=user.email,
                    permanent_address=s_address,
                    current_semester=4,
                    date_of_birth=s_dob,
                    medium_tag=s_medium,
                    is_active=True
                )
                db.session.add(student)
                stats["created_students"] += 1
            else:
                # Reactivate and update
                student.student_name = s_name
                student.surname = s_surname
                student.father_name = s_father
                student.gender = s_gender
                student.roll_no = s_roll
                student.mobile = mobile
                student.current_semester = 4
                student.date_of_birth = s_dob
                student.medium_tag = s_medium
                student.is_active = True
                student.trust_id_fk = trust_id
                stats["updated_students"] += 1

            # 3.3 Handle Subject Enrollments for 2025-26
            for subject in subjects:
                # Check for existing active enrollment
                existing_sub = db.session.execute(
                    select(StudentSubjectEnrollment).filter_by(
                        student_id_fk=enrollment_no,
                        subject_id_fk=subject.subject_id,
                        academic_year='2025-26'
                    )
                ).scalars().first()
                
                if not existing_sub:
                    new_sub = StudentSubjectEnrollment(
                        student_id_fk=enrollment_no,
                        subject_id_fk=subject.subject_id,
                        semester=4,
                        academic_year='2025-26',
                        is_active=True,
                        source='bulk_import'
                    )
                    db.session.add(new_sub)
                    stats["enrollments"] += 1
                else:
                    existing_sub.is_active = True

        try:
            db.session.commit()
            print(f"--- SUCCESS ---")
            print(f"New Users Created: {stats['created_users']}")
            print(f"Students Created: {stats['created_students']}")
            print(f"Students Updated/Reactivated: {stats['updated_students']}")
            print(f"Subject Enrollments Created: {stats['enrollments']}")
        except Exception as e:
            db.session.rollback()
            print(f"--- ERROR ---")
            print(f"Failed to commit changes: {str(e)}")

if __name__ == "__main__":
    import_bca_data()
