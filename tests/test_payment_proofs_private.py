"""P0-3 payment-proof privacy tests.

Covers the three acceptance-critical access paths for payment proofs after
moving the files out of /static/uploads/payment_proofs and into instance_path
with gated download via ``main.download_payment_proof``:

1. **Unauthenticated access must fail.**
   - Direct static URL       → 404 (blocked by before_request hook)
   - Download route          → 302 redirect to login page (Flask-Login required)
2. **Owner (student) of a payment record may download their own proof.**
   - GET /fees/proof/<id> as the owning student → 200 with correct content
3. **Cross-trust admin cannot download proofs from a trust they don't belong to.**
   - GET /fees/proof/<id> as wrong-trust admin → 403 Forbidden
"""

from __future__ import annotations

import os
import io
import pytest


def _create_test_image_bytes() -> bytes:
    """Return a 1x1 transparent PNG; small and valid for send_from_directory."""
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xcf"
        b"\xc0\x00\x00\x00\x02\x00\x01\xe2!\xbc3\x00\x00\x00\x00IEND\xaeB`\x82"
    )


def _seed_and_create_proof(app, trust_suffix="OWNER"):
    """Seed two trusts (owner_trust + other_trust), users, programs, one
    submitted fee_payment in owner_trust with a PNG proof file stored in
    PAYMENT_PROOFS_STORAGE_DIR, and return a dict with all ids."""
    from cms_app import db
    from cms_app.models import Trust, Institute, Program, User, Student, Division, FeePayment
    from werkzeug.security import generate_password_hash

    owner_trust_code = f"PP_OWN_{trust_suffix}"
    other_trust_code = f"PP_OTH_{trust_suffix}"
    owner_admin_username = f"pp_admin_{trust_suffix.lower()}"
    other_admin_username = f"pp_other_admin_{trust_suffix.lower()}"
    student_username = f"pp_stud_{trust_suffix.lower()}"
    student_enr = f"PP_ENR_{trust_suffix}"

    with app.app_context():
        existing = FeePayment.query.filter_by(enrollment_no=student_enr).first()
        if existing:
            return {
                "payment_id": existing.payment_id,
                "owner_trust_code": owner_trust_code,
                "other_trust_code": other_trust_code,
                "owner_admin": owner_admin_username,
                "other_admin": other_admin_username,
                "student": student_username,
                "student_enr": student_enr,
                "proof_file": (existing.proof_image_path or ""),
            }

        owner_trust = Trust(
            trust_name=f"Payment Proofs Owner {trust_suffix}",
            trust_code=owner_trust_code,
            is_active=True,
        )
        db.session.add(owner_trust)
        db.session.flush()
        other_trust = Trust(
            trust_name=f"Payment Proofs Other {trust_suffix}",
            trust_code=other_trust_code,
            is_active=True,
        )
        db.session.add(other_trust)
        db.session.flush()

        owner_institute = Institute(
            trust_id_fk=owner_trust.trust_id,
            institute_name=f"PP Owner Inst {trust_suffix}",
            institute_code=f"PPOI{trust_suffix}",
        )
        db.session.add(owner_institute)
        db.session.flush()
        other_institute = Institute(
            trust_id_fk=other_trust.trust_id,
            institute_name=f"PP Other Inst {trust_suffix}",
            institute_code=f"PPOIx{trust_suffix}",
        )
        db.session.add(other_institute)
        db.session.flush()

        owner_program = Program(
            institute_id_fk=owner_institute.institute_id,
            program_name=f"PP Owner Prog {trust_suffix}",
        )
        db.session.add(owner_program)
        db.session.flush()
        other_program = Program(
            institute_id_fk=other_institute.institute_id,
            program_name=f"PP Other Prog {trust_suffix}",
        )
        db.session.add(other_program)
        db.session.flush()

        division = Division(
            program_id_fk=owner_program.program_id,
            semester=1,
            division_code="A",
            capacity=40,
            medium_tag="English",
        )
        db.session.add(division)
        db.session.flush()

        owner_admin = User(
            username=owner_admin_username,
            password_hash=generate_password_hash("secret"),
            role="admin",
            trust_id_fk=owner_trust.trust_id,
            program_id_fk=owner_program.program_id,
        )
        db.session.add(owner_admin)
        db.session.flush()
        other_admin = User(
            username=other_admin_username,
            password_hash=generate_password_hash("secret"),
            role="admin",
            trust_id_fk=other_trust.trust_id,
            program_id_fk=other_program.program_id,
        )
        db.session.add(other_admin)
        db.session.flush()

        student_user = User(
            username=student_username,
            password_hash=generate_password_hash("secret"),
            role="student",
            trust_id_fk=owner_trust.trust_id,
            program_id_fk=owner_program.program_id,
        )
        db.session.add(student_user)
        db.session.flush()
        student = Student(
            enrollment_no=student_enr,
            student_name="Proof",
            surname="Owner",
            mobile="9999999999",
            program_id_fk=owner_program.program_id,
            division_id_fk=division.division_id,
            trust_id_fk=owner_trust.trust_id,
            current_semester=1,
            medium_tag="English",
            category="OPEN",
            user_id_fk=student_user.user_id,
        )
        db.session.add(student)
        db.session.flush()

        # Create the proof file physically in PAYMENT_PROOFS_STORAGE_DIR and
        # link the fee_payment row to it by basename-only.
        storage_dir = app.config["PAYMENT_PROOFS_STORAGE_DIR"]
        os.makedirs(storage_dir, exist_ok=True)
        basename = f"payproof_{student_enr}_p{owner_program.program_id}_sample.png"
        target = os.path.join(storage_dir, basename)
        with open(target, "wb") as fh:
            fh.write(_create_test_image_bytes())

        payment = FeePayment(
            enrollment_no=student_enr,
            program_id_fk=owner_program.program_id,
            semester=1,
            medium_tag="English",
            amount=1000.0,
            utr=f"PAYPROOF_UTR_{trust_suffix}",
            status="submitted",
            created_by_user_id=owner_admin.user_id,
            proof_image_path=basename,
        )
        db.session.add(payment)
        db.session.commit()
        return {
            "payment_id": payment.payment_id,
            "owner_trust_code": owner_trust_code,
            "other_trust_code": other_trust_code,
            "owner_admin": owner_admin_username,
            "other_admin": other_admin_username,
            "student": student_username,
            "student_enr": student_enr,
            "proof_file": basename,
        }


