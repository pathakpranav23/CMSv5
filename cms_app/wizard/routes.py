from flask import render_template, request, redirect, url_for, flash, current_app, Response, session
from flask_login import login_required, current_user
from . import wizard
from .. import db
from ..models import Trust, Institute, Program, User, Faculty
from sqlalchemy import MetaData, Table, inspect as sa_inspect, select
import os
import csv
from io import TextIOWrapper
from werkzeug.security import generate_password_hash


def _table_columns(table_name):
    try:
        return {c["name"] for c in sa_inspect(db.engine).get_columns(table_name)}
    except Exception:
        return set()


def _reflected_table(table_name):
    metadata = MetaData()
    return Table(table_name, metadata, autoload_with=db.engine)


def _fetch_row_mapping(table_name, pk_column, pk_value, column_names=None):
    table = _reflected_table(table_name)
    if pk_column not in table.c:
        return None
    selected_cols = []
    for name in column_names or []:
        if name in table.c:
            selected_cols.append(table.c[name])
    if not selected_cols:
        selected_cols = [table.c[pk_column]]
    stmt = select(*selected_cols).where(table.c[pk_column] == pk_value).limit(1)
    row = db.session.execute(stmt).mappings().first()
    return dict(row) if row else None

@wizard.route('/step1', methods=['GET', 'POST'])
@login_required
def step1_institute():
    # STRICT ACCESS: Only 'admin' (Super User) can access the Onboarding Wizard.
        # Principals/Clients should not access this core configuration tool.
    if not getattr(current_user, 'is_super_admin', False):
        flash("Unauthorized: Only System Administrators can access the Onboarding Wizard.", "danger")
        return redirect(url_for('main.dashboard'))

    # Context Management: Handle specific institute if passed
    inst_id = request.args.get('institute_id', type=int)
    if inst_id:
        session['wizard_institute_id'] = inst_id
    
    current_inst_id = session.get('wizard_institute_id')

    institute_cols = _table_columns("institutes")
    trust_cols = _table_columns("trusts")
    institute = (
        _fetch_row_mapping(
            "institutes",
            "institute_id",
            current_inst_id,
            ["institute_id", "trust_id_fk", "institute_name", "institute_code", "affiliation_body", "aicte_code"],
        )
        if current_inst_id
        else None
    )
    trust = (
        _fetch_row_mapping(
            "trusts",
            "trust_id",
            institute.get("trust_id_fk"),
            ["trust_id", "trust_name", "trust_code", "slogan", "vision", "mission"],
        )
        if institute and institute.get("trust_id_fk")
        else None
    )

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
        
        trust_payload = {}
        if "trust_name" in trust_cols:
            trust_payload["trust_name"] = t_name
        if "trust_code" in trust_cols:
            trust_payload["trust_code"] = t_code
        if "slogan" in trust_cols:
            trust_payload["slogan"] = t_slogan
        if "vision" in trust_cols:
            trust_payload["vision"] = t_vision
        if "mission" in trust_cols:
            trust_payload["mission"] = t_mission

        institute_payload = {}
        if "institute_name" in institute_cols:
            institute_payload["institute_name"] = i_name
        if "institute_code" in institute_cols:
            institute_payload["institute_code"] = i_code
        if "affiliation_body" in institute_cols:
            institute_payload["affiliation_body"] = i_affil
        if "aicte_code" in institute_cols:
            institute_payload["aicte_code"] = i_aicte

        try:
            trusts_table = _reflected_table("trusts")
            if not trust:
                result = db.session.execute(trusts_table.insert().values(**trust_payload))
                try:
                    trust_id = (getattr(result, "inserted_primary_key", None) or [None])[0]
                except Exception:
                    trust_id = None
                if not trust_id and "trust_name" in trust_payload:
                    trust_row = db.session.execute(
                        select(trusts_table.c.trust_id)
                        .where(trusts_table.c.trust_name == trust_payload["trust_name"])
                        .order_by(trusts_table.c.trust_id.desc())
                        .limit(1)
                    ).first()
                    trust_id = trust_row[0] if trust_row else None
            else:
                trust_id = trust.get("trust_id")
                db.session.execute(
                    trusts_table.update().where(trusts_table.c.trust_id == trust_id).values(**trust_payload)
                )

            if "trust_id_fk" in institute_cols:
                institute_payload["trust_id_fk"] = trust_id

            institutes_table = _reflected_table("institutes")
            if not institute:
                result = db.session.execute(institutes_table.insert().values(**institute_payload))
                try:
                    institute_id = (getattr(result, "inserted_primary_key", None) or [None])[0]
                except Exception:
                    institute_id = None
                if not institute_id and "institute_name" in institute_payload:
                    institute_row = db.session.execute(
                        select(institutes_table.c.institute_id)
                        .where(institutes_table.c.institute_name == institute_payload["institute_name"])
                        .order_by(institutes_table.c.institute_id.desc())
                        .limit(1)
                    ).first()
                    institute_id = institute_row[0] if institute_row else None
                if institute_id:
                    session['wizard_institute_id'] = institute_id
            else:
                institute_id = institute.get("institute_id")
                db.session.execute(
                    institutes_table.update().where(institutes_table.c.institute_id == institute_id).values(**institute_payload)
                )

            db.session.commit()
        except Exception:
            db.session.rollback()
            flash("Failed to save Step 1 details.", "danger")
            return render_template('wizard/step1_institute.html', trust=trust, institute=institute)

        flash("Step 1: Institute Profile & Branding Saved!", "success")
        return redirect(url_for('wizard.step2_staff'))

    return render_template('wizard/step1_institute.html', trust=trust, institute=institute)

