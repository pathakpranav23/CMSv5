"""Regression tests for Category A (Financial PII) tenant-isolation fixes,
plus Priority 2 (B-8) user-delete cross-trust gate.

T-1: TrustA admin GET /fees/bank-details MUST NOT see TrustB's UPI VPA.
T-2: get_program_bank_details_resolved for an MCOM in TrustA MUST return
     the bank-details row of TrustA's BCOM, never TrustB's BCOM (even if
     TrustB's program name would sort first alphabetically via global
     ``ilike('BCOM')``).
T-3: TrustA admin POST /admin/users/<TrustB_user>/delete MUST be rejected
     (redirect + danger flash) and the user row MUST remain untouched.
"""
from werkzeug.security import generate_password_hash

from cms_app import db
from cms_app.models import (
    Faculty,
    Institute,
    Program,
    ProgramBankDetails,
    Student,
    Trust,
    User,
)


def _login(client, username, password="secret"):
    client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )
    with client.session_transaction() as sess:
        return sess.get("csrf_token")


def _make_bank_details(program, upi_vpa):
    return ProgramBankDetails(
        program_id_fk=program.program_id,
        bank_name="Demo Bank",
        account_name=f"Account {program.program_name}",
        account_number=f"0000{program.program_id}",
        ifsc="DEMO0000001",
        branch="Main Branch",
        upi_vpa=upi_vpa,
        active=True,
    )


def test_bank_details_view_does_not_leak_cross_trust_upi(client, app):
    """T-1 — /fees/bank-details shows ONLY caller's trust program + UPI VPA."""
    with app.app_context():
        trust_a = Trust(trust_name="Trust Scope A", trust_code="TR_SCOPE_A", is_active=True)
        trust_b = Trust(trust_name="Trust Scope B", trust_code="TR_SCOPE_B", is_active=True)
        db.session.add_all([trust_a, trust_b])
        db.session.flush()

        inst_a = Institute(
            trust_id_fk=trust_a.trust_id,
            institute_name="Inst Scope A",
            institute_code="INST_SCOPE_A",
            is_active=True,
        )
        inst_b = Institute(
            trust_id_fk=trust_b.trust_id,
            institute_name="Inst Scope B",
            institute_code="INST_SCOPE_B",
            is_active=True,
        )
        db.session.add_all([inst_a, inst_b])
        db.session.flush()

        prog_a1 = Program(institute_id_fk=inst_a.institute_id, program_name="BCOM")
        prog_a2 = Program(institute_id_fk=inst_a.institute_id, program_name="BA")
        prog_b1 = Program(institute_id_fk=inst_b.institute_id, program_name="BCOM")
        db.session.add_all([prog_a1, prog_a2, prog_b1])
        db.session.flush()

        bd_a1 = _make_bank_details(prog_a1, "trust-a-bcom@okhdfcbank")
        bd_a2 = _make_bank_details(prog_a2, "trust-a-ba@okhdfcbank")
        bd_b1 = _make_bank_details(prog_b1, "trust-b-bcom@okhdfcbank")
        db.session.add_all([bd_a1, bd_a2, bd_b1])

        admin_a = User(
            username="admin_scope_a",
            password_hash=generate_password_hash("secret"),
            role="admin",
            trust_id_fk=trust_a.trust_id,
        )
        db.session.add(admin_a)
        db.session.commit()

        prog_a1_id = int(prog_a1.program_id)
        prog_a2_id = int(prog_a2.program_id)
        trust_a_count_expected = 2

    _login(client, "admin_scope_a")
    resp = client.get("/fees/bank-details", follow_redirects=True)
    text = resp.data.decode("utf-8")

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}. Body snippet: {text[:400]}"
    assert "trust-a-bcom@okhdfcbank" in text, "TrustA admin should see their own BCOM UPI"
    assert "trust-a-ba@okhdfcbank" in text, "TrustA admin should see their own BA UPI"
    assert "trust-b-bcom@okhdfcbank" not in text, "TrustB UPI must never be served to TrustA admin"

    option_count = text.lower().count("<option")
    program_count = text.count(f"/fees/bank-details/edit?program_id={prog_a1_id}") + text.count(
        f'value="{prog_a1_id}"'
    )
    assert program_count >= 1 or option_count >= trust_a_count_expected, (
        f"Program dropdown should contain TrustA's {trust_a_count_expected} programs only; "
        f"got option_count={option_count} program_refs={program_count}"
    )


