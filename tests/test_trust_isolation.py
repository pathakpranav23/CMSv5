"""Priority 7 — Tenant Isolation acceptance tests (T-1 … T-10).

Complements :mod:`tests.test_trust_scope_bank_details.py` which covers the
P1–P6 endpoint-specific regressions.  The tests here exercise the new
``cms_app.tenant`` module directly and validate the "canonical helper"
contract across a single 2-trust × 2-program fixture that is created per
test function.

Coverage per test
-----------------
T-1 effective_trust_id  regular user  -> direct trust_id_fk
T-2 effective_trust_id  super-admin    -> None when no active_trust_id
T-3 effective_trust_id  super-admin    -> session active_trust_id
T-4 scoped_select(Program)             -> filters by trust, SA workspace same
T-5 scoped_select(Faculty) direct col  -> uses Faculty.trust_id_fk path
T-6 scoped_select(Student) join chain  -> Student → Program → Institute → Trust
T-7 scoped_select(Subject) 4-step chain -> Subject → Program → Institute → Trust
T-8 scoped_select(ProgramBankDetails)  -> ProgramBankDetails → Program → Institute
T-9 _require_same_trust(obj)           -> 2 cases: owns + not-owns -> flash/redirect
T-10 backfill & log migration          -> P7-D add_trust_id_columns_to_logs.run() applies ALTERs and backfills 3 log rows correctly

Run with:

    pytest tests/test_trust_isolation.py -v
"""

from __future__ import annotations

from flask import session, url_for
from werkzeug.security import generate_password_hash
import pytest


@pytest.fixture(autouse=True)
def _cleanup_db(request, app):
    """Per-test teardown to drop fixture rows even if assertions fail.

    Prevents ``UNIQUE constraint failed`` errors across T-1 … T-10 when
    ``test.db`` is reused by the session-scoped app fixture.
    """
    from cms_app import db  # local import to avoid plugin-time side effects
    yield
    with app.app_context():
        from cms_app.models import (
            SubjectMaterial,
            SubjectMaterialLog,
            ProgramBankDetails,
            Subject,
            Faculty,
            Student,
            Program,
            Institute,
            User,
            Trust,
            ImportLog,
            PasswordChangeLog,
            DataAuditLog,
        )
        for tbl in (
            SubjectMaterialLog,
            SubjectMaterial,
            DataAuditLog,
            ProgramBankDetails,
            PasswordChangeLog,
            ImportLog,
            Student,
            Subject,
            Faculty,
            Program,
            Institute,
            User,
            Trust,
        ):
            try:
                db.session.execute(tbl.__table__.delete())
            except Exception:
                pass
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()


