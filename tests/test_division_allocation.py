from cms_app import db
from cms_app.models import (
    Division,
    Institute,
    Program,
    ProgramDivisionPlan,
    ProgramIntakeBatch,
    Student,
    StudentSubjectEnrollment,
    Subject,
    SubjectType,
    Trust,
)
from cms_app.services.division_allocation import apply_allocation, build_allocation_preview


def _division_fixture(app, suffix="A", students=5, capacity=3, planned=2):
    with app.app_context():
        trust = Trust(trust_name=f"Division Trust {suffix}", trust_code=f"DT{suffix}")
        db.session.add(trust)
        db.session.flush()
        institute = Institute(trust_id_fk=trust.trust_id, institute_name=f"Division Institute {suffix}", institute_code=f"DI{suffix}")
        db.session.add(institute)
        db.session.flush()
        program = Program(institute_id_fk=institute.institute_id, program_name=f"Division Program {suffix}", program_code=f"DP{suffix}")
        db.session.add(program)
        db.session.flush()
        divisions = [Division(program_id_fk=program.program_id, semester=1, division_code=code, capacity=capacity) for code in ("A", "B")]
        db.session.add_all(divisions)
        db.session.add(ProgramDivisionPlan(program_id_fk=program.program_id, semester=1, num_divisions=planned, capacity_per_division=capacity))
        subject_type = SubjectType(type_name=f"Major {suffix}", type_code=f"M{suffix}")
        db.session.add(subject_type)
        db.session.flush()
        subject = Subject(program_id_fk=program.program_id, subject_type_id_fk=subject_type.type_id, semester=1, subject_name=f"Subject {suffix}", subject_code=f"S{suffix}")
        db.session.add(subject)
        db.session.flush()
        for index in range(students):
            student = Student(enrollment_no=f"{suffix}{index:03}", program_id_fk=program.program_id, division_id_fk=divisions[0].division_id, trust_id_fk=trust.trust_id, current_semester=1, is_active=True)
            db.session.add(student)
            db.session.add(StudentSubjectEnrollment(student_id_fk=student.enrollment_no, subject_id_fk=subject.subject_id, semester=1, division_id_fk=divisions[0].division_id, academic_year="2026-27", is_active=True))
        db.session.commit()
        return trust.trust_id, program.program_id


def test_preview_balances_without_mutating(app):
    trust_id, program_id = _division_fixture(app, "P", students=5)
    with app.app_context():
        preview = build_allocation_preview(program_id, 1, approved_intake=6, trust_id=trust_id)
        assert preview.can_apply
        assert [row["proposed"] for row in preview.divisions] == [3, 2]
        assert len(preview.moves) == 2
        assert Student.query.filter_by(program_id_fk=program_id, division_id_fk=preview.divisions[0]["division"].division_id).count() == 5


def test_preview_blocks_intake_and_capacity_breach(app):
    trust_id, program_id = _division_fixture(app, "B", students=7)
    with app.app_context():
        preview = build_allocation_preview(program_id, 1, approved_intake=6, trust_id=trust_id)
        assert not preview.can_apply
        assert any("approved annual intake" in error for error in preview.errors)
        assert preview.required_divisions == 3
        assert any("Division C" in error for error in preview.errors)


def test_operational_count_uses_enrollment_not_stale_planned_count(app):
    trust_id, program_id = _division_fixture(app, "O", students=5, capacity=3, planned=3)
    with app.app_context():
        preview = build_allocation_preview(
            program_id,
            1,
            approved_intake=10,
            trust_id=trust_id,
            intake_division_capacity=3,
        )
        assert preview.required_divisions == 2
        assert preview.planned_divisions == 3
        assert [row["code"] for row in preview.divisions] == ["A", "B"]
        assert [row["proposed"] for row in preview.divisions] == [3, 2]
        assert any("current enrollment requires 2" in warning for warning in preview.warnings)


def test_apply_moves_students_and_syncs_current_enrollments(app):
    trust_id, program_id = _division_fixture(app, "S", students=5)
    with app.app_context():
        preview = build_allocation_preview(program_id, 1, approved_intake=6, trust_id=trust_id)
        target_id = preview.divisions[1]["division"].division_id
        result = apply_allocation(preview, preview.fingerprint)
        db.session.commit()
        assert result == {"students_moved": 2, "subject_enrollments_synced": 2}
        assert Student.query.filter_by(program_id_fk=program_id, division_id_fk=target_id).count() == 2
        assert StudentSubjectEnrollment.query.filter_by(division_id_fk=target_id, is_active=True).count() == 2


def test_manual_override_is_capacity_checked_and_applied(app):
    trust_id, program_id = _division_fixture(app, "M", students=5)
    with app.app_context():
        preview = build_allocation_preview(program_id, 1, approved_intake=6, trust_id=trust_id)
        first = preview.assignments[0]
        target_id = preview.divisions[1]["division"].division_id
        result = apply_allocation(preview, preview.fingerprint, {first.enrollment_no: "B"})
        db.session.commit()
        assert result["students_moved"] == 3
        assert Student.query.filter_by(program_id_fk=program_id, division_id_fk=target_id).count() == 3


def test_stored_intake_batch_scopes_students_without_guessing(app):
    trust_id, program_id = _division_fixture(app, "I", students=5)
    with app.app_context():
        batch = ProgramIntakeBatch(
            program_id_fk=program_id,
            admission_academic_year="2026-27",
            approved_intake=6,
            default_division_capacity=3,
            medium_tag="",
            status="active",
        )
        db.session.add(batch)
        db.session.flush()
        mapped = Student.query.filter_by(program_id_fk=program_id).order_by(Student.enrollment_no).limit(3).all()
        for student in mapped:
            student.admission_academic_year = "2026-27"
            student.intake_batch_id_fk = batch.intake_batch_id
        db.session.commit()
        preview = build_allocation_preview(
            program_id,
            1,
            approved_intake=batch.approved_intake,
            trust_id=trust_id,
            intake_batch_id=batch.intake_batch_id,
            admission_academic_year=batch.admission_academic_year,
            intake_division_capacity=batch.default_division_capacity,
        )
        assert preview.active_students == 3
        assert any("2 active student(s)" in warning for warning in preview.warnings)
