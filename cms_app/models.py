from datetime import datetime
from . import db
from flask_login import UserMixin


class Program(db.Model):
    __tablename__ = "programs"
    program_id = db.Column(db.Integer, primary_key=True)
    program_name = db.Column(db.String(64), nullable=False)
    program_duration_years = db.Column(db.Integer, default=3)

    divisions = db.relationship("Division", backref="program", lazy=True)
    subjects = db.relationship("Subject", backref="program", lazy=True)


class SubjectType(db.Model):
    __tablename__ = "subject_types"
    type_id = db.Column(db.Integer, primary_key=True)
    type_name = db.Column(db.String(64), nullable=False)
    description = db.Column(db.String(255))


class Division(db.Model):
    __tablename__ = "divisions"
    division_id = db.Column(db.Integer, primary_key=True)
    program_id_fk = db.Column(db.Integer, db.ForeignKey("programs.program_id"), nullable=False)
    semester = db.Column(db.Integer, nullable=False)
    division_code = db.Column(db.String(10), nullable=False)  # A, B, C...
    capacity = db.Column(db.Integer, default=60)


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
    password_hash = db.Column(db.String(256))
    role = db.Column(db.String(32), default="student")  # admin, principal, faculty, student, clerk
    is_active = db.Column(db.Boolean, default=True)

    def get_id(self):
        return str(self.user_id)



class Faculty(db.Model):
    __tablename__ = "faculty"
    faculty_id = db.Column(db.Integer, primary_key=True)
    user_id_fk = db.Column(db.Integer, db.ForeignKey("users.user_id"))
    program_id_fk = db.Column(db.Integer, db.ForeignKey("programs.program_id"))
    full_name = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(128))
    designation = db.Column(db.String(64))
    department = db.Column(db.String(64))
    
    # Extra profile fields
    emp_id = db.Column(db.String(32))
    date_of_joining = db.Column(db.Date)
    highest_qualification = db.Column(db.String(64))
    experience_years = db.Column(db.Float)
    specialization = db.Column(db.String(255))
    extra_data = db.Column(db.Text)  # JSON store for flexible fields


class Student(db.Model):
    __tablename__ = "students"
    enrollment_no = db.Column(db.String(32), primary_key=True, nullable=False)
    user_id_fk = db.Column(db.Integer, db.ForeignKey("users.user_id"))
    program_id_fk = db.Column(db.Integer, db.ForeignKey("programs.program_id"), nullable=False)
    division_id_fk = db.Column(db.Integer, db.ForeignKey("divisions.division_id"))
    
    first_name = db.Column("student_name", db.String(64))
    last_name = db.Column("surname", db.String(64))
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

    @property
    def full_name(self):
        return f"{self.first_name or ''} {self.last_name or ''}".strip()



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
    medium_tag = db.Column(db.String(32))
    academic_year = db.Column(db.String(16), nullable=False)
    faculty_user_id_fk = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint(
            "program_id_fk",
            "semester",
            "medium_tag",
            "academic_year",
            "faculty_user_id_fk",
            name="uq_semester_coordinator_scope_faculty",
        ),
    )


class Attendance(db.Model):
    __tablename__ = "attendance"
    attendance_id = db.Column(db.Integer, primary_key=True)
    student_id_fk = db.Column(db.String(32), db.ForeignKey("students.enrollment_no"))
    subject_id_fk = db.Column(db.Integer, db.ForeignKey("subjects.subject_id"))
    division_id_fk = db.Column(db.Integer, db.ForeignKey("divisions.division_id"))
    date_marked = db.Column(db.Date, default=datetime.utcnow)
    status = db.Column(db.String(2), default="P")  # P/A/L
    semester = db.Column(db.Integer)
    # Lecture period number (1-6) for day-wise schedule; optional for legacy rows
    period_no = db.Column(db.Integer)


class Grade(db.Model):
    __tablename__ = "grades"
    grade_id = db.Column(db.Integer, primary_key=True)
    student_id_fk = db.Column(db.String(32), db.ForeignKey("students.enrollment_no"))
    subject_id_fk = db.Column(db.Integer, db.ForeignKey("subjects.subject_id"))
    division_id_fk = db.Column(db.Integer, db.ForeignKey("divisions.division_id"))
    theory_marks = db.Column(db.Float, default=0.0)
    practical_marks = db.Column(db.Float, default=0.0)
    gpa_for_subject = db.Column(db.Float, default=0.0)


