from flask import render_template, flash, redirect, url_for, request
from flask_login import login_required, current_user
from .. import db
from ..models import Faculty, CourseAssignment, Subject, Division, Program, TimetableSlot, TimetableSettings, Attendance, Student
from ..decorators import role_required
from . import faculty_bp
from sqlalchemy import and_, func, case, distinct
from datetime import datetime, timedelta, date

@faculty_bp.route("/dashboard")
@login_required
@role_required("faculty")
def dashboard():
    # 1. Fetch Faculty Profile
    faculty = Faculty.query.filter_by(user_id_fk=current_user.user_id).first()
    if not faculty:
        flash("Faculty profile not found.", "danger")
        return redirect(url_for("main.index"))
        
    # 2. Fetch Active Course Assignments
    assignments = (
        db.session.query(CourseAssignment, Subject, Division, Program)
        .join(Subject, Subject.subject_id == CourseAssignment.subject_id_fk)
        .join(Division, Division.division_id == CourseAssignment.division_id_fk)
        .join(Program, Program.program_id == Division.program_id_fk)
        .filter(CourseAssignment.faculty_id_fk == current_user.user_id)
        .filter(CourseAssignment.is_active == True)
        .all()
    )
    
    # 3. Calculate Lecture Stats (Week/Month/Semester)
    # We need to count unique (date, period, subject, division) combinations for this faculty's assignments
    lecture_stats = {
        "week": 0,
        "month": 0,
        "total": 0
    }
    
    # Build list of (subject_id, division_id) for filtering
    assigned_pairs = [(a.CourseAssignment.subject_id_fk, a.CourseAssignment.division_id_fk) for a in assignments]
    
    if assigned_pairs:
        # Define date ranges
        today = date.today()
        start_of_week = today - timedelta(days=today.weekday()) # Monday
        start_of_month = today.replace(day=1)
        
        # Base query: distinct lectures (date, period, subject, division)
        # We filter by the assigned subject/division pairs
        conditions = [
            and_(
                Attendance.subject_id_fk == sid,
                Attendance.division_id_fk == did
            ) for sid, did in assigned_pairs
        ]
        
        if conditions:
            from sqlalchemy import or_
            base_q = db.session.query(
                Attendance.date_marked, 
                Attendance.period_no, 
                Attendance.subject_id_fk, 
                Attendance.division_id_fk
            ).filter(or_(*conditions)).group_by(
                Attendance.date_marked, 
                Attendance.period_no, 
                Attendance.subject_id_fk, 
                Attendance.division_id_fk
            )
            
            # Fetch all unique lectures for these assignments
            # Note: This might be heavy if history is huge, but for a single faculty it's okay.
            # Optimization: We can do 3 separate count queries or fetch all distinct dates and process in python.
            # Let's fetch all relevant unique lectures (date only matters for week/month check)
            
            all_lectures = base_q.all()
            
            for l_date, l_period, l_sub, l_div in all_lectures:
                # Total
                lecture_stats["total"] += 1
                
                # Week
                if l_date >= start_of_week:
                    lecture_stats["week"] += 1
                    
                # Month
                if l_date >= start_of_month:
                    lecture_stats["month"] += 1

    # 4. Identify At-Risk Students (< 60% Attendance)
    at_risk_students = []
    
    students_snapshot = []
    if assigned_pairs:
        # We need per-student attendance stats for the assigned subjects
        # Query: Student ID, Subject ID, Total Lectures, Present Count
        
        # 1. Total Lectures per Subject-Division (Denominator)
        # We already have 'all_lectures'. Let's organize it by (subject_id, division_id) -> count
        subject_div_counts = {}
        for l_date, l_period, l_sub, l_div in all_lectures:
            key = (l_sub, l_div)
            subject_div_counts[key] = subject_div_counts.get(key, 0) + 1
            
        # 2. Student Attendance Counts (Numerator)
        # Query: Student, Subject, Division, Count(Present)
        # Filter: Status in ('P', 'L') and (Subject, Div) in assigned_pairs
        
        # We need to handle this carefully.
        # We want to find students who are ENROLLED in these divisions.
        # So first, get all students in these divisions.
        division_ids = {did for _, did in assigned_pairs}
        
        students_in_divs = db.session.query(Student).filter(Student.division_id_fk.in_(division_ids)).all()
        student_map = {s.enrollment_no: s for s in students_in_divs}
        
        # Now query attendance for these students in relevant subjects
        # We aggregate by student, subject, division
        
        from sqlalchemy import or_
        att_conditions = [
            and_(
                Attendance.subject_id_fk == sid,
                Attendance.division_id_fk == did
            ) for sid, did in assigned_pairs
        ]
        
        if att_conditions:
            attendance_summary = db.session.query(
                Attendance.student_id_fk,
                Attendance.subject_id_fk,
                Attendance.division_id_fk,
                func.count(Attendance.attendance_id)
            ).filter(
                or_(*att_conditions),
                Attendance.status.in_(['P', 'L'])
            ).group_by(
                Attendance.student_id_fk,
                Attendance.subject_id_fk,
                Attendance.division_id_fk
            ).all()
            
            # Organize present counts: (student_id, subject_id, division_id) -> present_count
            present_counts = {}
            for st_id, sub_id, div_id, p_count in attendance_summary:
                present_counts[(st_id, sub_id, div_id)] = p_count
                
            # Now iterate over all students in the assigned divisions and check their stats for assigned subjects
            # Note: A student is in ONE division. So we only check subjects assigned to that division.
            
            # Map Subject Names for display
            subject_names = {sub.subject_id: sub.subject_name for _, sub, _, _ in assignments}
            
            for student in students_in_divs:
                # Find which subjects this student SHOULD have attended (based on their division)
                # Filter assigned_pairs for this student's division
                relevant_pairs = [(s, d) for s, d in assigned_pairs if d == student.division_id_fk]
                
                for sub_id, div_id in relevant_pairs:
                    total_lectures = subject_div_counts.get((sub_id, div_id), 0)
                    if total_lectures < 5: # Skip if very few lectures conducted
                        continue
                        
                    attended = present_counts.get((student.enrollment_no, sub_id, div_id), 0)
                    percentage = (attended / total_lectures) * 100
                    
                    if percentage < 60:
                        at_risk_students.append({
                            "student": student,
                            "subject_name": subject_names.get(sub_id, "Unknown"),
                            "percentage": round(percentage, 1),
                            "attended": attended,
                            "total": total_lectures
                        })
        div_info = {}
        for a in assignments:
            div_id = a.Division.division_id
            if div_id not in div_info:
                prog = a.Program
                div = a.Division
                div_info[div_id] = {
                    "program_code": prog.program_code or prog.program_name,
                    "semester": div.semester,
                    "division_code": div.division_code,
                }
        if division_ids:
            counts_rows = db.session.query(
                Student.division_id_fk,
                Student.gender,
                func.count(Student.enrollment_no),
            ).filter(
                Student.division_id_fk.in_(division_ids)
            ).group_by(
                Student.division_id_fk,
                Student.gender,
            ).all()
            counts_map = {}
            for div_id, g_raw, cnt in counts_rows:
                g = (g_raw or "").strip().lower()
                entry = counts_map.setdefault(div_id, {"male": 0, "female": 0, "other": 0})
                if g in ("male", "m"):
                    entry["male"] += cnt
                elif g in ("female", "f"):
                    entry["female"] += cnt
                else:
                    entry["other"] += cnt
            for div_id in sorted(division_ids):
                info = div_info.get(div_id)
                if not info:
                    continue
                c = counts_map.get(div_id, {"male": 0, "female": 0, "other": 0})
                total = c["male"] + c["female"] + c["other"]
                students_snapshot.append({
                    "program_code": info["program_code"],
                    "semester": info["semester"],
                    "division_code": info["division_code"],
                    "boys": c["male"],
                    "girls": c["female"],
                    "other": c["other"],
                    "total": total,
                })
        students_snapshot.sort(key=lambda x: (x["program_code"], x["semester"], x["division_code"]))

    return render_template(
        "faculty/dashboard.html", 
        faculty=faculty, 
        assignments=assignments,
        lecture_stats=lecture_stats,
        at_risk_students=at_risk_students,
        students_snapshot=students_snapshot
    )

