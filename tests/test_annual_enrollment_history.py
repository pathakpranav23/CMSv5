from werkzeug.security import generate_password_hash

from cms_app import db
from cms_app.models import AcademicYear, Institute, Program, Student, StudentAcademicEnrollment, Trust, User
from cms_app.main.routes import current_academic_year, _next_academic_year_label


def _login(client, username):
    client.post("/login", data={"username": username, "password": "secret"}, follow_redirects=True)
    client.get("/")
    with client.session_transaction() as session:
        return session["csrf_token"]


def _seed(app):
    with app.app_context():
        trust = Trust(trust_name="Annual History Trust", trust_code="AHT")
        db.session.add(trust)
        db.session.flush()
        institute = Institute(trust_id_fk=trust.trust_id, institute_name="Annual History College", institute_code="AHC")
        db.session.add(institute)
        db.session.flush()
        program = Program(institute_id_fk=institute.institute_id, program_name="BCA-HISTORY", program_duration_years=3)
        db.session.add(program)
        db.session.flush()
        user = User(username="annual-history-admin", password_hash=generate_password_hash("secret"), role="admin", trust_id_fk=trust.trust_id)
        student = Student(
            enrollment_no="AH-001", program_id_fk=program.program_id, trust_id_fk=trust.trust_id,
            student_name="History", surname="Student", current_semester=1,
            admission_academic_year=current_academic_year(), gender="Female", category="SEBC", medium_tag="English", is_active=True,
            permanent_address="Station Road, Kalsar, Bhavnagar", home_city="Kalsar", home_district="Bhavnagar",
        )
        db.session.add_all([user, student])
        db.session.commit()
        return trust.trust_id, program.program_id


def test_initialize_history_and_render_report(client, app):
    _, program_id = _seed(app)
    token = _login(client, "annual-history-admin")
    year = current_academic_year()
    response = client.post(
        "/annual-enrollment-history/initialize",
        data={"csrf_token": token, "academic_year": year}, follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Annual Enrollment History" in response.data
    assert b"History Student" in response.data
    with app.app_context():
        row = StudentAcademicEnrollment.query.filter_by(student_id_fk="AH-001", academic_year=year).one()
        assert row.program_id_fk == program_id
        assert row.category_snapshot == "SEBC"
        assert row.home_city_snapshot == "Kalsar"
        assert row.address_snapshot == "Station Road, Kalsar, Bhavnagar"

    filtered = client.get(f"/annual-enrollment-history?academic_year={year}&location=Kalsar")
    assert filtered.status_code == 200
    assert b"Kalsar" in filtered.data
    assert b"overflow-x:clip" in filtered.data
    assert b'id="historySemester"' in filtered.data
    assert b'id="historyGender"' in filtered.data
    assert b'id="historyCategory"' in filtered.data
    assert b">Semester 1<" in filtered.data
    assert b">Female<" in filtered.data
    assert b">SEBC<" in filtered.data

    with app.app_context():
        row = StudentAcademicEnrollment.query.filter_by(student_id_fk="AH-001", academic_year=year).one()
        row.address_snapshot = None
        row.home_city_snapshot = None
        row.home_district_snapshot = None
        db.session.commit()
    refreshed = client.post(
        "/annual-enrollment-history/initialize",
        data={"csrf_token": token, "academic_year": year, "action": "refresh_locations"},
        follow_redirects=True,
    )
    assert refreshed.status_code == 200
    assert b"Refreshed 1 draft location snapshot" in refreshed.data
    assert b"Refresh draft locations" in refreshed.data
    assert b"Kalsar" in client.get(f"/annual-enrollment-history?academic_year={year}&location=Kalsar").data


def test_prepare_next_year_creates_draft_without_changing_student(client, app):
    token = _login(client, "annual-history-admin")
    source = current_academic_year()
    target = _next_academic_year_label(source)
    response = client.post(
        "/admin/workflows/new-academic-year/prepare",
        data={"csrf_token": token, "source_year": source, "target_year": target}, follow_redirects=True,
    )
    assert response.status_code == 200
    assert target.encode() in response.data
    with app.app_context():
        year = AcademicYear.query.filter_by(year_label=target).one()
        annual = StudentAcademicEnrollment.query.filter_by(student_id_fk="AH-001", academic_year=target).one()
        student = db.session.get(Student, "AH-001")
        assert year.status == "draft"
        assert annual.semester == 3
        assert annual.division_id_fk is None
        assert student.current_semester == 1


def test_dashboard_history_selection_redirects_to_read_only_history(client, app):
    _login(client, "annual-history-admin")
    response = client.get("/dashboard?academic_year=2024-25", follow_redirects=True)
    assert response.status_code == 200
    assert b"Historical year" in response.data
    assert b"No current totals are substituted" in response.data