class StudentCreditLog(db.Model):
    __tablename__ = "student_credit_log"
    log_id = db.Column(db.Integer, primary_key=True)
    student_id_fk = db.Column(db.String(32), db.ForeignKey("students.enrollment_no"))
    subject_id_fk = db.Column(db.Integer, db.ForeignKey("subjects.subject_id"))
    credits_earned = db.Column(db.Integer, default=0)
    date_awarded = db.Column(db.Date)
    is_exit_eligible = db.Column(db.Boolean, default=False)


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
    credit_rules_json = db.Column(db.Text)  # Stores credit-based rules: [{credit:1, max_total:15, ...}]
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint(
            "program_id_fk",
            "semester",
            "medium_tag",
            "academic_year",
            name="uq_exam_scheme_scope",
        ),
    )


class ExamMark(db.Model):
    __tablename__ = "exam_marks"
    exam_mark_id = db.Column(db.Integer, primary_key=True)
    scheme_id_fk = db.Column(db.Integer, db.ForeignKey("exam_schemes.scheme_id"), nullable=False)
    student_id_fk = db.Column(db.String(32), db.ForeignKey("students.enrollment_no"), nullable=False)
    subject_id_fk = db.Column(db.Integer, db.ForeignKey("subjects.subject_id"), nullable=False)
    division_id_fk = db.Column(db.Integer)
    
    semester = db.Column(db.Integer)
    academic_year = db.Column(db.String(16))
    attempt_no = db.Column(db.Integer, default=1)
    
    internal_marks = db.Column(db.Float)
    external_marks = db.Column(db.Float)
    total_marks = db.Column(db.Float)
    
    grade_letter = db.Column(db.String(4))
    grade_point = db.Column(db.Float)
    
    is_absent = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def grade(self):
        return self.grade_letter
        
    @grade.setter
    def grade(self, value):
        self.grade_letter = value

    __table_args__ = (
        db.UniqueConstraint(
            "scheme_id_fk",
            "student_id_fk",
            "subject_id_fk",
            name="uq_exam_mark_entry",
        ),
    )


class StudentSemesterResult(db.Model):
    __tablename__ = "student_semester_results"
    result_id = db.Column(db.Integer, primary_key=True)
    scheme_id_fk = db.Column(db.Integer, db.ForeignKey("exam_schemes.scheme_id"), nullable=False)
    student_id_fk = db.Column(db.String(32), db.ForeignKey("students.enrollment_no"), nullable=False)
    sgpa = db.Column(db.Float)
    cgpa = db.Column(db.Float)
    total_credits_earned = db.Column(db.Integer)
    result_status = db.Column(db.String(16))  # Pass, Fail, ATKT
    calculated_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint(
            "scheme_id_fk",
            "student_id_fk",
            name="uq_student_semester_result",
        ),
    )


class FeesRecord(db.Model):
    __tablename__ = "fees_records"
    fee_id = db.Column(db.Integer, primary_key=True)
    student_id_fk = db.Column(db.String(32), db.ForeignKey("students.enrollment_no"), nullable=False)
    amount_due = db.Column(db.Float, default=0.0)
    amount_paid = db.Column(db.Float, default=0.0)
    date_paid = db.Column(db.Date, default=datetime.utcnow)
    semester = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class FeeStructure(db.Model):
    __tablename__ = "fee_structures"
    structure_id = db.Column(db.Integer, primary_key=True)
    program_id_fk = db.Column(db.Integer, db.ForeignKey("programs.program_id"), nullable=False)
    # If the Excel provides semester-wise components, store semester; else leave as NULL
    semester = db.Column(db.Integer)
    # Optional medium tag: empty/NULL means Common; else e.g., 'English', 'Gujarati'
    medium_tag = db.Column(db.String(32))
    component_name = db.Column(db.String(128), nullable=False)
    amount = db.Column(db.Float, default=0.0)
    due_date = db.Column(db.Date)
    is_active = db.Column(db.Boolean, default=True)
    # Clerk confirmation: when true, this component is frozen and used in receipt
    is_frozen = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class FeePayment(db.Model):
    __tablename__ = "fee_payments"
    payment_id = db.Column(db.Integer, primary_key=True)
    enrollment_no = db.Column(db.String(32), db.ForeignKey("students.enrollment_no"), nullable=False)
    program_id_fk = db.Column(db.Integer, db.ForeignKey("programs.program_id"), nullable=False)
    semester = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_date = db.Column(db.Date, default=datetime.utcnow)
    payment_mode = db.Column(db.String(32))  # Cash, UPI, Cheque
    reference_no = db.Column(db.String(64))  # Transaction ID / Cheque No
    status = db.Column(db.String(32), default="submitted")  # submitted, verified, rejected
    receipt_no = db.Column(db.String(64), unique=True)
    remarks = db.Column(db.Text)
    # Who entered this payment?
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"))
    # When verified, snapshot verification time
    verified_at = db.Column(db.DateTime)
    verified_by_user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ProgramBankDetails(db.Model):
    __tablename__ = "program_bank_details"
    bank_id = db.Column(db.Integer, primary_key=True)
    program_id_fk = db.Column(db.Integer, db.ForeignKey("programs.program_id"), nullable=False, unique=True)
    # Required bank information
    bank_name = db.Column(db.String(128), nullable=False)
    account_name = db.Column(db.String(128), nullable=False)
    account_number = db.Column(db.String(64), nullable=False)
    ifsc = db.Column(db.String(32), nullable=False)
    branch = db.Column(db.String(128), nullable=False)
    # Optional UPI and display fields
    upi_vpa = db.Column(db.String(128))
    payee_display = db.Column(db.String(128))
    qr_image_path = db.Column(db.String(255))
    # Optional tax identity
    gstin = db.Column(db.String(64))
    pan = db.Column(db.String(16))
    # Administrative flags
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    program = db.relationship("Program", backref="bank_details", lazy=True, uselist=False)