# ---------------------------------------------------------------------------
# Acceptance 1: unauthenticated access → not leaked
# ---------------------------------------------------------------------------
def test_unauthenticated_static_proofs_path_blocked_404(client, app):
    """Public /static/uploads/payment_proofs/* URL must be 404 via the
    _block_legacy_public_materials before_request hook, regardless of
    whether or not an actual file lives there."""
    resp = client.get("/static/uploads/payment_proofs/anything.png")
    assert resp.status_code == 404


def test_unauthenticated_route_redirect_login(client, app):
    """Download route must be gated by @login_required → 302 to /login."""
    ctx = _seed_and_create_proof(app, trust_suffix="UNAUTH")
    resp = client.get(f"/fees/proof/{ctx['payment_id']}", follow_redirects=False)
    assert resp.status_code in (302, 303)
    loc = resp.headers.get("Location") or ""
    assert "/login" in loc, "download route must redirect to login for anon users"


# ---------------------------------------------------------------------------
# Acceptance 2: owner student can download their proof
# ---------------------------------------------------------------------------
def test_owner_student_downloads_proof_ok(client, app):
    ctx = _seed_and_create_proof(app, trust_suffix="OWN")
    # Login as the student (username = same User record created above)
    login_resp = client.post(
        "/login",
        data={"username": ctx["student"], "password": "secret"},
        follow_redirects=False,
    )
    assert login_resp.status_code in (200, 302, 303)

    resp = client.get(f"/fees/proof/{ctx['payment_id']}")
    assert resp.status_code == 200
    # Content-Type must be image/png (not text/html error page)
    assert (resp.headers.get("Content-Type") or "").startswith("image/")
    # Body must match the exact bytes we wrote (ensure send_from_directory
    # actually returned the file and not a rendered template / placeholder)
    assert resp.data == _create_test_image_bytes()


# ---------------------------------------------------------------------------
# Acceptance 3: admin/principal/clerk scoped to another trust → 403
# ---------------------------------------------------------------------------
def test_wrong_trust_admin_cannot_download_proof(client, app):
    ctx = _seed_and_create_proof(app, trust_suffix="XTRUST")
    login_resp = client.post(
        "/login",
        data={"username": ctx["other_admin"], "password": "secret"},
        follow_redirects=False,
    )
    assert login_resp.status_code in (200, 302, 303)
    resp = client.get(f"/fees/proof/{ctx['payment_id']}", follow_redirects=False)
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Same-trust admin CAN download the proof (positive scoping)
# ---------------------------------------------------------------------------
def test_same_trust_admin_downloads_proof_ok(client, app):
    ctx = _seed_and_create_proof(app, trust_suffix="SAMETR")
    login_resp = client.post(
        "/login",
        data={"username": ctx["owner_admin"], "password": "secret"},
        follow_redirects=False,
    )
    assert login_resp.status_code in (200, 302, 303)
    resp = client.get(f"/fees/proof/{ctx['payment_id']}")
    assert resp.status_code == 200
    assert (resp.headers.get("Content-Type") or "").startswith("image/")
    assert resp.data == _create_test_image_bytes()
