from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta, timezone

from sqlalchemy import MetaData, Table, select

from cms_app import db
from cms_app.models import Faculty, FeePayment, Institute, Program, Student, Trust, User


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
        db.session.add(admin)
        db.session.flush()

        student = Student(
            enrollment_no="ENR_STUDENTS_MIN",
            student_name="Aarav",
            surname="Patel",
            father_name="Rakesh",
            mobile="9999999999",
            program_id_fk=program.program_id,
            trust_id_fk=trust.trust_id,
            current_semester=4,
            medium_tag="English",
            is_active=True,
        )
        db.session.add(student)
        db.session.commit()

        program_id = program.program_id

    original_execute = main_routes.db.session.execute

    def guarded_execute(statement, *args, **kwargs):
        sql = str(statement)
        if "FROM students" in sql and "students.aadhar_no" in sql:
            raise AssertionError("students pages should not select students.aadhar_no on old schemas")
        return original_execute(statement, *args, **kwargs)

    monkeypatch.setattr(main_routes.db.session, "execute", guarded_execute)

    _login(client, "admin_students_minimal")

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