@wizard.route('/step2', methods=['GET', 'POST'])
@login_required
def step2_staff():
    if not getattr(current_user, 'is_super_admin', False):
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
    if not getattr(current_user, 'is_super_admin', False):
         return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        if 'continue_next' in request.form:
             return redirect(url_for('wizard.step4_structure'))
             
        # Add New Program
        p_name = request.form.get('program_name')
        p_code = request.form.get('program_code')
        p_medium = request.form.get('medium')
        p_years = request.form.get('duration_years')
        
        inst_id = session.get('wizard_institute_id')
        inst = _fetch_row_mapping("institutes", "institute_id", inst_id, ["institute_id"]) if inst_id else None
        if not inst:
            flash("Please set up an Institute first (Step 1).", "danger")
            return redirect(url_for('wizard.step1_institute'))

        if p_name and p_code:
            existing = Program.query.filter_by(program_code=p_code, institute_id_fk=inst.get("institute_id")).first()
            if not existing:
                new_prog = Program(
                    program_name=p_name,
                    program_code=p_code,
                    medium=p_medium,
                    program_duration_years=int(p_years or 3),
                    institute_id_fk=inst.get("institute_id")
                )
                db.session.add(new_prog)
                db.session.commit()
                flash(f"Program '{p_name}' added successfully!", "success")
            else:
                flash(f"Program code '{p_code}' already exists.", "warning")
    
    inst_id = session.get('wizard_institute_id')
    inst = _fetch_row_mapping("institutes", "institute_id", inst_id, ["institute_id"]) if inst_id else None
    programs = Program.query.filter_by(institute_id_fk=inst.get("institute_id")).all() if inst else []
    return render_template('wizard/step3_programs.html', programs=programs)

@wizard.route('/step4', methods=['GET', 'POST'])
@login_required
def step4_structure():
    if not getattr(current_user, 'is_super_admin', False):
         return redirect(url_for('main.dashboard'))

    # Context
    inst_id = session.get('wizard_institute_id')
    inst = _fetch_row_mapping("institutes", "institute_id", inst_id, ["institute_id"]) if inst_id else None
    if not inst:
        flash("Please set up an Institute first (Step 1).", "danger")
        return redirect(url_for('wizard.step1_institute'))

    # Logic to manage divisions/semesters would go here
    # For now, just a placeholder or simple display
    if request.method == 'POST':
        if 'continue_next' in request.form:
             return redirect(url_for('wizard.step5_subjects'))
    
    # Filter programs by current institute
    programs = Program.query.filter_by(institute_id_fk=inst.get("institute_id")).all()

    return render_template('wizard/step4_structure.html', programs=programs)

@wizard.route('/step5', methods=['GET', 'POST'])
@login_required
def step5_subjects():
    if not getattr(current_user, 'is_super_admin', False):
         return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        if 'continue_next' in request.form:
             return redirect(url_for('wizard.step6_students'))
             
    return render_template('wizard/step5_subjects.html')

@wizard.route('/step6', methods=['GET', 'POST'])
@login_required
def step6_students():
    if not getattr(current_user, 'is_super_admin', False):
         return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        # Finalize onboarding
        flash("Onboarding completed! Welcome to CMSv5.", "success")
        return redirect(url_for('main.dashboard'))
             
    return render_template('wizard/step6_students.html')
