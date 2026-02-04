from flask import render_template, request, redirect, url_for, flash, current_app
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