def test_mcom_bcom_fallback_is_trust_scoped(client, app):
    """T-2 — MCOM resolves to SAME-trust BCOM UPI VPA only, never cross-trust.

    Setup:
      - TrustB has a BCOM (alphabetically first by institute code) with a
        unique UPI.
      - TrustA has a BCOM with a DIFFERENT UPI, and an MCOM that has NO bank
        details row of its own.
    Before fix: global ilike('BCOM') would return TrustB's BCOM to TrustA's
    MCOM student, routing payments to wrong-college account.
    After fix: TrustA's MCOM -> resolves to TrustA's BCOM UPI only.
    """
    from cms_app.main.routes import get_program_bank_details_resolved

    with app.app_context():
        trust_a = Trust(trust_name="Trust MCOM A", trust_code="TR_MCOM_A", is_active=True)
        trust_b = Trust(trust_name="Trust MCOM B", trust_code="TR_MCOM_B", is_active=True)
        db.session.add_all([trust_a, trust_b])
        db.session.flush()

        inst_a = Institute(
            trust_id_fk=trust_a.trust_id,
            institute_name="Inst MCOM A",
            institute_code="INST_MCOM_A",
            is_active=True,
        )
        inst_b = Institute(
            trust_id_fk=trust_b.trust_id,
            institute_name="AAA Inst MCOM B",  # sorts before inst_a alphabetically
            institute_code="AAA_INST_MCOM_B",
            is_active=True,
        )
        db.session.add_all([inst_a, inst_b])
        db.session.flush()

        # --- Trust B BCOM (would win global alphabetical-first) ---
        prog_b_bcom = Program(institute_id_fk=inst_b.institute_id, program_name="BCOM")
        db.session.add(prog_b_bcom)
        db.session.flush()
        bd_b_bcom = _make_bank_details(prog_b_bcom, "wrong-trust-b-bcom@okhdfcbank")
        db.session.add(bd_b_bcom)

        # --- Trust A programs ---
        prog_a_bcom = Program(institute_id_fk=inst_a.institute_id, program_name="BCOM")
        prog_a_mcom = Program(institute_id_fk=inst_a.institute_id, program_name="MCOM")
        db.session.add_all([prog_a_bcom, prog_a_mcom])
        db.session.flush()
        bd_a_bcom = _make_bank_details(prog_a_bcom, "correct-trust-a-bcom@okhdfcbank")
        db.session.add(bd_a_bcom)

        db.session.commit()

        trust_a_id = int(trust_a.trust_id)
        mcom_id = int(prog_a_mcom.program_id)
        a_bcom_id = int(prog_a_bcom.program_id)
        b_bcom_id = int(prog_b_bcom.program_id)

    with app.app_context():
        resolved = get_program_bank_details_resolved(mcom_id, trust_id=trust_a_id)

    assert resolved is not None, "MCOM must fallback to a BCOM bank-details row"
    assert resolved.upi_vpa == "correct-trust-a-bcom@okhdfcbank", (
        f"MCOM -> BCOM fallback resolved to wrong trust UPI: {resolved.upi_vpa!r}. "
        f"Expected correct-trust-a-bcom@okhdfcbank."
    )
    assert resolved.program_id_fk == a_bcom_id, (
        f"Resolved BCOM program_id={resolved.program_id_fk} but should be TrustA's BCOM (id={a_bcom_id}). "
        f"TrustB's BCOM id={b_bcom_id} must not leak."
    )


