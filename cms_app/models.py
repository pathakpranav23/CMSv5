from datetime import datetime, timezone
from . import db

def utc_now():
    return datetime.now(timezone.utc)

from flask_login import UserMixin

# ==========================================
# ORGANIZATION / TENANT MODELS
# ==========================================

class Trust(db.Model):
    __tablename__ = "trusts"
    trust_id = db.Column(db.Integer, primary_key=True)
    trust_name = db.Column(db.String(128), nullable=False)
    trust_code = db.Column(db.String(32), unique=True)
    address = db.Column(db.Text)
    contact_email = db.Column(db.String(128))
    contact_phone = db.Column(db.String(32))
    website = db.Column(db.String(128))
    logo_path = db.Column(db.String(255))
    slogan = db.Column(db.Text)
    vision = db.Column(db.Text)
    mission = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=utc_now)
    
    # New: Status for "Kill Switch" per tenant
    is_active = db.Column(db.Boolean, default=True)
    subscription_plan = db.Column(db.String(32), default="basic") # basic, pro, enterprise

    institutes = db.relationship("Institute", backref="trust", lazy=True)


class Institute(db.Model):
    __tablename__ = "institutes"
    institute_id = db.Column(db.Integer, primary_key=True)
    trust_id_fk = db.Column(db.Integer, db.ForeignKey("trusts.trust_id"))
    institute_name = db.Column(db.String(128), nullable=False)
    institute_code = db.Column(db.String(32), unique=True) # e.g. SCET, SRKI
    address = db.Column(db.Text)
    contact_email = db.Column(db.String(128))
    contact_phone = db.Column(db.String(32))
    website = db.Column(db.String(128))
    logo_path = db.Column(db.String(255))
    slogan = db.Column(db.Text)
    vision = db.Column(db.Text)
    mission = db.Column(db.Text)
    
    # Affiliation (e.g. GTU, VNSGU)
    affiliation_body = db.Column(db.String(64))
    aicte_code = db.Column(db.String(32))
    
    created_at = db.Column(db.DateTime, default=utc_now)
    
    # New: Status per institute
    is_active = db.Column(db.Boolean, default=True)

    programs = db.relationship("Program", backref="institute", lazy=True)


class Program(db.Model):
    __tablename__ = "programs"
    program_id = db.Column(db.Integer, primary_key=True)
    institute_id_fk = db.Column(db.Integer, db.ForeignKey("institutes.institute_id"))
    program_name = db.Column(db.String(64), nullable=False)
    program_code = db.Column(db.String(20)) # e.g. BCOM-ENG
    medium = db.Column(db.String(32), default="English") # English, Gujarati, Hindi
    program_duration_years = db.Column(db.Integer, default=3)

    divisions = db.relationship("Division", backref="program", lazy=True)
    subjects = db.relationship("Subject", backref="program", lazy=True)


class SubjectType(db.Model):
    __tablename__ = "subject_types"
    type_id = db.Column(db.Integer, primary_key=True)
    type_name = db.Column(db.String(64), nullable=False)
    type_code = db.Column(db.String(16), nullable=False, unique=True)
    description = db.Column(db.String(255))


class Division(db.Model):
    __tablename__ = "divisions"
    division_id = db.Column(db.Integer, primary_key=True)
    program_id_fk = db.Column(db.Integer, db.ForeignKey("programs.program_id"), nullable=False)
    semester = db.Column(db.Integer, nullable=False)
    division_code = db.Column(db.String(10), nullable=False)  # A, B, C...
    capacity = db.Column(db.Integer, default=60)
    # Medium tag (English/Gujarati) to distinguish divisions in multi-medium programs
    medium_tag = db.Column(db.String(32))


class ProgramDivisionPlan(db.Model):
    __tablename__ = "program_division_plans"
    plan_id = db.Column(db.Integer, primary_key=True)
    program_id_fk = db.Column(db.Integer, db.ForeignKey("programs.program_id"), nullable=False)
    semester = db.Column(db.Integer, nullable=False)
    num_divisions = db.Column(db.Integer, nullable=False)
    capacity_per_division = db.Column(db.Integer, nullable=False)
    roll_max_per_division = db.Column(db.Integer, default=200)
    roll_reset_each_semester = db.Column(db.Boolean, default=True)

    __table_args__ = (
        db.UniqueConstraint("program_id_fk", "semester", name="uq_program_semester_plan"),
    )


