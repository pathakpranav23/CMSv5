from cms_app import db
from cms_app.models import Institute, Program, ProgramIntakeBatch, Student, Trust, User


def _fixture(app, suffix, linked=False):
    with app.app_context():
        trust = Trust(trust_name=f"Intake Action Trust {suffix}", trust_code=f"IA{suffix}")
        db.session.add(trust)
        db.session.flush()
        institute = Institute(trust_id_fk=trust.trust_id, institute_name=f"Intake College {suffix}", institute_code=f"II{suffix}")
        db.session.add(institute)
        db.session.flush()
        program = Program(institute_id_fk=institute.institute_id, program_name=f"BCA Action {suffix}", program_duration_years=3)
        db.session.add(program)
        db.session.flush()
        batch = ProgramIntakeBatch(
            program_id_fk=program.program_id,
            admission_academic_year="2024-25",
            approved_intake=200,
            default_division_capacity=66,
            medium_tag="",
            status="active",
        )
        db.session.add(batch)
        db.session.flush()
        if linked:
            db.session.add(Student(
                enrollment_no=f"{suffix}001",
                program_id_fk=program.program_id,
                trust_id_fk=trust.trust_id,
                intake_batch_id_fk=batch.intake_batch_id,
                current_semester=1,
                is_active=True,
            ))
        user = User.query.filter_by(username="testuser").first()
        user.role = "admin"
        user.trust_id_fk = trust.trust_id
        db.session.commit()
        return user.user_id, program.program_id, batch.intake_batch_id


def _login(client, user_id):
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True
    client.get("/")
    with client.session_transaction() as session:
        return session["csrf_token"]


def test_unused_intake_can_be_deleted(app, client):
    user_id, program_id, batch_id = _fixture(app, "DEL")
    token = _login(client, user_id)
    response = client.post(
        f"/modules/program-intakes/{batch_id}/delete",
        data={"csrf_token": token},
        follow_redirects=False,
    )
    assert response.status_code == 302
    with app.app_context():
        assert db.session.get(ProgramIntakeBatch, batch_id) is None


def test_linked_intake_cannot_be_deleted_but_can_be_closed(app, client):
    user_id, program_id, batch_id = _fixture(app, "LINK", linked=True)
    token = _login(client, user_id)
    response = client.post(
        f"/modules/program-intakes/{batch_id}/delete",
        data={"csrf_token": token},
        follow_redirects=False,
    )
    assert response.status_code == 302
    with app.app_context():
        assert db.session.get(ProgramIntakeBatch, batch_id) is not None
    response = client.post(
        f"/modules/program-intakes/{batch_id}/status",
        data={"csrf_token": token, "status": "closed"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    with app.app_context():
        assert db.session.get(ProgramIntakeBatch, batch_id).status == "closed"
