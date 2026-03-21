from flask import render_template, request, redirect, url_for, flash, current_app, session
from flask_login import login_required, current_user
from . import super_admin
from ..models import db, SystemMessage, SystemConfig, Trust, Institute, User
from ..decorators import super_admin_required
from datetime import datetime

@super_admin.route('/dashboard')
@login_required
@super_admin_required
def dashboard():
    # Gather stats
    total_trusts = Trust.query.count()
    total_institutes = Institute.query.count()
    total_users = User.query.count()
    active_messages = SystemMessage.query.filter_by(is_active=True).count()
    
    # Check maintenance mode
    maint_mode_config = SystemConfig.query.get('maintenance_mode')
    is_maintenance = (maint_mode_config.config_value == 'true') if maint_mode_config else False

    return render_template('super_admin/dashboard.html', 
                           total_trusts=total_trusts,
                           total_institutes=total_institutes,
                           total_users=total_users,
                           active_messages=active_messages,
                           is_maintenance=is_maintenance)

# ==========================================
# SYSTEM MESSAGES
# ==========================================

@super_admin.route('/messages', methods=['GET', 'POST'])
@login_required
@super_admin_required
def messages():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        msg_type = request.form.get('message_type')
        target_role = request.form.get('target_role')
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        
        start_date = datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M') if start_date_str else datetime.now(timezone.utc)
        end_date = datetime.strptime(end_date_str, '%Y-%m-%dT%H:%M') if end_date_str else None
        
        new_msg = SystemMessage(
            title=title,
            content=content,
            message_type=msg_type,
            target_role=target_role,
            start_date=start_date,
            end_date=end_date,
            is_active=True
        )
        db.session.add(new_msg)
        db.session.commit()
        flash("System Message broadcasted successfully!", "success")
        return redirect(url_for('super_admin.messages'))
    
    all_messages = SystemMessage.query.order_by(SystemMessage.start_date.desc()).all()
    return render_template('super_admin/messages.html', messages=all_messages)

@super_admin.route('/messages/<int:msg_id>/delete', methods=['POST'])
@login_required
@super_admin_required
def delete_message(msg_id):
    msg = SystemMessage.query.get_or_404(msg_id)
    db.session.delete(msg)
    db.session.commit()
    flash("Message deleted.", "info")
    return redirect(url_for('super_admin.messages'))

@super_admin.route('/messages/<int:msg_id>/toggle', methods=['POST'])
@login_required
@super_admin_required
def toggle_message(msg_id):
    msg = SystemMessage.query.get_or_404(msg_id)
    msg.is_active = not msg.is_active
    db.session.commit()
    flash(f"Message {'activated' if msg.is_active else 'deactivated'}.", "info")
    return redirect(url_for('super_admin.messages'))


# ==========================================
# TENANT MANAGEMENT (KILL SWITCH)
# ==========================================

@super_admin.route('/tenants')
@login_required
@super_admin_required
def tenants():
    trusts = Trust.query.all()
    # We can also list institutes if we want granular control
    institutes = Institute.query.all()
    return render_template('super_admin/tenants.html', trusts=trusts, institutes=institutes)

@super_admin.route('/trusts/<int:trust_id>/toggle', methods=['POST'])
@login_required
@super_admin_required
def toggle_trust(trust_id):
    trust = Trust.query.get_or_404(trust_id)
    trust.is_active = not trust.is_active
    db.session.commit()
    status = "Active" if trust.is_active else "Suspended"
    flash(f"Trust '{trust.trust_name}' is now {status}.", "warning" if not trust.is_active else "success")
    return redirect(url_for('super_admin.tenants'))

@super_admin.route('/institutes/<int:inst_id>/toggle', methods=['POST'])
@login_required
@super_admin_required
def toggle_institute(inst_id):
    inst = Institute.query.get_or_404(inst_id)
    inst.is_active = not inst.is_active
    db.session.commit()
    status = "Active" if inst.is_active else "Suspended"
    flash(f"Institute '{inst.institute_name}' is now {status}.", "warning" if not inst.is_active else "success")
    return redirect(url_for('super_admin.tenants'))


@super_admin.route('/trusts/create', methods=['POST'])
@login_required
@super_admin_required
def create_trust():
    name = request.form.get('trust_name')
    code = request.form.get('trust_code')
    plan = request.form.get('subscription_plan', 'basic')
    
    if not name or not code:
        flash("Trust Name and Code are required.", "danger")
        return redirect(url_for('super_admin.tenants'))
        
    existing = Trust.query.filter_by(trust_code=code).first()
    if existing:
        flash("Trust Code must be unique.", "danger")
        return redirect(url_for('super_admin.tenants'))
        
    new_trust = Trust(trust_name=name, trust_code=code, subscription_plan=plan)
    db.session.add(new_trust)
    db.session.commit()
    
    flash(f"Trust '{name}' created successfully!", "success")
    return redirect(url_for('super_admin.tenants'))