class StudentSubjectEnrollment(db.Model):
    __tablename__ = "student_subject_enrollments"
    enrollment_id = db.Column(db.Integer, primary_key=True)
    student_id_fk = db.Column(db.String(32), db.ForeignKey("students.enrollment_no"), nullable=False)
    subject_id_fk = db.Column(db.Integer, db.ForeignKey("subjects.subject_id"), nullable=False)
    semester = db.Column(db.Integer)
    academic_year = db.Column(db.String(16))
    division_id_fk = db.Column(db.Integer, db.ForeignKey("divisions.division_id"))  # Optional snapshot
    is_active = db.Column(db.Boolean, default=True)
    source = db.Column(db.String(32))  # e.g., 'bulk_csv', 'manual', 'offering_default'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint(
            "student_id_fk",
            "subject_id_fk",
            "academic_year",
            name="uq_student_subject_enrollment_year",
        ),
    )


class Notification(db.Model):
    __tablename__ = "notifications"
    notification_id = db.Column(db.Integer, primary_key=True)
    user_id_fk = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    title = db.Column(db.String(128))
    message = db.Column(db.String(255))
    link = db.Column(db.String(255))
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class SubjectMaterial(db.Model):
    __tablename__ = "subject_materials"
    material_id = db.Column(db.Integer, primary_key=True)
    subject_id_fk = db.Column(db.Integer, db.ForeignKey("subjects.subject_id"), nullable=False)
    faculty_id_fk = db.Column(db.Integer, db.ForeignKey("users.user_id"))
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    kind = db.Column(db.String(16), nullable=False)  # file | link | embed
    file_path = db.Column(db.String(255))
    external_url = db.Column(db.String(255))
    tags = db.Column(db.String(255))
    academic_year = db.Column(db.String(16))
    is_published = db.Column(db.Boolean, default=False)
    is_flagged = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)


class SubjectMaterialLog(db.Model):
    __tablename__ = "subject_material_logs"
    log_id = db.Column(db.Integer, primary_key=True)
    material_id_fk = db.Column(db.Integer, db.ForeignKey("subject_materials.material_id"), nullable=False)
    action = db.Column(db.String(32), nullable=False)  # created | updated | deleted | flagged | unflagged | published | unpublished
    actor_user_id_fk = db.Column(db.Integer, db.ForeignKey("users.user_id"))
    actor_role = db.Column(db.String(32))
    meta_json = db.Column(db.Text)
    at = db.Column(db.DateTime, default=datetime.utcnow)


class Announcement(db.Model):
    __tablename__ = "announcements"
    announcement_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128), nullable=False)
    message = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(16), default="info")  # info, warning, danger, success
    is_active = db.Column(db.Boolean, default=True)
    
    # Targeting
    program_id_fk = db.Column(db.Integer, db.ForeignKey("programs.program_id")) # Null = All Programs
    
    start_at = db.Column(db.DateTime, default=datetime.utcnow)
    end_at = db.Column(db.DateTime)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Who created it?
    actor_user_id_fk = db.Column(db.Integer, db.ForeignKey("users.user_id"))


