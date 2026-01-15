import os
import sys
from typing import Dict

# Ensure project root is on sys.path when running from scripts/
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from cms_app import create_app, db
from cms_app.models import Program, Division, Student, StudentSubjectEnrollment
from sqlalchemy import select
import math

CAPACITY = 67


def _generate_codes(n: int):
    # Generate division codes like A, B, ..., Z, AA, AB, ...
    codes = []
    i = 0
    while len(codes) < n:
        num = i
        s = ""
        while True:
            s = chr(ord('A') + (num % 26)) + s
            num = num // 26 - 1
            if num < 0:
                break
        codes.append(s)
        i += 1
    return codes

def ensure_divisions(program: Program, semester: int, required_n: int) -> Dict[str, Division]:
    mapping: Dict[str, Division] = {}
    existing = db.session.execute(
        select(Division)
        .filter_by(program_id_fk=program.program_id, semester=semester)
        .order_by(Division.division_code.asc())
    ).scalars().all()
    # Update capacity for existing divisions
    for d in existing:
        if d.capacity != CAPACITY:
            d.capacity = CAPACITY
    db.session.commit()
    needed = max(required_n - len(existing), 0)
    if needed > 0:
        # Create new divisions with next codes
        used_codes = {d.division_code for d in existing}
        for code in _generate_codes(required_n):
            if code in used_codes:
                continue
            div = Division(program_id_fk=program.program_id, semester=semester, division_code=code, capacity=CAPACITY)
            db.session.add(div)
    db.session.commit()
    # Refresh and build mapping
    rows = db.session.execute(
        select(Division)
        .filter_by(program_id_fk=program.program_id, semester=semester)
        .order_by(Division.division_code.asc())
    ).scalars().all()
    for d in rows:
        mapping[d.division_code] = d
    return mapping


def assign_code(index: int, codes):
    # Determine division based on CAPACITY
    bucket = index // CAPACITY
    if bucket >= len(codes):
        bucket = len(codes) - 1
    return codes[bucket]


def rebalance_bca_divisions():
    app = create_app()
    with app.app_context():
        program = db.session.execute(
            select(Program).filter_by(program_name="BCA")
        ).scalars().first()
        if not program:
            print("Program BCA not found.")
            return

        # Determine semesters present among BCA students
        semesters = sorted({
            s.current_semester
            for s in db.session.execute(
                select(Student).filter_by(program_id_fk=program.program_id)
            ).scalars().all()
            if s.current_semester
        })
        total_updated = 0
        for sem in semesters:
            students = db.session.execute(
                select(Student)
                .filter_by(program_id_fk=program.program_id)
                .filter_by(current_semester=sem)
                .order_by(Student.enrollment_no.asc())
            ).scalars().all()
            required_n = max(math.ceil(len(students) / CAPACITY), 1)
            div_map = ensure_divisions(program, sem, required_n)
            codes = sorted(list(div_map.keys()))
            moved_students = []
            for idx, s in enumerate(students):
                code = assign_code(idx, codes)
                target_div = div_map[code]
                if s.division_id_fk != target_div.division_id:
                    s.division_id_fk = target_div.division_id
                    total_updated += 1
                    moved_students.append(s.enrollment_no)
            db.session.commit()
            # Post-rebalance: sync active StudentSubjectEnrollment.division_id_fk to student's current division
            sse_updates = 0
            if moved_students:
                # Fetch active enrollments for impacted students in this semester
                enr_rows = db.session.execute(
                    select(StudentSubjectEnrollment)
                    .where(StudentSubjectEnrollment.student_id_fk.in_(moved_students))
                    .filter_by(semester=sem, is_active=True)
                ).scalars().all()
                # Map student current division
                stu_map = {
                    s.enrollment_no: s
                    for s in db.session.execute(
                        select(Student).where(Student.enrollment_no.in_(moved_students))
                    ).scalars().all()
                }
                for enr in enr_rows:
                    stu = stu_map.get(enr.student_id_fk)
                    if not stu:
                        continue
                    if enr.division_id_fk != stu.division_id_fk:
                        enr.division_id_fk = stu.division_id_fk
                        sse_updates += 1
                db.session.commit()
            print(f"Semester {sem}: students={len(students)}, divisions={len(codes)}, moved={len(moved_students)}, sse_synced={sse_updates}, total_updated={total_updated}")

        print(f"Rebalancing complete. Total updated: {total_updated}")


def main():
    # Optional: accept program name in future; for now target BCA.
    rebalance_bca_divisions()


if __name__ == "__main__":
    main()