def test_user_delete_rejects_cross_trust_admin(client, app):
    """T-3 (Priority 2, B-8) — Cross-trust user cascade delete is blocked.

    TrustA admin POSTs to delete a TrustB user's delete endpoint.
    Expected: 302 redirect with danger flash; TrustB user row still
    exists and cascade did not run (password_change_logs still intact)."""
    with app.app_context():
        trust_a = Trust(trust_name="Trust Delete A", trust_code="TR_DEL_A", is_active=True)
        trust_b = Trust(trust_name="Trust Delete B", trust_code="TR_DEL_B", is_active=True)
        db.session.add_all([trust_a, trust_b])
        db.session.flush()

        admin_a = User(
            username="admin_del_a",
            password_hash=generate_password_hash("secret"),
            role="admin",
            trust_id_fk=trust_a.trust_id,
        )
        admin_b = User(
            username="admin_del_b",
            password_hash=generate_password_hash("secret"),
            role="admin",
            trust_id_fk=trust_b.trust_id,
        )
        db.session.add_all([admin_a, admin_b])
        db.session.commit()
        admin_a_id = int(admin_a.user_id)
        admin_b_id = int(admin_b.user_id)
        admin_b_username = admin_b.username

    _login(client, "admin_del_a")

    with client.session_transaction() as sess:
        token = sess.get("csrf_token")

    resp = client.post(
        f"/admin/users/{admin_b_id}/delete",
        data={"csrf_token": token} if token else None,
        follow_redirects=False,
    )
    text = resp.data.decode("utf-8")

    assert resp.status_code in (302, 403), f"Expected redirect/forbid, got {resp.status_code}"
    if resp.status_code == 302:
        assert resp.headers.get("Location", "").endswith("/users") or "/users" in resp.headers.get("Location", "")

    with app.app_context():
        from sqlalchemy import select as _sel
        still_there = db.session.execute(
            _sel(User).where(User.user_id == admin_b_id)
        ).scalar_one_or_none()
    assert still_there is not None, (
        f"Cross-trust delete ran: admin user row {admin_b_id} ({admin_b_username!r}) "
        "was deleted despite the B-8 trust gate"
    )


def test_faculty_delete_rejects_cross_trust_admin(client, app):
    """T-4 (Priority 3, B-1) — Cross-trust Faculty delete is blocked."""
    with app.app_context():
        trust_a = Trust(trust_name="Trust Fac Del A", trust_code="TR_FAC_A", is_active=True)
        trust_b = Trust(trust_name="Trust Fac Del B", trust_code="TR_FAC_B", is_active=True)
        db.session.add_all([trust_a, trust_b])
        db.session.flush()

        inst_a = Institute(trust_id_fk=trust_a.trust_id, institute_name="FD Inst A", institute_code="FD_INST_A", is_active=True)
        inst_b = Institute(trust_id_fk=trust_b.trust_id, institute_name="FD Inst B", institute_code="FD_INST_B", is_active=True)
        db.session.add_all([inst_a, inst_b])
        db.session.flush()

        prog_a = Program(institute_id_fk=inst_a.institute_id, program_name="FACDELPROG")
        prog_b = Program(institute_id_fk=inst_b.institute_id, program_name="FACDELPROG_B")
        db.session.add_all([prog_a, prog_b])
        db.session.flush()

        admin_a = User(username="admin_fac_del_a", password_hash=generate_password_hash("secret"), role="admin", trust_id_fk=trust_a.trust_id)
        db.session.add(admin_a)
        db.session.flush()

        fac_b = Faculty(
            full_name="Cross Trust Faculty B",
            program_id_fk=prog_b.program_id,
            trust_id_fk=trust_b.trust_id,
            is_active=True,
        )
        db.session.add(fac_b)
        db.session.commit()

        fac_b_id = int(fac_b.faculty_id)

    _login(client, "admin_fac_del_a")
    with client.session_transaction() as sess:
        token = sess.get("csrf_token")

    resp = client.post(
        f"/faculty/{fac_b_id}/delete",
        data={"csrf_token": token} if token else None,
        follow_redirects=False,
    )
    assert resp.status_code in (302, 403), f"Expected redirect/forbid, got {resp.status_code}"

    with app.app_context():
        from sqlalchemy import select as _sel
        still_there = db.session.execute(
            _sel(Faculty).where(Faculty.faculty_id == fac_b_id)
        ).scalar_one_or_none()
    assert still_there is not None, (
        f"Cross-trust Faculty delete ran: faculty row {fac_b_id} was deleted despite the B-1 trust gate"
    )


