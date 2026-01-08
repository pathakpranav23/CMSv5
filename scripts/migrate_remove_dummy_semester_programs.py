import os
import sys
import argparse

# Ensure project root
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from sqlalchemy import or_
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
    rows = Program.query.order_by(Program.program_name.asc()).all()
    targets = [p for p in rows if normalize_name(p.program_name) in target_set]
    return targets


def dependency_counts(pid: int):
    counts = {
        "divisions": Division.query.filter_by(program_id_fk=pid).count(),
        "subjects": Subject.query.filter_by(program_id_fk=pid).count(),
        "students": Student.query.filter_by(program_id_fk=pid).count(),
        "faculty": Faculty.query.filter_by(program_id_fk=pid).count(),
        "fees": FeeStructure.query.filter_by(program_id_fk=pid).count(),
        "announcements": Announcement.query.filter_by(program_id_fk=pid).count(),
        "plans": ProgramDivisionPlan.query.filter_by(program_id_fk=pid).count(),
    }
    # Linked via subjects/divisions/students
    subject_ids = [sid for (sid,) in db.session.query(Subject.subject_id).filter(Subject.program_id_fk == pid).all()]
    division_ids = [did for (did,) in db.session.query(Division.division_id).filter(Division.program_id_fk == pid).all()]
    student_ids = [enr for (enr,) in db.session.query(Student.enrollment_no).filter(Student.program_id_fk == pid).all()]
    material_ids = [mid for (mid,) in db.session.query(SubjectMaterial.material_id).filter(SubjectMaterial.subject_id_fk.in_(subject_ids)).all()] if subject_ids else []
    counts.update({
        "credit_structures": CreditStructure.query.filter(CreditStructure.subject_id_fk.in_(subject_ids)).count() if subject_ids else 0,
        "materials": len(material_ids),
        "material_logs": SubjectMaterialLog.query.filter(SubjectMaterialLog.material_id_fk.in_(material_ids)).count() if material_ids else 0,
        "assignments_subject": CourseAssignment.query.filter(CourseAssignment.subject_id_fk.in_(subject_ids)).count() if subject_ids else 0,
        "assignments_division": CourseAssignment.query.filter(CourseAssignment.division_id_fk.in_(division_ids)).count() if division_ids else 0,
        "enrollments_subject": StudentSubjectEnrollment.query.filter(StudentSubjectEnrollment.subject_id_fk.in_(subject_ids)).count() if subject_ids else 0,
        "enrollments_division": StudentSubjectEnrollment.query.filter(StudentSubjectEnrollment.division_id_fk.in_(division_ids)).count() if division_ids else 0,
        "enrollments_student": StudentSubjectEnrollment.query.filter(StudentSubjectEnrollment.student_id_fk.in_(student_ids)).count() if student_ids else 0,
        "attendance_subject": Attendance.query.filter(Attendance.subject_id_fk.in_(subject_ids)).count() if subject_ids else 0,
        "attendance_division": Attendance.query.filter(Attendance.division_id_fk.in_(division_ids)).count() if division_ids else 0,
        "attendance_student": Attendance.query.filter(Attendance.student_id_fk.in_(student_ids)).count() if student_ids else 0,
        "grades_subject": Grade.query.filter(Grade.subject_id_fk.in_(subject_ids)).count() if subject_ids else 0,
        "grades_division": Grade.query.filter(Grade.division_id_fk.in_(division_ids)).count() if division_ids else 0,
        "grades_student": Grade.query.filter(Grade.student_id_fk.in_(student_ids)).count() if student_ids else 0,
        "creditlog_subject": StudentCreditLog.query.filter(StudentCreditLog.subject_id_fk.in_(subject_ids)).count() if subject_ids else 0,
        "creditlog_student": StudentCreditLog.query.filter(StudentCreditLog.student_id_fk.in_(student_ids)).count() if student_ids else 0,
        "fees_records_student": FeesRecord.query.filter(FeesRecord.student_id_fk.in_(student_ids)).count() if student_ids else 0,
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
        deleted_logs = SubjectMaterialLog.query.filter(SubjectMaterialLog.material_id_fk.in_(material_ids)).delete(synchronize_session=False)
        print(f"Deleted SubjectMaterialLog: {deleted_logs}")
        deleted_mats = SubjectMaterial.query.filter(SubjectMaterial.material_id.in_(material_ids)).delete(synchronize_session=False)
        print(f"Deleted SubjectMaterial: {deleted_mats}")

    # Credit structures
    if subject_ids:
        deleted_cs = CreditStructure.query.filter(CreditStructure.subject_id_fk.in_(subject_ids)).delete(synchronize_session=False)
        print(f"Deleted CreditStructure: {deleted_cs}")

    # Assignments
    deleted_ca_sub = CourseAssignment.query.filter(CourseAssignment.subject_id_fk.in_(subject_ids)).delete(synchronize_session=False) if subject_ids else 0
    deleted_ca_div = CourseAssignment.query.filter(CourseAssignment.division_id_fk.in_(division_ids)).delete(synchronize_session=False) if division_ids else 0
    print(f"Deleted CourseAssignment (by subject): {deleted_ca_sub}, (by division): {deleted_ca_div}")

    # Enrollments, Attendance, Grades, Credit logs
    deleted_enr_sub = StudentSubjectEnrollment.query.filter(StudentSubjectEnrollment.subject_id_fk.in_(subject_ids)).delete(synchronize_session=False) if subject_ids else 0
    deleted_enr_div = StudentSubjectEnrollment.query.filter(StudentSubjectEnrollment.division_id_fk.in_(division_ids)).delete(synchronize_session=False) if division_ids else 0
    deleted_enr_stu = StudentSubjectEnrollment.query.filter(StudentSubjectEnrollment.student_id_fk.in_(student_ids)).delete(synchronize_session=False) if student_ids else 0
    print(f"Deleted StudentSubjectEnrollment (sub): {deleted_enr_sub}, (div): {deleted_enr_div}, (stu): {deleted_enr_stu}")

    deleted_att_sub = Attendance.query.filter(Attendance.subject_id_fk.in_(subject_ids)).delete(synchronize_session=False) if subject_ids else 0
    deleted_att_div = Attendance.query.filter(Attendance.division_id_fk.in_(division_ids)).delete(synchronize_session=False) if division_ids else 0
    deleted_att_stu = Attendance.query.filter(Attendance.student_id_fk.in_(student_ids)).delete(synchronize_session=False) if student_ids else 0
    print(f"Deleted Attendance (sub): {deleted_att_sub}, (div): {deleted_att_div}, (stu): {deleted_att_stu}")

    deleted_gra_sub = Grade.query.filter(Grade.subject_id_fk.in_(subject_ids)).delete(synchronize_session=False) if subject_ids else 0
    deleted_gra_div = Grade.query.filter(Grade.division_id_fk.in_(division_ids)).delete(synchronize_session=False) if division_ids else 0
    deleted_gra_stu = Grade.query.filter(Grade.student_id_fk.in_(student_ids)).delete(synchronize_session=False) if student_ids else 0
    print(f"Deleted Grade (sub): {deleted_gra_sub}, (div): {deleted_gra_div}, (stu): {deleted_gra_stu}")

    deleted_scl_sub = StudentCreditLog.query.filter(StudentCreditLog.subject_id_fk.in_(subject_ids)).delete(synchronize_session=False) if subject_ids else 0
    deleted_scl_stu = StudentCreditLog.query.filter(StudentCreditLog.student_id_fk.in_(student_ids)).delete(synchronize_session=False) if student_ids else 0
    print(f"Deleted StudentCreditLog (sub): {deleted_scl_sub}, (stu): {deleted_scl_stu}")

    # Fees
    deleted_fr = FeesRecord.query.filter(FeesRecord.student_id_fk.in_(student_ids)).delete(synchronize_session=False) if student_ids else 0
    print(f"Deleted FeesRecord: {deleted_fr}")
    deleted_fs = FeeStructure.query.filter(FeeStructure.program_id_fk == pid).delete(synchronize_session=False)
    print(f"Deleted FeeStructure: {deleted_fs}")

    # Announcements
    deleted_ann = Announcement.query.filter(Announcement.program_id_fk == pid).delete(synchronize_session=False)
    print(f"Deleted Announcement: {deleted_ann}")

    # Subjects, Students, Divisions, Plans, Faculty
    deleted_subj = Subject.query.filter(Subject.program_id_fk == pid).delete(synchronize_session=False)
    print(f"Deleted Subject: {deleted_subj}")

    deleted_stu = Student.query.filter(Student.program_id_fk == pid).delete(synchronize_session=False)
    print(f"Deleted Student: {deleted_stu}")

    deleted_div = Division.query.filter(Division.program_id_fk == pid).delete(synchronize_session=False)
    print(f"Deleted Division: {deleted_div}")

    deleted_plan = ProgramDivisionPlan.query.filter(ProgramDivisionPlan.program_id_fk == pid).delete(synchronize_session=False)
    print(f"Deleted ProgramDivisionPlan: {deleted_plan}")

    deleted_fac = Faculty.query.filter(Faculty.program_id_fk == pid).delete(synchronize_session=False)
    print(f"Deleted Faculty: {deleted_fac}")

    # Null out user program references to avoid FK constraint
    updated_users = User.query.filter(User.program_id_fk == pid).update({User.program_id_fk: None}, synchronize_session=False)
    print(f"Unlinked Users from program: {updated_users}")

    # Finally delete the Program
    deleted_prog = Program.query.filter(Program.program_id == pid).delete(synchronize_session=False)
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