class User(UserMixin, db.Model):
    __tablename__ = "users"
    user_id = db.Column(db.Integer, primary_key=True)
    program_id_fk = db.Column(db.Integer, db.ForeignKey("programs.program_id"))  # For Principals
    username = db.Column(db.String(128), unique=True, nullable=False)
    email = db.Column(db.String(128))
    # New: Mobile for Recovery
    mobile = db.Column(db.String(20))
    password_hash = db.Column(db.String(256))
    role = db.Column(db.String(32), default="student")  # admin, principal, faculty, student, clerk
    preferred_lang = db.Column(db.String(8))
    is_active = db.Column(db.Boolean, default=True)
    
    # New: Force password change on first login
    must_change_password = db.Column(db.Boolean, default=False)

    # New: Super Admin Flag
    is_super_admin = db.Column(db.Boolean, default=False)
    
    # New: Tenant/Trust Isolation
    trust_id_fk = db.Column(db.Integer, db.ForeignKey("trusts.trust_id"))

    def get_id(self):
        return str(self.user_id)


class Faculty(db.Model):
    __tablename__ = "faculty"
    faculty_id = db.Column(db.Integer, primary_key=True)
    user_id_fk = db.Column(db.Integer, db.ForeignKey("users.user_id"))
    program_id_fk = db.Column(db.Integer, db.ForeignKey("programs.program_id"))
    full_name = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(128))
    mobile = db.Column(db.String(20))
    designation = db.Column(db.String(64))
    department = db.Column(db.String(64))
    
    # Extra profile fields
    photo_url = db.Column(db.String(255))
    emp_id = db.Column(db.String(32))
    date_of_joining = db.Column(db.Date)
    highest_qualification = db.Column(db.String(64))
    experience_years = db.Column(db.Float)
    specialization = db.Column(db.String(255))
    medium_expertise = db.Column(db.String(32))
    extra_data = db.Column(db.Text)  # JSON store for flexible fields
    
    # New: Tenant/Trust Isolation
    trust_id_fk = db.Column(db.Integer, db.ForeignKey("trusts.trust_id"))

    is_active = db.Column(db.Boolean, default=True)
    


class Student(db.Model):
    __tablename__ = "students"
    enrollment_no = db.Column(db.String(32), primary_key=True, nullable=False)
    user_id_fk = db.Column(db.Integer, db.ForeignKey("users.user_id"))
    program_id_fk = db.Column(db.Integer, db.ForeignKey("programs.program_id"), nullable=False)
    division_id_fk = db.Column(db.Integer, db.ForeignKey("divisions.division_id"))
    
    student_name = db.Column("student_name", db.String(64))
    surname = db.Column("surname", db.String(64))
    father_name = db.Column(db.String(64))
    
    date_of_birth = db.Column(db.Date)
    email = db.Column(db.String(128))
    mobile = db.Column(db.String(20))
    # New fields
    roll_no = db.Column(db.String(20))
    gender = db.Column(db.String(16))
    photo_url = db.Column(db.String(255))
    permanent_address = db.Column(db.String(255))
    current_semester = db.Column(db.Integer)
    # Medium of instruction (e.g., English, Gujarati)
    medium_tag = db.Column(db.String(32))
    
    # New: Tenant/Trust Isolation
    trust_id_fk = db.Column(db.Integer, db.ForeignKey("trusts.trust_id"))

    is_active = db.Column(db.Boolean, default=True)


    @property
    def full_name(self):
        return f"{self.student_name or ''} {self.surname or ''}".strip()

    @property
    def first_name(self):
        return self.student_name

    @first_name.setter
    def first_name(self, value):
        self.student_name = value

    @property
    def last_name(self):
        return self.surname

    @last_name.setter
    def last_name(self, value):
        self.surname = value


class Subject(db.Model):
    __tablename__ = "subjects"
    subject_id = db.Column(db.Integer, primary_key=True)
    program_id_fk = db.Column(db.Integer, db.ForeignKey("programs.program_id"), nullable=False)
    subject_type_id_fk = db.Column(db.Integer, db.ForeignKey("subject_types.type_id"), nullable=False)
    subject_name = db.Column(db.String(128), nullable=False)
    subject_code = db.Column(db.String(64))
    paper_code = db.Column(db.String(64))
    semester = db.Column(db.Integer, nullable=False)
    # Elective support
    is_elective = db.Column(db.Boolean, default=False)
    capacity = db.Column(db.Integer)  # optional seat limit for elective
    elective_group_id = db.Column(db.String(64))  # group key for mutually exclusive sets
    # Teaching medium tag (e.g., English, Gujarati)
    medium_tag = db.Column(db.String(32))
    
    is_active = db.Column(db.Boolean, default=True)

    credit_structure = db.relationship("CreditStructure", backref="subject", uselist=False)


