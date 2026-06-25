from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta, timezone

from sqlalchemy import MetaData, Table, select

from cms_app import db
from cms_app.models import (
    Attendance,
    CourseAssignment,
    CreditStructure,
    Division,
    Faculty,
    FeePayment,
    FeeStructure,
    FeesRecord,
    Institute,
    Program,
    Student,
    Subject,
    SubjectType,
    Trust,
    User,
)


def _login(client, username, password="secret"):
    client.post("/login", data={"username": username, "password": password}, follow_redirects=True)
    with client.session_transaction() as sess:
        return sess.get("csrf_token")


def test_super_admin_institutes_page_counts_entities_through_programs(client, app):
    with app.app_context():
        trust = Trust(trust_name="Trust Counts", trust_code="TRUST_COUNTS", is_active=True)
        db.session.add(trust)
        db.session.flush()

        inst_alpha = Institute(
            trust_id_fk=trust.trust_id,
            institute_name="Institute Alpha",
            institute_code="INST_ALPHA",
            is_active=True,
        )
        inst_beta = Institute(
            trust_id_fk=trust.trust_id,
            institute_name="Institute Beta",
            institute_code="INST_BETA",
            is_active=True,
        )
        db.session.add_all([inst_alpha, inst_beta])
        db.session.flush()

        prog_alpha = Program(institute_id_fk=inst_alpha.institute_id, program_name="BCA Alpha")
        prog_beta = Program(institute_id_fk=inst_beta.institute_id, program_name="BCom Beta")
        db.session.add_all([prog_alpha, prog_beta])
        db.session.flush()

        super_admin = User(
            username="sa_institute_counts",
            password_hash=generate_password_hash("secret"),
            role="admin",
            is_super_admin=True,
        )
        alpha_admin = User(
            username="alpha_admin_counts",
            password_hash=generate_password_hash("secret"),
            role="admin",
            trust_id_fk=trust.trust_id,
            program_id_fk=prog_alpha.program_id,
        )
        alpha_student_user = User(
            username="alpha_student_counts",
            password_hash=generate_password_hash("secret"),
            role="student",
            trust_id_fk=trust.trust_id,
            program_id_fk=prog_alpha.program_id,
        )
        alpha_faculty_user = User(
            username="alpha_faculty_counts",
            password_hash=generate_password_hash("secret"),
            role="faculty",
            trust_id_fk=trust.trust_id,
            program_id_fk=prog_alpha.program_id,
        )
        beta_student_user = User(
            username="beta_student_counts",
            password_hash=generate_password_hash("secret"),
            role="student",
            trust_id_fk=trust.trust_id,
            program_id_fk=prog_beta.program_id,
        )
        db.session.add_all(
            [
                super_admin,
                alpha_admin,
                alpha_student_user,
                alpha_faculty_user,
                beta_student_user,
            ]
        )
        db.session.flush()

        alpha_faculty = Faculty(
            user_id_fk=alpha_faculty_user.user_id,
            program_id_fk=prog_alpha.program_id,
            full_name="Faculty Alpha",
            trust_id_fk=trust.trust_id,
            is_active=True,
        )
        alpha_student = Student(
            enrollment_no="ENR_ALPHA_COUNTS",
            user_id_fk=alpha_student_user.user_id,
            student_name="Student",
            surname="Alpha",
            program_id_fk=prog_alpha.program_id,
            trust_id_fk=trust.trust_id,
            is_active=True,
        )
        beta_student_one = Student(
            enrollment_no="ENR_BETA_COUNTS_1",
            user_id_fk=beta_student_user.user_id,
            student_name="Student",
            surname="BetaOne",
            program_id_fk=prog_beta.program_id,
            trust_id_fk=trust.trust_id,
            is_active=True,
        )
        beta_student_two = Student(
            enrollment_no="ENR_BETA_COUNTS_2",
            student_name="Student",
            surname="BetaTwo",
            program_id_fk=prog_beta.program_id,
            trust_id_fk=trust.trust_id,
            is_active=True,
        )
        db.session.add_all([alpha_faculty, alpha_student, beta_student_one, beta_student_two])
        db.session.commit()

        trust_id = trust.trust_id

    _login(client, "sa_institute_counts")
    response = client.get(f"/super-admin/trusts/{trust_id}/institutes-summary")
    text = response.data.decode("utf-8")

    assert response.status_code == 200
    assert "Institute Alpha" in text
    assert "Institute Beta" in text
    assert "Users: 3" in text
    assert "Users: 1" in text
    assert "Staff: 1" in text
    assert "Students: 2" in text


