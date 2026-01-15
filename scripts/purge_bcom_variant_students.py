import os
import sys

# Ensure project root
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from cms_app import create_app, db
from cms_app.models import (
    Program,
    Student,
    Attendance,
    Grade,
    StudentCreditLog,
    FeesRecord,
    AnnouncementRecipient,
    User,
)
from sqlalchemy import select, delete


def normalize_name(s: str) -> str:
    s = (s or "").strip().upper()
    s = s.replace(".", "").replace("_", " ").replace("-", " ")
    return s


def is_bcom_english(name: str) -> bool:
    n = normalize_name(name)
    if "BCOM" in n and "ENGLISH" in n:
        return True
    return n in ("BCOME",)


def is_bcom_gujarati(name: str) -> bool:
    n = normalize_name(name)
    if "BCOM" in n and "GUJARATI" in n:
        return True
    return n in ("BCOMG",)


def purge_students_for_program(prog: Program) -> None:
    print(f"\n=== Purging students for program: {prog.program_name} (id={prog.program_id}) ===")
    # Collect student IDs (enrollment_no)
    student_ids = db.session.execute(
        select(Student.enrollment_no).where(Student.program_id_fk == prog.program_id)
    ).scalars().all()
    print(f"Students to delete: {len(student_ids)}")
    if not student_ids:
        return

    # Dependent tables first
    deleted_enr = db.session.execute(
        delete(Attendance).where(Attendance.student_id_fk.in_(student_ids))
    ).rowcount or 0
    print(f"Deleted Attendance: {deleted_enr}")
    deleted_grade = db.session.execute(
        delete(Grade).where(Grade.student_id_fk.in_(student_ids))
    ).rowcount or 0
    print(f"Deleted Grade: {deleted_grade}")
    deleted_scl = db.session.execute(
        delete(StudentCreditLog).where(StudentCreditLog.student_id_fk.in_(student_ids))
    ).rowcount or 0
    print(f"Deleted StudentCreditLog: {deleted_scl}")
    deleted_fees = db.session.execute(
        delete(FeesRecord).where(FeesRecord.student_id_fk.in_(student_ids))
    ).rowcount or 0
    print(f"Deleted FeesRecord: {deleted_fees}")
    deleted_ann = db.session.execute(
        delete(AnnouncementRecipient).where(AnnouncementRecipient.student_id_fk.in_(student_ids))
    ).rowcount or 0
    print(f"Deleted AnnouncementRecipient: {deleted_ann}")

    # Finally delete Student rows
    deleted_students = db.session.execute(
        delete(Student).where(Student.program_id_fk == prog.program_id)
    ).rowcount or 0
    print(f"Deleted Student: {deleted_students}")

    # Clean up linked users with role Student
    try:
        users_to_delete = db.session.execute(
            select(User).where(
                User.role == "Student",
                User.program_id_fk == prog.program_id,
            )
        ).scalars().all()
        cnt_users = len(users_to_delete)
        for u in users_to_delete:
            db.session.delete(u)
        print(f"Deleted linked User accounts (role=Student): {cnt_users}")
    except Exception as e:
        print(f"Skipping user cleanup due to error: {e}")


def main():
    app = create_app()
    with app.app_context():
        targets = []
        for p in db.session.execute(
            select(Program).order_by(Program.program_name)
        ).scalars().all():
            if is_bcom_english(p.program_name or "") or is_bcom_gujarati(p.program_name or ""):
                targets.append(p)
        if not targets:
            print("No BCom English/Gujarati programs found. Nothing to purge.")
            return
        for prog in targets:
            purge_students_for_program(prog)
        db.session.commit()
        print("\nCompleted purge of BCom English/Gujarati students.")


if __name__ == "__main__":
    main()