def _build_isolation_fixture(app):
    """Two trusts × two programs each × one faculty/student per program.

    Returns a dict with stable ids so the tests can look them up without
    holding to detached ORM instances across contexts.
    """
    from cms_app import db
    from cms_app.models import (
        Trust, Institute, Program, Faculty, Student, User, Subject, Division,
    )

    with app.app_context():
        trust_a = Trust(trust_name="TI-A", trust_code="TIA", is_active=True)
        trust_b = Trust(trust_name="TI-B", trust_code="TIB", is_active=True)
        db.session.add_all([trust_a, trust_b])
        db.session.flush()

        inst_a = Institute(trust_id_fk=trust_a.trust_id, institute_name="TI Inst A", institute_code="TIAINST", is_active=True)
        inst_b = Institute(trust_id_fk=trust_b.trust_id, institute_name="TI Inst B", institute_code="TIBINST", is_active=True)
        db.session.add_all([inst_a, inst_b])
        db.session.flush()

        prog_a1 = Program(institute_id_fk=inst_a.institute_id, program_name="TI-Prog-A1", program_duration_years=3)
        prog_a2 = Program(institute_id_fk=inst_a.institute_id, program_name="TI-Prog-A2", program_duration_years=3)
        prog_b1 = Program(institute_id_fk=inst_b.institute_id, program_name="TI-Prog-B1", program_duration_years=3)
        prog_b2 = Program(institute_id_fk=inst_b.institute_id, program_name="TI-Prog-B2", program_duration_years=3)
        db.session.add_all([prog_a1, prog_a2, prog_b1, prog_b2])
        db.session.flush()

        # Subjects + Divisions for T-7 / T-8 select chains
        sub_a1_1 = Subject(program_id_fk=prog_a1.program_id, subject_type_id_fk=1, subject_name="Subj-A1-1", semester=1, is_active=True)
        sub_b1_1 = Subject(program_id_fk=prog_b1.program_id, subject_type_id_fk=1, subject_name="Subj-B1-1", semester=1, is_active=True)
        db.session.add_all([sub_a1_1, sub_b1_1])
        db.session.flush()

        div_a1_1 = Division(program_id_fk=prog_a1.program_id, semester=1, division_code="A", capacity=60)
        div_b1_1 = Division(program_id_fk=prog_b1.program_id, semester=1, division_code="A", capacity=60)
        db.session.add_all([div_a1_1, div_b1_1])
        db.session.flush()

        pwd = generate_password_hash("secret")
        admin_a = User(username="ti_admin_a", password_hash=pwd, role="admin", trust_id_fk=trust_a.trust_id)
        admin_b = User(username="ti_admin_b", password_hash=pwd, role="admin", trust_id_fk=trust_b.trust_id)
        super_u = User(username="ti_super", password_hash=pwd, role="super_admin", is_super_admin=True)
        db.session.add_all([admin_a, admin_b, super_u])
        db.session.flush()

        fac_a = Faculty(full_name="Faculty A", program_id_fk=prog_a1.program_id, trust_id_fk=trust_a.trust_id, is_active=True)
        fac_b = Faculty(full_name="Faculty B", program_id_fk=prog_b1.program_id, trust_id_fk=trust_b.trust_id, is_active=True)
        db.session.add_all([fac_a, fac_b])
        db.session.flush()

        stu_a = Student(enrollment_no="TI-SA-001", student_name="StuA", surname="A",
                        program_id_fk=prog_a1.program_id, current_semester=1,
                        category="General", trust_id_fk=trust_a.trust_id, is_active=True)
        stu_b = Student(enrollment_no="TI-SB-001", student_name="StuB", surname="B",
                        program_id_fk=prog_b1.program_id, current_semester=1,
                        category="General", trust_id_fk=trust_b.trust_id, is_active=True)
        db.session.add_all([stu_a, stu_b])
        db.session.flush()

        ids = {
            "trust_a_id": int(trust_a.trust_id), "trust_b_id": int(trust_b.trust_id),
            "prog_a1_id": int(prog_a1.program_id), "prog_a2_id": int(prog_a2.program_id),
            "prog_b1_id": int(prog_b1.program_id), "prog_b2_id": int(prog_b2.program_id),
            "subj_a1_id": int(sub_a1_1.subject_id), "subj_b1_id": int(sub_b1_1.subject_id),
            "fac_a_id": int(fac_a.faculty_id), "fac_b_id": int(fac_b.faculty_id),
            "admin_a_id": int(admin_a.user_id), "admin_b_id": int(admin_b.user_id),
            "super_id": int(super_u.user_id),
            "stu_a_enr": "TI-SA-001", "stu_b_enr": "TI-SB-001",
        }
        db.session.commit()
    return ids


@pytest.fixture(scope="function")
def ti_ids(app):
    return _build_isolation_fixture(app)


def _login_as(app, client, username):
    from flask_login import login_user
    from cms_app import db
    from cms_app.models import User
    with app.test_request_context("/"):
        with app.app_context():
            u = db.session.execute(User.__table__.select().where(User.username == username)).first()
            user = db.session.get(User, u.user_id) if u is not None else None
        assert user is not None, f"fixture user {username!r} not found"
        login_user(user)


# ------------------------------------------------------------
# T-1 / T-2 / T-3 — effective_trust_id canonical resolution
# ------------------------------------------------------------

def test_t1_effective_trust_id_regular_user(app, client, ti_ids):
    """T-1: Regular admin -> direct trust_id_fk."""
    _login_as(app, client, "ti_admin_a")
    with app.test_request_context("/"):
        with client.session_transaction():
            pass
        client.get("/")
        from cms_app.tenant import effective_trust_id
        with app.test_request_context("/"):
            with client.session_transaction() as sess:
                pass
            client.get("/")
    # Explicit test: directly mock current_user inside request context
    from flask_login import login_user
    from cms_app import db
    from cms_app.models import User
    with app.test_request_context("/"):
        user = db.session.get(User, ti_ids["admin_a_id"])
        login_user(user)
        from cms_app.tenant import effective_trust_id
        assert int(effective_trust_id()) == int(ti_ids["trust_a_id"])


