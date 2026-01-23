from flask import render_template, request, flash, redirect, url_for
import json
from flask_login import login_required, current_user
from sqlalchemy import select, func, and_, or_, case
from . import exams_bp
from .. import db, csrf_required
from ..models import ExamScheme, StudentSemesterResult, ExamMark, Student, Program, Subject, StudentSubjectEnrollment, SubjectType, CreditStructure
from ..main.routes import academic_year_options, current_academic_year, _program_dropdown_context
from ..decorators import role_required

def _resolve_exam_limits(scheme, subject):
    """
    Resolves max/min marks for a subject based on scheme rules.
    Priority: Credit-based rules > Global scheme limits.
    """
    limits = {
        "max_internal": scheme.max_internal_marks,
        "max_external": scheme.max_external_marks,
        "max_total": scheme.max_total_marks
    }
    
    if not scheme.credit_rules_json:
        return limits
        
    try:
        rules = json.loads(scheme.credit_rules_json)
        if not rules:
            return limits
            
        # Get subject credit and type
        credits = 0
        if subject.credit_structure:
             credits = subject.credit_structure.total_credits
        else:
             cs = db.session.execute(select(CreditStructure).filter_by(subject_id_fk=subject.subject_id)).scalars().first()
             if cs: credits = cs.total_credits
             
        # Get type
        type_code_real = "All"
        st = db.session.execute(select(SubjectType).filter_by(type_id=subject.subject_type_id_fk)).scalars().first()
        if st: type_code_real = st.type_name
        
        # Match rule: 1. Exact match (credit + type), 2. Fallback (credit + 'All')
        matched_rule = None
        fallback_rule = None
        
        for r in rules:
             r_credit = float(r.get("credit", 0))
             r_type = r.get("type", "All")
             
             if r_credit == credits:
                 if r_type == type_code_real:
                     matched_rule = r
                     break
                 if r_type == "All":
                     fallback_rule = r
        
        final_rule = matched_rule or fallback_rule
        
        if final_rule:
             limits["max_internal"] = float(final_rule.get("max_int", 0))
             limits["max_external"] = float(final_rule.get("max_ext", 0))
             limits["max_total"] = float(final_rule.get("max_tot", 0))
             if "min_tot" in final_rule:
                 limits["min_total"] = float(final_rule.get("min_tot", 0))
    except Exception as e:
        print(f"Error resolving exam rules: {e}")
        
    return limits

# --- EXAM MODULE ROUTES ---

@exams_bp.route("/academics/exams", methods=["GET"])
@login_required
@role_required("admin", "principal", "clerk", "faculty")
def dashboard():
    """
    Exam Dashboard.
    Lists recent exam schemes.
    """
    # Filter logic (program)
    ctx = _program_dropdown_context(request.args.get("program_id"), include_admin_all=True, prefer_user_program_default=True)
    selected_program_id = ctx.get("selected_program_id")
    
    q = select(ExamScheme).order_by(ExamScheme.created_at.desc())
    
    if selected_program_id:
        q = q.filter(ExamScheme.program_id_fk == selected_program_id)
        
    schemes = db.session.execute(q).scalars().all()
    
    # Enrich with Program names
    scheme_data = []
    for s in schemes:
        p = db.session.get(Program, s.program_id_fk)
        scheme_data.append({
            "scheme": s,
            "program_name": p.program_name if p else "Unknown"
        })
        
    return render_template(
        "exams/dashboard.html",
        programs=ctx.get("program_list"),
        selected_program_id=selected_program_id,
        scheme_data=scheme_data
    )

@exams_bp.route("/academics/exams/new", methods=["GET"])
@login_required
@role_required("admin", "principal")
def create_scheme():
    """
    Redirects to the exam rules page to create a new scheme.
    """
    return redirect(url_for("exams.exam_rules"))

@exams_bp.route("/academics/exams/<int:scheme_id>/marks-entry", methods=["GET"])
@login_required
@role_required("admin", "principal", "clerk", "faculty")
def marks_entry(scheme_id):
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
    
    if selected_subject_id:
        selected_subject = db.session.get(Subject, selected_subject_id)
        if selected_subject:
            # Resolve limits dynamically based on credit rules
            current_limits = _resolve_exam_limits(scheme, selected_subject)

            # Load Students Enrolled in this subject
            # Join StudentSubjectEnrollment
            
            # Get students who have active enrollment for this subject AND matching academic year
            q_stud = select(Student).join(StudentSubjectEnrollment, Student.enrollment_no == StudentSubjectEnrollment.student_id_fk)\
                .filter(
                    StudentSubjectEnrollment.subject_id_fk == selected_subject_id,
                    StudentSubjectEnrollment.is_active == True
                ).order_by(Student.enrollment_no)
                
            students = db.session.execute(q_stud).scalars().all()
            
            # Load existing marks
            q_marks = select(ExamMark).filter_by(
                scheme_id_fk=scheme_id,
                subject_id_fk=selected_subject_id
            )
            existing_marks = db.session.execute(q_marks).scalars().all()
            marks_map = {m.student_id_fk: m for m in existing_marks}
        
    return render_template(
        "exams/marks_entry.html",
        scheme=scheme,
        program=program,
        subjects=subjects,
        selected_subject=selected_subject,
        students=students,
        marks_map=marks_map,
        current_limits=current_limits
    )

@exams_bp.route("/academics/exams/<int:scheme_id>/save-marks", methods=["POST"])
@login_required
@role_required("admin", "principal", "clerk", "faculty")
@csrf_required
def save_marks(scheme_id):
    scheme = db.session.get(ExamScheme, scheme_id)
    if not scheme:
        flash("Exam not found", "danger")
        return redirect(url_for("exams.dashboard"))
        
    subject_id = request.form.get("subject_id")
    if not subject_id:
        flash("Subject missing.", "danger")
        return redirect(url_for("exams.marks_entry", scheme_id=scheme_id))
        
    subject = db.session.get(Subject, int(subject_id))
    
    # Resolve limits for validation
    limits = _resolve_exam_limits(scheme, subject)
    
    updates = 0
    inserts = 0
    errors = []
    
    student_ids = request.form.getlist("student_ids")
    
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
        if internal: total += internal
        if external: total += external
        mark.total_marks = total
        
    try:
        db.session.commit()
        flash(f"Marks saved. ({inserts} added, {updates} updated)", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error saving marks: {str(e)}", "danger")
    
    return redirect(url_for("exams.marks_entry", scheme_id=scheme_id, subject_id=subject_id))

@exams_bp.route("/academics/exams/<int:scheme_id>/result", methods=["GET"])
@login_required
@role_required("admin", "principal", "clerk", "faculty")
def result_view(scheme_id):
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
        
    return render_template(
        "exams/result_view.html",
        scheme=scheme,
        program=program,
        subjects=subjects,
        students=students,
        matrix=matrix
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
@role_required("admin", "principal")
def debug_exam_schemes():
    """List all exam schemes for debugging/viewing."""
    schemes = ExamScheme.query.order_by(ExamScheme.created_at.desc()).all()
    # Eager load programs for display if needed, but simple query is fine for now
    # We'll attach program names manually or join if performance matters later
    for s in schemes:
        s.program = Program.query.get(s.program_id_fk)
        
    return render_template("admin/exams/debug_schemes.html", schemes=schemes)

@exams_bp.route("/admin/exams/debug/<int:scheme_id>", methods=["GET"])
@login_required
@role_required("admin", "principal")
def debug_exam_results(scheme_id):
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
@role_required("admin", "principal", "clerk")
@csrf_required
def exam_rules():
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
