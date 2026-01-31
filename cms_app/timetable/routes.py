from datetime import datetime, time
from flask import render_template, request, jsonify, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from sqlalchemy import and_

from . import timetable_bp
from .. import db
from ..models import Program, Division, Subject, TimetableSlot, TimetableSettings, CourseAssignment, Faculty, SubjectType, Student
from ..decorators import role_required

def _get_timetable_settings(program_id, academic_year):
    return TimetableSettings.query.filter_by(
        program_id_fk=program_id, 
        academic_year=academic_year
    ).first()

@timetable_bp.route("/manage", methods=["GET", "POST"])
@login_required
@role_required("admin", "principal")
def manage():
    # 1. Selection State
    program_id = request.args.get("program_id", type=int)
    semester = request.args.get("semester", type=int)
    division_id = request.args.get("division_id", type=int)
    academic_year = request.args.get("academic_year", "2025-2026") # Default or from config
    demo_mode = ((request.args.get("demo") or "").strip() == "1")

    programs = []
    divisions = []
    subjects = []
    settings = None
    slots_data = {}
    
    if demo_mode:
        # Mock Data
        programs = [
            Program(program_id=1, program_name="BCA (Demo)", program_duration_years=3),
            Program(program_id=2, program_name="BSc IT (Demo)", program_duration_years=3)
        ]
        if program_id:
            settings = TimetableSettings(
                program_id_fk=program_id,
                academic_year=academic_year,
                start_time=time(8, 0),
                slot_duration_mins=55,
                slots_per_day=6,
                break_after_period=3,
                break_duration_mins=25
            )
            
        if division_id:
            semester = 3
            program_id = 1
            subjects = [
                Subject(subject_id=101, subject_name="Computer Networks", subject_code="CN301", credit_structure=None),
                Subject(subject_id=102, subject_name="DBMS", subject_code="DB302", credit_structure=None),
                Subject(subject_id=103, subject_name="Operating Systems", subject_code="OS303", credit_structure=None),
                Subject(subject_id=104, subject_name="Web Dev (Prac)", subject_code="WD304", credit_structure=None) # Mock practical
            ]
            # Mock Slots
            slots_data = {
                "Mon_1": TimetableSlot(day_of_week="Mon", period_no=1, subject_id_fk=101, slot_type="Theory"),
                "Mon_2": TimetableSlot(day_of_week="Mon", period_no=2, subject_id_fk=102, slot_type="Theory"),
                "Tue_1": TimetableSlot(day_of_week="Tue", period_no=1, subject_id_fk=103, slot_type="Theory"),
                "Wed_4": TimetableSlot(day_of_week="Wed", period_no=4, subject_id_fk=104, slot_type="Practical"),
            }

        # Mock Divisions for dropdown
        if program_id and semester:
            divisions = [
                Division(division_id=10, division_code="A", program_id_fk=program_id, semester=semester),
                Division(division_id=11, division_code="B", program_id_fk=program_id, semester=semester)
            ]

    else:
        # Real Data Logic
        programs = Program.query.all()
        
        # Defaults for Principal
        if current_user.role == "principal" and current_user.program_id_fk:
            program_id = current_user.program_id_fk
            # Lock program dropdown
    
        if program_id:
            # Fetch Settings
            settings = _get_timetable_settings(program_id, academic_year)
            if not settings:
                # Create default settings if missing
                settings = TimetableSettings(
                    program_id_fk=program_id,
                    academic_year=academic_year
                )
                db.session.add(settings)
                db.session.commit()
                
        if division_id:
            div = db.session.get(Division, division_id)
            if div:
                semester = div.semester # Sync sem
                program_id = div.program_id_fk
                
                # Fetch Subjects
                subjects = Subject.query.filter_by(
                    program_id_fk=program_id,
                    semester=semester
                ).all()
                
                # Fetch existing slots with Faculty Info
                slots_query = (
                    db.session.query(TimetableSlot, Faculty.full_name)
                    .outerjoin(CourseAssignment, and_(
                        CourseAssignment.subject_id_fk == TimetableSlot.subject_id_fk,
                        CourseAssignment.division_id_fk == TimetableSlot.division_id_fk,
                        CourseAssignment.is_active == True
                    ))
                    .outerjoin(Faculty, Faculty.user_id_fk == CourseAssignment.faculty_id_fk)
                    .filter(TimetableSlot.division_id_fk == division_id)
                )
                slots = slots_query.all()
                for s, fac_name in slots:
                    slots_data[f"{s.day_of_week}_{s.period_no}"] = {
                        "slot": s,
                        "faculty_name": fac_name or ""
                    }
                    
        # Helper for dropdowns
        if program_id and semester:
            divisions = Division.query.filter_by(program_id_fk=program_id, semester=semester).all()
        
    # Prepare Context
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    
    # Safely determine slots count (handle None in DB)
    slots_count = 6
    if settings and settings.slots_per_day:
        slots_count = settings.slots_per_day
        
    periods = range(1, slots_count + 1)
    
    return render_template(
        "timetable/manage.html",
        programs=programs,
        selected_program_id=program_id,
        selected_semester=semester,
        selected_division_id=division_id,
        academic_year=academic_year,
        divisions=divisions,
        subjects=subjects,
        days=days,
        periods=periods,
        settings=settings,
        slots_data=slots_data,
        demo_mode=demo_mode
    )

