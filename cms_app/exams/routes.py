from flask import render_template, request, flash, redirect, url_for, session
import json
from flask_login import login_required, current_user
from sqlalchemy import select, func, and_, or_, case, cast
from . import exams_bp
from .. import db, csrf_required
from ..models import ExamScheme, StudentSemesterResult, ExamMark, Student, Program, Subject, StudentSubjectEnrollment, SubjectType, CreditStructure, CourseAssignment, DataAuditLog, Division
from ..main.routes import academic_year_options, current_academic_year, _program_dropdown_context
from ..decorators import role_required
from .services import resolve_exam_limits, calculate_exam_results
from datetime import datetime, timedelta

def _effective_trust_id():
    if not getattr(current_user, "is_authenticated", False):
        return None
    if getattr(current_user, "is_super_admin", False):
        try:
            return int(session.get("active_trust_id") or 0) or None
        except Exception:
            return None
    return getattr(current_user, "trust_id_fk", None)

def _require_exam_view_access():
    role = (getattr(current_user, "role", "") or "").strip().lower()
    if not (getattr(current_user, "is_super_admin", False) or role in ("admin", "principal", "clerk", "faculty")):
        try:
            flash("You do not have permission to access Exams.", "danger")
        except Exception:
            pass
        return redirect(url_for("main.dashboard"))
    return None

def _require_exam_edit_access(scheme: ExamScheme, subject_id: int = None):
    role = (getattr(current_user, "role", "") or "").strip().lower()
    if getattr(current_user, "is_super_admin", False) or role in ("admin", "principal", "clerk"):
        return None
    if role == "faculty" and subject_id:
        try:
            uid = getattr(current_user, "user_id", None)
            q = select(CourseAssignment).where(
                CourseAssignment.is_active.is_(True),
                CourseAssignment.faculty_id_fk == uid,
                CourseAssignment.subject_id_fk == int(subject_id),
            )
            if getattr(scheme, "academic_year", None):
                q = q.where(or_(CourseAssignment.academic_year == scheme.academic_year, CourseAssignment.academic_year.is_(None)))
            row = db.session.execute(q.limit(1)).scalars().first()
            if row:
                return None
        except Exception:
            pass
    try:
        flash("You do not have permission to enter marks for this subject.", "danger")
    except Exception:
        pass
    return redirect(url_for("exams.dashboard"))

def _require_exam_admin_access():
    role = (getattr(current_user, "role", "") or "").strip().lower()
    if getattr(current_user, "is_super_admin", False) or role in ("admin", "principal"):
        return None
    try:
        flash("Only Admin/Principal can perform this action.", "danger")
    except Exception:
        pass
    return redirect(url_for("exams.dashboard"))

def _is_scheme_locked(scheme: ExamScheme) -> bool:
    if not getattr(scheme, "is_frozen", False):
        return False
    until = getattr(scheme, "unlock_until", None)
    if not until:
        return True
    try:
        return datetime.utcnow() > until
    except Exception:
        return True

def _mark_is_pass(scheme: ExamScheme, internal: float, external: float, total: float, is_absent: bool) -> bool:
    if is_absent:
        return False
    if getattr(scheme, "min_internal_marks", None) is not None:
        try:
            if internal is None or float(internal) < float(scheme.min_internal_marks or 0):
                return False
        except Exception:
            return False
    if getattr(scheme, "min_external_marks", None) is not None:
        try:
            if external is None or float(external) < float(scheme.min_external_marks or 0):
                return False
        except Exception:
            return False
    if getattr(scheme, "min_total_marks", None) is not None:
        try:
            if total is None or float(total) < float(scheme.min_total_marks or 0):
                return False
        except Exception:
            return False
    return True

@exams_bp.route("/academics/exams/<int:scheme_id>/calculate", methods=["POST"])
@login_required
@csrf_required
def calculate_results(scheme_id):
    rv = _require_exam_view_access()
    if rv:
        return rv
    rv_admin = _require_exam_admin_access()
    if rv_admin:
        return rv_admin
    """
    Triggers result calculation for an exam scheme.
    Computes Grades, SGPA, and updates StudentSemesterResult.
    """
    success, message, count = calculate_exam_results(scheme_id)
    
    if success:
        flash(message, "success")
    else:
        # If failure was due to "not found" or "no marks", message might be warning level
        if "not found" in message.lower() or "no marks" in message.lower():
            flash(message, "warning")
        else:
            flash(f"Error calculating results: {message}", "danger")
            
    return redirect(url_for("exams.result_view", scheme_id=scheme_id))

