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


# Remove only the language variant programs, keep generic BCOM intact
TARGET_PROGRAM_NAMES = ["BCom (English)", "BCom (Gujarati)"]


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
    app = create_app()
    with app.app_context():
        targets = Program.query.filter(Program.program_name.in_(TARGET_PROGRAM_NAMES)).order_by(Program.program_name).all()
        if not targets:
            print("No target programs found. Nothing to remove.")
            return
        for prog in targets:
            remove_program_and_related(prog)
        db.session.commit()
        print("\nCompleted removal of target BCOM variants.")


if __name__ == "__main__":
    main()