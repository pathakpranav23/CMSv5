import json
from sqlalchemy import select
from .. import db
from ..models import ExamScheme, StudentSemesterResult, ExamMark, Subject, CreditStructure, SubjectType

def resolve_exam_limits(scheme, subject):
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

def get_grade_point(marks_obtained, max_marks, grading_scheme=None):
    """
    Calculates Grade Point and Letter based on marks.
    Default: 10-point scale.
    """
    if max_marks <= 0:
        return 0.0, "F"
        
    percentage = (marks_obtained / max_marks) * 100
    
    # Use provided scheme or default
    if grading_scheme:
        # Expected format: [{"min": 90, "grade": "O", "gp": 10}, ...]
        # Sort by min descending to ensure correct matching
        sorted_scheme = sorted(grading_scheme, key=lambda x: x.get("min", 0), reverse=True)
        for band in sorted_scheme:
            if percentage >= band.get("min", 0):
                return float(band.get("gp", 0)), band.get("grade", "F")
    
    # Default Standard 10-point scale
    if percentage >= 90: return 10.0, "O"
    elif percentage >= 80: return 9.0, "A+"
    elif percentage >= 70: return 8.0, "A"
    elif percentage >= 60: return 7.0, "B+"
    elif percentage >= 50: return 6.0, "B"
    elif percentage >= 40: return 5.0, "C"
    else: return 0.0, "F"

def calculate_exam_results(scheme_id):
    """
    Calculates results for an exam scheme.
    Computes Grades, SGPA, and updates StudentSemesterResult.
    Returns: (success: bool, message: str, count: int)
    """
    scheme = db.session.get(ExamScheme, scheme_id)
    if not scheme:
        return False, "Exam scheme not found.", 0
        
    # Parse grading scheme
    grading_scheme = None
    if scheme.grading_scheme_json:
        try:
            grading_data = json.loads(scheme.grading_scheme_json)
            if isinstance(grading_data, dict) and "bands" in grading_data:
                grading_scheme = sorted(grading_data["bands"], key=lambda x: x["min"], reverse=True)
        except:
            pass
            
    # Fetch all students with marks in this scheme
    marks = db.session.execute(
        select(ExamMark).filter_by(scheme_id_fk=scheme_id)
    ).scalars().all()
    
    if not marks:
        return False, "No marks found to process.", 0
        
    # Group marks by Student
    student_marks = {}
    subject_ids = set()
    for m in marks:
        if m.student_id_fk not in student_marks:
            student_marks[m.student_id_fk] = []
        student_marks[m.student_id_fk].append(m)
        subject_ids.add(m.subject_id_fk)
        
    # Fetch Subjects and Credits
    subjects = db.session.execute(
        select(Subject).filter(Subject.subject_id.in_(subject_ids))
    ).scalars().all()
    
    subject_map = {s.subject_id: s for s in subjects}
    
    # Fetch Credit Structures
    credit_map = {}
    for s in subjects:
        c = 0
        if s.credit_structure:
            c = s.credit_structure.total_credits
        else:
            # Fallback check
            cs = db.session.execute(select(CreditStructure).filter_by(subject_id_fk=s.subject_id)).scalars().first()
            if cs: c = cs.total_credits
        credit_map[s.subject_id] = c
        
    processed_count = 0
    
    try:
        for student_id, s_marks in student_marks.items():
            total_credits = 0
            total_points = 0
            total_registered_credits = 0
            
            # 1. Update individual Subject Grades
            for m in s_marks:
                subject = subject_map.get(m.subject_id_fk)
                if not subject: continue
                
                # Determine Max Marks for this subject (using rule logic or defaults)
                limits = resolve_exam_limits(scheme, subject)
                max_tot = limits.get("max_total", 100)
                
                # Calculate Grade
                obtained = m.total_marks or 0
                if m.is_absent:
                    obtained = 0
                    
                gp, letter = get_grade_point(obtained, max_tot, grading_scheme)
                
                # Update Mark Record
                m.grade_point = gp
                m.grade_letter = letter
                
                # SGPA Calculation Accumulation
                credits = credit_map.get(m.subject_id_fk, 0)
                if credits > 0:
                    total_registered_credits += credits
                    if not m.is_absent: 
                        total_points += (gp * credits)
                        if letter != "F":
                            total_credits += credits # Credits Earned
            
            # 2. Calculate SGPA
            sgpa = 0.0
            if total_registered_credits > 0:
                sgpa = total_points / total_registered_credits
                
            # 3. Update/Create StudentSemesterResult
            result = db.session.execute(
                select(StudentSemesterResult).filter_by(
                    student_id_fk=student_id,
                    scheme_id_fk=scheme_id
                )
            ).scalars().first()
            
            if not result:
                result = StudentSemesterResult(
                    student_id_fk=student_id,
                    program_id_fk=scheme.program_id_fk,
                    scheme_id_fk=scheme_id,
                    semester=scheme.semester,
                    academic_year=scheme.academic_year,
                    attempt_no=1 
                )
                db.session.add(result)
                
            result.total_credits_registered = total_registered_credits
            result.total_credits_earned = total_credits
            result.sgpa = round(sgpa, 2)
            
            processed_count += 1
            
        db.session.commit()
        return True, f"Results calculated for {processed_count} students.", processed_count
        
    except Exception as e:
        db.session.rollback()
        return False, str(e), 0