# --- EXAM MODULE ROUTES ---

@exams_bp.route("/academics/exams", methods=["GET"])
@login_required
def dashboard():
    rv = _require_exam_view_access()
    if rv:
        return rv
    """
    Exam Dashboard.
    Lists recent exam schemes.
    """
    # Filter logic (program)
    ctx = _program_dropdown_context(request.args.get("program_id"), include_admin_all=True, prefer_user_program_default=True)
    selected_program_id = ctx.get("selected_program_id")
    effective_trust_id = None
    if getattr(current_user, "is_authenticated", False):
        if getattr(current_user, "is_super_admin", False):
            try:
                effective_trust_id = int(session.get("active_trust_id") or 0) or None
            except Exception:
                effective_trust_id = None
        else:
            effective_trust_id = getattr(current_user, "trust_id_fk", None)
    
    q = select(ExamScheme).order_by(ExamScheme.created_at.desc())
    
    if effective_trust_id:
        try:
            from ..models import Institute
            q = q.join(Program, ExamScheme.program_id_fk == Program.program_id).join(Institute, Program.institute_id_fk == Institute.institute_id).filter(Institute.trust_id_fk == effective_trust_id)
        except Exception:
            pass

    if selected_program_id:
        q = q.filter(ExamScheme.program_id_fk == selected_program_id)
        
    schemes = db.session.execute(q).scalars().all()
    
    # Enrich with Program names
    scheme_data = []
    for s in schemes:
        p = db.session.get(Program, s.program_id_fk)
        is_locked = _is_scheme_locked(s)
        try:
            pat = f"\"scheme_id\": {int(s.scheme_id)}"
            flips_count = db.session.scalar(
                select(func.count()).select_from(DataAuditLog).where(DataAuditLog.action == "exam_pass_fail_flip").where(DataAuditLog.selection_json.like(f"%{pat}%"))
            ) or 0
        except Exception:
            flips_count = 0
        scheme_data.append({
            "scheme": s,
            "program_name": p.program_name if p else "Unknown",
            "is_locked": is_locked,
            "flips_count": flips_count,
        })
        
    return render_template(
        "exams/dashboard.html",
        programs=ctx.get("program_list"),
        selected_program_id=selected_program_id,
        scheme_data=scheme_data
    )

@exams_bp.route("/academics/exams/new", methods=["GET"])
@login_required
def create_scheme():
    rv = _require_exam_view_access()
    if rv:
        return rv
    rv_admin = _require_exam_admin_access()
    if rv_admin:
        return rv_admin
    """
    Redirects to the exam rules page to create a new scheme.
    """
    return redirect(url_for("exams.exam_rules"))

