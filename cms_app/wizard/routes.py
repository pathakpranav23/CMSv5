from flask import render_template, request, redirect, url_for, flash, current_app, Response, session
from flask_login import login_required, current_user
from . import wizard
from .. import db
from ..models import Trust, Institute, Program, User, Faculty
import os
import csv
from io import TextIOWrapper
from werkzeug.security import generate_password_hash

@wizard.route('/step1', methods=['GET', 'POST'])
@login_required
def step1_institute():
    # STRICT ACCESS: Only 'admin' (Super User) can access the Onboarding Wizard.
    # Principals/Clients should not access this core configuration tool.
    if getattr(current_user, 'role', '') != 'admin' and not getattr(current_user, 'is_super_admin', False):
        flash("Unauthorized: Only System Administrators can access the Onboarding Wizard.", "danger")
        return redirect(url_for('main.dashboard'))

    # Context Management: Handle specific institute if passed
    inst_id = request.args.get('institute_id', type=int)
    if inst_id:
        session['wizard_institute_id'] = inst_id
    
    current_inst_id = session.get('wizard_institute_id')
    
    # Fetch existing data
    trust = Trust.query.first()
    if current_inst_id:
        institute = db.session.get(Institute, current_inst_id)
    else:
        institute = Institute.query.first()

    if request.method == 'POST':
        # Trust Details
        t_name = request.form.get('trust_name')
        t_code = request.form.get('trust_code')
        t_slogan = request.form.get('trust_slogan')
        t_vision = request.form.get('trust_vision')
        t_mission = request.form.get('trust_mission')
        
        # Institute Details
        i_name = request.form.get('institute_name')
        i_code = request.form.get('institute_code')
        i_affil = request.form.get('affiliation_body')
        i_aicte = request.form.get('aicte_code')
        
        # Update or Create Trust
        if not trust:
            trust = Trust(
                trust_name=t_name, 
                trust_code=t_code, 
                slogan=t_slogan,
                vision=t_vision,
                mission=t_mission
            )
            db.session.add(trust)
        else:
            trust.trust_name = t_name
            trust.trust_code = t_code
            trust.slogan = t_slogan
            trust.vision = t_vision
            trust.mission = t_mission
            
        db.session.flush() # Get trust_id if needed

        # Update or Create Institute
        if not institute:
            institute = Institute(
                institute_name=i_name, 
                institute_code=i_code, 
                trust_id_fk=trust.trust_id,
                affiliation_body=i_affil,
                aicte_code=i_aicte
            )
            db.session.add(institute)
            db.session.flush()
            # If created new institute, set it as context
            session['wizard_institute_id'] = institute.institute_id
        else:
            institute.institute_name = i_name
            institute.institute_code = i_code
            institute.trust_id_fk = trust.trust_id # Ensure link
            institute.affiliation_body = i_affil
            institute.aicte_code = i_aicte
            
        db.session.commit()
        flash("Step 1: Institute Profile & Branding Saved!", "success")
        return redirect(url_for('wizard.step2_staff'))

    return render_template('wizard/step1_institute.html', trust=trust, institute=institute)

@wizard.route('/step2', methods=['GET', 'POST'])
@login_required
def step2_staff():
    # Allow admin, principal, OR super_admin
    if getattr(current_user, 'role', '') not in ['admin', 'principal'] and not getattr(current_user, 'is_super_admin', False):
         return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        # Check if this is a "Continue" action
        if 'continue_next' in request.form:
             return redirect(url_for('wizard.step3_programs'))

        file = request.files.get('file')
        if file and file.filename.endswith('.csv'):
            try:
                stream = TextIOWrapper(file.stream, encoding='utf-8-sig', newline='')
                csv_reader = csv.DictReader(stream)
                
                added_count = 0
                for row in csv_reader:
                    # Normalize headers (lower case)
                    row = {k.lower().strip(): v.strip() for k, v in row.items() if k}
                    
                    full_name = row.get('name') or row.get('full name')
                    email = row.get('email')
                    mobile = row.get('mobile')
                    role = row.get('role', 'Faculty').capitalize()
                    designation = row.get('designation', 'Assistant Professor')
                    
                    if not full_name or not email:
                        continue

                    # Determine Username and Password
                    # Preference: Mobile > Email (for non-admin/principal)
                    user_username = email
                    user_password_plain = 'Password123'
                    
                    is_privileged = role.lower() in ['admin', 'principal', 'super admin']
                    
                    if mobile and not is_privileged:
                        # Basic cleanup
                        digits = ''.join(ch for ch in mobile if ch.isdigit())
                        if len(digits) >= 10:
                            user_username = digits
                            user_password_plain = digits
                        
                    # Check if user exists
                    existing_user = User.query.filter_by(username=user_username).first()
                    if not existing_user:
                        # Create User
                        new_user = User(
                            username=user_username,
                            email=email,
                            role=role,
                            password_hash=generate_password_hash(user_password_plain),
                            must_change_password=True
                        )
                        db.session.add(new_user)
                        db.session.flush()
                        
                        # Create Faculty Record (linked to User)
                        new_faculty = Faculty(
                            full_name=full_name,
                            email=email,
                            designation=designation,
                            user_id_fk=new_user.user_id
                        )
                        db.session.add(new_faculty)
                        added_count += 1
                
                db.session.commit()
                flash(f"Successfully imported {added_count} staff members.", "success")
            except Exception as e:
                db.session.rollback()
                flash(f"Error importing CSV: {str(e)}", "danger")
        else:
            flash("Please upload a valid CSV file.", "warning")
            
    # Get recent staff for display
    recent_staff = Faculty.query.order_by(Faculty.faculty_id.desc()).limit(5).all()
    return render_template('wizard/step2_staff.html', recent_staff=recent_staff)

