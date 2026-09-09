"""P0-1 global CSRF enforcement tests.

Ensures the new global ``enforce_global_csrf`` before_request hook blocks
unprotected mutating requests, tolerates whitelisted endpoints, and still
accepts requests that carry a correctly-matched in-date session CSRF token.

Three NEGATIVE cases + one POSITIVE case (per endpoint) cover the
acceptance-critical paths:
* MISSING CSRF token      → 302 redirect + "Refresh the Page or login again" flash
* WRONG CSRF token        → same 302 + same flash message
* EXPIRED CSRF token      → same 302 + same flash message
* CORRECT CSRF token      → POST succeeds (non-flash 302 or 200)

Endpoints exercised (chosen because each has distinct controller behaviour
that must still work under global CSRF):
* ``/login``                     → whitelisted, so no CSRF is required to POST.
* ``/account/settings``          → generic POST route for settings updates;
                                   subject to global CSRF.
* ``/admin/users/new``           → user creation (typical mutating form POST)
* ``/fees/payments/<id>/verify`` → financial write path (mark proof verified)
"""

from __future__ import annotations

import time
import pytest


FLASH_EXPECTED = "Refresh the Page or login again"


def _login_and_get_csrf(client, username="testuser", password="secret"):
    """Fetch the /login page so Flask session CSRF is issued, POST credentials,
    then return the CSRF token stored inside the resulting Flask session.
    """
    # Login is CSRF-whitelisted, so it succeeds with no csrf_token in body.
    login_resp = client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=False,
    )
    # We accept either 200 (re-rendered login form with errors) or the 302
    # redirect to dashboard; the session CSRF token is always available from
    # the Flask session after processing, because inject_i18n set it.
    assert login_resp.status_code in (200, 302, 303)
    with client.session_transaction() as sess:
        token = sess.get("csrf_token")
    assert token, "expected session CSRF token after login interaction"
    return token


# ---------------------------------------------------------------------------
# 1. /login is in the CSRF_WHITELIST: POST must NOT be blocked.
# ---------------------------------------------------------------------------
def test_login_whitelisted_missing_csrf_succeeds(client):
    resp = client.post(
        "/login",
        data={"username": "testuser", "password": "wrong"},
        follow_redirects=False,
    )
    # Accepts 200 (invalid credentials → re-render) or 302 (valid → dashboard)
    # The critical assertion is that the global CSRF hook did NOT return a
    # flashy redirect back to / (its normal failure mode).
    assert resp.status_code in (200, 302, 303)
    with client.session_transaction() as sess:
        flashes = sess.pop("_flashes", []) if sess else []
    assert not any(FLASH_EXPECTED in (msg or "") for (_, msg) in flashes), (
        "login endpoint is whitelisted and must NOT trigger the csrf flash"
    )


# ---------------------------------------------------------------------------
# 2. /account/settings: generic POST path — global CSRF hook must enforce
# ---------------------------------------------------------------------------
def _admin_scoped_seed(app):
    """Create admin user + small program scope so the settings endpoint has
    the required active_workspace context.  Returns the created admin user
    (or the pre-existing one on re-runs for idempotency).
    """
    from cms_app import db
    from cms_app.models import Trust, Institute, Program, User
    from werkzeug.security import generate_password_hash

    with app.app_context():
        existing = User.query.filter_by(username="csrf_admin").first()
        if existing:
            return {"admin": existing}

        trust = Trust(trust_name="CSRF Trust", trust_code="CSRF_TR", is_active=True)
        db.session.add(trust)
        db.session.flush()
        institute = Institute(
            trust_id_fk=trust.trust_id,
            institute_name="CSRF Institute",
            institute_code="CSRF_INST",
        )
        db.session.add(institute)
        db.session.flush()
        program = Program(
            institute_id_fk=institute.institute_id,
            program_name="CSRF Program",
        )
        db.session.add(program)
        db.session.flush()
        admin = User(
            username="csrf_admin",
            password_hash=generate_password_hash("secret"),
            role="admin",
            trust_id_fk=trust.trust_id,
            program_id_fk=program.program_id,
        )
        db.session.add(admin)
        db.session.commit()
        return {"admin": admin}