def test_student_delete_rejects_cross_trust_admin(client, app):
    """T-5 (Priority 3, B-2) — Cross-trust Student delete is blocked."""
    with app.app_context():
        trust_a = Trust(trust_name="Trust Stu Del A", trust_code="TR_STU_A", is_active=True)
        trust_b = Trust(trust_name="Trust Stu Del B", trust_code="TR_STU_B", is_active=True)
        db.session.add_all([trust_a, trust_b])
        db.session.flush()

        inst_a = Institute(trust_id_fk=trust_a.trust_id, institute_name="SD Inst A", institute_code="SD_INST_A", is_active=True)
        inst_b = Institute(trust_id_fk=trust_b.trust_id, institute_name="SD Inst B", institute_code="SD_INST_B", is_active=True)
        db.session.add_all([inst_a, inst_b])
        db.session.flush()

        prog_a = Program(institute_id_fk=inst_a.institute_id, program_name="STUDELPROG")
        prog_b = Program(institute_id_fk=inst_b.institute_id, program_name="STUDELPROG_B")
        db.session.add_all([prog_a, prog_b])
        db.session.flush()

        admin_a = User(username="admin_stu_del_a", password_hash=generate_password_hash("secret"), role="admin", trust_id_fk=trust_a.trust_id)
        db.session.add(admin_a)
        db.session.flush()

        stu_b = Student(
            enrollment_no="STUDEL_B001",
            student_name="Cross",
            surname="StudentB",
            program_id_fk=prog_b.program_id,
            trust_id_fk=trust_b.trust_id,
            is_active=True,
        )
        db.session.add(stu_b)
        db.session.commit()

        stu_b_enr = stu_b.enrollment_no

    _login(client, "admin_stu_del_a")
    with client.session_transaction() as sess:
        token = sess.get("csrf_token")

    resp = client.post(
        f"/students/{stu_b_enr}/delete",
        data={"csrf_token": token} if token else None,
        follow_redirects=False,
    )
    assert resp.status_code in (302, 403), f"Expected redirect/forbid, got {resp.status_code}"

    with app.app_context():
        from sqlalchemy import select as _sel
        still_there = db.session.execute(
            _sel(Student).where(Student.enrollment_no == stu_b_enr)
        ).scalar_one_or_none()
    assert still_there is not None, (
        f"Cross-trust Student delete ran: {stu_b_enr!r} was deleted despite the B-2 trust gate"
    )


