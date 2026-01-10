
@main_bp.route("/analytics")
@login_required
@role_required("admin", "principal")
def module_analytics():
    from ..models import Faculty, AttendanceMaster, Subject, Class, Program
    from datetime import datetime, date, timedelta
    from collections import defaultdict
    
    role = (getattr(current_user, "role", "") or "").strip().lower()
    user_pid = int(getattr(current_user, "program_id_fk", 0) or 0)
    
    # 1. Daily Logs (Today)
    today = date.today()
    q_daily = db.session.query(
        AttendanceMaster, 
        Faculty.faculty_name, 
        Faculty.role, 
        Subject.subject_name,
        Class.division,
        Class.semester,
        Program.program_name,
        Program.program_id
    ).join(Faculty, AttendanceMaster.faculty_id == Faculty.faculty_id)\
     .join(Subject, AttendanceMaster.subject_id == Subject.subject_id)\
     .join(Class, AttendanceMaster.class_id == Class.class_id)\
     .join(Program, Class.program_id == Program.program_id)\
     .filter(AttendanceMaster.date == today)\
     .order_by(AttendanceMaster.start_time.asc())
     
    if role == "principal" and user_pid:
        q_daily = q_daily.filter(Program.program_id == user_pid)
        
    daily_rows = q_daily.all()
    
    daily_logs = []
    for am, fname, frole, sname, div, sem, pname, pid in daily_rows:
        daily_logs.append({
            "start_time": am.start_time.strftime("%I:%M %p"),
            "end_time": am.end_time.strftime("%I:%M %p"),
            "period_no": am.period_no,
            "faculty_name": fname,
            "faculty_role": frole,
            "faculty_id": am.faculty_id,
            "subject_name": sname,
            "division": div,
            "semester": sem,
            "program_name": pname,
            "topic": am.topic_covered,
            "status": "Conducted", # Currently we only store conducted ones
            "present_count": am.present_count,
            "total_students": am.total_students
        })
        
    # 2. Weekly Grid (Pivot)
    start_week = today - timedelta(days=today.weekday()) # Monday
    end_week = start_week + timedelta(days=6) # Sunday
    
    q_week = db.session.query(
        Faculty.faculty_name,
        AttendanceMaster.date
    ).join(Faculty, AttendanceMaster.faculty_id == Faculty.faculty_id)\
     .filter(AttendanceMaster.date >= start_week)\
     .filter(AttendanceMaster.date <= end_week)
     
    if role == "principal" and user_pid:
        q_week = q_week.join(Class, AttendanceMaster.class_id == Class.class_id)\
                       .filter(Class.program_id == user_pid)
                       
    week_rows = q_week.all()
    
    # Process into pivot structure
    faculty_map = defaultdict(lambda: {"total": 0, "days": defaultdict(int)})
    
    for fname, log_date in week_rows:
        day_str = log_date.strftime("%a") # Mon, Tue...
        faculty_map[fname]["days"][day_str] += 1
        faculty_map[fname]["total"] += 1
        
    weekly_grid = []
    for fname, data in faculty_map.items():
        weekly_grid.append({
            "faculty_name": fname,
            "days": dict(data["days"]),
            "total": data["total"]
        })
    weekly_grid.sort(key=lambda x: x["total"], reverse=True)

    # 3. Performance Alerts (For Actions)
    # Simple logic: High > 15 lectures/week, Low < 5 lectures/week (Example threshold)
    performance_alerts = {"high": [], "low": []}
    
    # We need faculty IDs for the action buttons
    fac_ids = db.session.query(Faculty.faculty_id, Faculty.faculty_name).all()
    fac_lookup = {f.faculty_name: f.faculty_id for f in fac_ids}

    for item in weekly_grid:
        fid = fac_lookup.get(item["faculty_name"])
        if item["total"] >= 12: # High performer threshold
             performance_alerts["high"].append({
                 "id": fid,
                 "name": item["faculty_name"],
                 "lectures_taken": item["total"],
                 "avg_attendance": 85 # Placeholder, would need complex query
             })
        elif item["total"] < 5: # Low performer threshold
             performance_alerts["low"].append({
                 "id": fid,
                 "name": item["faculty_name"],
                 "lectures_taken": item["total"],
                 "target": 12
             })
             
    return render_template("module_analytics.html", 
                           daily_logs=daily_logs, 
                           weekly_grid=weekly_grid,
                           performance_alerts=performance_alerts,
                           today_date=today.strftime("%d %b %Y"),
                           lecture_stats={"total_today": len(daily_logs)})


@main_bp.route("/analytics/notify", methods=["POST"])
@login_required
@role_required("admin", "principal")
def analytics_notify():
    from ..email_utils import send_email
    
    fid = request.form.get("faculty_id")
    notif_type = request.form.get("type") # 'warning' or 'appreciation'
    
    faculty = Faculty.query.get_or_404(fid)
    
    if not faculty.email:
        flash(f"Cannot send notification: {faculty.faculty_name} has no email address.", "danger")
        return redirect(url_for("main.module_analytics"))
        
    if notif_type == "warning":
        subject = "Action Required: Academic Delivery Review"
        body = f"""Dear Prof. {faculty.faculty_name},

This is an automated alert regarding your lecture completion rate for this week.
It appears to be below the expected target.

Please ensure all scheduled classes are conducted and marked in the system.
If you are facing any issues, please contact the Principal's office.

Regards,
Principal's Office"""
        flash(f"Warning sent to {faculty.faculty_name}.", "warning")
        
    elif notif_type == "appreciation":
        subject = "Appreciation: Excellent Academic Performance"
        body = f"""Dear Prof. {faculty.faculty_name},

We noticed your excellent lecture delivery and student engagement this week.
Thank you for your dedication and hard work. Keep it up!

Regards,
Principal's Office"""
        flash(f"Appreciation sent to {faculty.faculty_name}!", "success")
    
    # Fire and forget email
    try:
        send_email(faculty.email, subject, body)
    except Exception as e:
        flash(f"Email failed: {str(e)}", "danger")
        
    return redirect(url_for("main.module_analytics"))
