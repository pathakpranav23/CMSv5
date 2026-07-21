from cms_app import db
from cms_app.models import (
    Trust,
    Institute,
    Program,
    Division,
    SubjectType,
    Subject,
    User,
    Faculty,
    CourseAssignment,
)


def test_faculty_dashboard_renders_with_assignments(client, app):
    with app.app_context():
        trust = Trust(trust_name="Test Trust")
        db.session.add(trust)
        db.session.flush()

        institute = Institute(trust_id_fk=trust.trust_id, institute_name="Test Institute")
        db.session.add(institute)
        db.session.flush()

        program = Program(institute_id_fk=institute.institute_id, program_name="BCA", program_code="BCA")
        db.session.add(program)
        db.session.flush()

        division = Division(program_id_fk=program.program_id, semester=1, division_code="A")
        subject_type = SubjectType(type_name="Theory", type_code="TH-FD")
        db.session.add_all([division, subject_type])
        db.session.flush()

        subject = Subject(
            program_id_fk=program.program_id,
            subject_type_id_fk=subject_type.type_id,
            subject_name="Mathematics",
            subject_code="MATH-101",
            semester=1,
        )
        faculty_user = User(
            username="faculty-dashboard-user",
            email="faculty-dashboard@example.com",
            role="faculty",
            trust_id_fk=trust.trust_id,
            is_active=True,
        )
        db.session.add_all([subject, faculty_user])
        db.session.flush()

        faculty = Faculty(
            user_id_fk=faculty_user.user_id,
            program_id_fk=program.program_id,
            full_name="Faculty Dashboard User",
            trust_id_fk=trust.trust_id,
            is_active=True,
        )
        assignment = CourseAssignment(
            faculty_id_fk=faculty_user.user_id,
            subject_id_fk=subject.subject_id,
            division_id_fk=division.division_id,
            is_active=True,
        )
        db.session.add_all([faculty, assignment])
        db.session.commit()

    with client.session_transaction() as sess:
        sess["_user_id"] = str(faculty_user.user_id)
        sess["_fresh"] = True

    response = client.get("/faculty/dashboard")
    assert response.status_code == 200
    body = response.data.decode("utf-8")
    assert "Faculty Dashboard User" in body
    assert "Mathematics" in body