@super_admin.route('/institutes/create', methods=['POST'])
@login_required
@super_admin_required
def create_institute():
    trust_id = request.form.get('trust_id')
    name = request.form.get('institute_name')
    code = request.form.get('institute_code')
    
    if not trust_id or not name or not code:
        flash("All fields are required.", "danger")
        return redirect(url_for('super_admin.tenants'))
        
    existing = Institute.query.filter_by(institute_code=code).first()
    if existing:
        flash("Institute Code must be unique.", "danger")
        return redirect(url_for('super_admin.tenants'))
        
    new_inst = Institute(
        trust_id_fk=trust_id,
        institute_name=name,
        institute_code=code
    )
    db.session.add(new_inst)
    db.session.commit()
    
    flash(f"Institute '{name}' added successfully! Redirecting to setup wizard...", "success")
    # Redirect to Wizard Step 1 to complete setup (with institute_id)
    return redirect(url_for('wizard.step1_institute', institute_id=new_inst.institute_id))


# ==========================================
# SYSTEM CONFIG (MAINTENANCE MODE)
# ==========================================

@super_admin.route('/config', methods=['GET', 'POST'])
@login_required
@super_admin_required
def config():
    if request.method == 'POST':
        # Maintenance Mode
        maint_mode = request.form.get('maintenance_mode') # 'on' or None
        is_maint = 'true' if maint_mode else 'false'
        
        conf = SystemConfig.query.get('maintenance_mode')
        if not conf:
            conf = SystemConfig(config_key='maintenance_mode', config_value=is_maint)
            db.session.add(conf)
        else:
            conf.config_value = is_maint
        
        db.session.commit()
        flash("System Configuration updated.", "success")
        return redirect(url_for('super_admin.config'))

    configs = SystemConfig.query.all()
    config_dict = {c.config_key: c.config_value for c in configs}
    return render_template('super_admin/config.html', config=config_dict)