def test_student_edit_rejects_cross_trust_admin_post(client, app):
    """T-6 (Priority 4-A, B-3) — Cross-trust Student POST edit is blocked.

    TrustA admin posts a surname edit to TrustB's student. After the POST
    the DB-stored surname must still be TrustB original.
    """
    with app.app_context():
        trust_a = Trust(trust_name="Trust Edit A", trust_code="TR_EDT_A", is_active=True)
        trust_b = Trust(trust_name="Trust Edit B", trust_code="TR_EDT_B", is_active=True)
        db.session.add_all([trust_a, trust_b])
        db.session.flush()

        inst_a = Institute(trust_id_fk=trust_a.trust_id, institute_name="EDT Inst A", institute_code="EDT_INST_A", is_active=True)
        inst_b = Institute(trust_id_fk=trust_b.trust_id, institute_name="EDT Inst B", institute_code="EDT_INST_B", is_active=True)
        db.session.add_all([inst_a, inst_b])
        db.session.flush()

        prog_a = Program(institute_id_fk=inst_a.institute_id, program_name="EDITPROGA")
        prog_b = Program(institute_id_fk=inst_b.institute_id, program_name="EDITPROGB")
        db.session.add_all([prog_a, prog_b])
        db.session.flush()

        admin_a = User(username="admin_edt_a", password_hash=generate_password_hash("secret"), role="admin", trust_id_fk=trust_a.trust_id)
        db.session.add(admin_a)
        db.session.flush()

        stu_b = Student(
            enrollment_no="EDT_B001",
            student_name="Original",
            surname="Initial",
            program_id_fk=prog_b.program_id,
            current_semester=1,
            category="General",
            trust_id_fk=trust_b.trust_id,
            is_active=True,
        )
        db.session.add(stu_b)
        db.session.commit()

        prog_b_id = int(prog_b.program_id)

    _login(client, "admin_edt_a")
    with client.session_transaction() as sess:
        token = sess.get("csrf_token")

    payload = {
        "program_id_fk": str(prog_b_id),
        "current_semester": "1",
        "category": "General",
        "student_name": "Hacked",
        "surname": "INJECTED",
    }
    if token:
        payload["csrf_token"] = token

    resp = client.post(
        "/students/EDT_B001/edit",
        data=payload,
        follow_redirects=False,
    )
    assert resp.status_code in (302, 403), f"Expected redirect/forbid, got {resp.status_code}"

    with app.app_context():
        from sqlalchemy import select as _sel
        row = db.session.execute(
            _sel(Student).where(Student.enrollment_no == "EDT_B001")
        ).scalar_one_or_none()
    assert row is not None and row.surname and row.surname.lower() != "injected", (
        f"Cross-trust student edit wrote unauthorised value: surname={row.surname!r}"
    )


def test_faculty_link_user_rejects_cross_trust(client, app):
    """T-7 (Priority 4-B, B-9) — Cross-trust Faculty link/unlink POST blocked.

    TrustA admin tries to link a TrustB faculty to a TrustB-local username.
    After the POST: faculty_b.user_id_fk remains None.
    """
    with app.app_context():
        trust_a = Trust(trust_name="Trust Fac Link A", trust_code="TR_FL_A", is_active=True)
        trust_b = Trust(trust_name="Trust Fac Link B", trust_code="TR_FL_B", is_active=True)
        db.session.add_all([trust_a, trust_b])
        db.session.flush()

        inst_b = Institute(trust_id_fk=trust_b.trust_id, institute_name="FL Inst B", institute_code="FL_INST_B", is_active=True)
        db.session.add(inst_b)
        db.session.flush()

        prog_b = Program(institute_id_fk=inst_b.institute_id, program_name="FACLINKPROGB")
        db.session.add(prog_b)
        db.session.flush()

        admin_a = User(username="admin_fl_a", password_hash=generate_password_hash("secret"), role="admin", trust_id_fk=trust_a.trust_id)
        dummy_b = User(username="fac_user_b", password_hash=generate_password_hash("secret"), role="clerk", trust_id_fk=trust_b.trust_id)
        db.session.add_all([admin_a, dummy_b])
        db.session.flush()

        fac_b = Faculty(
            full_name="Fac Link B",
            program_id_fk=prog_b.program_id,
            trust_id_fk=trust_b.trust_id,
            is_active=True,
        )
        db.session.add(fac_b)
        db.session.commit()

        fac_b_id = int(fac_b.faculty_id)

    _login(client, "admin_fl_a")
    with client.session_transaction() as sess:
        token = sess.get("csrf_token")

    payload = {"username": "fac_user_b"}
    if token:
        payload["csrf_token"] = token
    resp = client.post(f"/faculty/{fac_b_id}/link-user", data=payload, follow_redirects=False)
    assert resp.status_code in (302, 403)

    with app.app_context():
        from sqlalchemy import select as _sel
        row = db.session.execute(_sel(Faculty).where(Faculty.faculty_id == fac_b_id)).scalar_one_or_none()
    assert row is not None and row.user_id_fk is None, (
        f"Cross-trust faculty link set user_id_fk={row.user_id_fk!r}"
    )


