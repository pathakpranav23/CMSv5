import os
import sys
import csv
import random
import string

# Ensure project root on path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from cms_app import create_app, db
from cms_app.models import User, Student, Division, Program
from werkzeug.security import generate_password_hash


def gen_password(length: int = 10) -> str:
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


def compute_roll_numbers() -> dict:
    """Compute roll numbers per division, ordered by enrollment_no."""
    rolls = {}
    divisions = Division.query.order_by(Division.program_id_fk.asc(), Division.semester.asc(), Division.division_code.asc()).all()
    for d in divisions:
        stu_rows = Student.query.filter_by(division_id_fk=d.division_id).order_by(Student.enrollment_no.asc()).all()
        for idx, s in enumerate(stu_rows, start=1):
            rolls[s.enrollment_no] = idx
    return rolls


def ensure_student_user(student: Student) -> tuple:
    """Create or update a user for the given student.

    Returns: (username, plain_password, user_obj)
    """
    username = (student.enrollment_no or '').strip()
    if not username:
        # Fallback to generated username if enrollment missing
        base = (student.student_name or 'student').replace(' ', '').lower()
        username = f"{base}{random.randint(1000,9999)}"

    user = User.query.filter_by(username=username).first()
    plain_password = gen_password(10)
    password_hash = generate_password_hash(plain_password)

    # Determine program id
    program_id = student.program_id_fk
    # Role as lowercase 'student' to match role checks
    role = 'student'

    if not user:
        user = User(username=username, password_hash=password_hash, role=role, program_id_fk=program_id)
        db.session.add(user)
        db.session.flush()  # assign user_id
    else:
        # Update role/program if missing; refresh password each run
        user.role = role
        user.program_id_fk = program_id
        user.password_hash = password_hash

    # Link student to user
    student.user_id_fk = user.user_id
    return username, plain_password, user


def generate_csv(output_path: str) -> None:
    rolls = compute_roll_numbers()
    students = Student.query.order_by(Student.program_id_fk.asc(), Student.division_id_fk.asc(), Student.enrollment_no.asc()).all()

    rows = []
    for s in students:
        username, plain_password, _u = ensure_student_user(s)
        division = Division.query.get(s.division_id_fk) if s.division_id_fk else None
        div_code = division.division_code if division else ''
        semester = s.current_semester or (division.semester if division else None)
        roll_no = rolls.get(s.enrollment_no) or ''
        full_name = f"{(s.surname or '').strip()} {(s.student_name or '').strip()}".strip() or (s.student_name or '')
        rows.append([
            s.enrollment_no,
            roll_no,
            full_name,
            semester,
            div_code,
            username,
            plain_password,
        ])

    # Commit DB changes (users + student links)
    db.session.commit()

    # Write CSV
    headers = [
        'enrollment_no', 'roll_number', 'name', 'semester', 'division', 'username', 'password'
    ]
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)

    print(f"Generated CSV: {output_path} (rows={len(rows)})")


def main():
    app = create_app()
    with app.app_context():
        out_path = os.path.join(BASE_DIR, 'student_users.csv')
        generate_csv(out_path)


if __name__ == '__main__':
    main()