@timetable_bp.route("/api/save_slot", methods=["POST"])
@login_required
@role_required("admin", "principal")
def save_slot():
    data = request.json
    division_id = data.get("division_id")
    day = data.get("day")
    period = data.get("period")
    subject_id = data.get("subject_id") # Null/Empty to clear
    
    if not (division_id and day and period):
        return jsonify({"error": "Missing coordinates"}), 400
        
    slot = TimetableSlot.query.filter_by(
        division_id_fk=division_id,
        day_of_week=day,
        period_no=period
    ).first()
    
    if not subject_id:
        # Clear slot
        if slot:
            db.session.delete(slot)
            db.session.commit()
        return jsonify({"status": "cleared"})
        
    subject = db.session.get(Subject, subject_id)
    if not subject:
        return jsonify({"error": "Invalid subject"}), 400
        
    # --- Validation Logic ---
    # 1. Practical Check ("Make practical session together")
    is_practical = (subject.credit_structure and subject.credit_structure.practical_credits > 0) or "practical" in subject.subject_name.lower()
    
    # 2. Same Subject Check ("Not for the same subject")
    # Count slots for this subject on this day (excluding current)
    existing_on_day = TimetableSlot.query.filter(
        TimetableSlot.division_id_fk == division_id,
        TimetableSlot.day_of_week == day,
        TimetableSlot.subject_id_fk == subject_id,
        TimetableSlot.period_no != period
    ).count()
    
    warning = None
    if is_practical:
        # Check for adjacent slots (period +/- 1)
        adjacent = TimetableSlot.query.filter(
            TimetableSlot.division_id_fk == division_id,
            TimetableSlot.day_of_week == day,
            TimetableSlot.subject_id_fk == subject_id,
            TimetableSlot.period_no.in_([int(period)-1, int(period)+1])
        ).count()
        if adjacent == 0:
             warning = "Note: Practical usually requires block sessions (adjacent slots)."
    elif existing_on_day > 0:
        warning = "Note: Theory subject already assigned today."
        
    # Create or Update
    if not slot:
        slot = TimetableSlot(
            division_id_fk=division_id,
            day_of_week=day,
            period_no=period
        )
        db.session.add(slot)
    
    slot.subject_id_fk = subject_id
    slot.slot_type = "Practical" if is_practical else "Theory"
    
    db.session.commit()
    
    # Fetch Faculty Name (if assigned)
    faculty_name = "Unassigned"
    assignment = CourseAssignment.query.filter_by(
        subject_id_fk=subject_id,
        division_id_fk=division_id,
        is_active=True
    ).first()
    if assignment and assignment.faculty_id_fk:
        # CourseAssignment.faculty_id_fk references users.user_id
        # Faculty model also links to users via user_id_fk
        fac = Faculty.query.filter_by(user_id_fk=assignment.faculty_id_fk).first()
        if fac:
            faculty_name = fac.full_name

    return jsonify({
        "status": "saved", 
        "warning": warning,
        "faculty": faculty_name,
        "slot_type": slot.slot_type
    })

@timetable_bp.route("/settings", methods=["POST"])
@login_required
@role_required("admin", "principal")
def update_settings():
    program_id = request.form.get("program_id")
    academic_year = request.form.get("academic_year")
    
    settings = _get_timetable_settings(program_id, academic_year)
    if not settings:
        settings = TimetableSettings(program_id_fk=program_id, academic_year=academic_year)
        db.session.add(settings)
        
    settings.start_time = datetime.strptime(request.form.get("start_time"), "%H:%M").time()
    settings.slot_duration_mins = int(request.form.get("slot_duration_mins"))
    settings.break_after_period = int(request.form.get("break_after_period"))
    settings.break_duration_mins = int(request.form.get("break_duration_mins"))
    
    db.session.commit()
    flash("Settings updated.", "success")
    return redirect(request.referrer)

@timetable_bp.route("/my_timetable")
@login_required
@role_required("student")
def my_timetable():
    # Find student profile
    student = Student.query.filter_by(user_id_fk=current_user.user_id).first()
    if not student:
        flash("Student profile not found.", "warning")
        return redirect(url_for("main.dashboard"))
        
    if not student.division_id_fk:
        flash("You are not assigned to any division yet.", "info")
        return redirect(url_for("main.dashboard"))
        
    division = db.session.get(Division, student.division_id_fk)
    if not division:
        flash("Assigned division not found.", "danger")
        return redirect(url_for("main.dashboard"))
        
    # Fetch Settings
    academic_year = "2025-2026" 
    settings = _get_timetable_settings(student.program_id_fk, academic_year)
    
    # Fetch Slots
    slots_query = (
        db.session.query(TimetableSlot, Faculty.full_name, Subject.subject_name, Subject.subject_code)
        .join(Subject, Subject.subject_id == TimetableSlot.subject_id_fk)
        .outerjoin(CourseAssignment, and_(
            CourseAssignment.subject_id_fk == TimetableSlot.subject_id_fk,
            CourseAssignment.division_id_fk == TimetableSlot.division_id_fk,
            CourseAssignment.is_active == True
        ))
        .outerjoin(Faculty, Faculty.user_id_fk == CourseAssignment.faculty_id_fk)
        .filter(TimetableSlot.division_id_fk == division.division_id)
    )
    
    slots = slots_query.all()
    slots_data = {}
    for s, fac_name, sub_name, sub_code in slots:
        slots_data[f"{s.day_of_week}_{s.period_no}"] = {
            "slot": s,
            "faculty_name": fac_name or "TBA",
            "subject_name": sub_name,
            "subject_code": sub_code
        }
        
    # Prepare Context
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    slots_count = 6
    if settings and settings.slots_per_day:
        slots_count = settings.slots_per_day
        
    periods = range(1, slots_count + 1)
    
    return render_template(
        "timetable/student_view.html",
        student=student,
        division=division,
        days=days,
        periods=periods,
        slots_data=slots_data,
        settings=settings
    )
