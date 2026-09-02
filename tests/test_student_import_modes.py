from openpyxl import Workbook

from cms_app import db
from cms_app.models import Institute, Program, ProgramIntakeBatch, Student, Trust
from scripts.import_students import import_excel


def _scope(app, suffix, approved_intake=None):
    with app.app_context():
        trust = Trust(trust_name=f"Import Trust {suffix}", trust_code=f"IM{suffix}")
        db.session.add(trust)
        db.session.flush()
        institute = Institute(
            trust_id_fk=trust.trust_id,
            institute_name=f"Import College {suffix}",
            institute_code=f"IC{suffix}",
        )
        db.session.add(institute)
        db.session.flush()
        program = Program(
            institute_id_fk=institute.institute_id,
            program_name=f"BCA Import {suffix}",
            program_code=f"BI{suffix}",
            program_duration_years=3,
        )
        db.session.add(program)
        db.session.flush()
        if approved_intake is not None:
            db.session.add(ProgramIntakeBatch(
                program_id_fk=program.program_id,
                admission_academic_year="2026-27",
                approved_intake=approved_intake,
                default_division_capacity=67,
                medium_tag="English",
                status="active",
            ))
        db.session.commit()
        return trust.trust_id, program.program_id


def _workbook(tmp_path, name, rows):
    path = tmp_path / name
    wb = Workbook()
    ws = wb.active
    ws.append(["enrollment_no", "student_name", "current_semester", "admission_academic_year", "medium_tag"])
    for row in rows:
        ws.append(row)
    wb.save(path)
    return str(path)


def test_existing_student_import_records_historical_batch_without_intake_link(app, tmp_path):
    trust_id, program_id = _scope(app, "EX")
    path = _workbook(tmp_path, "existing.xlsx", [["EX001", "Existing Student", 3, "2025-26", "English"]])

    with app.app_context():
        report = import_excel(
            path,
            program_id=program_id,
            trust_id=trust_id,
            semester_hint=3,
            import_mode="existing",
            admission_academic_year_hint="2025-26",
            medium_hint="English",
        )
        student = db.session.get(Student, "EX001")
        assert student.admission_academic_year == "2025-26"
        assert student.intake_batch_id_fk is None
        assert report["completion_academic_year"] == "2028-29"


def test_import_is_additive_and_does_not_delete_omitted_students(app, tmp_path):
    trust_id, program_id = _scope(app, "ADD")
    with app.app_context():
        db.session.add(Student(
            enrollment_no="ADD-KEEP",
            trust_id_fk=trust_id,
            program_id_fk=program_id,
            current_semester=3,
            medium_tag="English",
            is_active=True,
        ))
        db.session.commit()
    path = _workbook(tmp_path, "additive.xlsx", [["ADD-NEW", "New Row", 3, "2025-26", "English"]])

    with app.app_context():
        report = import_excel(
            path,
            program_id=program_id,
            trust_id=trust_id,
            semester_hint=3,
            import_mode="existing",
            admission_academic_year_hint="2025-26",
            medium_hint="English",
        )
        assert db.session.get(Student, "ADD-KEEP") is not None
        assert report["deleted"] == 0


def test_new_admission_requires_and_enforces_approved_intake(app, tmp_path):
    trust_id, program_id = _scope(app, "NEW", approved_intake=1)
    path = _workbook(tmp_path, "new.xlsx", [
        ["NEW001", "First", 1, "2026-27", "English"],
        ["NEW002", "Second", 1, "2026-27", "English"],
    ])

    with app.app_context():
        try:
            import_excel(
                path,
                program_id=program_id,
                trust_id=trust_id,
                semester_hint=1,
                import_mode="new",
                admission_academic_year_hint="2026-27",
                medium_hint="English",
            )
        except ValueError as exc:
            assert "Approved intake exceeded" in str(exc)
        else:
            raise AssertionError("import exceeding approved intake was accepted")
        assert db.session.get(Student, "NEW001") is None
        assert db.session.get(Student, "NEW002") is None


def test_conflicting_spreadsheet_scope_is_skipped(app, tmp_path):
    trust_id, program_id = _scope(app, "CON")
    path = _workbook(tmp_path, "conflict.xlsx", [["CON001", "Conflict", 5, "2024-25", "Gujarati"]])

    with app.app_context():
        report = import_excel(
            path,
            program_id=program_id,
            trust_id=trust_id,
            semester_hint=3,
            import_mode="existing",
            admission_academic_year_hint="2025-26",
            medium_hint="English",
        )
        assert report["skipped"] == 1
        assert db.session.get(Student, "CON001") is None
        assert report["preview_total"] == 1
        assert report["preview_rows"][0]["action"] == "skip"
        assert report["preview_rows"][0]["status"] == "error"


def test_numeric_admission_start_year_matches_selected_academic_year(app, tmp_path):
    trust_id, program_id = _scope(app, "YEAR", approved_intake=10)
    path = _workbook(tmp_path, "numeric-year.xlsx", [["YEAR001", "Numeric Year", 1, 2026, "English"]])

    with app.app_context():
        report = import_excel(
            path,
            program_id=program_id,
            trust_id=trust_id,
            semester_hint=1,
            import_mode="new",
            admission_academic_year_hint="2026-27",
            medium_hint="English",
        )
        student = db.session.get(Student, "YEAR001")
        assert report["created"] == 1
        assert report["skipped"] == 0
        assert student.admission_academic_year == "2026-27"
        assert report["preview_rows"] == [{
            "row_number": 2,
            "enrollment_no": "YEAR001",
            "roll_no": "",
            "student_name": "Numeric Year",
            "admission_academic_year": "2026-27",
            "semester": 1,
            "medium_tag": "English",
            "division_code": "Unassigned",
            "action": "create",
            "status": "valid",
            "reason": "",
        }]