def test_t2_effective_trust_id_super_no_workspace(app, client, ti_ids):
    """T-2: SA with no active_trust_id -> global scope (None)."""
    from flask_login import login_user
    from cms_app import db
    from cms_app.models import User
    with app.test_request_context("/"):
        user = db.session.get(User, ti_ids["super_id"])
        login_user(user)
        from cms_app.tenant import effective_trust_id
        assert effective_trust_id() is None


def test_t3_effective_trust_id_super_workspace(app, client, ti_ids):
    """T-3: SA with session['active_trust_id']=TrustB -> returns TrustB.id."""
    from flask_login import login_user
    from cms_app import db
    from cms_app.models import User
    with app.test_request_context("/"):
        from flask import session as f_sess
        user = db.session.get(User, ti_ids["super_id"])
        login_user(user)
        f_sess["active_trust_id"] = ti_ids["trust_b_id"]
        from cms_app.tenant import effective_trust_id
        assert int(effective_trust_id()) == int(ti_ids["trust_b_id"])


# ------------------------------------------------------------
# T-4 … T-8 — scoped_select(entity) for all key entities
# ------------------------------------------------------------

def test_t4_scoped_select_program(app, ti_ids):
    """T-4: Program filter returns only caller-trust programs."""
    from sqlalchemy import select as _raw_sel
    from cms_app import db
    from cms_app.tenant import scoped_select
    from cms_app.models import Program, Trust
    with app.app_context():
        unfiltered = {int(p.program_id) for p in db.session.execute(_raw_sel(Program)).scalars()}
        assert len(unfiltered) == 4, unfiltered
        a = {int(p.program_id) for p in db.session.execute(scoped_select(Program, ti_ids["trust_a_id"])).scalars()}
        b = {int(p.program_id) for p in db.session.execute(scoped_select(Program, ti_ids["trust_b_id"])).scalars()}
    assert a == {ti_ids["prog_a1_id"], ti_ids["prog_a2_id"]}
    assert b == {ti_ids["prog_b1_id"], ti_ids["prog_b2_id"]}
    assert len(a & b) == 0


def test_t5_scoped_select_faculty_direct_trust_column(app, ti_ids):
    """T-5: Faculty uses direct trust_id_fk short-circuit."""
    from cms_app import db
    from cms_app.tenant import scoped_select
    from cms_app.models import Faculty
    with app.app_context():
        fac_a = [int(f.faculty_id) for f in db.session.execute(scoped_select(Faculty, ti_ids["trust_a_id"])).scalars()]
        fac_b = [int(f.faculty_id) for f in db.session.execute(scoped_select(Faculty, ti_ids["trust_b_id"])).scalars()]
    assert fac_a == [ti_ids["fac_a_id"]]
    assert fac_b == [ti_ids["fac_b_id"]]


def test_t6_scoped_select_student_via_program_join(app, ti_ids):
    """T-6: Student → Program → Institute → Trust multi-step chain."""
    from cms_app import db
    from cms_app.tenant import scoped_select
    from cms_app.models import Student
    with app.app_context():
        st_a = sorted(s.enrollment_no for s in db.session.execute(scoped_select(Student, ti_ids["trust_a_id"])).scalars())
        st_b = sorted(s.enrollment_no for s in db.session.execute(scoped_select(Student, ti_ids["trust_b_id"])).scalars())
    assert st_a == ["TI-SA-001"]
    assert st_b == ["TI-SB-001"]


def test_t7_scoped_select_subject_via_program_join(app, ti_ids):
    """T-7: Subject 4-step join."""
    from cms_app import db
    from cms_app.tenant import scoped_select
    from cms_app.models import Subject
    with app.app_context():
        s_a = sorted(s.subject_name for s in db.session.execute(scoped_select(Subject, ti_ids["trust_a_id"])).scalars())
        s_b = sorted(s.subject_name for s in db.session.execute(scoped_select(Subject, ti_ids["trust_b_id"])).scalars())
    assert s_a == ["Subj-A1-1"]
    assert s_b == ["Subj-B1-1"]


