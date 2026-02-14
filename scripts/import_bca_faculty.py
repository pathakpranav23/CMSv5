import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cms_app import create_app, db
from cms_app.models import User, Faculty, Program
from sqlalchemy import select
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
        try:
            return datetime.strptime(date_val, '%Y-%m-%d').date()
        except:
            try:
                return datetime.strptime(date_val, '%d/%m/%Y').date()
            except:
                return None
    return None

def import_faculty_data():
    app = create_app()
    with app.app_context():
        file_path = r'c:\project\CMSv5\DATA FOR IMPORT EXPORT\BCA\BCA Staff info.xlsx'
        if not os.path.exists(file_path):
            print(f"Excel file not found at {file_path}")
            return

        print("--- Step 1: Loading Faculty Excel Data ---")
        df = pd.read_excel(file_path, sheet_name='Sheet1')
        
        # Identify BCA Program for default linking
        bca_program = db.session.execute(
            select(Program).filter(Program.program_name.like('%BCA%'))
        ).scalars().first()
        
        if not bca_program:
            print("BCA Program not found in database.")
            return
            
        program_id = bca_program.program_id
        trust_id = bca_program.institute.trust_id_fk
        print(f"Linking to Program: {bca_program.program_name} (ID: {program_id}, Trust: {trust_id})")

        stats = {"created_users": 0, "created_faculty": 0, "updated_faculty": 0}

        for _, row in df.iterrows():
            emp_id = str(row.get('EmpId', '')).strip()
            if not emp_id or emp_id == 'nan':
                continue
                
            email = str(row.get('Email ID', '')).strip().lower()
            if not email or email == 'nan':
                # Use EmpId as username if email missing
                username = emp_id.lower()
                email = f"{username}@sbpet.edu.in"
            else:
                username = email

            full_name = str(row.get('Faculty Name', '')).strip()
            mobile_raw = row.get('Mobile No')
            # Handle mobile number string/float issues
            if pd.isna(mobile_raw):
                mobile = None
            else:
                mobile = str(mobile_raw).replace(' ', '').replace('.0', '')
            
            designation = str(row.get('Designation ', '')).strip()
            qualification = str(row.get('Qualification', '')).strip()
            specialization = str(row.get('Subject\n Specialization', '')).strip()
            doj = parse_date(row.get('DOJ'))
            dob = parse_date(row.get('DOB'))

            # 1. Handle User Account
            user = db.session.execute(select(User).filter((User.username == username) | (User.email == email))).scalars().first()
            
            if not user:
                user = User(
                    username=username,
                    email=email,
                    mobile=mobile,
                    role='faculty',
                    trust_id_fk=trust_id,
                    program_id_fk=program_id,
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
                # Update existing user
                user.role = 'faculty'
                user.trust_id_fk = trust_id
                if not user.program_id_fk:
                    user.program_id_fk = program_id
                if mobile: user.mobile = mobile
                user.is_active = True

            # 2. Handle Faculty Profile
            faculty = db.session.execute(select(Faculty).filter_by(emp_id=emp_id)).scalars().first()
            if not faculty:
                # Try finding by user_id
                faculty = db.session.execute(select(Faculty).filter_by(user_id_fk=user.user_id)).scalars().first()

            if not faculty:
                faculty = Faculty(
                    user_id_fk=user.user_id,
                    program_id_fk=program_id,
                    trust_id_fk=trust_id,
                    emp_id=emp_id,
                    full_name=full_name,
                    email=email,
                    mobile=mobile,
                    designation=designation,
                    highest_qualification=qualification,
                    specialization=specialization,
                    date_of_joining=doj,
                    is_active=True
                )
                db.session.add(faculty)
                stats["created_faculty"] += 1
            else:
                # Update existing faculty
                faculty.full_name = full_name
                faculty.email = email
                faculty.mobile = mobile
                faculty.designation = designation
                faculty.highest_qualification = qualification
                faculty.specialization = specialization
                faculty.date_of_joining = doj
                faculty.trust_id_fk = trust_id
                faculty.is_active = True
                stats["updated_faculty"] += 1

        try:
            db.session.commit()
            print(f"--- SUCCESS ---")
            print(f"New Users Created: {stats['created_users']}")
            print(f"Faculty Created: {stats['created_faculty']}")
            print(f"Faculty Updated: {stats['updated_faculty']}")
        except Exception as e:
            db.session.rollback()
            print(f"--- ERROR ---")
            print(f"Failed to commit changes: {str(e)}")

if __name__ == "__main__":
    import_faculty_data()