@super_admin.route("/students/purge", methods=["GET", "POST"])
@login_required
@super_admin_required
def students_purge():
    import io
    import csv
    import json
    import time
    import zipfile
    from flask import Response
    from sqlalchemy import select, func
    from ..models import (
        Alumni,
        Attendance,
        DataAuditLog,
        ExamMark,
        FeePayment,
        FeesRecord,
        Grade,
        Notification,
        Program,
        Student,
        StudentCreditLog,
        StudentSemesterResult,
        StudentSubjectEnrollment,
        Trust,
    )

    trusts = Trust.query.order_by(Trust.trust_name.asc()).all()
    trust_id_raw = (request.values.get("trust_id") or "").strip()
    program_id_raw = (request.values.get("program_id") or "").strip()
    semester_raw = (request.values.get("semester") or "").strip().lower()
    include_inactive = (request.values.get("include_inactive") or "").strip().lower() in ("1", "true", "yes", "on")

    try:
        trust_id = int(trust_id_raw) if trust_id_raw else None
    except Exception:
        trust_id = None
    try:
        program_id = int(program_id_raw) if program_id_raw else None
    except Exception:
        program_id = None
    semester = None
    if semester_raw and semester_raw not in ("all", ""):
        try:
            semester = int(semester_raw)
        except Exception:
            semester = None

    def _scope_students_query():
        q = select(Student)
        if trust_id:
            q = q.filter(Student.trust_id_fk == trust_id)
        if program_id:
            q = q.filter(Student.program_id_fk == program_id)
        if semester is not None:
            q = q.filter(Student.current_semester == semester)
        if not include_inactive:
            q = q.filter(Student.is_active == True)
        return q

    def _get_target_enrollments():
        q = _scope_students_query().with_only_columns(Student.enrollment_no).order_by(Student.enrollment_no.asc())
        return [enr for (enr,) in db.session.execute(q).all()]

    def _selection_key():
        return json.dumps(
            {
                "trust_id": trust_id,
                "program_id": program_id,
                "semester": semester_raw or "all",
                "include_inactive": include_inactive,
            },
            sort_keys=True,
        )

    def _write_csv_from_query(zf, filename, model, q):
        cols = [c.name for c in model.__table__.columns]
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(cols)
        rows = db.session.execute(q).scalars().all()
        for obj in rows:
            w.writerow([getattr(obj, c, "") for c in cols])
        zf.writestr(filename, buf.getvalue().encode("utf-8"))

    def _backup_zip(enrollments):
        mem = io.BytesIO()
        with zipfile.ZipFile(mem, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            _write_csv_from_query(
                zf,
                "students.csv",
                Student,
                select(Student).filter(Student.enrollment_no.in_(enrollments)).order_by(Student.enrollment_no.asc()),
            )
            _write_csv_from_query(
                zf,
                "student_subject_enrollments.csv",
                StudentSubjectEnrollment,
                select(StudentSubjectEnrollment).filter(StudentSubjectEnrollment.student_id_fk.in_(enrollments)).order_by(StudentSubjectEnrollment.enrollment_id.asc()),
            )
            _write_csv_from_query(
                zf,
                "attendance.csv",
                Attendance,
                select(Attendance).filter(Attendance.student_id_fk.in_(enrollments)).order_by(Attendance.date_marked.asc(), Attendance.period_no.asc()),
            )
            _write_csv_from_query(
                zf,
                "fees_records.csv",
                FeesRecord,
                select(FeesRecord).filter(FeesRecord.student_id_fk.in_(enrollments)).order_by(FeesRecord.fee_id.asc()),
            )
            _write_csv_from_query(
                zf,
                "fee_payments.csv",
                FeePayment,
                select(FeePayment).filter(FeePayment.enrollment_no.in_(enrollments)).order_by(FeePayment.payment_id.asc()),
            )
            _write_csv_from_query(
                zf,
                "exam_marks.csv",
                ExamMark,
                select(ExamMark).filter(ExamMark.student_id_fk.in_(enrollments)).order_by(ExamMark.exam_mark_id.asc()),
            )
            _write_csv_from_query(
                zf,
                "student_semester_results.csv",
                StudentSemesterResult,
                select(StudentSemesterResult).filter(StudentSemesterResult.student_id_fk.in_(enrollments)).order_by(StudentSemesterResult.result_id.asc()),
            )
            _write_csv_from_query(
                zf,
                "grades.csv",
                Grade,
                select(Grade).filter(Grade.student_id_fk.in_(enrollments)).order_by(Grade.grade_id.asc()),
            )
            _write_csv_from_query(
                zf,
                "student_credit_log.csv",
                StudentCreditLog,
                select(StudentCreditLog).filter(StudentCreditLog.student_id_fk.in_(enrollments)).order_by(StudentCreditLog.log_id.asc()),
            )
            _write_csv_from_query(
                zf,
                "notifications.csv",
                Notification,
                select(Notification).filter(Notification.student_id_fk.in_(enrollments)).order_by(Notification.notification_id.asc()),
            )
            _write_csv_from_query(
                zf,
                "alumni.csv",
                Alumni,
                select(Alumni).filter(Alumni.enrollment_no.in_(enrollments)).order_by(Alumni.alumni_id.asc()),
            )
        mem.seek(0)
        return mem.getvalue()

    def _require_backup():
        sel = _selection_key()
        ok_at = session.get("super_purge_backup_at")
        ok_sel = session.get("super_purge_backup_sel")
        try:
            ok_at = float(ok_at) if ok_at else None
        except Exception:
            ok_at = None
        if not ok_at or not ok_sel or ok_sel != sel:
            return False
        if (time.time() - ok_at) > (30 * 60):
            return False
        return True

    def _audit(action, counts):
        entry = DataAuditLog(
            action=action,
            actor_user_id_fk=getattr(current_user, "user_id", None),
            actor_role="super_admin",
            trust_id_fk=trust_id,
            program_id_fk=program_id,
            semester=(semester if semester is not None else None),
            selection_json=_selection_key(),
            counts_json=json.dumps(counts or {}, ensure_ascii=False),
        )
        db.session.add(entry)

    programs = []
    if trust_id:
        programs = Program.query.join(Institute).filter(Institute.trust_id_fk == trust_id).order_by(Program.program_name.asc()).all()

    try:
        preview_count = db.session.scalar(select(func.count()).select_from(_scope_students_query().subquery())) or 0
    except Exception:
        preview_count = 0

    if request.method == "POST":
        action = (request.form.get("action") or "").strip().lower()
        confirm = (request.form.get("confirm") or "").strip()
        enrollments = _get_target_enrollments()
        if not enrollments:
            flash("No students found for the selected scope.", "warning")
            return redirect(url_for("super_admin.students_purge", trust_id=trust_id_raw, program_id=program_id_raw, semester=(semester_raw or "all")))

        if action == "backup":
            content = _backup_zip(enrollments)
            session["super_purge_backup_at"] = time.time()
            session["super_purge_backup_sel"] = _selection_key()
            _audit("backup", {"students": len(enrollments)})
            db.session.commit()
            fname = f"super_students_backup_{int(time.time())}.zip"
            return Response(content, headers={"Content-Type": "application/zip", "Content-Disposition": f"attachment; filename={fname}"})

        if action == "purge_all":
            if confirm != "PURGE":
                flash("Type PURGE to confirm.", "danger")
                return redirect(url_for("super_admin.students_purge", trust_id=trust_id_raw, program_id=program_id_raw, semester=(semester_raw or "all")))
            if not _require_backup():
                flash("Download backup ZIP first (valid for 30 minutes) before purging.", "danger")
                return redirect(url_for("super_admin.students_purge", trust_id=trust_id_raw, program_id=program_id_raw, semester=(semester_raw or "all")))

            def _chunks(items, size=500):
                for i in range(0, len(items), size):
                    yield items[i : i + size]

            counts = {"students": len(enrollments)}
            try:
                deleted = {
                    "attendance": 0,
                    "enrollments": 0,
                    "fees_records": 0,
                    "fee_payments": 0,
                    "exam_marks": 0,
                    "semester_results": 0,
                    "grades": 0,
                    "credit_log": 0,
                    "notifications": 0,
                    "alumni": 0,
                    "students": 0,
                }
                for chunk in _chunks(enrollments):
                    deleted["attendance"] += Attendance.query.filter(Attendance.student_id_fk.in_(chunk)).delete(synchronize_session=False)
                    deleted["enrollments"] += StudentSubjectEnrollment.query.filter(StudentSubjectEnrollment.student_id_fk.in_(chunk)).delete(synchronize_session=False)
                    deleted["fees_records"] += FeesRecord.query.filter(FeesRecord.student_id_fk.in_(chunk)).delete(synchronize_session=False)
                    deleted["fee_payments"] += FeePayment.query.filter(FeePayment.enrollment_no.in_(chunk)).delete(synchronize_session=False)
                    deleted["exam_marks"] += ExamMark.query.filter(ExamMark.student_id_fk.in_(chunk)).delete(synchronize_session=False)
                    deleted["semester_results"] += StudentSemesterResult.query.filter(StudentSemesterResult.student_id_fk.in_(chunk)).delete(synchronize_session=False)
                    deleted["grades"] += Grade.query.filter(Grade.student_id_fk.in_(chunk)).delete(synchronize_session=False)
                    deleted["credit_log"] += StudentCreditLog.query.filter(StudentCreditLog.student_id_fk.in_(chunk)).delete(synchronize_session=False)
                    deleted["notifications"] += Notification.query.filter(Notification.student_id_fk.in_(chunk)).delete(synchronize_session=False)
                    deleted["alumni"] += Alumni.query.filter(Alumni.enrollment_no.in_(chunk)).delete(synchronize_session=False)
                    deleted["students"] += Student.query.filter(Student.enrollment_no.in_(chunk)).delete(synchronize_session=False)
                counts.update(deleted)
                _audit("purge_all", counts)
                db.session.commit()
                flash(f"Purged {counts.get('students', 0)} student(s).", "warning")
            except Exception:
                db.session.rollback()
                flash("Purge failed.", "danger")
            return redirect(url_for("super_admin.students_purge", trust_id=trust_id_raw, program_id=program_id_raw, semester=(semester_raw or "all"), include_inactive="1"))

        flash("Unknown action.", "danger")
        return redirect(url_for("super_admin.students_purge", trust_id=trust_id_raw, program_id=program_id_raw, semester=(semester_raw or "all")))

    logs = []
    try:
        ql = select(DataAuditLog).order_by(DataAuditLog.created_at.desc())
        if trust_id:
            ql = ql.filter(DataAuditLog.trust_id_fk == trust_id)
        logs = db.session.execute(ql.limit(50)).scalars().all()
    except Exception:
        logs = []

    logs_view = []
    for r in logs:
        students_n = None
        try:
            cj = json.loads(r.counts_json or "{}")
            students_n = cj.get("students")
        except Exception:
            students_n = None
        logs_view.append(
            {
                "created_at": getattr(r, "created_at", None),
                "action": getattr(r, "action", ""),
                "actor_user_id_fk": getattr(r, "actor_user_id_fk", None),
                "students": students_n,
            }
        )

    return render_template(
        "super_admin/student_purge.html",
        trusts=trusts,
        programs=programs,
        selected={"trust_id": trust_id, "program_id": program_id, "semester": (semester_raw or "all"), "include_inactive": include_inactive},
        preview_count=preview_count,
        logs=logs_view,
    )