class CreditStructure(db.Model):
    __tablename__ = "credit_structure"
    structure_id = db.Column(db.Integer, primary_key=True)
    subject_id_fk = db.Column(db.Integer, db.ForeignKey("subjects.subject_id"), nullable=False)
    theory_credits = db.Column(db.Integer, default=0)
    practical_credits = db.Column(db.Integer, default=0)
    total_credits = db.Column(db.Integer, default=0)


class CourseAssignment(db.Model):
    __tablename__ = "course_assignments"
    assignment_id = db.Column(db.Integer, primary_key=True)
    faculty_id_fk = db.Column(db.Integer, db.ForeignKey("users.user_id"))
    subject_id_fk = db.Column(db.Integer, db.ForeignKey("subjects.subject_id"))
    division_id_fk = db.Column(db.Integer, db.ForeignKey("divisions.division_id"))
    academic_year = db.Column(db.String(16))
    role = db.Column(db.String(16), default="primary")
    is_active = db.Column(db.Boolean, default=True)


class SemesterCoordinator(db.Model):
    __tablename__ = "semester_coordinators"
    coordinator_id = db.Column(db.Integer, primary_key=True)
    program_id_fk = db.Column(db.Integer, db.ForeignKey("programs.program_id"), nullable=False)
    semester = db.Column(db.Integer, nullable=False)
    faculty_user_id_fk = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    academic_year = db.Column(db.String(16), nullable=False)
    medium_tag = db.Column(db.String(32))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utc_now)


# ==========================================
# ATTENDANCE & ACADEMICS
# ==========================================

class Attendance(db.Model):
    __tablename__ = "attendance"
    attendance_id = db.Column(db.Integer, primary_key=True)
    student_id_fk = db.Column(db.String(32), db.ForeignKey("students.enrollment_no"))
    subject_id_fk = db.Column(db.Integer, db.ForeignKey("subjects.subject_id"))
    division_id_fk = db.Column(db.Integer, db.ForeignKey("divisions.division_id"))
    date_marked = db.Column(db.Date)
    status = db.Column(db.String(2)) # P, A, L...
    semester = db.Column(db.Integer)
    period_no = db.Column(db.Integer)


class StudentSubjectEnrollment(db.Model):
    __tablename__ = "student_subject_enrollments"
    enrollment_id = db.Column(db.Integer, primary_key=True)
    student_id_fk = db.Column(db.String(32), db.ForeignKey("students.enrollment_no"), nullable=False)
    subject_id_fk = db.Column(db.Integer, db.ForeignKey("subjects.subject_id"), nullable=False)
    semester = db.Column(db.Integer)
    division_id_fk = db.Column(db.Integer, db.ForeignKey("divisions.division_id"))
    academic_year = db.Column(db.String(16))
    is_active = db.Column(db.Boolean, default=True)
    source = db.Column(db.String(32)) # 'manual', 'bulk', 'auto'
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, onupdate=utc_now)


# ==========================================
# EXAMS & RESULTS
# ==========================================

class ExamScheme(db.Model):
    __tablename__ = "exam_schemes"
    scheme_id = db.Column(db.Integer, primary_key=True)
    program_id_fk = db.Column(db.Integer, db.ForeignKey("programs.program_id"), nullable=False)
    semester = db.Column(db.Integer, nullable=False)
    academic_year = db.Column(db.String(16), nullable=False)
    medium_tag = db.Column(db.String(32))
    name = db.Column(db.String(128))
    max_internal_marks = db.Column(db.Float)
    max_external_marks = db.Column(db.Float)
    min_internal_marks = db.Column(db.Float)
    min_external_marks = db.Column(db.Float)
    min_total_marks = db.Column(db.Float)
    max_total_marks = db.Column(db.Float)
    grading_scheme_json = db.Column(db.Text)
    credit_rules_json = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, onupdate=utc_now)


class Grade(db.Model):
    __tablename__ = "grades"
    grade_id = db.Column(db.Integer, primary_key=True)
    student_id_fk = db.Column(db.String(32), db.ForeignKey("students.enrollment_no"))
    subject_id_fk = db.Column(db.Integer, db.ForeignKey("subjects.subject_id"))
    division_id_fk = db.Column(db.Integer, db.ForeignKey("divisions.division_id"))
    theory_marks = db.Column(db.Float)
    practical_marks = db.Column(db.Float)
    gpa_for_subject = db.Column(db.Float)