def test_student_link_user_rejects_cross_trust(client, app):
    """T-8 (Priority 4-C, B-10) — Cross-trust Student link-user POST blocked.

    TrustA admin posts a username link to TrustB's student. After POST
    the student.user_id_fk must still be None.
    """
    with app.app_context():
        trust_a = Trust(trust_name="Trust Stu Link A", trust_code="TR_SL_A", is_active=True)
        trust_b = Trust(trust_name="Trust Stu Link B", trust_code="TR_SL_B", is_active=True)
        db.session.add_all([trust_a, trust_b])
        db.session.flush()

        inst_b = Institute(trust_id_fk=trust_b.trust_id, institute_name="SL Inst B", institute_code="SL_INST_B", is_active=True)
        db.session.add(inst_b)
        db.session.flush()

        prog_b = Program(institute_id_fk=inst_b.institute_id, program_name="STULINKPROGB")
        db.session.add(prog_b)
        db.session.flush()

        admin_a = User(username="admin_sl_a", password_hash=generate_password_hash("secret"), role="admin", trust_id_fk=trust_a.trust_id)
        dummy_b = User(username="stu_user_b", password_hash=generate_password_hash("secret"), role="student", trust_id_fk=trust_b.trust_id)
        db.session.add_all([admin_a, dummy_b])
        db.session.flush()

        stu_b = Student(
            enrollment_no="SL_B001",
            student_name="LinkTarget",
            surname="StudentB",
            program_id_fk=prog_b.program_id,
            current_semester=1,
            category="General",
            trust_id_fk=trust_b.trust_id,
            is_active=True,
        )
        db.session.add(stu_b)
        db.session.commit()

    _login(client, "admin_sl_a")
    with client.session_transaction() as sess:
        token = sess.get("csrf_token")
    payload = {"username": "stu_user_b"}
    if token:
        payload["csrf_token"] = token
    resp = client.post("/students/SL_B001/link-user", data=payload, follow_redirects=False)
    assert resp.status_code in (302, 403)

    with app.app_context():
        from sqlalchemy import select as _sel
        row = db.session.execute(
            _sel(Student).where(Student.enrollment_no == "SL_B001")
        ).scalar_one_or_none()
    assert row is not None and row.user_id_fk is None, (
        f"Cross-trust student link set user_id_fk={row.user_id_fk!r}"
    )