@exams_bp.route("/academics/exams/<int:scheme_id>/marks-entry", methods=["GET"])
@login_required
def marks_entry(scheme_id):
    rv = _require_exam_view_access()
    if rv:
        return rv
    scheme = db.session.get(ExamScheme, scheme_id)
    if not scheme:
        flash("Exam not found.", "danger")
        return redirect(url_for("exams.dashboard"))
        
    program = db.session.get(Program, scheme.program_id_fk)
    
    # Subject selection
    subjects_q = select(Subject).filter_by(
        program_id_fk=scheme.program_id_fk,
        semester=scheme.semester
    ).order_by(Subject.subject_code)
    
    subjects = db.session.execute(subjects_q).scalars().all()
    
    # Filter subjects by medium if scheme has specific medium
    if scheme.medium_tag:
        subjects = [s for s in subjects if not s.medium_tag or s.medium_tag == scheme.medium_tag]
        
    # Faculty restriction: only show assigned subjects (Optional enforcement, strictness can be added here)
    # For now, allow faculty to view all subjects of the exam to support collaborative entry.

    selected_subject_id = request.args.get("subject_id", type=int)
    selected_subject = None
    students = []
    marks_map = {}
    current_limits = {
        "max_internal": scheme.max_internal_marks,
        "max_external": scheme.max_external_marks,
        "max_total": scheme.max_total_marks
    }
    is_locked = _is_scheme_locked(scheme)
    
    if selected_subject_id:
        selected_subject = db.session.get(Subject, selected_subject_id)
        if selected_subject:
            rv2 = _require_exam_edit_access(scheme, selected_subject_id)
            if rv2:
                return rv2
            # Resolve limits dynamically based on credit rules
            current_limits = resolve_exam_limits(scheme, selected_subject)

            # Load Students Enrolled in this subject
            # Join StudentSubjectEnrollment
            
            # Get students who have active enrollment for this subject AND matching academic year
            q_stud = select(Student).join(StudentSubjectEnrollment, Student.enrollment_no == StudentSubjectEnrollment.student_id_fk)\
                .filter(
                    StudentSubjectEnrollment.subject_id_fk == selected_subject_id,
                    StudentSubjectEnrollment.is_active == True
                ).order_by(cast(Student.roll_no, db.Integer), Student.enrollment_no)
                
            students = db.session.execute(q_stud).scalars().all()
            
            # Load existing marks
            q_marks = select(ExamMark).filter_by(
                scheme_id_fk=scheme_id,
                subject_id_fk=selected_subject_id
            )
            existing_marks = db.session.execute(q_marks).scalars().all()
            marks_map = {m.student_id_fk: m for m in existing_marks}

    # Fetch divisions for mapping
    divisions = db.session.execute(
        select(Division).filter_by(
            program_id_fk=scheme.program_id_fk,
            semester=scheme.semester
        )
    ).scalars().all()
    division_map = {d.division_id: d.division_code for d in divisions}
        
    return render_template(
        "exams/marks_entry.html",
        scheme=scheme,
        program=program,
        subjects=subjects,
        selected_subject=selected_subject,
        students=students,
        marks_map=marks_map,
        current_limits=current_limits,
        division_map=division_map,
        is_locked=is_locked
    )

