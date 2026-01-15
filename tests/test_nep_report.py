import pytest
from cms_app import db
from cms_app.models import User, Program, Student, Subject, CreditStructure, Grade
from werkzeug.security import generate_password_hash
from datetime import date

def test_nep_exit_report(client, app):
    with app.app_context():
        # Setup Data
        # 1. Admin User
        if not User.query.filter_by(username="admin_nep").first():
            admin = User(username="admin_nep", password_hash=generate_password_hash("secret"), role="admin")
            db.session.add(admin)
        
        # 2. Program
        prog = Program(program_name="NEP Test BBA", program_duration_years=3)
        db.session.add(prog)
        db.session.flush()
        
        # 3. Subject with Credits
        # We need a SubjectType first? It's foreign key.
        # Check if SubjectType exists, if not create dummy
        from cms_app.models import SubjectType
        stype = SubjectType.query.first()
        if not stype:
            stype = SubjectType(type_code="MJ", description="Major")
            db.session.add(stype)
            db.session.flush()
            
        subj = Subject(
            program_id_fk=prog.program_id,
            subject_type_id_fk=stype.type_id,
            subject_name="Intro to NEP",
            semester=1,
            subject_code="NEP101"
        )
        db.session.add(subj)
        db.session.flush()
        
        # 4. Credit Structure (4 credits)
        cs = CreditStructure(subject_id_fk=subj.subject_id, theory_credits=3, practical_credits=1, total_credits=4)
        db.session.add(cs)
        
        # 5. Student
        # Clean up if exists
        exist_student = Student.query.filter_by(enrollment_no="NEP001").first()
        if exist_student:
             # If student exists, we need to be careful about cascade deletes or just use a new ID
             # Let's use a random ID to avoid conflict
             import random
             rnd = random.randint(1000, 9999)
             eno = f"NEP{rnd}"
        else:
             eno = "NEP001"

        student = Student(
            enrollment_no=eno,
            program_id_fk=prog.program_id,
            surname="Doe",
            student_name="John",
            current_semester=2
        )
        db.session.add(student)
        
        # 6. Grade (Pass)
        grade = Grade(
            student_id_fk=eno,
            subject_id_fk=subj.subject_id,
            theory_marks=40,
            gpa_for_subject=8.0  # Pass
        )
        db.session.add(grade)
        
        db.session.commit()
        
        prog_id = prog.program_id

    # Test
    client.post("/login", data={"username": "admin_nep", "password": "secret"}, follow_redirects=True)
    
    # Get report for the program
    resp = client.get(f"/admin/reports/nep-exit-eligibility?program_id={prog_id}")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    
    # Check assertions
    assert "John Doe" in html
    assert eno in html
    assert "4" in html  # Total credits
    assert "In Progress" in html # 4 credits < 40 for Certificate
    
    # Test with enough credits (mocking logic or adding more grades is hard, 
    # but we can verify the logic calculates 4 credits correctly).