@faculty_bp.route("/timetable")
@login_required
@role_required("faculty")
def my_timetable():
    # 1. Fetch Faculty Profile
    faculty = Faculty.query.filter_by(user_id_fk=current_user.user_id).first()
    if not faculty:
        flash("Faculty profile not found.", "danger")
        return redirect(url_for("main.index"))

    # 2. Fetch Timetable Slots for this Faculty
    # We find slots where the subject/division matches an active assignment for this faculty
    # OR direct link if we had a faculty_id on the slot (which we don't, we resolve via CourseAssignment)
    
    # Actually, the logic in timetable/routes.py resolves faculty via CourseAssignment.
    # So we can query CourseAssignments for this faculty, and then find Slots matching those Subject+Division pairs.
    
    assignments = CourseAssignment.query.filter_by(
        faculty_id_fk=current_user.user_id,
        is_active=True
    ).all()
    
    if not assignments:
        flash("No active course assignments found.", "info")
        # Still show empty timetable
    
    # Build a filter for slots
    # (subject_id, division_id) tuples
    assigned_pairs = [(a.subject_id_fk, a.division_id_fk) for a in assignments]
    
    slots_data = {}
    
    if assigned_pairs:
        # Construct query: Slots where (subject, division) is in assigned_pairs
        # SQLAlchemy 'tuple_' can handle this, or we can iterate.
        # Since a faculty won't have huge number of assignments, we can iterate or use OR conditions.
        
        conditions = []
        for sid, did in assigned_pairs:
            conditions.append(and_(
                TimetableSlot.subject_id_fk == sid,
                TimetableSlot.division_id_fk == did
            ))
            
        if conditions:
            from sqlalchemy import or_
            slots_query = (
                db.session.query(TimetableSlot, Subject, Division, Program)
                .join(Subject, Subject.subject_id == TimetableSlot.subject_id_fk)
                .join(Division, Division.division_id == TimetableSlot.division_id_fk)
                .join(Program, Program.program_id == Division.program_id_fk)
                .filter(or_(*conditions))
            )
            
            slots = slots_query.all()
            
            for s, sub, div, prog in slots:
                key = f"{s.day_of_week}_{s.period_no}"
                # Handle potential conflict (multiple slots same time?) - unlikely for one faculty unless data error
                # If multiple, just overwrite or append.
                slots_data[key] = {
                    "slot": s,
                    "subject_name": sub.subject_name,
                    "subject_code": sub.subject_code,
                    "division_code": div.division_code,
                    "program_code": prog.program_code,
                    "semester": div.semester
                }

    # Prepare Grid
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    periods = range(1, 7) # Default 6
    
    # Try to get settings from one of the programs (just for break times)
    settings = None
    if assignments:
        # Just grab the first program's settings
        # We need to join to get program_id from assignment -> division -> program
        # Simplified:
        first_assign = assignments[0]
        div = db.session.get(Division, first_assign.division_id_fk)
        if div:
             settings = TimetableSettings.query.filter_by(
                program_id_fk=div.program_id_fk,
                academic_year="2025-2026"
             ).first()
             if settings and settings.slots_per_day:
                 periods = range(1, settings.slots_per_day + 1)

    return render_template(
        "faculty/timetable.html",
        faculty=faculty,
        days=days,
        periods=periods,
        slots_data=slots_data,
        settings=settings
    )