@exams_bp.route("/academics/exams/<int:scheme_id>/save-marks", methods=["POST"])
@login_required
@csrf_required
def save_marks(scheme_id):
    rv = _require_exam_view_access()
    if rv:
        return rv
    scheme = db.session.get(ExamScheme, scheme_id)
    if not scheme:
        flash("Exam not found", "danger")
        return redirect(url_for("exams.dashboard"))

    if _is_scheme_locked(scheme):
        flash("This scheme is frozen. Ask Admin/Principal to unlock with reason.", "warning")
        return redirect(url_for("exams.marks_entry", scheme_id=scheme_id))
        
    subject_id = request.form.get("subject_id")
    if not subject_id:
        flash("Subject missing.", "danger")
        return redirect(url_for("exams.marks_entry", scheme_id=scheme_id))
    rv2 = _require_exam_edit_access(scheme, int(subject_id))
    if rv2:
        return rv2
        
    subject = db.session.get(Subject, int(subject_id))
    
    # Resolve limits for validation
    limits = resolve_exam_limits(scheme, subject)
    
    updates = 0
    inserts = 0
    errors = []
    
    student_ids = request.form.getlist("student_ids")
    changed_students = 0
    
    flips = 0
    for enrollment in student_ids:
        internal_raw = request.form.get(f"internal_{enrollment}")
        external_raw = request.form.get(f"external_{enrollment}")
        absent_raw = request.form.get(f"absent_{enrollment}")
        
        is_absent = (absent_raw == "on")
        
        internal = None
        if internal_raw and internal_raw.strip():
            try:
                internal = float(internal_raw)
            except:
                pass
            
        external = None
        if external_raw and external_raw.strip():
            try:
                external = float(external_raw)
            except:
                pass
            
        # Find existing mark or create
        mark = db.session.execute(
            select(ExamMark).filter_by(
                scheme_id_fk=scheme_id, 
                subject_id_fk=subject.subject_id, 
                student_id_fk=enrollment
            )
        ).scalars().first()
        
        old_internal = None
        old_external = None
        old_total = None
        old_absent = False
        old_pass = None

        if mark:
            old_internal = mark.internal_marks
            old_external = mark.external_marks
            old_total = mark.total_marks
            old_absent = bool(mark.is_absent)
            old_pass = _mark_is_pass(scheme, old_internal, old_external, old_total, old_absent)

        if not mark:
            # Only create if there is some data to save
            if internal is None and external is None and not is_absent:
                continue

            mark = ExamMark(
                scheme_id_fk=scheme_id,
                subject_id_fk=subject.subject_id,
                student_id_fk=enrollment,
                semester=scheme.semester,
                academic_year=scheme.academic_year,
                attempt_no=1 
            )
            db.session.add(mark)
            inserts += 1
        else:
            updates += 1
            
        mark.internal_marks = internal
        mark.external_marks = external
        mark.is_absent = is_absent
        
        # Calculate Total
        total = 0
        if internal is not None:
            total += internal
        if external is not None:
            total += external
        mark.total_marks = total

        changed_students += 1

        if getattr(scheme, "is_frozen", False):
            try:
                unlocked = not _is_scheme_locked(scheme)
            except Exception:
                unlocked = False
            if unlocked:
                new_pass = _mark_is_pass(scheme, internal, external, total, is_absent)
                if old_pass is not None and new_pass != old_pass:
                    flips += 1
                    try:
                        db.session.add(
                            DataAuditLog(
                                action="exam_pass_fail_flip",
                                actor_user_id_fk=getattr(current_user, "user_id", None),
                                actor_role=(getattr(current_user, "role", "") or "").strip().lower(),
                                trust_id_fk=_effective_trust_id(),
                                program_id_fk=getattr(scheme, "program_id_fk", None),
                                semester=getattr(scheme, "semester", None),
                                selection_json=json.dumps(
                                    {"scheme_id": scheme_id, "subject_id": int(subject_id), "student_id": enrollment}
                                ),
                                counts_json=json.dumps(
                                    {
                                        "old_pass": bool(old_pass),
                                        "new_pass": bool(new_pass),
                                        "old_total": old_total,
                                        "new_total": total,
                                        "unlock_until": (scheme.unlock_until.isoformat() if getattr(scheme, "unlock_until", None) else None),
                                        "unlock_reason": (scheme.unlock_reason or ""),
                                    }
                                ),
                            )
                        )
                    except Exception:
                        pass
        
    try:
        try:
            db.session.add(
                DataAuditLog(
                    action="exam_marks_save",
                    actor_user_id_fk=getattr(current_user, "user_id", None),
                    actor_role=(getattr(current_user, "role", "") or "").strip().lower(),
                    trust_id_fk=_effective_trust_id(),
                    program_id_fk=getattr(scheme, "program_id_fk", None),
                    semester=getattr(scheme, "semester", None),
                    selection_json=json.dumps({"scheme_id": scheme_id, "subject_id": int(subject_id)}),
                    counts_json=json.dumps(
                        {
                            "inserts": inserts,
                            "updates": updates,
                            "changed_students": changed_students,
                            "is_frozen": bool(getattr(scheme, "is_frozen", False)),
                            "unlock_until": (scheme.unlock_until.isoformat() if getattr(scheme, "unlock_until", None) else None),
                            "flips_flagged": flips,
                        }
                    ),
                )
            )
        except Exception:
            pass
        if flips:
            db.session.flush()
        db.session.commit()
        if flips:
            flash(f"Marks saved. ({inserts} added, {updates} updated). Flips flagged: {flips}", "warning")
        else:
            flash(f"Marks saved. ({inserts} added, {updates} updated)", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error saving marks: {str(e)}", "danger")
    
    return redirect(url_for("exams.marks_entry", scheme_id=scheme_id, subject_id=subject_id))

@exams_bp.route("/academics/exams/<int:scheme_id>/result", methods=["GET"])
@login_required
def result_view(scheme_id):
    rv = _require_exam_view_access()
    if rv:
        return rv
    scheme = db.session.get(ExamScheme, scheme_id)
    if not scheme:
        flash("Exam not found.", "danger")
        return redirect(url_for("exams.dashboard"))
        
    program = db.session.get(Program, scheme.program_id_fk)
    
    # Fetch all marks for this scheme
    marks = db.session.execute(
        select(ExamMark).filter_by(scheme_id_fk=scheme_id)
    ).scalars().all()
    
    if not marks:
        flash("No marks found for this exam.", "warning")
        return redirect(url_for("exams.dashboard"))

    # Organize by Student -> Subject
    subject_ids = {m.subject_id_fk for m in marks}
    subjects = db.session.execute(
        select(Subject).filter(Subject.subject_id.in_(subject_ids)).order_by(Subject.subject_code)
    ).scalars().all()
    
    student_ids = {m.student_id_fk for m in marks}
    students = db.session.execute(
        select(Student).filter(Student.enrollment_no.in_(student_ids)).order_by(Student.enrollment_no)
    ).scalars().all()
    
    # Matrix: row=student, col=subject
    matrix = {}
    for m in marks:
        if m.student_id_fk not in matrix:
            matrix[m.student_id_fk] = {}
        matrix[m.student_id_fk][m.subject_id_fk] = m

    # Fetch Semester Results (SGPA/CGPA)
    results_q = select(StudentSemesterResult).filter_by(scheme_id_fk=scheme_id)
    results = db.session.execute(results_q).scalars().all()
    student_results_map = {r.student_id_fk: r for r in results}
        
    return render_template(
        "exams/result_view.html",
        scheme=scheme,
        program=program,
        subjects=subjects,
        students=students,
        matrix=matrix,
        student_results_map=student_results_map
    )


@exams_bp.route("/student/results", methods=["GET"])
@login_required
@role_required("student")
def student_result_view():
    try:
        s = db.session.execute(select(Student).filter_by(user_id_fk=current_user.user_id)).scalars().first()
    except Exception:
        s = None
    if not s:
        flash("Student profile not found for your account.", "danger")
        return redirect(url_for("main.dashboard"))

    schemes = []
    selected_scheme = None
    selected_result = None
    marks = []

    rows = db.session.execute(
        select(StudentSemesterResult, ExamScheme)
        .join(ExamScheme, StudentSemesterResult.scheme_id_fk == ExamScheme.scheme_id)
        .filter(StudentSemesterResult.student_id_fk == s.enrollment_no)
        .order_by(
            ExamScheme.academic_year.desc(),
            ExamScheme.semester.desc(),
            StudentSemesterResult.attempt_no.desc(),
        )
    ).all()

    if rows:
        scheme_id_raw = (request.args.get("scheme_id") or "").strip()
        selected_scheme_id = None
        if scheme_id_raw:
            try:
                selected_scheme_id = int(scheme_id_raw)
            except Exception:
                selected_scheme_id = None
        if not selected_scheme_id:
            selected_scheme_id = rows[0][1].scheme_id

        for res, scheme in rows:
            label_parts = []
            if scheme.name:
                label_parts.append(scheme.name)
            else:
                label_parts.append(f"Sem {scheme.semester}")
            label_parts.append(scheme.academic_year)
            if res.attempt_no and res.attempt_no > 1:
                label_parts.append(f"Attempt {res.attempt_no}")
            schemes.append({"scheme": scheme, "result": res, "label": " – ".join(label_parts)})
            if scheme.scheme_id == selected_scheme_id:
                selected_scheme = scheme
                selected_result = res

        if selected_scheme:
            mark_rows = db.session.execute(
                select(ExamMark, Subject)
                .join(Subject, ExamMark.subject_id_fk == Subject.subject_id)
                .filter(
                    ExamMark.student_id_fk == s.enrollment_no,
                    ExamMark.scheme_id_fk == selected_scheme.scheme_id,
                )
                .order_by(Subject.subject_code)
            ).all()
            for m, sub in mark_rows:
                marks.append(
                    {
                        "subject_code": sub.subject_code,
                        "subject_name": sub.subject_name,
                        "internal": m.internal_marks,
                        "external": m.external_marks,
                        "total": m.total_marks,
                        "grade": m.grade_letter,
                        "is_absent": m.is_absent,
                    }
                )

    return render_template(
        "exams/student_result_view.html",
        student=s,
        schemes=schemes,
        selected_scheme=selected_scheme,
        selected_result=selected_result,
        marks=marks,
    )

@exams_bp.route("/admin/exams/debug", methods=["GET"])
@login_required
def debug_exam_schemes():
    rv = _require_exam_view_access()
    if rv:
        return rv
    rv_admin = _require_exam_admin_access()
    if rv_admin:
        return rv_admin
    """List all exam schemes for debugging/viewing."""
    schemes = ExamScheme.query.order_by(ExamScheme.created_at.desc()).all()
    # Eager load programs for display if needed, but simple query is fine for now
    # We'll attach program names manually or join if performance matters later
    for s in schemes:
        s.program = Program.query.get(s.program_id_fk)
        
    return render_template("admin/exams/debug_schemes.html", schemes=schemes)

@exams_bp.route("/admin/exams/debug/<int:scheme_id>", methods=["GET"])
@login_required
def debug_exam_results(scheme_id):
    rv = _require_exam_view_access()
    if rv:
        return rv
    rv_admin = _require_exam_admin_access()
    if rv_admin:
        return rv_admin
    """View results for a specific scheme."""
    scheme = ExamScheme.query.get_or_404(scheme_id)
    program = Program.query.get(scheme.program_id_fk)
    
    # Get all results for this scheme
    results = StudentSemesterResult.query.filter_by(scheme_id_fk=scheme_id).all()
    
    # Enrich with student details
    # In a real app, we'd use a join. keeping it simple for debug.
    rows = []
    for res in results:
        student = Student.query.get(res.student_id_fk)
        
        # Get individual subject marks
        marks = ExamMark.query.filter_by(
            scheme_id_fk=scheme_id,
            student_id_fk=res.student_id_fk
        ).all()
        
        # Sort marks by subject ID or something consistent
        marks.sort(key=lambda m: m.subject_id_fk)
        
        # Enrich marks with subject names
        marks_display = []
        for m in marks:
            sub = Subject.query.get(m.subject_id_fk)
            marks_display.append({
                "subject_code": sub.subject_code if sub else "??",
                "subject_name": sub.subject_name if sub else "Unknown",
                "internal": m.internal_marks,
                "external": m.external_marks,
                "total": m.total_marks,
                "grade": m.grade_letter,
                "is_absent": m.is_absent
            })
            
        rows.append({
            "student": student,
            "result": res,
            "marks": marks_display
        })

    return render_template(
        "admin/exams/debug_results.html", 
        scheme=scheme, 
        program=program, 
        rows=rows
    )


@exams_bp.route("/academics/exam-rules", methods=["GET", "POST"])
@login_required
@csrf_required
def exam_rules():
    rv = _require_exam_view_access()
    if rv:
        return rv
    role = (getattr(current_user, "role", "") or "").strip().lower()
    if not (getattr(current_user, "is_super_admin", False) or role in ("admin", "principal", "clerk")):
        flash("You do not have permission to edit exam rules.", "danger")
        return redirect(url_for("exams.dashboard"))
    ctx = _program_dropdown_context(
        request.values.get("program_id"),
        include_admin_all=True,
        default_program_name=None,
        exclude_names=None,
        warn_unmapped=True,
        fallback_to_first=False,
        prefer_user_program_default=True,
    )
    program_list = ctx.get("program_list", [])
    selected_program_id = ctx.get("selected_program_id")
    program = db.session.get(Program, selected_program_id) if selected_program_id else None

    sem_raw = (request.values.get("semester") or "").strip()
    try:
        semester = int(sem_raw) if sem_raw else None
    except Exception:
        semester = None

    medium_raw = (request.values.get("medium_tag") or "").strip()
    selected_medium = medium_raw if medium_raw else None

    ay_raw = (request.values.get("academic_year") or "").strip()
    ay_options = academic_year_options()
    default_ay = current_academic_year()
    academic_year = ay_raw or default_ay
    if academic_year not in ay_options:
        ay_options.append(academic_year)

    available_mediums = []
    if program and semester:
        q = select(Subject.medium_tag).filter(
            Subject.program_id_fk == program.program_id,
            Subject.semester == semester,
        )
        vals = [row[0] for row in db.session.execute(q).all()]
        available_mediums = sorted({(v or "").strip() for v in vals if (v or "").strip()})
        if selected_medium and selected_medium not in available_mediums:
            available_mediums.append(selected_medium)

    scheme = None
    if program and semester and academic_year:
        scheme = (
            db.session.execute(
                select(ExamScheme).filter_by(
                    program_id_fk=program.program_id,
                    semester=semester,
                    academic_year=academic_year,
                    medium_tag=selected_medium,
                )
            )
            .scalars()
            .first()
        )

    existing_credits = []
    if program and semester:
        q_ec = select(
            func.coalesce(CreditStructure.total_credits, 0).label("credits"),
            SubjectType.type_name
        ).select_from(Subject)\
        .outerjoin(CreditStructure, Subject.subject_id == CreditStructure.subject_id_fk)\
        .join(SubjectType, Subject.subject_type_id_fk == SubjectType.type_id)\
        .filter(Subject.program_id_fk == program.program_id, Subject.semester == semester)
        
        if selected_medium:
             q_ec = q_ec.filter(or_(Subject.medium_tag == None, Subject.medium_tag == selected_medium))

        q_ec = q_ec.distinct()
        
        rows = db.session.execute(q_ec).all()
        for r in rows:
            existing_credits.append({
                "credits": r[0],
                "type": r[1]
            })

    # Fetch all subject types for dropdown
    all_subject_types = db.session.execute(select(SubjectType)).scalars().all()
    subject_type_codes = sorted([st.type_name for st in all_subject_types])

    if request.method == "POST":
        errors = []
        if not program or not semester or not academic_year:
            errors.append("Select program, semester, and academic year.")

        def _parse_float(field_name):
            raw = (request.form.get(field_name) or "").strip()
            if not raw:
                return None
            try:
                return float(raw)
            except Exception:
                errors.append(f"Invalid value for {field_name.replace('_', ' ')}.")
                return None

        if not errors:
            name = (request.form.get("name") or "").strip()
            if not name and program and semester and academic_year:
                name = f"{program.program_name} Sem {semester} {academic_year} Exam"

            max_internal = _parse_float("max_internal_marks")
            max_external = _parse_float("max_external_marks")
            min_internal = _parse_float("min_internal_marks")
            min_external = _parse_float("min_external_marks")
            min_total = _parse_float("min_total_marks")
            max_total = _parse_float("max_total_marks")

            is_active = (request.form.get("is_active") == "y")
            grading_json = (request.form.get("grading_scheme_json") or "").strip() or None
            credit_rules_json = (request.form.get("credit_rules_json") or "").strip() or None

            if not errors:
                if not scheme:
                    scheme = ExamScheme(
                        program_id_fk=program.program_id,
                        semester=semester,
                        academic_year=academic_year,
                        medium_tag=selected_medium,
                    )
                    db.session.add(scheme)

                scheme.name = name
                scheme.max_internal_marks = max_internal
                scheme.max_external_marks = max_external
                scheme.min_internal_marks = min_internal
                scheme.min_external_marks = min_external
                scheme.min_total_marks = min_total
                scheme.max_total_marks = max_total
                scheme.grading_scheme_json = grading_json
                scheme.credit_rules_json = credit_rules_json
                scheme.is_active = is_active

                try:
                    db.session.commit()
                    try:
                        flash("Exam rules saved.", "success")
                    except Exception:
                        pass
                except Exception:
                    db.session.rollback()
                    errors.append("Failed to save exam rules.")

        if errors:
            try:
                flash(errors[0], "danger")
            except Exception:
                pass

        return redirect(
            url_for(
                "exams.exam_rules",
                program_id=(program.program_id if program else None),
                semester=semester,
                medium_tag=(selected_medium or ""),
                academic_year=academic_year,
            )
        )

    return render_template(
        "exams/exam_rules.html",
        program_list=program_list,
        selected_program=program,
        semester=semester,
        available_mediums=available_mediums,
        selected_medium=selected_medium,
        academic_year=academic_year,
        academic_year_options=ay_options,
        scheme=scheme,
        existing_credits=existing_credits,
        subject_type_codes=subject_type_codes
    )


@exams_bp.route("/academics/exams/<int:scheme_id>/freeze", methods=["POST"])
@login_required
@csrf_required
def scheme_freeze(scheme_id):
    rv = _require_exam_view_access()
    if rv:
        return rv
    role = (getattr(current_user, "role", "") or "").strip().lower()
    if not (getattr(current_user, "is_super_admin", False) or role in ("admin", "principal")):
        flash("Only Admin/Principal can freeze an exam scheme.", "danger")
        return redirect(url_for("exams.dashboard"))
    scheme = db.session.get(ExamScheme, scheme_id)
    if not scheme:
        flash("Exam not found.", "danger")
        return redirect(url_for("exams.dashboard"))
    scheme.is_frozen = True
    scheme.frozen_at = datetime.utcnow()
    scheme.frozen_by_fk = getattr(current_user, "user_id", None)
    scheme.unlock_until = None
    scheme.unlock_by_fk = None
    scheme.unlock_reason = None
    try:
        db.session.add(
            DataAuditLog(
                action="exam_scheme_freeze",
                actor_user_id_fk=getattr(current_user, "user_id", None),
                actor_role=role,
                trust_id_fk=_effective_trust_id(),
                program_id_fk=getattr(scheme, "program_id_fk", None),
                semester=getattr(scheme, "semester", None),
                selection_json=json.dumps({"scheme_id": scheme_id}),
                counts_json=json.dumps({"is_frozen": True}),
            )
        )
    except Exception:
        pass
    try:
        db.session.commit()
        flash("Scheme frozen.", "success")
    except Exception:
        db.session.rollback()
        flash("Failed to freeze scheme.", "danger")
    return redirect(url_for("exams.dashboard"))


@exams_bp.route("/academics/exams/<int:scheme_id>/unlock", methods=["POST"])
@login_required
@csrf_required
def scheme_unlock(scheme_id):
    rv = _require_exam_view_access()
    if rv:
        return rv
    role = (getattr(current_user, "role", "") or "").strip().lower()
    if not (getattr(current_user, "is_super_admin", False) or role in ("admin", "principal")):
        flash("Only Admin/Principal can unlock an exam scheme.", "danger")
        return redirect(url_for("exams.dashboard"))
    scheme = db.session.get(ExamScheme, scheme_id)
    if not scheme:
        flash("Exam not found.", "danger")
        return redirect(url_for("exams.dashboard"))
    if not getattr(scheme, "is_frozen", False):
        scheme.is_frozen = True
    reason = (request.form.get("reason") or "").strip()
    if not reason:
        flash("Unlock reason is required.", "warning")
        return redirect(url_for("exams.dashboard"))
    duration_raw = (request.form.get("duration_minutes") or "30").strip()
    try:
        minutes = int(duration_raw)
    except Exception:
        minutes = 30
    minutes = min(max(minutes, 5), 240)
    until = datetime.utcnow() + timedelta(minutes=minutes)
    scheme.unlock_until = until
    scheme.unlock_by_fk = getattr(current_user, "user_id", None)
    scheme.unlock_reason = reason
    try:
        db.session.add(
            DataAuditLog(
                action="exam_scheme_unlock",
                actor_user_id_fk=getattr(current_user, "user_id", None),
                actor_role=role,
                trust_id_fk=_effective_trust_id(),
                program_id_fk=getattr(scheme, "program_id_fk", None),
                semester=getattr(scheme, "semester", None),
                selection_json=json.dumps({"scheme_id": scheme_id}),
                counts_json=json.dumps({"unlock_until": until.isoformat(), "reason": reason}),
            )
        )
    except Exception:
        pass
    try:
        db.session.commit()
        flash(f"Scheme unlocked for {minutes} minutes.", "warning")
    except Exception:
        db.session.rollback()
        flash("Failed to unlock scheme.", "danger")
    return redirect(url_for("exams.dashboard"))


@exams_bp.route("/academics/exams/<int:scheme_id>/flips", methods=["GET"])
@login_required
def scheme_flips(scheme_id):
    rv = _require_exam_view_access()
    if rv:
        return rv
    scheme = db.session.get(ExamScheme, scheme_id)
    if not scheme:
        flash("Exam not found.", "danger")
        return redirect(url_for("exams.dashboard"))
    pat = f"\"scheme_id\": {scheme_id}"
    q = select(DataAuditLog).where(DataAuditLog.action == "exam_pass_fail_flip").where(DataAuditLog.selection_json.like(f"%{pat}%")).order_by(DataAuditLog.created_at.desc()).limit(200)
    rows = db.session.execute(q).scalars().all()
    items = []
    for r in rows:
        try:
            sel = json.loads(r.selection_json or "{}")
        except Exception:
            sel = {}
        try:
            cnt = json.loads(r.counts_json or "{}")
        except Exception:
            cnt = {}
        items.append({"log": r, "sel": sel, "cnt": cnt})
    return render_template("exams/flips.html", scheme=scheme, items=items)