def test_settings_missing_csrf_blocked(client, app):
    _admin_scoped_seed(app)
    csrf = _login_and_get_csrf(client, "csrf_admin", "secret")
    assert csrf

    # POST without csrf_token — should be redirected + flash
    resp = client.post(
        "/account/settings",
        data={"display_name": "Changed", "mobile": "0000000000"},
        follow_redirects=False,
    )
    assert resp.status_code in (302, 303)
    with client.session_transaction() as sess:
        flashes = sess.pop("_flashes", []) if sess else []
    assert any(FLASH_EXPECTED in (msg or "") for (_, msg) in flashes), (
        "missing csrf must trigger Refresh-the-Page flash"
    )


def test_settings_wrong_csrf_blocked(client, app):
    _admin_scoped_seed(app)
    csrf = _login_and_get_csrf(client, "csrf_admin", "secret")
    resp = client.post(
        "/account/settings",
        data={"csrf_token": "DEFINITELY_NOT_THE_CORRECT_TOKEN",
              "display_name": "Changed",
              "mobile": "0000000000"},
        follow_redirects=False,
    )
    assert resp.status_code in (302, 303)
    with client.session_transaction() as sess:
        flashes = sess.pop("_flashes", []) if sess else []
    assert any(FLASH_EXPECTED in (msg or "") for (_, msg) in flashes)


def test_settings_expired_csrf_blocked(client, app):
    _admin_scoped_seed(app)
    csrf = _login_and_get_csrf(client, "csrf_admin", "secret")
    with client.session_transaction() as sess:
        # CSRF TTL is 7200s default — roll back by 7200 + 10s to force expire
        ttl = int(app.config.get("CSRF_TOKEN_TTL", 7200) or 7200)
        sess["csrf_token_issued_at"] = int(time.time()) - ttl - 10
    resp = client.post(
        "/account/settings",
        data={"csrf_token": csrf, "display_name": "Changed", "mobile": "0000000000"},
        follow_redirects=False,
    )
    assert resp.status_code in (302, 303)
    with client.session_transaction() as sess:
        flashes = sess.pop("_flashes", []) if sess else []
    assert any(FLASH_EXPECTED in (msg or "") for (_, msg) in flashes)


def test_settings_correct_csrf_succeeds(client, app):
    _admin_scoped_seed(app)
    csrf = _login_and_get_csrf(client, "csrf_admin", "secret")
    resp = client.post(
        "/account/settings",
        data={"csrf_token": csrf, "display_name": "Changed", "mobile": "0000000000"},
        follow_redirects=False,
    )
    # Either 200 OK or 302 redirect back to settings page (success path) —
    # must NOT be the 302 + flash "Refresh the Page" block response.
    assert resp.status_code in (200, 302, 303)
    with client.session_transaction() as sess:
        flashes = sess.pop("_flashes", []) if sess else []
    assert not any(FLASH_EXPECTED in (msg or "") for (_, msg) in flashes), (
        "valid csrf_token must NOT be blocked by global enforce hook"
    )


# ---------------------------------------------------------------------------
# 3. User new POST path: /admin/users/new
# ---------------------------------------------------------------------------
def _seed_user_context(app):
    from cms_app import db
    from cms_app.models import Trust, Institute, Program, User, Division
    from werkzeug.security import generate_password_hash

    with app.app_context():
        if User.query.filter_by(username="csrf_admin_users").first():
            return

        trust = Trust(trust_name="CSRF Users Trust", trust_code="CSRF_USR_TR", is_active=True)
        db.session.add(trust)
        db.session.flush()
        institute = Institute(
            trust_id_fk=trust.trust_id,
            institute_name="CSRF Users Institute",
            institute_code="CSRF_USR_INST",
        )
        db.session.add(institute)
        db.session.flush()
        program = Program(
            institute_id_fk=institute.institute_id,
            program_name="CSRF Users Program",
        )
        db.session.add(program)
        db.session.flush()
        admin = User(
            username="csrf_admin_users",
            password_hash=generate_password_hash("secret"),
            role="admin",
            trust_id_fk=trust.trust_id,
            program_id_fk=program.program_id,
        )
        db.session.add(admin)
        db.session.commit()


def test_users_new_missing_csrf_blocked(client, app):
    _seed_user_context(app)
    csrf = _login_and_get_csrf(client, "csrf_admin_users", "secret")
    assert csrf
    resp = client.post(
        "/admin/users/new",
        data={"username": "student_csrfa", "role": "student", "password": "secret",
              "confirm_password": "secret"},
        follow_redirects=False,
    )
    assert resp.status_code in (302, 303)
    with client.session_transaction() as sess:
        flashes = sess.pop("_flashes", []) if sess else []
    assert any(FLASH_EXPECTED in (msg or "") for (_, msg) in flashes)


