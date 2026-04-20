from werkzeug.security import generate_password_hash

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
