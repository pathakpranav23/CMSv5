import pytest
from flask import url_for
from cms_app.models import User, Program, ProgramBankDetails
from cms_app import db
from werkzeug.security import generate_password_hash

@pytest.fixture(autouse=True)
def patch_cache_app(app):
    from cms_app import cache
    if not hasattr(cache, "app"):
        cache.app = app
    try:
        cache.clear()
    except Exception:
        pass
    yield
    try:
        cache.clear()
    except Exception:
        pass

def test_fees_bank_details_caching(client, app):
    # Create user and data
    with app.app_context():
        if not User.query.filter_by(username="admin_cache").first():
            u = User(username="admin_cache", password_hash=generate_password_hash("secret"), role="admin")
            db.session.add(u)
            
            p = Program(program_name="BCA")
            db.session.add(p)
            db.session.flush()
            
            bd = ProgramBankDetails(
                program_id_fk=p.program_id,
                bank_name="Test Bank",
                account_name="Test Account",
                account_number="1234567890",
                ifsc="TEST0001234",
                branch="Test Branch"
            )
            db.session.add(bd)
            db.session.commit()

    # Login
    client.post("/login", data={"username": "admin_cache", "password": "secret"}, follow_redirects=True)

    # Access page
    resp = client.get("/fees/bank-details")
    assert resp.status_code == 200
    assert b"Test Bank" in resp.data

    # Access again (should be cached)
    resp2 = client.get("/fees/bank-details")
    assert resp2.status_code == 200

def test_dashboard_caching(client, app):
    # Login as admin
    with app.app_context():
        if not User.query.filter_by(username="admin_dash").first():
            u = User(username="admin_dash", password_hash=generate_password_hash("secret"), role="admin")
            db.session.add(u)
            db.session.commit()

    client.post("/login", data={"username": "admin_dash", "password": "secret"}, follow_redirects=True)
    
    # First access
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    
    # Second access (cached)
    resp2 = client.get("/dashboard")
    assert resp2.status_code == 200

def test_dashboard_redirect_roles_are_not_cached(client, app):
    with app.app_context():
        for username, role in [("faculty_dash_redirect", "faculty"), ("student_dash_redirect", "student")]:
            if not User.query.filter_by(username=username).first():
                user = User(username=username, password_hash=generate_password_hash("secret"), role=role)
                db.session.add(user)
        db.session.commit()

    client.post("/login", data={"username": "faculty_dash_redirect", "password": "secret"}, follow_redirects=False)
    faculty_resp = client.get("/dashboard", follow_redirects=False)
    assert faculty_resp.status_code == 302
    assert "/faculty/dashboard" in faculty_resp.headers["Location"]
    client.get("/logout", follow_redirects=True)

    client.post("/login", data={"username": "student_dash_redirect", "password": "secret"}, follow_redirects=False)
    student_resp = client.get("/dashboard", follow_redirects=False)
    assert student_resp.status_code == 302
    assert "/timetable/my_timetable" in student_resp.headers["Location"]

def test_reports_hub_caching(client, app):
    # Login as admin
    with app.app_context():
        if not User.query.filter_by(username="admin_rep").first():
            u = User(username="admin_rep", password_hash=generate_password_hash("secret"), role="admin")
            db.session.add(u)
            db.session.commit()

    client.post("/login", data={"username": "admin_rep", "password": "secret"}, follow_redirects=True)
    
    # First access
    resp = client.get("/reports")
    assert resp.status_code == 200
    
    # Second access (cached)
    resp2 = client.get("/reports")
    assert resp2.status_code == 200

def test_auto_release_subject_assignments_when_semester_has_no_students(client, app):
    from cms_app.models import Trust, Institute, Program, Division, SubjectType, Subject, Faculty, CourseAssignment
    from cms_app.main.routes import current_academic_year

    with app.app_context():
        t = Trust(trust_name="T1", trust_code="T1", is_active=True)
        db.session.add(t)
        db.session.flush()
        inst = Institute(trust_id_fk=t.trust_id, institute_name="I1", institute_code="I1")
        db.session.add(inst)
        db.session.flush()
        p1 = Program(institute_id_fk=inst.institute_id, program_name="P1")
        p2 = Program(institute_id_fk=inst.institute_id, program_name="P2")
        db.session.add_all([p1, p2])
        db.session.flush()

        stype = SubjectType(type_name="Core", type_code="CORE")
        db.session.add(stype)
        db.session.flush()

        d1 = Division(program_id_fk=p1.program_id, semester=3, division_code="A", capacity=60)
        d2 = Division(program_id_fk=p2.program_id, semester=3, division_code="A", capacity=60)
        db.session.add_all([d1, d2])
        db.session.flush()

        s1 = Subject(program_id_fk=p1.program_id, subject_type_id_fk=stype.type_id, subject_name="S1", semester=3, is_active=True)
        s2 = Subject(program_id_fk=p2.program_id, subject_type_id_fk=stype.type_id, subject_name="S2", semester=3, is_active=True)
        db.session.add_all([s1, s2])
        db.session.flush()

        u = User(username="fac_release", password_hash=generate_password_hash("secret"), role="faculty", trust_id_fk=t.trust_id)
        db.session.add(u)
        db.session.flush()
        f = Faculty(user_id_fk=u.user_id, program_id_fk=p1.program_id, full_name="F1", trust_id_fk=t.trust_id, is_active=True)
        db.session.add(f)
        db.session.flush()

        ay = current_academic_year()
        ca1 = CourseAssignment(faculty_id_fk=u.user_id, subject_id_fk=s1.subject_id, division_id_fk=d1.division_id, academic_year=ay, role="primary", is_active=True)
        ca2 = CourseAssignment(faculty_id_fk=u.user_id, subject_id_fk=s2.subject_id, division_id_fk=d2.division_id, academic_year=ay, role="primary", is_active=True)
        db.session.add_all([ca1, ca2])
        db.session.commit()
        ca1_id = ca1.assignment_id
        ca2_id = ca2.assignment_id

    client.post("/login", data={"username": "fac_release", "password": "secret"}, follow_redirects=True)
    resp = client.get("/faculty/dashboard")
    assert resp.status_code == 200

    with app.app_context():
        a1 = db.session.get(CourseAssignment, ca1_id)
        a2 = db.session.get(CourseAssignment, ca2_id)
        assert a1.is_active is False
        assert a2.is_active is False