def test_users_new_correct_csrf_succeeds(client, app):
    _seed_user_context(app)
    csrf = _login_and_get_csrf(client, "csrf_admin_users", "secret")
    resp = client.post(
        "/admin/users/new",
        data={"csrf_token": csrf, "username": "student_csrfb",
              "role": "student", "password": "secret", "confirm_password": "secret"},
        follow_redirects=False,
    )
    assert resp.status_code in (200, 302, 303)
    with client.session_transaction() as sess:
        flashes = sess.pop("_flashes", []) if sess else []
    assert not any(FLASH_EXPECTED in (msg or "") for (_, msg) in flashes)


# ---------------------------------------------------------------------------
# 4. Financial write path: fees/payments/<id>/verify
# ---------------------------------------------------------------------------
def _seed_fee_context(app):
    from cms_app import db
    from cms_app.models import (
        Trust, Institute, Program, User, Student, Division, FeePayment,
    )
    from werkzeug.security import generate_password_hash

    with app.app_context():
        existing = User.query.filter_by(username="csrf_admin_fees").first()
        if existing:
            latest = FeePayment.query.order_by(FeePayment.payment_id.desc()).first()
            return latest.payment_id if latest else None

        trust = Trust(trust_name="CSRF Fees Trust", trust_code="CSRF_FEE_TR", is_active=True)
        db.session.add(trust)
        db.session.flush()
        institute = Institute(
            trust_id_fk=trust.trust_id,
            institute_name="CSRF Fees Institute",
            institute_code="CSRF_FEE_INST",
        )
        db.session.add(institute)
        db.session.flush()
        program = Program(
            institute_id_fk=institute.institute_id,
            program_name="CSRF Fees Program",
        )
        db.session.add(program)
        db.session.flush()
        division = Division(
            program_id_fk=program.program_id,
            semester=1,
            division_code="A",
            capacity=40,
            medium_tag="English",
        )
        db.session.add(division)
        db.session.flush()
        admin = User(
            username="csrf_admin_fees",
            password_hash=generate_password_hash("secret"),
            role="admin",
            trust_id_fk=trust.trust_id,
            program_id_fk=program.program_id,
        )
        db.session.add(admin)
        db.session.flush()
        student = Student(
            enrollment_no="CSRF_STUD_FEE_001",
            student_name="Fees CSRF",
            surname="Student",
            mobile="9999999999",
            program_id_fk=program.program_id,
            division_id_fk=division.division_id,
            trust_id_fk=trust.trust_id,
            current_semester=1,
            medium_tag="English",
            category="OPEN",
        )
        db.session.add(student)
        db.session.flush()
        payment = FeePayment(
            enrollment_no=student.enrollment_no,
            program_id_fk=program.program_id,
            semester=1,
            medium_tag="English",
            amount=1000.0,
            utr="CSRF_UTR_FEES_001",
            status="submitted",
            created_by_user_id=admin.user_id,
        )
        db.session.add(payment)
        db.session.commit()
        return payment.payment_id


def test_fee_verify_missing_csrf_blocked(client, app):
    pid = _seed_fee_context(app)
    csrf = _login_and_get_csrf(client, "csrf_admin_fees", "secret")
    assert csrf
    resp = client.post(
        f"/fees/payments/{pid}/verify",
        data={"payer_name": "Accounts Desk"},
        follow_redirects=False,
    )
    assert resp.status_code in (302, 303)
    with client.session_transaction() as sess:
        flashes = sess.pop("_flashes", []) if sess else []
    assert any(FLASH_EXPECTED in (msg or "") for (_, msg) in flashes)


def test_fee_verify_correct_csrf_succeeds(client, app):
    pid = _seed_fee_context(app)
    csrf = _login_and_get_csrf(client, "csrf_admin_fees", "secret")
    resp = client.post(
        f"/fees/payments/{pid}/verify",
        data={"csrf_token": csrf, "payer_name": "Accounts Desk"},
        follow_redirects=False,
    )
    assert resp.status_code in (200, 302, 303)
    with client.session_transaction() as sess:
        flashes = sess.pop("_flashes", []) if sess else []
    assert not any(FLASH_EXPECTED in (msg or "") for (_, msg) in flashes)