def test_fee_queue_scopes_by_trust_and_verify_sets_verifier(client, app):
    with app.app_context():
        trust_a = Trust(trust_name="Trust Fees A", trust_code="TRUST_FEES_A", is_active=True)
        trust_b = Trust(trust_name="Trust Fees B", trust_code="TRUST_FEES_B", is_active=True)
        db.session.add_all([trust_a, trust_b])
        db.session.flush()

        inst_a = Institute(
            trust_id_fk=trust_a.trust_id,
            institute_name="Institute Fees A",
            institute_code="INST_FEES_A",
            is_active=True,
        )
        inst_b = Institute(
            trust_id_fk=trust_b.trust_id,
            institute_name="Institute Fees B",
            institute_code="INST_FEES_B",
            is_active=True,
        )
        db.session.add_all([inst_a, inst_b])
        db.session.flush()

        prog_a = Program(institute_id_fk=inst_a.institute_id, program_name="Program Fees A")
        prog_b = Program(institute_id_fk=inst_b.institute_id, program_name="Program Fees B")
        db.session.add_all([prog_a, prog_b])
        db.session.flush()

        admin_a = User(
            username="admin_fee_scope",
            password_hash=generate_password_hash("secret"),
            role="admin",
            trust_id_fk=trust_a.trust_id,
        )
        db.session.add(admin_a)
        db.session.flush()

        student_a = Student(
            enrollment_no="ENR_FEE_SCOPE_A",
            student_name="Fee",
            surname="Alpha",
            program_id_fk=prog_a.program_id,
            trust_id_fk=trust_a.trust_id,
            is_active=True,
        )
        student_b = Student(
            enrollment_no="ENR_FEE_SCOPE_B",
            student_name="Fee",
            surname="Beta",
            program_id_fk=prog_b.program_id,
            trust_id_fk=trust_b.trust_id,
            is_active=True,
        )
        db.session.add_all([student_a, student_b])
        db.session.flush()

        payment_a = FeePayment(
            enrollment_no=student_a.enrollment_no,
            program_id_fk=prog_a.program_id,
            semester=1,
            amount=1200.0,
            utr="UTR-SCOPE-A",
            status="submitted",
        )
        payment_b = FeePayment(
            enrollment_no=student_b.enrollment_no,
            program_id_fk=prog_b.program_id,
            semester=1,
            amount=2400.0,
            utr="UTR-SCOPE-B",
            status="submitted",
        )
        db.session.add_all([payment_a, payment_b])
        db.session.commit()

        admin_id = admin_a.user_id
        payment_a_id = payment_a.payment_id
        payment_b_id = payment_b.payment_id

    csrf = _login(client, "admin_fee_scope")

    queue_response = client.get("/fees/verification-queue")
    queue_text = queue_response.data.decode("utf-8")
    assert queue_response.status_code == 200
    assert "UTR-SCOPE-A" in queue_text
    assert "UTR-SCOPE-B" not in queue_text

    unauthorized_verify = client.post(
        f"/fees/verification-queue/{payment_b_id}/verify",
        data={"csrf_token": csrf},
        follow_redirects=True,
    )
    assert unauthorized_verify.status_code == 200
    assert "Not authorized to verify this payment." in unauthorized_verify.data.decode("utf-8")

    verify_response = client.post(
        f"/fees/verification-queue/{payment_a_id}/verify",
        data={"csrf_token": csrf, "payer_name": "Accounts Desk"},
        follow_redirects=True,
    )
    assert verify_response.status_code == 200

    with app.app_context():
        refreshed_a = db.session.get(FeePayment, payment_a_id)
        refreshed_b = db.session.get(FeePayment, payment_b_id)
        assert refreshed_a.status == "verified"
        verifier_field = "verified_by_fk" if hasattr(refreshed_a, "verified_by_fk") else "verified_by_user_id"
        assert getattr(refreshed_a, verifier_field) == admin_id
        assert refreshed_b.status == "submitted"


def test_super_admin_dashboard_handles_timezone_aware_subscription_dates(client, app):
    with app.app_context():
        trust = Trust(
            trust_name="Trust TZ Aware",
            trust_code="TRUST_TZ_AWARE",
            is_active=True,
            subscription_end_at=datetime.now(timezone.utc) + timedelta(days=12),
            subscription_grace_days=7,
        )
        super_admin = User(
            username="sa_dashboard_tz",
            password_hash=generate_password_hash("secret"),
            role="admin",
            is_super_admin=True,
        )
        db.session.add_all([trust, super_admin])
        db.session.commit()

    _login(client, "sa_dashboard_tz")
    response = client.get("/super-admin/dashboard")
    text = response.data.decode("utf-8")

    assert response.status_code == 200
    assert "Super Admin Control Tower" in text