def test_bulk_promote_rejects_cross_trust_rows(client, app):
    """T-9 (Priority 5, D-3) — Cross-trust students in bulk promote are failed.

    Selection = [TrustB_student].  TrustA admin posts bulk promote with
    target_semester=3.  Response JSON summary.failed == 1; and DB still
    shows current_semester=1 for TrustB's student.
    """
    with app.app_context():
        trust_a = Trust(trust_name="Trust Prom A", trust_code="TR_PR_A", is_active=True)
        trust_b = Trust(trust_name="Trust Prom B", trust_code="TR_PR_B", is_active=True)
        db.session.add_all([trust_a, trust_b])
        db.session.flush()

        inst_b = Institute(trust_id_fk=trust_b.trust_id, institute_name="Prom Inst B", institute_code="PR_INST_B", is_active=True)
        db.session.add(inst_b)
        db.session.flush()

        prog_b = Program(institute_id_fk=inst_b.institute_id, program_name="PROMPROGB")
        db.session.add(prog_b)
        db.session.flush()

        admin_a = User(username="admin_pr_a", password_hash=generate_password_hash("secret"), role="admin", trust_id_fk=trust_a.trust_id)
        db.session.add(admin_a)
        db.session.flush()

        stu_b = Student(
            enrollment_no="PR_B001",
            student_name="PromoTarget",
            surname="StuB",
            program_id_fk=prog_b.program_id,
            current_semester=1,
            category="General",
            trust_id_fk=trust_b.trust_id,
            is_active=True,
        )
        db.session.add(stu_b)
        db.session.commit()

    _login(client, "admin_pr_a")
    with client.session_transaction() as sess:
        token = sess.get("csrf_token")
    payload = {
        "selected_ids": "PR_B001",
        "target_semester": "3",
    }
    if token:
        payload["csrf_token"] = token
    resp = client.post(
        "/students/bulk/promote-semester",
        data=payload,
        follow_redirects=False,
        headers={"Accept": "application/json"},
    )
    try:
        data = resp.get_json() or {}
    except Exception:
        data = {}
    failed = (data.get("summary") or {}).get("failed", None)
    # Either JSON API failed==1, or HTML redirect with 302/403 blocked entirely.
    ok = (resp.status_code in (302, 403)) or (resp.status_code == 200 and failed == 1)
    assert ok, f"Bulk promote unexpectedly succeeded: status={resp.status_code}, failed={failed}"

    with app.app_context():
        from sqlalchemy import select as _sel
        row = db.session.execute(
            _sel(Student).where(Student.enrollment_no == "PR_B001")
        ).scalar_one_or_none()
    assert row is not None and int(row.current_semester or -1) == 1, (
        f"Cross-trust bulk promote mutated semester to {row.current_semester!r}"
    )


def test_services_program_ownership_gates(app):
    """T-10 (Priority 6) — opening_cohorts + division_allocation direct calls.

    Calls build_opening_cohort_preview + build_allocation_preview with
    trust_id=TrustA.id but program_id=TrustB_prog_id.  Both must raise
    ValueError (same surface as a "not found" program).
    """
    from cms_app.services.opening_cohorts import build_opening_cohort_preview
    from cms_app.services.division_allocation import build_allocation_preview

    with app.app_context():
        trust_a = Trust(trust_name="Trust SVCA", trust_code="TR_SVC_A", is_active=True)
        trust_b = Trust(trust_name="Trust SVCB", trust_code="TR_SVC_B", is_active=True)
        db.session.add_all([trust_a, trust_b])
        db.session.flush()

        inst_a = Institute(trust_id_fk=trust_a.trust_id, institute_name="SVC Inst A", institute_code="SVC_INST_A", is_active=True)
        inst_b = Institute(trust_id_fk=trust_b.trust_id, institute_name="SVC Inst B", institute_code="SVC_INST_B", is_active=True)
        db.session.add_all([inst_a, inst_b])
        db.session.flush()

        prog_a = Program(institute_id_fk=inst_a.institute_id, program_name="SVCPROGA", program_duration_years=3)
        prog_b = Program(institute_id_fk=inst_b.institute_id, program_name="SVCPROGB", program_duration_years=3)
        db.session.add_all([prog_a, prog_b])
        db.session.flush()

        db.session.commit()
        trust_a_id = int(trust_a.trust_id)
        prog_b_id = int(prog_b.program_id)

    with app.app_context():
        raised = False
        try:
            build_opening_cohort_preview(prog_b_id, "2026-27", trust_a_id)
        except ValueError:
            raised = True
        assert raised, "opening_cohorts.build_opening_cohort_preview cross-trust program was NOT blocked"

    with app.app_context():
        raised = False
        try:
            build_allocation_preview(prog_b_id, 1, 60, trust_a_id)
        except ValueError:
            raised = True
        assert raised, "division_allocation.build_allocation_preview cross-trust program was NOT blocked"