class StudentSemesterResult(db.Model):
    __tablename__ = "student_semester_results"
    result_id = db.Column(db.Integer, primary_key=True)
    student_id_fk = db.Column(db.String(32), db.ForeignKey("students.enrollment_no"), nullable=False)
    program_id_fk = db.Column(db.Integer, db.ForeignKey("programs.program_id"), nullable=False)
    scheme_id_fk = db.Column(db.Integer, db.ForeignKey("exam_schemes.scheme_id"))
    semester = db.Column(db.Integer, nullable=False)
    academic_year = db.Column(db.String(16), nullable=False)
    attempt_no = db.Column(db.Integer, default=1)
    total_credits_registered = db.Column(db.Integer)
    total_credits_earned = db.Column(db.Integer)
    sgpa = db.Column(db.Float)




class ExamMark(db.Model):
    __tablename__ = "exam_marks"
    exam_mark_id = db.Column(db.Integer, primary_key=True)
    student_id_fk = db.Column(db.String(32), db.ForeignKey("students.enrollment_no"), nullable=False)
    subject_id_fk = db.Column(db.Integer, db.ForeignKey("subjects.subject_id"), nullable=False)
    division_id_fk = db.Column(db.Integer, db.ForeignKey("divisions.division_id"))
    scheme_id_fk = db.Column(db.Integer, db.ForeignKey("exam_schemes.scheme_id"))
    semester = db.Column(db.Integer)
    academic_year = db.Column(db.String(16))
    attempt_no = db.Column(db.Integer)
    internal_marks = db.Column(db.Float)
    external_marks = db.Column(db.Float)
    total_marks = db.Column(db.Float)
    grade_point = db.Column(db.Float)
    grade_letter = db.Column(db.String(4))
    is_absent = db.Column(db.Boolean)
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, onupdate=utc_now)

    __table_args__ = (
        db.UniqueConstraint("student_id_fk", "subject_id_fk", "semester", "academic_year", "attempt_no", name="uq_exam_mark_attempt"),
    )


class StudentCreditLog(db.Model):
    __tablename__ = "student_credit_log"
    log_id = db.Column(db.Integer, primary_key=True)
    student_id_fk = db.Column(db.String(32), db.ForeignKey("students.enrollment_no"))
    subject_id_fk = db.Column(db.Integer, db.ForeignKey("subjects.subject_id"))
    credits_earned = db.Column(db.Integer)
    date_awarded = db.Column(db.Date)
    is_exit_eligible = db.Column(db.Boolean)


# ==========================================
# FEES
# ==========================================

class FeeStructure(db.Model):
    __tablename__ = "fee_structures"
    structure_id = db.Column(db.Integer, primary_key=True)
    program_id_fk = db.Column(db.Integer, db.ForeignKey("programs.program_id"), nullable=False)
    semester = db.Column(db.Integer)
    component_name = db.Column(db.String(128), nullable=False)
    amount = db.Column(db.Float)
    due_date = db.Column(db.Date)
    is_active = db.Column(db.Boolean, default=True)
    is_frozen = db.Column(db.Boolean, default=False)
    medium_tag = db.Column(db.String(32))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, onupdate=utc_now)


class ProgramBankDetails(db.Model):
    __tablename__ = "program_bank_details"
    bank_id = db.Column(db.Integer, primary_key=True)
    program_id_fk = db.Column(db.Integer, db.ForeignKey("programs.program_id"), nullable=False, unique=True)
    bank_name = db.Column(db.String(128), nullable=False)
    account_name = db.Column(db.String(128), nullable=False)
    account_number = db.Column(db.String(64), nullable=False)
    ifsc = db.Column(db.String(32), nullable=False)
    branch = db.Column(db.String(128), nullable=False)
    upi_vpa = db.Column(db.String(128))
    payee_display = db.Column(db.String(128))
    qr_image_path = db.Column(db.String(255))
    gstin = db.Column(db.String(64))
    pan = db.Column(db.String(16))
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, onupdate=utc_now)


