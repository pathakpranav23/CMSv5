import os
import sys

# Ensure project root
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

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
    User,
)
from sqlalchemy import select, delete, update


# Remove only the language variant programs, keep generic BCOM intact
TARGET_PROGRAM_NAMES = ["BCom (English)", "BCom (Gujarati)"]


def remove_program_and_related(prog: Program):
    pid = prog.program_id
    pname = prog.program_name
    print(f"\n=== Removing program {pname} (id={pid}) and related data ===")

    # Collect IDs
    subject_ids = db.session.execute(select(Subject.subject_id).where(Subject.program_id_fk == pid)).scalars().all()
    division_ids = db.session.execute(select(Division.division_id).where(Division.program_id_fk == pid)).scalars().all()
    student_ids = db.session.execute(select(Student.enrollment_no).where(Student.program_id_fk == pid)).scalars().all()
    
    material_ids = []
    if subject_ids:
        material_ids = db.session.execute(
            select(SubjectMaterial.material_id).where(SubjectMaterial.subject_id_fk.in_(subject_ids))
        ).scalars().all()

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
    app = create_app()
    with app.app_context():
        targets = db.session.execute(
            select(Program).where(Program.program_name.in_(TARGET_PROGRAM_NAMES)).order_by(Program.program_name)
        ).scalars().all()
        if not targets:
            print("No target programs found. Nothing to remove.")
            return
        for prog in targets:
            remove_program_and_related(prog)
        db.session.commit()
        print("\nCompleted removal of target BCOM variants.")


if __name__ == "__main__":
    main()
