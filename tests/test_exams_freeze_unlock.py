import json

from werkzeug.security import generate_password_hash

from cms_app import db
from cms_app.models import User, Trust, Institute, Program, Division, SubjectType, Subject, Student, Faculty, CourseAssignment, ExamScheme, ExamMark, DataAuditLog
from sqlalchemy import select


def _login(client, username, password):
    client.post("/login", data={"username": username, "password": password}, follow_redirects=True)
    with client.session_transaction() as sess:
        return sess.get("csrf_token")


def test_exam_scheme_freeze_unlock_and_flip_flag(client, app):
    with app.app_context():
        t = Trust(trust_name="T_EXAM", trust_code="T_EXAM", is_active=True)
        db.session.add(t)
        db.session.flush()
        inst = Institute(trust_id_fk=t.trust_id, institute_name="I_EXAM", institute_code="I_EXAM")
        db.session.add(inst)
        db.session.flush()
        p = Program(institute_id_fk=inst.institute_id, program_name="BCA")
        db.session.add(p)
        db.session.flush()
        d = Division(program_id_fk=p.program_id, semester=3, division_code="A", capacity=60)
        db.session.add(d)
        db.session.flush()
        stype = SubjectType(type_name="Core", type_code="CORE_EXAM")
        db.session.add(stype)
        db.session.flush()
        sub = Subject(program_id_fk=p.program_id, subject_type_id_fk=stype.type_id, subject_name="S_EXAM", subject_code="S_EXAM", semester=3, is_active=True)
        db.session.add(sub)
        db.session.flush()
        stu = Student(enrollment_no="E_EXAM_1", student_name="A", surname="B", program_id_fk=p.program_id, current_semester=3, trust_id_fk=t.trust_id, is_active=True, division_id_fk=d.division_id)
        db.session.add(stu)
        db.session.flush()

        u_principal = User(username="principal1", password_hash=generate_password_hash("secret"), role="principal", trust_id_fk=t.trust_id, program_id_fk=p.program_id)
        u_clerk = User(username="clerk1", password_hash=generate_password_hash("secret"), role="clerk", trust_id_fk=t.trust_id, program_id_fk=p.program_id)
        db.session.add_all([u_principal, u_clerk])
        db.session.flush()

        scheme = ExamScheme(program_id_fk=p.program_id, semester=3, academic_year="2025-26", name="Sem3 Mid", min_total_marks=40.0, max_total_marks=100.0, is_active=True)
        db.session.add(scheme)
        db.session.flush()

        m = ExamMark(student_id_fk=stu.enrollment_no, subject_id_fk=sub.subject_id, division_id_fk=d.division_id, scheme_id_fk=scheme.scheme_id, semester=3, academic_year="2025-26", attempt_no=1, internal_marks=10.0, external_marks=20.0, total_marks=30.0, is_absent=False)
        db.session.add(m)
        db.session.commit()
        scheme_id = scheme.scheme_id
        subject_id = sub.subject_id

    csrf = _login(client, "principal1", "secret")
    resp = client.post(f"/academics/exams/{scheme_id}/freeze", data={"csrf_token": csrf}, follow_redirects=True)
    assert resp.status_code == 200

    csrf_clerk = _login(client, "clerk1", "secret")
    resp2 = client.post(f"/academics/exams/{scheme_id}/save-marks", data={"csrf_token": csrf_clerk, "subject_id": str(subject_id), "student_ids": ["E_EXAM_1"], "internal_E_EXAM_1": "20", "external_E_EXAM_1": "30"}, follow_redirects=True)
    assert resp2.status_code == 200
    with app.app_context():
        s = db.session.get(ExamScheme, scheme_id)
        assert bool(getattr(s, "is_frozen", False)) is True
        assert getattr(s, "unlock_until", None) is None
        mark = db.session.execute(select(ExamMark).filter_by(scheme_id_fk=scheme_id, subject_id_fk=subject_id, student_id_fk="E_EXAM_1")).scalars().first()
        assert mark.total_marks == 30.0

    csrf2 = _login(client, "principal1", "secret")
    resp3 = client.post(
        f"/academics/exams/{scheme_id}/unlock",
        data={"csrf_token": csrf2, "reason": "Correction after verification", "duration_minutes": "30"},
        follow_redirects=True,
    )
    assert resp3.status_code == 200

    csrf_clerk2 = _login(client, "clerk1", "secret")
    resp4 = client.post(
        f"/academics/exams/{scheme_id}/save-marks",
        data={"csrf_token": csrf_clerk2, "subject_id": str(subject_id), "student_ids": ["E_EXAM_1"], "internal_E_EXAM_1": "20", "external_E_EXAM_1": "30"},
        follow_redirects=True,
    )
    assert resp4.status_code == 200

    with app.app_context():
        mark2 = db.session.execute(select(ExamMark).filter_by(scheme_id_fk=scheme_id, subject_id_fk=subject_id, student_id_fk="E_EXAM_1")).scalars().first()
        assert mark2.total_marks == 50.0
        saves = db.session.execute(select(DataAuditLog).where(DataAuditLog.action == "exam_marks_save")).scalars().all()
        assert len(saves) >= 1
        flips = db.session.execute(select(DataAuditLog).where(DataAuditLog.action == "exam_pass_fail_flip")).scalars().all()
        assert len(flips) >= 1
        found = False
        for f in flips:
            try:
                sel = json.loads(f.selection_json or "{}")
                cnt = json.loads(f.counts_json or "{}")
            except Exception:
                continue
            if sel.get("scheme_id") == scheme_id and sel.get("student_id") == "E_EXAM_1" and sel.get("subject_id") == subject_id:
                assert cnt.get("old_pass") is False
                assert cnt.get("new_pass") is True
                found = True
                break
        assert found is True
