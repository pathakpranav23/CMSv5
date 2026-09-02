from cms_app import db
from cms_app.models import Institute, Program, Student, Trust
from cms_app.services.opening_cohorts import apply_opening_cohort_preview, build_opening_cohort_preview


def _opening_fixture(app, suffix):
    with app.app_context():
        trust = Trust(trust_name=f"Opening Cohort Trust {suffix}", trust_code=f"OC{suffix}")
        db.session.add(trust)
        db.session.flush()
        institute = Institute(trust_id_fk=trust.trust_id, institute_name=f"Opening College {suffix}", institute_code=f"OI{suffix}")
        db.session.add(institute)
        db.session.flush()
        program = Program(
            institute_id_fk=institute.institute_id,
            program_name=f"BCA Opening {suffix}",
            program_code=f"BC{suffix}",
            program_duration_years=3,
        )
        db.session.add(program)
        db.session.flush()
        rows = [
            Student(enrollment_no=f"{suffix}OPEN1", program_id_fk=program.program_id, trust_id_fk=trust.trust_id, current_semester=1, is_active=True),
            Student(enrollment_no=f"{suffix}OPEN3", program_id_fk=program.program_id, trust_id_fk=trust.trust_id, current_semester=3, is_active=True),
            Student(enrollment_no=f"{suffix}OPEN5", program_id_fk=program.program_id, trust_id_fk=trust.trust_id, current_semester=5, is_active=True),
            Student(enrollment_no=f"{suffix}BAD0", program_id_fk=program.program_id, trust_id_fk=trust.trust_id, current_semester=0, is_active=True),
            Student(enrollment_no=f"{suffix}KNOWN", program_id_fk=program.program_id, trust_id_fk=trust.trust_id, current_semester=5, admission_academic_year="2023-24", is_active=True),
        ]
        db.session.add_all(rows)
        db.session.commit()
        return trust.trust_id, program.program_id


def test_opening_preview_shows_start_and_completion_years(app):
    trust_id, program_id = _opening_fixture(app, "A")
    with app.app_context():
        preview = build_opening_cohort_preview(program_id, "2026-27", trust_id)
        assert preview.proposed_count == 3
        assert len(preview.preserved_students) == 1
        assert len(preview.exceptions) == 1
        rows = {
            group.current_stage: (group.admission_academic_year, group.completion_academic_year)
            for group in preview.proposed_groups
        }
        assert rows == {
            "Year 1": ("2026-27", "2028-29"),
            "Year 2": ("2025-26", "2027-28"),
            "Year 3": ("2024-25", "2026-27"),
        }


def test_opening_apply_only_fills_blank_admission_years(app):
    trust_id, program_id = _opening_fixture(app, "B")
    with app.app_context():
        preview = build_opening_cohort_preview(program_id, "2026-27", trust_id)
        assert apply_opening_cohort_preview(preview, preview.fingerprint) == 3
        db.session.commit()
        assert db.session.get(Student, "BOPEN1").admission_academic_year == "2026-27"
        assert db.session.get(Student, "BOPEN3").admission_academic_year == "2025-26"
        assert db.session.get(Student, "BOPEN5").admission_academic_year == "2024-25"
        assert db.session.get(Student, "BKNOWN").admission_academic_year == "2023-24"
        assert db.session.get(Student, "BBAD0").admission_academic_year is None


def test_opening_apply_rejects_stale_preview(app):
    trust_id, program_id = _opening_fixture(app, "C")
    with app.app_context():
        preview = build_opening_cohort_preview(program_id, "2026-27", trust_id)
        try:
            apply_opening_cohort_preview(preview, "stale")
        except ValueError as exc:
            assert "fresh preview" in str(exc)
        else:
            raise AssertionError("stale preview was accepted")