def test_super_admin_dashboard_legacy_redirects_to_control_tower(client, app):
    with app.app_context():
        super_admin = User(
            username="sa_dashboard_legacy_redirect",
            password_hash=generate_password_hash("secret"),
            role="admin",
            is_super_admin=True,
        )
        db.session.add(super_admin)
        db.session.commit()

    _login(client, "sa_dashboard_legacy_redirect")
    response = client.get("/super-admin/dashboard-legacy", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/super-admin/dashboard")


def test_super_admin_tenants_page_renders_and_links_to_canonical_institutes_view(client, app):
    with app.app_context():
        trust = Trust(
            trust_name="Trust Tenants Page",
            trust_code="TRUST_TENANTS_PAGE",
            is_active=True,
        )
        db.session.add(trust)
        db.session.flush()

        institute = Institute(
            trust_id_fk=trust.trust_id,
            institute_name="Tenants Institute",
            institute_code="TENANTS_INST",
            is_active=True,
        )
        super_admin = User(
            username="sa_tenants_page",
            password_hash=generate_password_hash("secret"),
            role="admin",
            is_super_admin=True,
        )
        db.session.add_all([institute, super_admin])
        db.session.commit()

        trust_id = trust.trust_id

    _login(client, "sa_tenants_page")
    response = client.get("/super-admin/tenants")
    text = response.data.decode("utf-8")

    assert response.status_code == 200
    assert "Tenant Management (Kill Switch)" in text
    assert "Trust Tenants Page" in text
    assert f"/super-admin/trusts/{trust_id}/institutes" in text


def test_super_admin_tenants_page_tolerates_missing_optional_schema_columns(client, app, monkeypatch):
    from cms_app.super_admin import routes as super_admin_routes
    original_table_columns = super_admin_routes._table_columns

    with app.app_context():
        trust = Trust(
            trust_name="Trust Minimal Schema",
            trust_code="TRUST_MIN_SCHEMA",
            is_active=True,
        )
        db.session.add(trust)
        db.session.flush()

        institute = Institute(
            trust_id_fk=trust.trust_id,
            institute_name="Minimal Institute",
            institute_code="MIN_INST",
            is_active=True,
        )
        super_admin = User(
            username="sa_min_schema",
            password_hash=generate_password_hash("secret"),
            role="admin",
            is_super_admin=True,
        )
        db.session.add_all([institute, super_admin])
        db.session.commit()

    def fake_table_columns(table_name):
        if table_name == "trusts":
            return {"trust_id", "trust_name"}
        if table_name == "institutes":
            return {"institute_id", "trust_id_fk", "institute_name", "institute_code"}
        return original_table_columns(table_name)

    monkeypatch.setattr(super_admin_routes, "_table_columns", fake_table_columns)

    _login(client, "sa_min_schema")
    response = client.get("/super-admin/tenants")
    text = response.data.decode("utf-8")

    assert response.status_code == 200
    assert "Trust Minimal Schema" in text
    assert "Minimal Institute" in text


def test_super_admin_create_endpoints_redirect_on_direct_get(client, app):
    with app.app_context():
        super_admin = User(
            username="sa_create_redirects",
            password_hash=generate_password_hash("secret"),
            role="admin",
            is_super_admin=True,
        )
        db.session.add(super_admin)
        db.session.commit()

    _login(client, "sa_create_redirects")

    trust_create = client.get("/super-admin/trusts/create", follow_redirects=False)
    institute_create = client.get("/super-admin/institutes/create", follow_redirects=False)

    assert trust_create.status_code == 302
    assert trust_create.headers["Location"].endswith("/super-admin/tenants")
    assert institute_create.status_code == 302
    assert institute_create.headers["Location"].endswith("/super-admin/tenants")


def test_super_admin_create_trust_tolerates_missing_subscription_columns(client, app, monkeypatch):
    from cms_app.super_admin import routes as super_admin_routes

    original_table_columns = super_admin_routes._table_columns

    with app.app_context():
        super_admin = User(
            username="sa_create_min_schema",
            password_hash=generate_password_hash("secret"),
            role="admin",
            is_super_admin=True,
        )
        db.session.add(super_admin)
        db.session.commit()

    def fake_table_columns(table_name):
        if table_name == "trusts":
            return {"trust_id", "trust_name", "trust_code"}
        return original_table_columns(table_name)

    class BlockingTrustQuery:
        def filter_by(self, **kwargs):
            raise AssertionError("create_trust should not use Trust.query on old schemas")

    monkeypatch.setattr(super_admin_routes, "_table_columns", fake_table_columns)
    with app.app_context():
        monkeypatch.setattr(super_admin_routes.Trust, "query", BlockingTrustQuery(), raising=False)

    csrf = _login(client, "sa_create_min_schema")
    response = client.post(
        "/super-admin/trusts/create",
        data={
            "csrf_token": csrf,
            "trust_name": "Trust Minimal Create",
            "trust_code": "TRUST_MIN_CREATE",
            "subscription_plan": "enterprise",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/super-admin/tenants")

    with app.app_context():
        trusts_table = Table("trusts", MetaData(), autoload_with=db.engine)
        created_name = db.session.execute(
            select(trusts_table.c.trust_name).where(trusts_table.c.trust_code == "TRUST_MIN_CREATE")
        ).scalar_one_or_none()
        assert created_name == "Trust Minimal Create"


def test_programs_page_super_admin_renders_without_full_trust_institute_gets(client, app, monkeypatch):
    from cms_app.main import routes as main_routes

    with app.app_context():
        trust = Trust(
            trust_name="Trust Programs Minimal",
            trust_code="TRUST_PROGRAMS_MIN",
            is_active=True,
        )
        db.session.add(trust)
        db.session.flush()

        institute = Institute(
            trust_id_fk=trust.trust_id,
            institute_name="Programs Minimal Institute",
            institute_code="PROG_MIN_INST",
            is_active=True,
        )
        db.session.add(institute)
        db.session.flush()

        program = Program(institute_id_fk=institute.institute_id, program_name="Minimal Program")
        super_admin = User(
            username="sa_programs_minimal",
            password_hash=generate_password_hash("secret"),
            role="admin",
            is_super_admin=True,
        )
        db.session.add_all([program, super_admin])
        db.session.commit()

        trust_id = trust.trust_id
        institute_id = institute.institute_id

    csrf = _login(client, "sa_programs_minimal")
    with client.session_transaction() as sess:
        sess["active_trust_id"] = trust_id
        sess["active_institute_id"] = institute_id
        sess["csrf_token"] = csrf

    original_get = main_routes.db.session.get

    def guarded_get(entity, ident, *args, **kwargs):
        if entity in (main_routes.Trust, main_routes.Institute):
            raise AssertionError("Programs pages should not use full Trust/Institute session.get")
        return original_get(entity, ident, *args, **kwargs)

    monkeypatch.setattr(main_routes.db.session, "get", guarded_get)

    response = client.get(f"/programs?trust_id={trust_id}")
    text = response.data.decode("utf-8")

    assert response.status_code == 200
    assert "Minimal Program" in text
    assert "Programs Minimal Institute" in text


def test_wizard_step1_renders_without_full_trust_institute_gets(client, app, monkeypatch):
    from cms_app.wizard import routes as wizard_routes

    with app.app_context():
        trust = Trust(
            trust_name="Trust Wizard Minimal",
            trust_code="TRUST_WIZARD_MIN",
            is_active=True,
        )
        db.session.add(trust)
        db.session.flush()

        institute = Institute(
            trust_id_fk=trust.trust_id,
            institute_name="Wizard Minimal Institute",
            institute_code="WIZ_MIN_INST",
            is_active=True,
        )
        super_admin = User(
            username="sa_wizard_minimal",
            password_hash=generate_password_hash("secret"),
            role="admin",
            is_super_admin=True,
        )
        db.session.add_all([institute, super_admin])
        db.session.commit()

        institute_id = institute.institute_id

    _login(client, "sa_wizard_minimal")

    original_get = wizard_routes.db.session.get

    def guarded_get(entity, ident, *args, **kwargs):
        if entity in (wizard_routes.Trust, wizard_routes.Institute):
            raise AssertionError("Wizard step1 should not use full Trust/Institute session.get")
        return original_get(entity, ident, *args, **kwargs)

    monkeypatch.setattr(wizard_routes.db.session, "get", guarded_get)

    response = client.get(f"/wizard/step1?institute_id={institute_id}")
    text = response.data.decode("utf-8")

    assert response.status_code == 200
    assert "Wizard Minimal Institute" in text


def test_students_pages_tolerate_missing_aadhar_column(client, app, monkeypatch):
    from cms_app.main import routes as main_routes

    with app.app_context():
        trust = Trust(
            trust_name="Trust Students Minimal",
            trust_code="TRUST_STUDENTS_MIN",
            is_active=True,
        )
        db.session.add(trust)
        db.session.flush()

        institute = Institute(
            trust_id_fk=trust.trust_id,
            institute_name="Students Minimal Institute",
            institute_code="STUD_MIN_INST",
            is_active=True,
        )
        db.session.add(institute)
        db.session.flush()

        program = Program(institute_id_fk=institute.institute_id, program_name="Students Minimal Program")
        db.session.add(program)
        db.session.flush()

        admin = User(
            username="admin_students_minimal",
            password_hash=generate_password_hash("secret"),
            role="admin",
            trust_id_fk=trust.trust_id,
            program_id_fk=program.program_id,
        )
        linked_user = User(
            username="student_link_target",
            password_hash=generate_password_hash("secret"),
            role="student",
            trust_id_fk=trust.trust_id,
            program_id_fk=program.program_id,
        )
        db.session.add(admin)
        db.session.add(linked_user)
        db.session.flush()

        faculty_user = User(
            username="faculty_students_minimal",
            password_hash=generate_password_hash("secret"),
            role="faculty",
            trust_id_fk=trust.trust_id,
            program_id_fk=program.program_id,
        )
        db.session.add(faculty_user)
        db.session.flush()

        division = Division(
            program_id_fk=program.program_id,
            semester=4,
            division_code="A",
            capacity=60,
            medium_tag="English",
        )
        db.session.add(division)
        db.session.flush()

        student = Student(
            enrollment_no="ENR_STUDENTS_MIN",
            student_name="Aarav",
            surname="Patel",
            father_name="Rakesh",
            mobile="9999999999",
            program_id_fk=program.program_id,
            division_id_fk=division.division_id,
            trust_id_fk=trust.trust_id,
            current_semester=4,
            medium_tag="English",
            category="OPEN",
            is_active=True,
        )
        student_delete = Student(
            enrollment_no="ENR_STUDENTS_MIN_DELETE",
            student_name="Delete",
            surname="Me",
            program_id_fk=program.program_id,
            division_id_fk=division.division_id,
            trust_id_fk=trust.trust_id,
            current_semester=4,
            medium_tag="English",
            category="OPEN",
            is_active=True,
        )
        db.session.add_all([student, student_delete])
        db.session.flush()

        faculty = Faculty(
            user_id_fk=faculty_user.user_id,
            program_id_fk=program.program_id,
            full_name="Faculty Minimal",
            trust_id_fk=trust.trust_id,
            is_active=True,
        )
        subject_type = SubjectType(type_code="TH_STUD_MIN", type_name="Theory")
        db.session.add_all([faculty, subject_type])
        db.session.flush()

        subject = Subject(
            program_id_fk=program.program_id,
            subject_type_id_fk=subject_type.type_id,
            subject_name="Data Structures",
            subject_code="DS101",
            semester=4,
            medium_tag="English",
            is_active=True,
        )
        db.session.add(subject)
        db.session.flush()

        credit_structure = CreditStructure(subject_id_fk=subject.subject_id, total_credits=4)
        course_assignment = CourseAssignment(
            faculty_id_fk=faculty_user.user_id,
            subject_id_fk=subject.subject_id,
            division_id_fk=division.division_id,
            academic_year="2026-27",
            is_active=True,
        )
        attendance_rows = [
            Attendance(
                student_id_fk=student.enrollment_no,
                subject_id_fk=subject.subject_id,
                division_id_fk=division.division_id,
                date_marked=datetime(2026, 6, 10, tzinfo=timezone.utc).date(),
                status="P",
                semester=4,
                period_no=1,
            ),
            Attendance(
                student_id_fk=student.enrollment_no,
                subject_id_fk=subject.subject_id,
                division_id_fk=division.division_id,
                date_marked=datetime(2026, 6, 11, tzinfo=timezone.utc).date(),
                status="A",
                semester=4,
                period_no=2,
            ),
            Attendance(
                student_id_fk=student.enrollment_no,
                subject_id_fk=subject.subject_id,
                division_id_fk=division.division_id,
                date_marked=datetime(2026, 6, 12, tzinfo=timezone.utc).date(),
                status="L",
                semester=4,
                period_no=3,
            ),
        ]
        fee_structures = [
            FeeStructure(
                program_id_fk=program.program_id,
                semester=4,
                component_name="Tuition Fee",
                amount=5000.0,
                is_active=True,
                is_frozen=True,
                medium_tag=None,
            ),
            FeeStructure(
                program_id_fk=program.program_id,
                semester=4,
                component_name="Exam Fee",
                amount=1000.0,
                is_active=True,
                is_frozen=True,
                medium_tag="English",
            ),
        ]
        fees_record = FeesRecord(
            student_id_fk=student.enrollment_no,
            amount_due=6000.0,
            amount_paid=2500.0,
            semester=4,
        )
        payment_submitted = FeePayment(
            enrollment_no=student.enrollment_no,
            program_id_fk=program.program_id,
            semester=4,
            medium_tag="English",
            amount=2500.0,
            utr="UTR-STUD-MIN-1",
            status="submitted",
            created_by_user_id=admin.user_id,
        )
        payment_submitted_reject = FeePayment(
            enrollment_no=student.enrollment_no,
            program_id_fk=program.program_id,
            semester=4,
            medium_tag="English",
            amount=1500.0,
            utr="UTR-STUD-MIN-2",
            status="submitted",
            created_by_user_id=admin.user_id,
        )
        payment_verified = FeePayment(
            enrollment_no=student.enrollment_no,
            program_id_fk=program.program_id,
            semester=4,
            medium_tag="English",
            amount=1000.0,
            utr="UTR-STUD-MIN-VER",
            status="verified",
            created_by_user_id=admin.user_id,
        )
        db.session.add_all(
            [credit_structure, course_assignment, fees_record, payment_submitted, payment_submitted_reject, payment_verified]
            + attendance_rows
            + fee_structures
        )
        db.session.commit()

        program_id = program.program_id
        subject_id = subject.subject_id
        division_id = division.division_id
        payment_submitted_id = payment_submitted.payment_id
        payment_reject_id = payment_submitted_reject.payment_id

    original_execute = main_routes.db.session.execute
    original_get = main_routes.db.session.get

    def guarded_student_columns():
        return set(main_routes._STUDENT_FIELD_NAMES) - {"aadhar_no"}

    def guarded_execute(statement, *args, **kwargs):
        sql = str(statement)
        if "FROM students" in sql and "students.aadhar_no" in sql:
            raise AssertionError("students pages should not select students.aadhar_no on old schemas")
        if "UPDATE students" in sql and "aadhar_no" in sql:
            raise AssertionError("students pages should not update students.aadhar_no on old schemas")
        if "INSERT INTO students" in sql and "aadhar_no" in sql:
            raise AssertionError("students pages should not insert students.aadhar_no on old schemas")
        return original_execute(statement, *args, **kwargs)

    def guarded_get(entity, ident, *args, **kwargs):
        if entity is main_routes.Student:
            raise AssertionError("students workflow should not use full Student session.get on old schemas")
        return original_get(entity, ident, *args, **kwargs)

    monkeypatch.setattr(main_routes, "_student_present_columns", guarded_student_columns)
    monkeypatch.setattr(main_routes.db.session, "execute", guarded_execute)
    monkeypatch.setattr(main_routes.db.session, "get", guarded_get)

    csrf = _login(client, "admin_students_minimal")

    list_response = client.get(f"/students?program_id={program_id}")
    list_text = list_response.data.decode("utf-8")
    assert list_response.status_code == 200
    assert "ENR_STUDENTS_MIN" in list_text
    assert "Aarav" in list_text
    assert "Patel" in list_text

    search_response = client.get(f"/api/students/search?q=Aarav&program_id={program_id}")
    assert search_response.status_code == 200
    payload = search_response.get_json()
    assert payload["success"] is True
    assert payload["data"]["items"][0]["enrollment_no"] == "ENR_STUDENTS_MIN"

    edit_get = client.get("/students/ENR_STUDENTS_MIN/edit")
    assert edit_get.status_code == 200
    assert "Aarav" in edit_get.data.decode("utf-8")

    edit_post = client.post(
        "/students/ENR_STUDENTS_MIN/edit",
        data={
            "program_id_fk": str(program_id),
            "division_id_fk": "",
            "surname": "Patel",
            "student_name": "Aarav Updated",
            "father_name": "Rakesh",
            "date_of_birth": "",
            "mobile": "9999999999",
            "current_semester": "4",
            "category": "OPEN",
            "aadhar_no": "123412341234",
            "gender": "Male",
            "medium_tag": "English",
            "permanent_address": "Rajkot",
        },
        follow_redirects=True,
    )
    assert edit_post.status_code == 200
    assert "updated successfully" in edit_post.data.decode("utf-8")

    show_response = client.get("/students/ENR_STUDENTS_MIN")
    show_text = show_response.data.decode("utf-8")
    assert show_response.status_code == 200
    assert "Aarav Updated" in show_text

    attendance_response = client.get("/students/ENR_STUDENTS_MIN/attendance")
    assert attendance_response.status_code == 200

    attendance_export = client.get("/students/ENR_STUDENTS_MIN/attendance/export")
    assert attendance_export.status_code == 200

    grades_response = client.get("/students/ENR_STUDENTS_MIN/grades")
    assert grades_response.status_code == 200

    grades_export = client.get("/students/ENR_STUDENTS_MIN/grades/export")
    assert grades_export.status_code == 200

    link_response = client.post(
        "/students/ENR_STUDENTS_MIN/link-user",
        data={"username": "student_link_target"},
        follow_redirects=True,
    )
    assert link_response.status_code == 200
    assert "Linked student to user successfully." in link_response.data.decode("utf-8")

    unlink_response = client.post(
        "/students/ENR_STUDENTS_MIN/unlink-user",
        follow_redirects=True,
    )
    assert unlink_response.status_code == 200
    assert "Unlinked student from user account." in unlink_response.data.decode("utf-8")

    fees_response = client.get("/students/ENR_STUDENTS_MIN/fees")
    assert fees_response.status_code == 200

    receipt_semester_response = client.get(
        f"/fees/receipt_semester?program_id={program_id}&semester=4&enrollment_no=ENR_STUDENTS_MIN&medium=English"
    )
    assert receipt_semester_response.status_code == 200

    payment_status_response = client.get(f"/fees/payment-status?program_id={program_id}&semester=4&medium=English")
    assert payment_status_response.status_code == 200

    payment_page_response = client.get("/fees/payment/ENR_STUDENTS_MIN?semester=4&medium=English")
    assert payment_page_response.status_code == 200

    queue_response = client.get("/fees/payments/queue")
    assert queue_response.status_code == 200
    assert "UTR-STUD-MIN-1" in queue_response.data.decode("utf-8")

    verify_response = client.post(
        f"/fees/verification-queue/{payment_submitted_id}/verify",
        data={"csrf_token": csrf, "payer_name": "Accounts Desk"},
        follow_redirects=True,
    )
    assert verify_response.status_code == 200

    reject_response = client.post(
        f"/fees/verification-queue/{payment_reject_id}/reject",
        data={"csrf_token": csrf, "remarks": "Mismatch"},
        follow_redirects=True,
    )
    assert reject_response.status_code == 200

    attendance_show_response = client.get("/attendance/show?date=2026-06-11")
    assert attendance_show_response.status_code == 200

    attendance_report_response = client.get(
        f"/attendance/report?subject_id={subject_id}&division_id={division_id}&start=2026-06-01&end=2026-06-30"
    )
    assert attendance_report_response.status_code == 200

    attendance_search_response = client.get("/attendance/search?q=Aarav&period=month&month=2026-06")
    assert attendance_search_response.status_code == 200

    enrollment_summary_response = client.get(
        f"/api/reports/enrollment-summary?program_id={program_id}&semester=4&medium=english"
    )
    assert enrollment_summary_response.status_code == 200

    fees_program_status_response = client.get(f"/api/reports/fees-program-status?program_id={program_id}&semester=4")
    assert fees_program_status_response.status_code == 200

    fees_program_status_export_response = client.get(f"/fees/program-status/export.csv?program_id={program_id}&semester=4")
    assert fees_program_status_export_response.status_code == 200

    subject_lectures_response = client.get(
        f"/api/reports/subject-lectures?program_id={program_id}&semester=4&subject_id={subject_id}&division_id={division_id}&date_from=2026-06-01&date_to=2026-06-30"
    )
    assert subject_lectures_response.status_code == 200

    subject_lectures_export_response = client.get(
        f"/subject-lectures/export.csv?program_id={program_id}&semester=4&subject_id={subject_id}&division_id={division_id}&date_from=2026-06-01&date_to=2026-06-30"
    )
    assert subject_lectures_export_response.status_code == 200

    absentees_response = client.get(f"/api/reports/absentees?subject_id={subject_id}&days=30")
    assert absentees_response.status_code == 200

    absentees_export_response = client.get(f"/absentees/export.csv?subject_id={subject_id}&days=30")
    assert absentees_export_response.status_code == 200

    attendance_students_response = client.get(
        f"/api/reports/attendance-students?program_id={program_id}&semester=4&subject_id={subject_id}&threshold=80&mode=below"
    )
    assert attendance_students_response.status_code == 200

    nep_report_response = client.get(f"/admin/reports/nep-exit-eligibility?program_id={program_id}")
    assert nep_report_response.status_code == 200

    attendance_export_response = client.get(
        f"/attendance/export.csv?program_id={program_id}&semester=4&subject_id={subject_id}&threshold=80&mode=below"
    )
    assert attendance_export_response.status_code == 200

    _login(client, "faculty_students_minimal")
    faculty_attendance_report_response = client.get(
        f"/attendance/faculty-report?subject_id={subject_id}&division_id={division_id}&start=2026-06-01&end=2026-06-30"
    )
    assert faculty_attendance_report_response.status_code == 200

    _login(client, "admin_students_minimal")

    export_response = client.get(f"/students/export.csv?program_id={program_id}")
    assert export_response.status_code == 200
    assert "ENR_STUDENTS_MIN" in export_response.data.decode("utf-8")

    promotion_get = client.get(f"/students/semester-promotion?program_id={program_id}&from_semester=4")
    assert promotion_get.status_code == 200
    assert "ENR_STUDENTS_MIN" in promotion_get.data.decode("utf-8")

    allocation_get = client.get(f"/student/subject/allocation?program_id={program_id}&semester=4")
    assert allocation_get.status_code == 200

    import io
    bulk_csv = io.BytesIO(b"EnrollmentNo\nENR_STUDENTS_MIN\n")
    bulk_response = client.post(
        "/student/subject/allocation/bulk/csv",
        data={
            "program_id": str(program_id),
            "semester": "4",
            "subject_id": "",
            "file": (bulk_csv, "students.csv"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert bulk_response.status_code == 200

    lifecycle_response = client.get(f"/admin/student-lifecycle?program_id={program_id}&semester=4")
    assert lifecycle_response.status_code == 200

    delete_response = client.post(
        "/students/ENR_STUDENTS_MIN_DELETE/delete",
        follow_redirects=True,
    )
    assert delete_response.status_code == 200
    assert "Student ENR_STUDENTS_MIN_DELETE deleted." in delete_response.data.decode("utf-8")


def test_subject_pages_tolerate_missing_optional_subject_columns(client, app, monkeypatch):
    from cms_app.main import routes as main_routes

    with app.app_context():
        trust = Trust(trust_name="Trust Subject Minimal", trust_code="TRUST_SUBJ_MIN", is_active=True)
        db.session.add(trust)
        db.session.flush()

        institute = Institute(
            trust_id_fk=trust.trust_id,
            institute_name="Subject Minimal Institute",
            institute_code="SUBJ_MIN_INST",
            is_active=True,
        )
        db.session.add(institute)
        db.session.flush()

        program = Program(institute_id_fk=institute.institute_id, program_name="Subject Minimal Program")
        db.session.add(program)
        db.session.flush()

        admin = User(
            username="admin_subject_minimal",
            password_hash=generate_password_hash("secret"),
            role="admin",
            trust_id_fk=trust.trust_id,
            program_id_fk=program.program_id,
        )
        db.session.add(admin)
        db.session.flush()

        subject_type = SubjectType(type_code="TH", type_name="Theory")
        db.session.add(subject_type)
        db.session.flush()

        subject = Subject(
            program_id_fk=program.program_id,
            semester=4,
            subject_name="Database Systems",
            subject_code="DBS401",
            paper_code="DBS-401",
            subject_type_id_fk=subject_type.type_id,
            is_active=True,
        )
        db.session.add(subject)
        db.session.flush()

        db.session.add(
            CreditStructure(
                subject_id_fk=subject.subject_id,
                theory_credits=4,
                practical_credits=2,
                total_credits=6,
            )
        )
        db.session.commit()

        program_id = program.program_id
        subject_id = subject.subject_id

    original_get = main_routes.db.session.get

    def guarded_get(entity, ident, *args, **kwargs):
        if entity is main_routes.Subject:
            raise AssertionError("subject workflow should not use full Subject session.get on legacy schemas")
        return original_get(entity, ident, *args, **kwargs)

    def legacy_fetch_subject(subject_id_value):
        row = main_routes._fetch_subject_mapping.__wrapped__(subject_id_value) if hasattr(main_routes._fetch_subject_mapping, "__wrapped__") else None
        if row is None:
            reflected = main_routes._reflected_table("subjects")
            row = main_routes.db.session.execute(
                select(reflected).where(reflected.c.subject_id == subject_id_value)
            ).mappings().first()
        if row is None:
            return None
        data = dict(row)
        data.pop("medium_tag", None)
        data.pop("is_elective", None)
        data.pop("capacity", None)
        data.pop("elective_group_id", None)
        return data

    monkeypatch.setattr(main_routes.db.session, "get", guarded_get)
    monkeypatch.setattr(main_routes, "_fetch_subject_mapping", legacy_fetch_subject)

    _login(client, "admin_subject_minimal")

    list_response = client.get(f"/subjects?program_id={program_id}&semester=4")
    assert list_response.status_code == 200
    assert "Database Systems" in list_response.data.decode("utf-8")

    export_response = client.get(f"/subjects/export.csv?program_id={program_id}&semester=4")
    assert export_response.status_code == 200
    assert "DBS401" in export_response.data.decode("utf-8")

    toggle_response = client.post(
        f"/subjects/{subject_id}/toggle-elective",
        data={"action": "make_elective"},
        follow_redirects=True,
    )
    assert toggle_response.status_code == 200
    with app.app_context():
        reflected = main_routes._reflected_table("subjects")
        refreshed = db.session.execute(
            select(reflected.c.is_elective).where(reflected.c.subject_id == subject_id)
        ).scalar_one()
        assert refreshed is True


def test_faculty_pages_tolerate_missing_optional_faculty_columns(client, app, monkeypatch):
    from cms_app.main import routes as main_routes
    from cms_app.faculty import routes as faculty_routes

    with app.app_context():
        trust = Trust(trust_name="Trust Faculty Minimal", trust_code="TRUST_FAC_MIN", is_active=True)
        db.session.add(trust)
        db.session.flush()

        institute = Institute(
            trust_id_fk=trust.trust_id,
            institute_name="Faculty Minimal Institute",
            institute_code="FAC_MIN_INST",
            is_active=True,
        )
        db.session.add(institute)
        db.session.flush()

        program = Program(institute_id_fk=institute.institute_id, program_name="Faculty Minimal Program")
        db.session.add(program)
        db.session.flush()

        admin = User(
            username="admin_faculty_minimal",
            password_hash=generate_password_hash("secret"),
            role="admin",
            trust_id_fk=trust.trust_id,
            program_id_fk=program.program_id,
        )
        faculty_user = User(
            username="faculty_minimal_user",
            password_hash=generate_password_hash("secret"),
            role="faculty",
            trust_id_fk=trust.trust_id,
            program_id_fk=program.program_id,
        )
        db.session.add_all([admin, faculty_user])
        db.session.flush()

        faculty = Faculty(
            user_id_fk=faculty_user.user_id,
            program_id_fk=program.program_id,
            full_name="Kiran Joshi",
            email="kiran@example.com",
            mobile="9999999998",
            designation="Professor",
            department="CS",
            is_active=True,
        )
        db.session.add(faculty)
        db.session.commit()

        faculty_id = faculty.faculty_id

    original_main_get = main_routes.db.session.get

    def guarded_main_get(entity, ident, *args, **kwargs):
        if entity is main_routes.Faculty:
            raise AssertionError("faculty workflow should not use full Faculty session.get on legacy schemas")
        return original_main_get(entity, ident, *args, **kwargs)

    def legacy_fetch_faculty(faculty_id_value):
        reflected = main_routes._reflected_table("faculty")
        row = main_routes.db.session.execute(
            select(reflected).where(reflected.c.faculty_id == faculty_id_value)
        ).mappings().first()
        if row is None:
            return None
        data = dict(row)
        for key in (
            "photo_url",
            "emp_id",
            "date_of_joining",
            "highest_qualification",
            "experience_years",
            "specialization",
            "medium_expertise",
            "extra_data",
        ):
            data.pop(key, None)
        return data

    def legacy_fetch_faculty_by_user_id(user_id_value):
        reflected = main_routes._reflected_table("faculty")
        row = main_routes.db.session.execute(
            select(reflected).where(reflected.c.user_id_fk == user_id_value)
        ).mappings().first()
        if row is None:
            return None
        data = dict(row)
        for key in (
            "photo_url",
            "emp_id",
            "date_of_joining",
            "highest_qualification",
            "experience_years",
            "specialization",
            "medium_expertise",
            "extra_data",
        ):
            data.pop(key, None)
        return data

    monkeypatch.setattr(main_routes.db.session, "get", guarded_main_get)
    monkeypatch.setattr(main_routes, "_fetch_faculty_mapping", legacy_fetch_faculty)
    monkeypatch.setattr(main_routes, "_fetch_faculty_by_user_id_mapping", legacy_fetch_faculty_by_user_id)
    monkeypatch.setattr(faculty_routes, "_fetch_faculty_by_user_id_mapping", legacy_fetch_faculty_by_user_id)

    _login(client, "admin_faculty_minimal")

    list_response = client.get("/faculty")
    assert list_response.status_code == 200
    assert "Kiran Joshi" in list_response.data.decode("utf-8")

    profile_response = client.get(f"/faculty/{faculty_id}")
    assert profile_response.status_code == 200
    assert "Kiran Joshi" in profile_response.data.decode("utf-8")

    _login(client, "faculty_minimal_user")
    dashboard_response = client.get("/faculty/dashboard", follow_redirects=True)
    assert dashboard_response.status_code == 200

    timetable_response = client.get("/faculty/timetable", follow_redirects=True)
    assert timetable_response.status_code == 200


def test_wizard_exit_clears_context_and_returns_to_tenants(client, app):
    with app.app_context():
        super_admin = User(
            username="sa_wizard_exit",
            password_hash=generate_password_hash("secret"),
            role="admin",
            is_super_admin=True,
        )
        db.session.add(super_admin)
        db.session.commit()

    _login(client, "sa_wizard_exit")
    with client.session_transaction() as sess:
        sess["wizard_institute_id"] = 999

    response = client.get("/wizard/exit", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/super-admin/tenants")

    with client.session_transaction() as sess:
        assert "wizard_institute_id" not in sess
