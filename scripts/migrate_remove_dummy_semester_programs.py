import os
import sys
import argparse

# Ensure project root
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from sqlalchemy import or_, select, func, delete, update
from cms_app import create_app, db
from cms_app.models import (
    Program,
    Division,
    ProgramDivisionPlan,
    Subject,
    CreditStructure,
    SubjectMaterial,
    SubjectMaterialLog,
    CourseAssignment,
    Attendance,
    Grade,
    Student,
    StudentCreditLog,
    StudentSubjectEnrollment,
    FeeStructure,
    FeesRecord,
    Faculty,
    Announcement,
    User,
)


# Target dummy program names to remove (case-insensitive exact match)
TARGET_PROGRAM_NAMES = [
    # SEM variants
    "SEM-1", "SEM-2", "SEM-3", "SEM-4", "SEM-5", "SEM-6", "SEM-7", "SEM-8",
    # SEMESTER variants
    "SEMESTER-1", "SEMESTER-2", "SEMESTER-3", "SEMESTER-4",
    # Misc
    "TALLY",
]


def normalize_name(name: str) -> str:
    return (name or "").strip().lower()


def find_targets():
    target_set = {normalize_name(n) for n in TARGET_PROGRAM_NAMES}
    rows = db.session.execute(
        select(Program).order_by(Program.program_name.asc())
    ).scalars().all()
    targets = [p for p in rows if normalize_name(p.program_name) in target_set]
    return targets


def dependency_counts(pid: int):
    counts = {
        "divisions": db.session.execute(
            select(func.count()).select_from(Division).where(Division.program_id_fk == pid)
        ).scalar_one(),
        "subjects": db.session.execute(
            select(func.count()).select_from(Subject).where(Subject.program_id_fk == pid)
        ).scalar_one(),
        "students": db.session.execute(
            select(func.count()).select_from(Student).where(Student.program_id_fk == pid)
        ).scalar_one(),
        "faculty": db.session.execute(
            select(func.count()).select_from(Faculty).where(Faculty.program_id_fk == pid)
        ).scalar_one(),
        "fees": db.session.execute(
            select(func.count()).select_from(FeeStructure).where(FeeStructure.program_id_fk == pid)
        ).scalar_one(),
        "announcements": db.session.execute(
            select(func.count()).select_from(Announcement).where(Announcement.program_id_fk == pid)
        ).scalar_one(),
        "plans": db.session.execute(
            select(func.count()).select_from(ProgramDivisionPlan).where(ProgramDivisionPlan.program_id_fk == pid)
        ).scalar_one(),
    }
    # Linked via subjects/divisions/students
    subject_ids = db.session.execute(select(Subject.subject_id).where(Subject.program_id_fk == pid)).scalars().all()
    division_ids = db.session.execute(select(Division.division_id).where(Division.program_id_fk == pid)).scalars().all()
    student_ids = db.session.execute(select(Student.enrollment_no).where(Student.program_id_fk == pid)).scalars().all()
    
    material_ids = []
    if subject_ids:
        material_ids = db.session.execute(
            select(SubjectMaterial.material_id).where(SubjectMaterial.subject_id_fk.in_(subject_ids))
        ).scalars().all()
    counts.update({
        "credit_structures": db.session.execute(
            select(func.count()).select_from(CreditStructure).where(CreditStructure.subject_id_fk.in_(subject_ids))
        ).scalar_one() if subject_ids else 0,
        "materials": len(material_ids),
        "material_logs": db.session.execute(
            select(func.count()).select_from(SubjectMaterialLog).where(SubjectMaterialLog.material_id_fk.in_(material_ids))
        ).scalar_one() if material_ids else 0,
        "assignments_subject": db.session.execute(
            select(func.count()).select_from(CourseAssignment).where(CourseAssignment.subject_id_fk.in_(subject_ids))
        ).scalar_one() if subject_ids else 0,
        "assignments_division": db.session.execute(
            select(func.count()).select_from(CourseAssignment).where(CourseAssignment.division_id_fk.in_(division_ids))
        ).scalar_one() if division_ids else 0,
        "enrollments_subject": db.session.execute(
            select(func.count()).select_from(StudentSubjectEnrollment).where(StudentSubjectEnrollment.subject_id_fk.in_(subject_ids))
        ).scalar_one() if subject_ids else 0,
        "enrollments_division": db.session.execute(
            select(func.count()).select_from(StudentSubjectEnrollment).where(StudentSubjectEnrollment.division_id_fk.in_(division_ids))
        ).scalar_one() if division_ids else 0,
        "enrollments_student": db.session.execute(
            select(func.count()).select_from(StudentSubjectEnrollment).where(StudentSubjectEnrollment.student_id_fk.in_(student_ids))
        ).scalar_one() if student_ids else 0,
        "attendance_subject": db.session.execute(
            select(func.count()).select_from(Attendance).where(Attendance.subject_id_fk.in_(subject_ids))
        ).scalar_one() if subject_ids else 0,
        "attendance_division": db.session.execute(
            select(func.count()).select_from(Attendance).where(Attendance.division_id_fk.in_(division_ids))
        ).scalar_one() if division_ids else 0,
        "attendance_student": db.session.execute(
            select(func.count()).select_from(Attendance).where(Attendance.student_id_fk.in_(student_ids))
        ).scalar_one() if student_ids else 0,
        "grades_subject": db.session.execute(
            select(func.count()).select_from(Grade).where(Grade.subject_id_fk.in_(subject_ids))
        ).scalar_one() if subject_ids else 0,
        "grades_division": db.session.execute(
            select(func.count()).select_from(Grade).where(Grade.division_id_fk.in_(division_ids))
        ).scalar_one() if division_ids else 0,
        "grades_student": db.session.execute(
            select(func.count()).select_from(Grade).where(Grade.student_id_fk.in_(student_ids))
        ).scalar_one() if student_ids else 0,
        "creditlog_subject": db.session.execute(
            select(func.count()).select_from(StudentCreditLog).where(StudentCreditLog.subject_id_fk.in_(subject_ids))
        ).scalar_one() if subject_ids else 0,
        "creditlog_student": db.session.execute(
            select(func.count()).select_from(StudentCreditLog).where(StudentCreditLog.student_id_fk.in_(student_ids))
        ).scalar_one() if student_ids else 0,
        "fees_records_student": db.session.execute(
            select(func.count()).select_from(FeesRecord).where(FeesRecord.student_id_fk.in_(student_ids))
        ).scalar_one() if student_ids else 0,
    })
    return counts


