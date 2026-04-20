import json
from datetime import datetime, timezone

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func, select

from . import csrf_required, db
from .decorators import super_admin_required
from .email_utils import send_email


route_overrides_bp = Blueprint("route_overrides", __name__)


def _user_is_admin_or_clerk():
    role = (getattr(current_user, "role", "") or "").strip().lower()
    return role in ("admin", "clerk")


def _effective_trust_id():
    if getattr(current_user, "is_super_admin", False):
        return None
    return getattr(current_user, "trust_id_fk", None)


def _queue_query():
    from .models import FeePayment, Student

    query = select(FeePayment).filter_by(status="submitted")
    trust_id = _effective_trust_id()
    if trust_id:
        query = query.join(Student, Student.enrollment_no == FeePayment.enrollment_no).where(
            Student.trust_id_fk == trust_id
        )
    return query.order_by(FeePayment.created_at.asc())


def _fee_payment_accessible(payment):
    trust_id = _effective_trust_id()
    if trust_id is None:
        return True
    try:
        from .models import Student

        student = db.session.get(Student, payment.enrollment_no)
        return getattr(student, "trust_id_fk", None) == trust_id
    except Exception:
        return False


def _set_payment_verifier(payment, user_id):
    if hasattr(payment, "verified_by_fk"):
        payment.verified_by_fk = user_id
        return
    payment.verified_by_user_id = user_id


def _payment_notification_payload(payment, include_receipt=False):
    payload = {
        "program_id": payment.program_id_fk,
        "semester": payment.semester,
        "medium": payment.medium_tag,
        "payment_id": payment.payment_id,
        "utr": payment.utr,
    }
    if include_receipt:
        payload["receipt_no"] = payment.receipt_no
    return payload


@route_overrides_bp.route("/fees/verification-queue", methods=["GET"])
@login_required
def fees_payments_queue():
    if not _user_is_admin_or_clerk():
        flash("Not authorized to view verification queue.", "danger")
        return redirect(url_for("main.dashboard"))

    from .models import FeePayment, Program, Student

    payments = db.session.execute(_queue_query()).scalars().all()
    student_ids = [payment.enrollment_no for payment in payments]
    students = (
        {
            student.enrollment_no: student
            for student in db.session.execute(
                select(Student).filter(Student.enrollment_no.in_(student_ids))
            ).scalars().all()
        }
        if student_ids
        else {}
    )
    program_ids = sorted({payment.program_id_fk for payment in payments if payment.program_id_fk})
    programs = (
        {
            program.program_id: program
            for program in db.session.execute(
                select(Program).filter(Program.program_id.in_(program_ids))
            ).scalars().all()
        }
        if program_ids
        else {}
    )
    return render_template("fees_verification_queue.html", payments=payments, students=students, programs=programs)


@route_overrides_bp.route("/fees/verification-queue/<int:payment_id>/verify", methods=["POST"])
@login_required
@csrf_required
def fees_payment_verify(payment_id):
    if not _user_is_admin_or_clerk():
        flash("Not authorized to verify payments.", "danger")
        return redirect(url_for("main.dashboard"))

    from .models import FeePayment, Notification, Student, User

    payment = db.session.get(FeePayment, payment_id)
    if not payment:
        flash("Payment not found.", "danger")
        return redirect(url_for("route_overrides.fees_payments_queue"))
    if not _fee_payment_accessible(payment):
        flash("Not authorized to verify this payment.", "danger")
        return redirect(url_for("route_overrides.fees_payments_queue"))

    override_duplicate = ((request.form.get("override_duplicate") or "").strip().lower() in ("1", "true", "yes"))
    try:
        duplicate_exists = (
            db.session.execute(
                select(FeePayment).filter(
                    FeePayment.utr == payment.utr,
                    FeePayment.payment_id != payment.payment_id,
                )
            ).scalars().first()
            is not None
        )
    except Exception:
        duplicate_exists = False
    if duplicate_exists and not override_duplicate:
        flash("Duplicate UTR detected. Check and verify with override if legitimate.", "warning")
        return redirect(url_for("route_overrides.fees_payments_queue"))

    payer_name = (request.form.get("payer_name") or "").strip() or None
    bank_credit_raw = (request.form.get("bank_credit_at") or "").strip()
    bank_credit_at = None
    if bank_credit_raw:
        try:
            bank_credit_at = (
                datetime.strptime(bank_credit_raw, "%Y-%m-%d")
                if len(bank_credit_raw) == 10
                else datetime.fromisoformat(bank_credit_raw)
            )
        except Exception:
            bank_credit_at = None

    try:
        payment.receipt_no = f"R{payment.payment_id:06d}"
    except Exception:
        payment.receipt_no = payment.receipt_no or None

    try:
        payment.status = "verified"
        payment.verified_at = datetime.now(timezone.utc)
        _set_payment_verifier(payment, getattr(current_user, "user_id", None))
        payment.payer_name = payer_name
        payment.bank_credit_at = bank_credit_at
        db.session.commit()

        try:
            student = db.session.get(Student, payment.enrollment_no)
            if student:
                notification = Notification(
                    student_id_fk=payment.enrollment_no,
                    kind="fee_verified",
                    title="Payment verified",
                    message=f"Your payment (UTR: {payment.utr}) has been verified.",
                    data_json=json.dumps(_payment_notification_payload(payment, include_receipt=True)),
                    payment_id_fk=payment.payment_id,
                )
                db.session.add(notification)
                db.session.commit()
        except Exception:
            pass

        try:
            student = db.session.get(Student, payment.enrollment_no)
            user_id = getattr(student, "user_id_fk", None) if student else None
            user = db.session.get(User, user_id) if user_id else None
            to_address = getattr(user, "username", None) or None
            if to_address:
                send_email("Payment Verified", to_address, f"Your payment (UTR: {payment.utr}) has been verified.")
        except Exception:
            pass

        flash("Payment verified.", "success")
    except Exception:
        db.session.rollback()
        flash("Failed to verify payment.", "danger")
    return redirect(url_for("route_overrides.fees_payments_queue"))