@wizard.route('/step2/template')
@login_required
def step2_template():
    # Return a CSV template
    csv_content = "Name,Email,Mobile,Role,Designation\nJohn Doe,john@example.com,9876543210,Faculty,Assistant Professor\nJane Smith,jane@example.com,9123456789,Principal,Principal"
    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=staff_import_template.csv"}
    )

@wizard.route('/step3', methods=['GET', 'POST'])
@login_required
def step3_programs():
    if getattr(current_user, 'role', '') not in ['admin', 'principal'] and not getattr(current_user, 'is_super_admin', False):
         return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        if 'continue_next' in request.form:
             return redirect(url_for('wizard.step4_structure'))
             
        # Add New Program
        p_name = request.form.get('program_name')
        p_code = request.form.get('program_code')
        p_medium = request.form.get('medium')
        p_years = request.form.get('duration_years')
        
        # Determine Institute (Assuming single institute context for now, or first one)
        # Ideally, admin selects institute if multiple exist.
        inst = Institute.query.first() 
        if not inst:
            flash("Please set up an Institute first (Step 1).", "danger")
            return redirect(url_for('wizard.step1_institute'))

        if p_name and p_code:
            existing = Program.query.filter_by(program_code=p_code, institute_id_fk=inst.institute_id).first()
            if not existing:
                new_prog = Program(
                    program_name=p_name,
                    program_code=p_code,
                    medium=p_medium,
                    program_duration_years=int(p_years or 3),
                    institute_id_fk=inst.institute_id
                )
                db.session.add(new_prog)
                db.session.commit()
                flash(f"Program '{p_name}' added successfully!", "success")
            else:
                flash(f"Program code '{p_code}' already exists.", "warning")
    
    programs = Program.query.all()
    return render_template('wizard/step3_programs.html', programs=programs)

@wizard.route('/step4', methods=['GET', 'POST'])
@login_required
def step4_structure():
    if getattr(current_user, 'role', '') not in ['admin', 'principal'] and not getattr(current_user, 'is_super_admin', False):
         return redirect(url_for('main.dashboard'))

    # Context
    inst_id = session.get('wizard_institute_id')
    inst = db.session.get(Institute, inst_id) if inst_id else Institute.query.first()

    # Logic to manage divisions/semesters would go here
    # For now, just a placeholder or simple display
    if request.method == 'POST':
        if 'continue_next' in request.form:
             return redirect(url_for('wizard.step5_subjects'))
    
    # Filter programs by current institute
    if inst:
        programs = Program.query.filter_by(institute_id_fk=inst.institute_id).all()
    else:
        programs = Program.query.all()

    return render_template('wizard/step4_structure.html', programs=programs)

@wizard.route('/step5', methods=['GET', 'POST'])
@login_required
def step5_subjects():
    if current_user.role not in ['admin', 'principal']:
         return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        if 'continue_next' in request.form:
             return redirect(url_for('wizard.step6_students'))
             
    return render_template('wizard/step5_subjects.html')

@wizard.route('/step6', methods=['GET', 'POST'])
@login_required
def step6_students():
    if getattr(current_user, 'role', '') not in ['admin', 'principal'] and not getattr(current_user, 'is_super_admin', False):
         return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        # Finalize onboarding
        flash("Onboarding completed! Welcome to CMSv5.", "success")
        return redirect(url_for('main.dashboard'))
             
    return render_template('wizard/step6_students.html')
