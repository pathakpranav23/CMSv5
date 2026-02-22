import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cms_app import create_app, db
from cms_app.models import User, Student, Program, Division
from sqlalchemy import select, update
import pandas as pd
import random
import string
from datetime import datetime


def generate_random_password(length=8):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def parse_date(date_val):
    if pd.isna(date_val):
        return None
    if isinstance(date_val, (datetime, pd.Timestamp)):
        return date_val.date()
    if isinstance(date_val, str):
        for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y'):
            try:
                return datetime.strptime(date_val, fmt).date()
            except ValueError:
                continue
    return None


def import_bca_sem6():
    app = create_app()
    with app.app_context():
        file_path = r'c:\project\CMSv5\DATA FOR IMPORT EXPORT\BCA\BCA Sem 6 Bulk Student Data 2025 FOR SOFTWARE.xlsx'
        if not os.path.exists(file_path):
            print("Excel file not found.")
            return

        print("--- Step 1: Loading Excel Data for BCA Semester 6 ---")
        df = pd.read_excel(file_path)

        bca_program = db.session.execute(
            select(Program).filter(Program.program_name.like('%BCA%'))
        ).scalars().first()

        if not bca_program:
            print("BCA Program not found in database.")
            return

        program_id = bca_program.program_id
        trust_id = bca_program.institute.trust_id_fk
        print(f"Target Program: {bca_program.program_name} (ID: {program_id}, Trust: {trust_id})")

        print("--- Step 2: Deactivating existing BCA Semester 6 students ---")
        db.session.execute(
            update(Student)
            .where(
                Student.program_id_fk == program_id,
                Student.current_semester == 6
            )
            .values(is_active=False)
            .execution_options(synchronize_session=False)
        )
        db.session.flush()

        print("--- Step 3: Importing / Updating Semester 6 Students ---")
        stats = {"created_users": 0, "created_students": 0, "updated_students": 0}

        for index, row in df.iterrows():
            degree_program = str(row.get('Degree Program', '')).strip()
            if degree_program and 'bca' not in degree_program.lower():
                continue

            sem_raw = row.get('Semester')
            try:
                sem_val = int(sem_raw) if not pd.isna(sem_raw) else None
            except Exception:
                sem_val = None
            if sem_val is not None and sem_val != 6:
                continue

            enroll_raw = row.get('Enrollment Number')
            if pd.isna(enroll_raw):
                print(f"Skipping row {index+2}: Missing Enrollment Number")
                continue
            try:
                enrollment_no = str(int(enroll_raw))
            except Exception:
                print(f"Skipping row {index+2}: Invalid Enrollment Number {enroll_raw}")
                continue

            roll_raw = row.get('Roll No') if 'Roll No' in df.columns else row.get('RollNo')
            if pd.isna(roll_raw):
                print(f"Skipping row {index+2}: Missing RollNo")
                continue
            try:
                roll_num = int(roll_raw)
            except Exception:
                print(f"Skipping row {index+2}: Invalid RollNo {roll_raw}")
                continue
            roll_no = str(roll_num)

            div_raw = row.get('Division')
            if pd.isna(div_raw):
                print(f"Skipping row {index+2}: Missing Division")
                continue
            div_code = str(div_raw).strip().upper()
            if div_code and len(div_code) > 1:
                div_code = div_code[0]

            division = db.session.execute(
                select(Division).where(
                    Division.program_id_fk == program_id,
                    Division.semester == 6,
                    Division.division_code == div_code
                )
            ).scalars().first()
            if not division:
                print(f"Skipping row {index+2}: Division '{div_code}' not found for BCA Sem 6")
                continue
            division_id = division.division_id

            user = db.session.execute(select(User).filter_by(username=enrollment_no)).scalars().first()
            mobile_raw = row.get('Mobile')
            mobile = (
                str(int(mobile_raw))
                if pd.notnull(mobile_raw) and not isinstance(mobile_raw, str)
                else str(mobile_raw) if pd.notnull(mobile_raw) else None
            )

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
                password = mobile if mobile and len(mobile) >= 6 else generate_random_password()
                user.set_password(password)
                db.session.add(user)
                db.session.flush()
                stats["created_users"] += 1
            else:
                user.is_active = True
                user.trust_id_fk = trust_id
                if mobile:
                    user.mobile = mobile

            student = db.session.execute(select(Student).filter_by(enrollment_no=enrollment_no)).scalars().first()

            s_name = str(row.get('Student Name', '')).strip()
            s_surname = str(row.get('Surname', '')).strip()
            s_father = str(row.get("Father's Name", '')).strip()
            s_gender = str(row.get('Gender', 'Male')).strip()
            s_address = (
                str(row.get('Permanent Address', ''))[:255]
                if pd.notnull(row.get('Permanent Address')) else None
            )
            s_dob = parse_date(row.get('Date of Birth'))
            s_medium = str(row.get('Medium', 'English')).strip()
            aadhar_raw = row.get('Aadhar Card Number')
            s_aadhar = str(aadhar_raw).strip() if pd.notnull(aadhar_raw) else None
            category_raw = row.get('Category')
            s_category = str(category_raw).strip() if pd.notnull(category_raw) else None

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
                    roll_no=roll_no,
                    division_id_fk=division_id,
                    aadhar_no=s_aadhar,
                    category=s_category,
                    mobile=mobile,
                    email=user.email,
                    permanent_address=s_address,
                    current_semester=6,
                    date_of_birth=s_dob,
                    medium_tag=s_medium,
                    is_active=True
                )
                db.session.add(student)
                stats["created_students"] += 1
            else:
                student.student_name = s_name
                student.surname = s_surname
                student.father_name = s_father
                student.gender = s_gender
                student.roll_no = roll_no
                student.division_id_fk = division_id
                student.aadhar_no = s_aadhar
                student.category = s_category
                student.mobile = mobile
                student.current_semester = 6
                student.date_of_birth = s_dob
                student.medium_tag = s_medium
                student.is_active = True
                student.trust_id_fk = trust_id
                stats["updated_students"] += 1

        try:
            db.session.commit()
            print("--- SUCCESS (BCA Sem 6) ---")
            print(f"New Users Created: {stats['created_users']}")
            print(f"Students Created: {stats['created_students']}")
            print(f"Students Updated/Reactivated: {stats['updated_students']}")
        except Exception as e:
            db.session.rollback()
            print("--- ERROR (BCA Sem 6) ---")
            print(f"Failed to commit changes: {str(e)}")


if __name__ == "__main__":
    import_bca_sem6()