class AnnouncementRevision(db.Model):
    __tablename__ = "announcement_revisions"
    revision_id = db.Column(db.Integer, primary_key=True)
    announcement_id_fk = db.Column(db.Integer, db.ForeignKey("announcements.announcement_id"), nullable=False)
    version = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(128), nullable=False)
    message = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(16))
    is_active = db.Column(db.Boolean, default=True)
    program_id_fk = db.Column(db.Integer)
    start_at = db.Column(db.DateTime)
    end_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class MaterialRevision(db.Model):
    __tablename__ = "material_revisions"
    revision_id = db.Column(db.Integer, primary_key=True)
    material_id_fk = db.Column(db.Integer, db.ForeignKey("subject_materials.material_id"), nullable=False)
    version = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    kind = db.Column(db.String(16), nullable=False)
    file_path = db.Column(db.String(255))
    external_url = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    actor_user_id_fk = db.Column(db.Integer, db.ForeignKey("users.user_id"))


class AnnouncementAudience(db.Model):
    __tablename__ = "announcement_audience"
    audience_id = db.Column(db.Integer, primary_key=True)
    announcement_id_fk = db.Column(db.Integer, db.ForeignKey("announcements.announcement_id"), nullable=False)
    role = db.Column(db.String(32), nullable=False)  # lowercase: student, faculty, principal, clerk, admin


class AnnouncementDismissal(db.Model):
    __tablename__ = "announcement_dismissals"
    dismissal_id = db.Column(db.Integer, primary_key=True)
    announcement_id_fk = db.Column(db.Integer, db.ForeignKey("announcements.announcement_id"), nullable=False)
    user_id_fk = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    dismissed_at = db.Column(db.DateTime, default=datetime.utcnow)


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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    extra_json = db.Column(db.Text)


class AnnouncementRecipient(db.Model):
    __tablename__ = "announcement_recipients"
    recipient_id = db.Column(db.Integer, primary_key=True)
    announcement_id_fk = db.Column(db.Integer, db.ForeignKey("announcements.announcement_id"), nullable=False)
    student_id_fk = db.Column(db.String(32), db.ForeignKey("students.enrollment_no"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class PasswordChangeLog(db.Model):
    __tablename__ = "password_change_log"
    log_id = db.Column(db.Integer, primary_key=True)
    user_id_fk = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)  # whose password changed
    changed_by_user_id_fk = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)  # actor
    changed_at = db.Column(db.DateTime, default=datetime.utcnow)
    method = db.Column(db.String(32))  # self, clerk, admin, principal


class TimetableSettings(db.Model):
    __tablename__ = "timetable_settings"
    setting_id = db.Column(db.Integer, primary_key=True)
    program_id_fk = db.Column(db.Integer, db.ForeignKey("programs.program_id"), nullable=False)
    academic_year = db.Column(db.String(16), nullable=False)
    # Configuration
    start_time = db.Column(db.Time, default=datetime.strptime("08:00", "%H:%M").time())
    slot_duration_mins = db.Column(db.Integer, default=55)
    break_after_period = db.Column(db.Integer, default=3)
    break_duration_mins = db.Column(db.Integer, default=25)
    slots_per_day = db.Column(db.Integer, default=6)
    
    __table_args__ = (
        db.UniqueConstraint("program_id_fk", "academic_year", name="uq_timetable_settings"),
    )


class TimetableSlot(db.Model):
    __tablename__ = "timetable_slots"
    slot_id = db.Column(db.Integer, primary_key=True)
    division_id_fk = db.Column(db.Integer, db.ForeignKey("divisions.division_id"), nullable=False)
    subject_id_fk = db.Column(db.Integer, db.ForeignKey("subjects.subject_id"), nullable=False)
    day_of_week = db.Column(db.String(10), nullable=False) # Mon, Tue, Wed...
    period_no = db.Column(db.Integer, nullable=False)
    slot_type = db.Column(db.String(16), default="Theory") # Theory, Practical
    room_no = db.Column(db.String(32))
    
    __table_args__ = (
        db.UniqueConstraint("division_id_fk", "day_of_week", "period_no", name="uq_timetable_slot_div_day_period"),
    )
