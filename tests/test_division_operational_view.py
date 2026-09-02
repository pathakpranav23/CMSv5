from cms_app import db
from cms_app.models import Division, Institute, Program, ProgramIntakeBatch, Student, Trust, User


def _login(client, user_id):
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True
    client.get("/")
    with client.session_transaction() as session:
        return session["csrf_token"]


def _operational_fixture(app, suffix):
    with app.app_context():
        trust = Trust(trust_name=f"Operational Trust {suffix}", trust_code=f"OT{suffix}")
        db.session.add(trust)
        db.session.flush()
        institute = Institute(trust_id_fk=trust.trust_id, institute_name=f"Operational College {suffix}", institute_code=f"OC{suffix}")
        db.session.add(institute)
        db.session.flush()
        program = Program(institute_id_fk=institute.institute_id, program_name=f"Operational BCA {suffix}")
        db.session.add(program)
        db.session.flush()
        batch = ProgramIntakeBatch(
            program_id_fk=program.program_id,
            admission_academic_year="2026-27",
            approved_intake=4,
            default_division_capacity=2,
            medium_tag="",
            status="active",
        )
        occupied = Division(program_id_fk=program.program_id, semester=1, division_code="A", capacity=2)
        empty = Division(program_id_fk=program.program_id, semester=2, division_code="Z", capacity=2)
        db.session.add_all([batch, occupied, empty])
        db.session.flush()
        for index in range(2):
            db.session.add(Student(
                enrollment_no=f"{suffix}{index}",
                program_id_fk=program.program_id,
                trust_id_fk=trust.trust_id,
                division_id_fk=occupied.division_id,
                current_semester=1,
                admission_academic_year="2026-27",
                intake_batch_id_fk=batch.intake_batch_id,
                is_active=True,
            ))
        user = User.query.filter_by(username="testuser").first()
        user.role = "admin"
        user.trust_id_fk = trust.trust_id
        db.session.commit()
        return user.user_id, program.program_id


def test_division_view_hides_empty_records_and_reports_semester_intake(app, client):
    user_id, program_id = _operational_fixture(app, "VIEW")
    _login(client, user_id)
    response = client.get(f"/divisions?program_id={program_id}")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Semester 1" in body
    assert "2 / 4" in body
    assert "50.0%" in body
    assert ">Z<" not in body

    response = client.get(f"/divisions?program_id={program_id}&show_empty=1")
    assert response.status_code == 200
    assert ">Z<" in response.get_data(as_text=True)


def test_intake_settings_copy_to_next_year_as_draft(app, client):
    user_id, program_id = _operational_fixture(app, "COPY")
    token = _login(client, user_id)
    response = client.post(
        "/admin/workflows/new-academic-year/intakes",
        data={"csrf_token": token, "source_year": "2026-27", "target_year": "2027-28"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    with app.app_context():
        copied = ProgramIntakeBatch.query.filter_by(
            program_id_fk=program_id,
            admission_academic_year="2027-28",
        ).one()
        assert copied.status == "draft"
        assert copied.approved_intake == 4
        assert copied.default_division_capacity == 2