@route_overrides_bp.route("/fees/verification-queue/<int:payment_id>/reject", methods=["POST"])
@login_required
@csrf_required
def fees_payment_reject(payment_id):
    if not _user_is_admin_or_clerk():
        flash("Not authorized to reject payments.", "danger")
        return redirect(url_for("main.dashboard"))

    from .models import FeePayment, Notification, Student, User

    payment = db.session.get(FeePayment, payment_id)
    if not payment:
        flash("Payment not found.", "danger")
        return redirect(url_for("route_overrides.fees_payments_queue"))
    if not _fee_payment_accessible(payment):
        flash("Not authorized to reject this payment.", "danger")
        return redirect(url_for("route_overrides.fees_payments_queue"))

    remarks = (request.form.get("remarks") or "").strip()
    try:
        payment.status = "rejected"
        payment.verified_at = None
        _set_payment_verifier(payment, getattr(current_user, "user_id", None))
        payment.remarks = remarks or None
        db.session.commit()

        try:
            student = db.session.get(Student, payment.enrollment_no)
            if student:
                message = "Your fee submission was rejected." + (f" Reason: {remarks}." if remarks else "")
                notification = Notification(
                    student_id_fk=payment.enrollment_no,
                    kind="fee_rejected",
                    title="Fee submission rejected",
                    message=message,
                    data_json=json.dumps(_payment_notification_payload(payment)),
                    payment_id_fk=payment.payment_id,
                )
                db.session.add(notification)
                db.session.commit()
        except Exception:
            pass

        try:
            student = db.session.get(Student, payment.enrollment_no)
            user_id = getattr(student, "user_id_fk", None) if student else None
            user = db.session.get(User, user_id) if user_id else None
            to_address = getattr(user, "username", None) or None
            if to_address:
                send_email(
                    "Payment Rejected",
                    to_address,
                    f"Your payment (UTR: {payment.utr}) was rejected. Remarks: {remarks}",
                )
        except Exception:
            pass

        flash("Payment rejected.", "success")
    except Exception:
        db.session.rollback()
        flash("Failed to reject payment.", "danger")
    return redirect(url_for("route_overrides.fees_payments_queue"))


@route_overrides_bp.route("/super-admin/trusts/<int:trust_id>/institutes-summary", methods=["GET"])
@login_required
@super_admin_required
def trust_institutes(trust_id):
    from .models import Faculty, Institute, Program, Student, Trust, User

    trust = Trust.query.get_or_404(trust_id)
    institutes = (
        Institute.query.filter_by(trust_id_fk=trust_id).order_by(Institute.institute_name.asc()).all()
    )
    institute_ids = [institute.institute_id for institute in institutes]
    program_counts = {}
    student_counts = {}
    faculty_counts = {}
    user_counts = {}
    if institute_ids:
        program_counts = {
            institute_id: count
            for (institute_id, count) in db.session.execute(
                select(Program.institute_id_fk, func.count())
                .where(Program.institute_id_fk.in_(institute_ids))
                .group_by(Program.institute_id_fk)
            ).all()
        }
        student_counts = {
            institute_id: count
            for (institute_id, count) in db.session.execute(
                select(Program.institute_id_fk, func.count(Student.enrollment_no))
                .select_from(Student)
                .join(Program, Student.program_id_fk == Program.program_id)
                .where(Program.institute_id_fk.in_(institute_ids))
                .group_by(Program.institute_id_fk)
            ).all()
        }
        faculty_counts = {
            institute_id: count
            for (institute_id, count) in db.session.execute(
                select(Program.institute_id_fk, func.count(Faculty.faculty_id))
                .select_from(Faculty)
                .join(Program, Faculty.program_id_fk == Program.program_id)
                .where(Program.institute_id_fk.in_(institute_ids))
                .group_by(Program.institute_id_fk)
            ).all()
        }
        user_counts = {
            institute_id: count
            for (institute_id, count) in db.session.execute(
                select(Program.institute_id_fk, func.count(User.user_id))
                .select_from(User)
                .join(Program, User.program_id_fk == Program.program_id)
                .where(Program.institute_id_fk.in_(institute_ids))
                .group_by(Program.institute_id_fk)
            ).all()
        }

    counts = {
        institute.institute_id: {
            "programs": program_counts.get(institute.institute_id, 0),
            "students": student_counts.get(institute.institute_id, 0),
            "faculty": faculty_counts.get(institute.institute_id, 0),
            "users": user_counts.get(institute.institute_id, 0),
        }
        for institute in institutes
    }
    return render_template("super_admin/institutes.html", trust=trust, institutes=institutes, counts=counts)