class FeePayment(db.Model):
    __tablename__ = "fee_payments"
    payment_id = db.Column(db.Integer, primary_key=True)
    enrollment_no = db.Column(db.String(32), db.ForeignKey("students.enrollment_no"), nullable=False)
    program_id_fk = db.Column(db.Integer, db.ForeignKey("programs.program_id"), nullable=False)
    semester = db.Column(db.Integer, nullable=False)
    medium_tag = db.Column(db.String(32))
    amount = db.Column(db.Float, nullable=False)
    txn_ref = db.Column(db.String(64))
    utr = db.Column(db.String(64))
    status = db.Column(db.String(16))
    payment_mode = db.Column(db.String(32))
    reference_no = db.Column(db.String(64))
    payment_date = db.Column(db.Date)
    
    proof_image_path = db.Column(db.String(255))
    remarks = db.Column(db.Text)
    
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"))
    verified_by_user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"))
    
    created_at = db.Column(db.DateTime, default=utc_now)
    verified_at = db.Column(db.DateTime)
    bank_credit_at = db.Column(db.DateTime)
    
    payer_name = db.Column(db.String(128))
    receipt_no = db.Column(db.String(32))


class FeesRecord(db.Model):
    __tablename__ = "fees_records"
    fee_id = db.Column(db.Integer, primary_key=True)
    student_id_fk = db.Column(db.String(32), db.ForeignKey("students.enrollment_no"))
    amount_due = db.Column(db.Float)
    amount_paid = db.Column(db.Float)
    date_paid = db.Column(db.Date)
    semester = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=utc_now)


# ==========================================
# TIMETABLE
# ==========================================

class TimetableSettings(db.Model):
    __tablename__ = "timetable_settings"
    setting_id = db.Column(db.Integer, primary_key=True)
    program_id_fk = db.Column(db.Integer, db.ForeignKey("programs.program_id"), nullable=False)
    academic_year = db.Column(db.String(16), nullable=False)
    start_time = db.Column(db.Time)
    slot_duration_mins = db.Column(db.Integer)
    break_after_period = db.Column(db.Integer)
    break_duration_mins = db.Column(db.Integer)
    slots_per_day = db.Column(db.Integer)

    __table_args__ = (
        db.UniqueConstraint("program_id_fk", "academic_year", name="uq_timetable_settings"),
    )


class TimetableSlot(db.Model):
    __tablename__ = "timetable_slots"
    slot_id = db.Column(db.Integer, primary_key=True)
    division_id_fk = db.Column(db.Integer, db.ForeignKey("divisions.division_id"), nullable=False)
    subject_id_fk = db.Column(db.Integer, db.ForeignKey("subjects.subject_id"), nullable=False)
    day_of_week = db.Column(db.String(10), nullable=False)
    period_no = db.Column(db.Integer, nullable=False)
    slot_type = db.Column(db.String(16))
    room_no = db.Column(db.String(32))

    __table_args__ = (
        db.UniqueConstraint("division_id_fk", "day_of_week", "period_no", name="uq_timetable_slot_div_day_period"),
    )


# ==========================================
# COMMUNICATION & SYSTEM
# ==========================================

class Notification(db.Model):
    __tablename__ = "notifications"
    notification_id = db.Column(db.Integer, primary_key=True)
    student_id_fk = db.Column(db.String(32), db.ForeignKey("students.enrollment_no"), nullable=False)
    kind = db.Column(db.String(32), nullable=False) # e.g. 'fee_due', 'exam_result'
    title = db.Column(db.String(128), nullable=False)
    message = db.Column(db.Text)
    data_json = db.Column(db.Text)
    payment_id_fk = db.Column(db.Integer, db.ForeignKey("fee_payments.payment_id"))
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=utc_now)
    read_at = db.Column(db.DateTime)


class Announcement(db.Model):
    __tablename__ = "announcements"
    announcement_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128), nullable=False)
    message = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(16))
    is_active = db.Column(db.Boolean)
    program_id_fk = db.Column(db.Integer, db.ForeignKey("programs.program_id"))
    start_at = db.Column(db.DateTime)
    end_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime)
    created_by = db.Column(db.Integer, db.ForeignKey("users.user_id"))
    actor_user_id_fk = db.Column(db.Integer, db.ForeignKey("users.user_id"))

    audiences = db.relationship("AnnouncementAudience", backref="announcement", lazy=True)


class AnnouncementAudience(db.Model):
    __tablename__ = "announcement_audience"
    audience_id = db.Column(db.Integer, primary_key=True)
    announcement_id_fk = db.Column(db.Integer, db.ForeignKey("announcements.announcement_id"), nullable=False)
    role = db.Column(db.String(32), nullable=False)