def remove_program_and_related(prog: Program):
    pid = prog.program_id
    pname = prog.program_name
    print(f"\n=== Removing program {pname} (id={pid}) and related data ===")

    # Collect IDs
    subject_ids = [sid for (sid,) in db.session.query(Subject.subject_id).filter(Subject.program_id_fk == pid).all()]
    division_ids = [did for (did,) in db.session.query(Division.division_id).filter(Division.program_id_fk == pid).all()]
    student_ids = [enr for (enr,) in db.session.query(Student.enrollment_no).filter(Student.program_id_fk == pid).all()]
    material_ids = [mid for (mid,) in db.session.query(SubjectMaterial.material_id).filter(SubjectMaterial.subject_id_fk.in_(subject_ids)).all()] if subject_ids else []

    print(f"Subjects: {len(subject_ids)}, Divisions: {len(division_ids)}, Students: {len(student_ids)}, Materials: {len(material_ids)}")

    # Dependent logs and materials
    if material_ids:
        deleted_logs = db.session.execute(
            delete(SubjectMaterialLog).where(SubjectMaterialLog.material_id_fk.in_(material_ids))
        ).rowcount or 0
        print(f"Deleted SubjectMaterialLog: {deleted_logs}")
        deleted_mats = db.session.execute(
            delete(SubjectMaterial).where(SubjectMaterial.material_id.in_(material_ids))
        ).rowcount or 0
        print(f"Deleted SubjectMaterial: {deleted_mats}")

    # Credit structures
    if subject_ids:
        deleted_cs = db.session.execute(
            delete(CreditStructure).where(CreditStructure.subject_id_fk.in_(subject_ids))
        ).rowcount or 0
        print(f"Deleted CreditStructure: {deleted_cs}")

    # Assignments
    deleted_ca_sub = db.session.execute(
        delete(CourseAssignment).where(CourseAssignment.subject_id_fk.in_(subject_ids))
    ).rowcount if subject_ids else 0
    deleted_ca_div = db.session.execute(
        delete(CourseAssignment).where(CourseAssignment.division_id_fk.in_(division_ids))
    ).rowcount if division_ids else 0
    print(f"Deleted CourseAssignment (by subject): {deleted_ca_sub}, (by division): {deleted_ca_div}")

    # Enrollments, Attendance, Grades, Credit logs
    deleted_enr_sub = db.session.execute(
        delete(StudentSubjectEnrollment).where(StudentSubjectEnrollment.subject_id_fk.in_(subject_ids))
    ).rowcount if subject_ids else 0
    deleted_enr_div = db.session.execute(
        delete(StudentSubjectEnrollment).where(StudentSubjectEnrollment.division_id_fk.in_(division_ids))
    ).rowcount if division_ids else 0
    deleted_enr_stu = db.session.execute(
        delete(StudentSubjectEnrollment).where(StudentSubjectEnrollment.student_id_fk.in_(student_ids))
    ).rowcount if student_ids else 0
    print(f"Deleted StudentSubjectEnrollment (sub): {deleted_enr_sub}, (div): {deleted_enr_div}, (stu): {deleted_enr_stu}")

    deleted_att_sub = db.session.execute(
        delete(Attendance).where(Attendance.subject_id_fk.in_(subject_ids))
    ).rowcount if subject_ids else 0
    deleted_att_div = db.session.execute(
        delete(Attendance).where(Attendance.division_id_fk.in_(division_ids))
    ).rowcount if division_ids else 0
    deleted_att_stu = db.session.execute(
        delete(Attendance).where(Attendance.student_id_fk.in_(student_ids))
    ).rowcount if student_ids else 0
    print(f"Deleted Attendance (sub): {deleted_att_sub}, (div): {deleted_att_div}, (stu): {deleted_att_stu}")

    deleted_gra_sub = db.session.execute(
        delete(Grade).where(Grade.subject_id_fk.in_(subject_ids))
    ).rowcount if subject_ids else 0
    deleted_gra_div = db.session.execute(
        delete(Grade).where(Grade.division_id_fk.in_(division_ids))
    ).rowcount if division_ids else 0
    deleted_gra_stu = db.session.execute(
        delete(Grade).where(Grade.student_id_fk.in_(student_ids))
    ).rowcount if student_ids else 0
    print(f"Deleted Grade (sub): {deleted_gra_sub}, (div): {deleted_gra_div}, (stu): {deleted_gra_stu}")

    deleted_scl_sub = db.session.execute(
        delete(StudentCreditLog).where(StudentCreditLog.subject_id_fk.in_(subject_ids))
    ).rowcount if subject_ids else 0
    deleted_scl_stu = db.session.execute(
        delete(StudentCreditLog).where(StudentCreditLog.student_id_fk.in_(student_ids))
    ).rowcount if student_ids else 0
    print(f"Deleted StudentCreditLog (sub): {deleted_scl_sub}, (stu): {deleted_scl_stu}")

    # Fees
    deleted_fr = db.session.execute(
        delete(FeesRecord).where(FeesRecord.student_id_fk.in_(student_ids))
    ).rowcount if student_ids else 0
    print(f"Deleted FeesRecord: {deleted_fr}")
    deleted_fs = db.session.execute(
        delete(FeeStructure).where(FeeStructure.program_id_fk == pid)
    ).rowcount or 0
    print(f"Deleted FeeStructure: {deleted_fs}")

    # Announcements
    deleted_ann = db.session.execute(
        delete(Announcement).where(Announcement.program_id_fk == pid)
    ).rowcount or 0
    print(f"Deleted Announcement: {deleted_ann}")

    # Subjects, Students, Divisions, Plans, Faculty
    deleted_subj = db.session.execute(
        delete(Subject).where(Subject.program_id_fk == pid)
    ).rowcount or 0
    print(f"Deleted Subject: {deleted_subj}")

    deleted_stu = db.session.execute(
        delete(Student).where(Student.program_id_fk == pid)
    ).rowcount or 0
    print(f"Deleted Student: {deleted_stu}")

    deleted_div = db.session.execute(
        delete(Division).where(Division.program_id_fk == pid)
    ).rowcount or 0
    print(f"Deleted Division: {deleted_div}")

    deleted_plan = db.session.execute(
        delete(ProgramDivisionPlan).where(ProgramDivisionPlan.program_id_fk == pid)
    ).rowcount or 0
    print(f"Deleted ProgramDivisionPlan: {deleted_plan}")

    deleted_fac = db.session.execute(
        delete(Faculty).where(Faculty.program_id_fk == pid)
    ).rowcount or 0
    print(f"Deleted Faculty: {deleted_fac}")

    # Null out user program references to avoid FK constraint
    updated_users = db.session.execute(
        update(User).where(User.program_id_fk == pid).values(program_id_fk=None)
    ).rowcount or 0
    print(f"Unlinked Users from program: {updated_users}")

    # Finally delete the Program
    deleted_prog = db.session.execute(
        delete(Program).where(Program.program_id == pid)
    ).rowcount or 0
    print(f"Deleted Program row: {deleted_prog}")


def main():
    parser = argparse.ArgumentParser(description="Remove dummy semester programs and all related data.")
    parser.add_argument("--dry-run", action="store_true", help="Print dependency counts without deleting.")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        targets = find_targets()
        if not targets:
            print("No target programs found. Nothing to remove.")
            return
        print("Targets:")
        for p in targets:
            print(f" - {p.program_name} (id={p.program_id})")
        if args.dry_run:
            print("\nDry-run dependency counts:")
            for p in targets:
                counts = dependency_counts(p.program_id)
                summary = ", ".join([f"{k}={v}" for k, v in counts.items() if v]) or "no dependencies"
                print(f" {p.program_name}: {summary}")
            return
        # Execute deletion
        for prog in targets:
            remove_program_and_related(prog)
        db.session.commit()
        print("\nCompleted removal of dummy semester programs.")


if __name__ == "__main__":
    main()