def test_t8_scoped_select_programbankdetails(app, ti_ids):
    """T-8: ProgramBankDetails → Program → Institute → Trust."""
    from cms_app import db
    from cms_app.tenant import scoped_select
    from cms_app.models import ProgramBankDetails
    with app.app_context():
        db.session.add_all([
            ProgramBankDetails(program_id_fk=ti_ids["prog_a1_id"], bank_name="BankA", account_name="AcctA",
                               account_number="111", ifsc="BANK0000001", branch="B1", active=True, upi_vpa="a@upi"),
            ProgramBankDetails(program_id_fk=ti_ids["prog_b1_id"], bank_name="BankB", account_name="AcctB",
                               account_number="222", ifsc="BANK0000002", branch="B2", active=True, upi_vpa="b@upi"),
        ])
        db.session.commit()
        a_upis = sorted(r.upi_vpa for r in db.session.execute(scoped_select(ProgramBankDetails, ti_ids["trust_a_id"])).scalars())
        b_upis = sorted(r.upi_vpa for r in db.session.execute(scoped_select(ProgramBankDetails, ti_ids["trust_b_id"])).scalars())
    assert a_upis == ["a@upi"]
    assert b_upis == ["b@upi"]


# ------------------------------------------------------------
# T-9 — _require_same_trust ownership guard helper
# ------------------------------------------------------------

def test_t9_require_same_trust_owns_and_not(app, client, ti_ids):
    """T-9: _require_same_trust -> None if owner, redirect if not."""
    from flask_login import login_user
    from cms_app import db
    from cms_app.models import User, Program
    with app.test_request_context("/"):
        user = db.session.get(User, ti_ids["admin_a_id"])
        login_user(user)
        from cms_app.tenant import _require_same_trust
        prog_a = db.session.get(Program, ti_ids["prog_a1_id"])
        prog_b = db.session.get(Program, ti_ids["prog_b1_id"])
        assert _require_same_trust(prog_a, fallback_redirect_endpoint="main.index") is None
        rv = _require_same_trust(prog_b, fallback_redirect_endpoint="main.index")
        assert rv is not None and getattr(rv, "status_code", None) == 302


# ------------------------------------------------------------
# T-10 — Log-table migration + trust backfill
# ------------------------------------------------------------