class AnnouncementRecipient(db.Model):
    __tablename__ = "announcement_recipients"
    recipient_id = db.Column(db.Integer, primary_key=True)
    announcement_id_fk = db.Column(db.Integer, db.ForeignKey("announcements.announcement_id"), nullable=False)
    student_id_fk = db.Column(db.String(32), db.ForeignKey("students.enrollment_no"), nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now)


class AnnouncementDismissal(db.Model):
    __tablename__ = "announcement_dismissals"
    dismissal_id = db.Column(db.Integer, primary_key=True)
    announcement_id_fk = db.Column(db.Integer, db.ForeignKey("announcements.announcement_id"), nullable=False)
    user_id_fk = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    dismissed_at = db.Column(db.DateTime, default=utc_now)


class PasswordChangeLog(db.Model):
    __tablename__ = "password_change_log"
    log_id = db.Column(db.Integer, primary_key=True)
    user_id_fk = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    changed_by_user_id_fk = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    changed_at = db.Column(db.DateTime, default=utc_now)
    method = db.Column(db.String(32))
    note = db.Column(db.String(255))


class SubjectMaterial(db.Model):
    __tablename__ = "subject_materials"
    material_id = db.Column(db.Integer, primary_key=True)
    subject_id_fk = db.Column(db.Integer, db.ForeignKey("subjects.subject_id"), nullable=False)
    faculty_id_fk = db.Column(db.Integer, db.ForeignKey("users.user_id"))
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    kind = db.Column(db.String(16), nullable=False)
    file_path = db.Column(db.String(255))
    external_url = db.Column(db.String(255))
    tags = db.Column(db.String(255))
    academic_year = db.Column(db.String(16))
    is_published = db.Column(db.Boolean)
    is_flagged = db.Column(db.Boolean)
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime)


class SubjectMaterialLog(db.Model):
    __tablename__ = "subject_material_logs"
    log_id = db.Column(db.Integer, primary_key=True)
    material_id_fk = db.Column(db.Integer, db.ForeignKey("subject_materials.material_id"), nullable=False)
    action = db.Column(db.String(32), nullable=False)
    actor_user_id_fk = db.Column(db.Integer, db.ForeignKey("users.user_id"))
    actor_role = db.Column(db.String(32))
    meta_json = db.Column(db.Text)
    at = db.Column(db.DateTime, default=utc_now)


class ImportLog(db.Model):
    __tablename__ = "import_logs"
    log_id = db.Column(db.Integer, primary_key=True)
    user_id_fk = db.Column(db.Integer, db.ForeignKey("users.user_id"))
    kind = db.Column(db.String(16), nullable=False)  # students | subjects | fees
    program_id_fk = db.Column(db.Integer, db.ForeignKey("programs.program_id"))
    semester = db.Column(db.Integer)
    medium_tag = db.Column(db.String(32))
    path = db.Column(db.String(255))
    dry_run = db.Column(db.Boolean, default=False)
    created_count = db.Column(db.Integer, default=0)
    updated_count = db.Column(db.Integer, default=0)
    skipped_count = db.Column(db.Integer, default=0)
    errors_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=utc_now)
    extra_json = db.Column(db.Text)


# ==========================================
# SUPER ADMIN / SYSTEM MODELS
# ==========================================

class SystemMessage(db.Model):
    """
    For broadcasting messages, offers, holiday wishes, or instructions.
    """
    __tablename__ = "system_messages"
    message_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False) # Supports HTML
    
    # Type: 'info', 'success', 'warning', 'danger' (for alerts), 'popup' (for modals)
    message_type = db.Column(db.String(32), default='info') 
    
    start_date = db.Column(db.DateTime, default=utc_now)
    end_date = db.Column(db.DateTime)
    
    is_active = db.Column(db.Boolean, default=True)
    
    # Target Audience
    # 'all', 'super_admin', 'trust_admin', 'principal', 'faculty', 'student'
    target_role = db.Column(db.String(32), default='all')
    
    # Optional: Target specific Trust (if null, applies to all matching target_role)
    target_trust_id = db.Column(db.Integer, nullable=True)


class SystemConfig(db.Model):
    """
    Global configuration for the Super Admin.
    Key-Value store for system-wide settings like 'maintenance_mode'.
    """
    __tablename__ = "system_config"
    config_key = db.Column(db.String(64), primary_key=True)
    config_value = db.Column(db.Text)
    description = db.Column(db.String(255))