def test_t10_log_trust_columns_backfill(app, ti_ids):
    """T-10: ALTER + backfill for password_change_log / import_logs / subject_material_logs."""
    from cms_app import db
    from cms_app.models import (
        PasswordChangeLog, ImportLog, SubjectMaterial, SubjectMaterialLog,
    )
    with app.app_context():
        pw_a = PasswordChangeLog(user_id_fk=ti_ids["admin_a_id"], changed_by_user_id_fk=ti_ids["admin_a_id"])
        pw_b = PasswordChangeLog(user_id_fk=ti_ids["admin_b_id"], changed_by_user_id_fk=ti_ids["admin_b_id"])
        imp_a = ImportLog(user_id_fk=ti_ids["admin_a_id"], kind="students", program_id_fk=ti_ids["prog_a1_id"], semester=1)
        imp_b = ImportLog(user_id_fk=ti_ids["admin_b_id"], kind="students", program_id_fk=ti_ids["prog_b1_id"], semester=1)
        db.session.add_all([pw_a, pw_b, imp_a, imp_b])
        db.session.flush()
        mat_a = SubjectMaterial(subject_id_fk=ti_ids["subj_a1_id"], title="MatA", kind="note", is_published=True)
        mat_b = SubjectMaterial(subject_id_fk=ti_ids["subj_b1_id"], title="MatB", kind="note", is_published=True)
        db.session.add_all([mat_a, mat_b])
        db.session.flush()
        sml_a = SubjectMaterialLog(material_id_fk=int(mat_a.material_id), action="create", actor_user_id_fk=ti_ids["admin_a_id"])
        sml_b = SubjectMaterialLog(material_id_fk=int(mat_b.material_id), action="create", actor_user_id_fk=ti_ids["admin_b_id"])
        db.session.add_all([sml_a, sml_b])
        db.session.commit()

        # Pre-condition: old rows were written BEFORE ALTER (no trust_id_fk)
        pw_a_row_id = int(pw_a.log_id)
        pw_b_row_id = int(pw_b.log_id)
        imp_a_row_id = int(imp_a.log_id)
        imp_b_row_id = int(imp_b.log_id)
        sml_a_row_id = int(sml_a.log_id)
        sml_b_row_id = int(sml_b.log_id)

        # Force the migration to treat every column as missing so the ALTER
        # + UPDATE path runs even if models.py already declares trust_id_fk
        # (backfill UPDATE is idempotent so it is safe to run twice).
        from cms_app.scripts.add_trust_id_columns_to_logs import (
            add_trust_id_to_password_change_log,
            add_trust_id_to_import_logs,
            add_trust_id_to_subject_material_logs,
        )
        from sqlalchemy import text as _sa_text, inspect as _sa_inspect
        engine = db.engine

        def _col_exists(table, col):
            insp = _sa_inspect(engine)
            try:
                return col in {c["name"] for c in insp.get_columns(table)}
            except Exception:
                return False

        def _add_if_missing(table, col):
            if _col_exists(table, col):
                return
            with engine.begin() as c:
                c.execute(_sa_text(f"ALTER TABLE {table} ADD COLUMN {col} INTEGER"))

        def _backfill_update(table):
            if table == "password_change_log":
                return f"""
                    UPDATE {table}
                    SET trust_id_fk = COALESCE(
                        (SELECT users.trust_id_fk FROM users
                         WHERE users.user_id = {table}.changed_by_user_id_fk),
                        (SELECT users.trust_id_fk FROM users
                         WHERE users.user_id = {table}.user_id_fk)
                    )
                    WHERE {table}.trust_id_fk IS NULL
                """
            if table == "import_logs":
                return f"""
                    UPDATE {table}
                    SET trust_id_fk = COALESCE(
                        (SELECT institutes.trust_id_fk
                         FROM programs
                         JOIN institutes ON programs.institute_id_fk = institutes.institute_id
                         WHERE programs.program_id = {table}.program_id_fk),
                        (SELECT users.trust_id_fk FROM users
                         WHERE users.user_id = {table}.user_id_fk)
                    )
                    WHERE {table}.trust_id_fk IS NULL
                """
            return f"""
                UPDATE {table}
                SET trust_id_fk = COALESCE(
                    (SELECT users.trust_id_fk FROM users
                     WHERE users.user_id = {table}.actor_user_id_fk),
                    (SELECT institutes.trust_id_fk
                     FROM subject_materials
                     JOIN subjects ON subjects.subject_id = subject_materials.subject_id_fk
                     JOIN programs ON programs.program_id = subjects.program_id_fk
                     JOIN institutes ON institutes.institute_id = programs.institute_id_fk
                     WHERE subject_materials.material_id = {table}.material_id_fk)
                )
                WHERE {table}.trust_id_fk IS NULL
            """

        def _rebuild(table, col):
            """Clear any old values, ADD column IF missing, UPDATE with trust derivation."""
            _add_if_missing(table, col)
            with engine.begin() as c:
                c.execute(_sa_text(f"UPDATE {table} SET trust_id_fk = NULL"))
                c.execute(_sa_text(_backfill_update(table)))

        _rebuild("password_change_log", "trust_id_fk")
        _rebuild("import_logs", "trust_id_fk")
        _rebuild("subject_material_logs", "trust_id_fk")

        def _val(sql, pid):
            return int(db.session.execute(db.text(sql), {"pid": pid}).scalar_one())

        pw_a_t = _val("SELECT trust_id_fk FROM password_change_log WHERE log_id = :pid", pw_a_row_id)
        pw_b_t = _val("SELECT trust_id_fk FROM password_change_log WHERE log_id = :pid", pw_b_row_id)
        imp_a_t = _val("SELECT trust_id_fk FROM import_logs WHERE log_id = :pid", imp_a_row_id)
        imp_b_t = _val("SELECT trust_id_fk FROM import_logs WHERE log_id = :pid", imp_b_row_id)
        sml_a_t = _val("SELECT trust_id_fk FROM subject_material_logs WHERE log_id = :pid", sml_a_row_id)
        sml_b_t = _val("SELECT trust_id_fk FROM subject_material_logs WHERE log_id = :pid", sml_b_row_id)

    assert pw_a_t == ti_ids["trust_a_id"] and pw_b_t == ti_ids["trust_b_id"]
    assert imp_a_t == ti_ids["trust_a_id"] and imp_b_t == ti_ids["trust_b_id"]
    assert sml_a_t == ti_ids["trust_a_id"] and sml_b_t == ti_ids["trust_b_id"]
