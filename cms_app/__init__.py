import os
import secrets
import time
import uuid
import sqlite3
from flask import Flask, session, request, url_for, flash, redirect, current_app, render_template, g
from flask_login import LoginManager, current_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy import inspect
from sqlalchemy import select, or_
from werkzeug.exceptions import RequestEntityTooLarge
from functools import wraps
from flask_migrate import Migrate
from datetime import timedelta
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache
from werkzeug.exceptions import HTTPException
from flask_limiter.errors import RateLimitExceeded

# Global extensions
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
def _rate_key():
    try:
        ip = (request.headers.get("X-Forwarded-For") or request.remote_addr or "local")
        token = (session.get("rlid") or "")
        path = (getattr(request, "path", "/") or "/")
        return f"{ip}|{token}|{path}"
    except Exception:
        return "local"

limiter = Limiter(key_func=_rate_key)
cache = Cache()

_sqlite_pragmas_registered = False


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")
    
    # Session Timeout: 10 minutes
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=10)
    
    REDIS_URL = os.environ.get("REDIS_URL")
    if REDIS_URL:
        app.config["CACHE_TYPE"] = "RedisCache"
        app.config["CACHE_REDIS_URL"] = REDIS_URL
        app.config["RATELIMIT_STORAGE_URI"] = REDIS_URL
    else:
        app.config["CACHE_TYPE"] = "SimpleCache"
    try:
        app.jinja_env.globals.setdefault("t", lambda s: s)
        app.jinja_env.globals.setdefault("lang_code", "en")
    except Exception:
        pass
    # Feature flags
    app.config["FEES_DISABLED"] = False  # Enable Fees module visibility
    app.config["ROLLS_CONTINUOUS_PER_PROGRAM_SEM"] = (os.environ.get("ROLLS_CONTINUOUS_PER_PROGRAM_SEM", "false").lower() == "true")
    # Global upload cap (can be overridden via env)
    app.config["MAX_CONTENT_LENGTH"] = int(os.environ.get("MAX_CONTENT_LENGTH", str(32 * 1024 * 1024)))
    # CSRF token TTL (seconds)
    app.config["CSRF_TOKEN_TTL"] = int(os.environ.get("CSRF_TOKEN_TTL", "7200"))
    # UI hints toggle: set INFO_HINTS_ENABLED=false to hide soft guidance text globally
    app.config["INFO_HINTS_ENABLED"] = (os.environ.get("INFO_HINTS_ENABLED", "false").lower() == "true")

    # Mail configuration (optional; for password reset emails)
    app.config["MAIL_HOST"] = os.environ.get("MAIL_HOST")
    app.config["MAIL_PORT"] = int(os.environ.get("MAIL_PORT", "587"))
    app.config["MAIL_USER"] = os.environ.get("MAIL_USER")
    app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD")
    app.config["MAIL_FROM"] = os.environ.get("MAIL_FROM", os.environ.get("MAIL_USER", "noreply@example.com"))
    app.config["MAIL_USE_TLS"] = (os.environ.get("MAIL_USE_TLS", "true").lower() == "true")
    app.config["MAIL_USE_SSL"] = (os.environ.get("MAIL_USE_SSL", "false").lower() == "true")

    # Database configuration: use DATABASE_URL if provided, else sqlite file
    database_url = os.environ.get("DATABASE_URL")
    if database_url and database_url.startswith("postgres://"):
        database_url = "postgresql://" + database_url[len("postgres://"):]
    if database_url and database_url.startswith("postgresql"):
        try:
            import psycopg2  # noqa: F401
        except Exception:
            database_url = None
    if not database_url:
        db_path = os.path.join(os.path.dirname(__file__), "..", "cms.db")
        database_url = f"sqlite:///{os.path.abspath(db_path)}"

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    if (database_url or "").startswith("sqlite:"):
        app.config.setdefault(
            "SQLALCHEMY_ENGINE_OPTIONS",
            {
                "connect_args": {"timeout": 30, "check_same_thread": False},
                "pool_pre_ping": True,
            },
        )
        global _sqlite_pragmas_registered
        if not _sqlite_pragmas_registered:
            @event.listens_for(Engine, "connect")
            def _set_sqlite_pragmas(dbapi_connection, _):
                if not isinstance(dbapi_connection, sqlite3.Connection):
                    return
                try:
                    cur = dbapi_connection.cursor()
                    try:
                        cur.execute("PRAGMA journal_mode=WAL;")
                    except Exception:
                        pass
                    try:
                        cur.execute("PRAGMA synchronous=NORMAL;")
                    except Exception:
                        pass
                    try:
                        cur.execute("PRAGMA busy_timeout=5000;")
                    except Exception:
                        pass
                    cur.close()
                except Exception:
                    pass
            _sqlite_pragmas_registered = True

    app.config.setdefault("RATELIMIT_STORAGE_URI", "memory://")
    db.init_app(app)
    migrate.init_app(app, db)
    try:
        limiter.init_app(app)
    except Exception:
        pass
    try:
        cache.init_app(app)
        # Fix for Flask-Caching AttributeError: 'Cache' object has no attribute 'app'
        if not hasattr(cache, "app"):
            cache.app = app
    except Exception:
        pass
    # Auth: Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = "main.login"

    # Import models so they are registered with SQLAlchemy
    from . import models  # noqa: F401

    def _slugify_program(name: str) -> str:
        try:
            s = (name or "").strip().lower()
            # Normalize common program names
            s = s.replace("b.com", "bcom").replace("b.com.", "bcom")
            s = s.replace("(", " ").replace(")", " ")
            # Remove non-alphanumerics, collapse spaces, join with hyphens
            import re
            s = re.sub(r"[^a-z0-9\s]", "", s)
            s = re.sub(r"\s+", " ", s).strip()
            s = s.replace(" ", "-")
            return s
        except Exception:
            return ""

    def _cached_value(key, loader, timeout=60):
        try:
            cached = cache.get(key)
        except Exception:
            cached = None
        if cached is not None:
            return cached
        value = loader()
        try:
            cache.set(key, value, timeout=timeout)
        except Exception:
            pass
        return value

    def _maintenance_mode_enabled():
        from .models import SystemConfig

        def _load():
            try:
                maint = db.session.get(SystemConfig, "maintenance_mode")
                return 1 if (maint and (maint.config_value or "").strip().lower() == "true") else 0
            except Exception:
                return 0

        return bool(_cached_value("__maintenance_mode__", _load, timeout=15))

    def _trust_access_snapshot(trust_id):
        try:
            trust_id = int(trust_id)
        except Exception:
            return {}

        def _load():
            try:
                from .models import Trust

                trust = db.session.get(Trust, trust_id)
                if not trust:
                    return {}
                end_at = getattr(trust, "subscription_end_at", None)
                return {
                    "is_active": False if getattr(trust, "is_active", True) is False else True,
                    "subscription_end_at": end_at.isoformat() if end_at else None,
                    "subscription_grace_days": int(getattr(trust, "subscription_grace_days", 0) or 0),
                }
            except Exception:
                return {}

        return _cached_value(f"trust_access_{trust_id}", _load, timeout=30)

    def _program_theme_context(program_id):
        try:
            program_id = int(program_id)
        except Exception:
            return {}

        def _load():
            try:
                from .models import Program

                program = db.session.get(Program, program_id)
                if not program:
                    return {}
                return {
                    "program_name": program.program_name,
                    "program_slug": _slugify_program(program.program_name),
                }
            except Exception:
                return {}

        return _cached_value(f"ui_program_theme_{program_id}", _load, timeout=300)

    def _user_identity_context(user_id, role, fallback_username):
        try:
            user_id = int(user_id)
        except Exception:
            user_id = None

        role_key = (role or "").strip().lower()
        fallback_name = (fallback_username or "").strip() or "User"

        def _load():
            photo_url = None
            display_name = fallback_name
            try:
                if role_key == "faculty" and user_id:
                    from .models import Faculty

                    row = db.session.execute(
                        select(Faculty.photo_url, Faculty.full_name).filter_by(user_id_fk=user_id)
                    ).first()
                    if row:
                        photo_url = row.photo_url or None
                        display_name = (row.full_name or "").strip() or display_name
                elif role_key == "student" and user_id:
                    from .models import Student

                    row = db.session.execute(
                        select(Student.photo_url, Student.surname, Student.student_name).filter_by(user_id_fk=user_id)
                    ).first()
                    if row:
                        photo_url = row.photo_url or None
                        display_name = (
                            f"{(row.surname or '').strip()} {(row.student_name or '').strip()}".strip() or display_name
                        )
            except Exception:
                pass
            return {
                "ctx_user_photo_url": photo_url,
                "ctx_user_display_name": display_name,
            }

        if role_key in {"faculty", "student"} and user_id:
            return _cached_value(f"user_identity_{role_key}_{user_id}", _load, timeout=120)
        return _load()

    def _active_system_messages_context(role, effective_trust_id, is_super_admin):
        role_key = (role or "").strip().lower() or "guest"
        trust_key = "global"
        if effective_trust_id is not None:
            try:
                trust_key = int(effective_trust_id)
            except Exception:
                trust_key = "global"
        cache_key = f"layout_system_messages_{'super' if is_super_admin else role_key}_{trust_key}"

        def _load():
            from datetime import datetime, timezone
            from .models import SystemMessage

            now = datetime.now(timezone.utc)
            query = (
                select(
                    SystemMessage.message_id,
                    SystemMessage.title,
                    SystemMessage.content,
                    SystemMessage.message_type,
                    SystemMessage.target_role,
                )
                .where(
                    SystemMessage.is_active.is_(True),
                    or_(SystemMessage.start_date == None, SystemMessage.start_date <= now),
                    or_(SystemMessage.end_date == None, SystemMessage.end_date >= now),
                )
                .order_by(SystemMessage.start_date.desc(), SystemMessage.message_id.desc())
            )
            if not is_super_admin:
                if effective_trust_id is not None:
                    query = query.where(
                        or_(SystemMessage.target_trust_id == None, SystemMessage.target_trust_id == int(effective_trust_id))
                    )
                else:
                    query = query.where(SystemMessage.target_trust_id == None)
                if role_key == "guest":
                    query = query.where(SystemMessage.target_role == "all")
                else:
                    query = query.where(or_(SystemMessage.target_role == "all", SystemMessage.target_role == role_key))

            rows = db.session.execute(query).all()
            return [
                {
                    "message_id": row.message_id,
                    "title": row.title,
                    "content": row.content,
                    "message_type": row.message_type or "info",
                    "target_role": (row.target_role or "all").strip().lower(),
                }
                for row in rows
            ]

        return _cached_value(cache_key, _load, timeout=30)

    def _cache_backend_status():
        if app.config.get("CACHE_TYPE") != "RedisCache":
            return False
        state = app.extensions.setdefault("cache_health_state", {})
        now_ts = time.time()
        checked_at = float(state.get("checked_at") or 0)
        if now_ts - checked_at < 30:
            return bool(state.get("active", False))
        active = False
        try:
            cache.set("__redis_health_probe__", "ok", timeout=60)
            active = (cache.get("__redis_health_probe__") == "ok")
        except Exception:
            active = False
        state["checked_at"] = now_ts
        state["active"] = active
        return active

    @app.before_request
    def check_maintenance_mode():
        # Allow static files (CSS, JS, images)
        if request.endpoint and 'static' in request.endpoint:
            return
            
        # Allow login/logout endpoints so Super Admin can access
        if request.endpoint in ['main.login', 'main.logout']:
            return

        try:
            if _maintenance_mode_enabled():
                # If user is logged in
                if current_user.is_authenticated:
                    # If super admin, allow access
                    if getattr(current_user, 'is_super_admin', False):
                        return
                
                # Otherwise, return 503 Maintenance
                return render_template('maintenance.html'), 503
        except Exception:
            # If DB error or table missing, fail open (allow access)
            pass

    @app.before_request
    def enforce_trust_access():
        if request.endpoint and 'static' in request.endpoint:
            return
        if request.endpoint in ['main.login', 'main.logout']:
            return
        try:
            if request.blueprint == 'super_admin':
                return
        except Exception:
            pass
        if not current_user.is_authenticated:
            return
        if getattr(current_user, 'is_super_admin', False):
            return
        trust_id = getattr(current_user, 'trust_id_fk', None)
        if not trust_id:
            return
        try:
            from datetime import datetime, timedelta, timezone
            snapshot = _trust_access_snapshot(trust_id)
            if not snapshot:
                return
            if snapshot.get("is_active") is False:
                from .models import Trust

                trust = db.session.get(Trust, int(trust_id))
                if trust:
                    return render_template('trust_suspended.html', trust=trust), 403
                return
            end_at = None
            end_at_raw = snapshot.get("subscription_end_at")
            if end_at_raw:
                try:
                    end_at = datetime.fromisoformat(end_at_raw)
                    if getattr(end_at, "tzinfo", None) is not None:
                        end_at = end_at.astimezone(timezone.utc).replace(tzinfo=None)
                except Exception:
                    end_at = None
            if end_at:
                now = datetime.now(timezone.utc).replace(tzinfo=None)
                try:
                    grace_days = int(snapshot.get("subscription_grace_days") or 0)
                except Exception:
                    grace_days = 0
                if now > (end_at + timedelta(days=grace_days)):
                    from .models import Trust

                    trust = db.session.get(Trust, int(trust_id))
                    return render_template('trust_expired.html', trust=trust, end_at=end_at, grace_days=grace_days), 403
        except Exception:
            return

    @app.context_processor
    def inject_ui_flags():
        cached_ctx = getattr(g, "_ui_flags_ctx", None)
        if cached_ctx is not None:
            return cached_ctx

        # Base UI flags
        ctx = {
            "info_hints_enabled": app.config.get("INFO_HINTS_ENABLED", False),
            "fees_disabled": app.config.get("FEES_DISABLED", False),
            "system_messages": [],
        }

        try:
            is_authenticated = bool(getattr(current_user, "is_authenticated", False))
            is_super_admin = bool(getattr(current_user, "is_super_admin", False)) if is_authenticated else False
            role = (getattr(current_user, "role", "") or "").strip().lower() if is_authenticated else ""
            effective_trust_id = None
            if is_authenticated and not is_super_admin:
                effective_trust_id = getattr(current_user, "trust_id_fk", None)
            ctx["system_messages"] = _active_system_messages_context(role, effective_trust_id, is_super_admin)
        except Exception:
            pass

        try:
            if getattr(current_user, "is_authenticated", False):
                prog_id = getattr(current_user, "program_id_fk", None)
                if prog_id:
                    ctx.update(_program_theme_context(prog_id))
        except Exception:
            pass

        try:
            if getattr(current_user, "is_authenticated", False):
                ctx.update(
                    _user_identity_context(
                        getattr(current_user, "user_id", None),
                        getattr(current_user, "role", ""),
                        getattr(current_user, "username", ""),
                    )
                )
        except Exception:
            pass

        ctx["redis_active"] = _cache_backend_status()
        g._ui_flags_ctx = ctx
        return ctx

    @app.context_processor
    def inject_csrf_token():
        token = session.get("csrf_token")
        issued_at = session.get("csrf_token_issued_at")
        ttl = app.config.get("CSRF_TOKEN_TTL", 7200)
        # Regenerate token if missing or expired
        now = int(time.time())
        if (not token) or (not issued_at) or (ttl > 0 and (now - int(issued_at)) > ttl):
            token = secrets.token_urlsafe(32)
            session["csrf_token"] = token
            session["csrf_token_issued_at"] = now
        class _CsrfToken(str):
            def __call__(self):
                return str(self)
            def __html__(self):
                return str(self)
        tok = _CsrfToken(token)
        return {"csrf_token": tok, "csrf_token_value": token}

    @app.context_processor
    def inject_breadcrumbs():
        from werkzeug.routing import BuildError

        items = []
        try:
            endpoint = (request.endpoint or "").strip()
        except Exception:
            endpoint = ""
        try:
            path = (request.path or "").strip()
        except Exception:
            path = ""

        def _safe_url(ep, **kwargs):
            try:
                return url_for(ep, **kwargs)
            except BuildError:
                return None
            except Exception:
                return None

        mapping = {
            "main.dashboard": ("Dashboard", "main.dashboard"),
            "main.module_admin": ("Admin Module", "main.module_admin"),
            "main.student_lifecycle": ("Student Lifecycle", "main.student_lifecycle"),
            "main.staff_lifecycle": ("Staff Lifecycle", "main.staff_lifecycle"),
            "main.students_semester_promotion": ("Semester Promotion", "main.students_semester_promotion"),
            "main.admin_import_logs": ("Import Logs", "main.admin_import_logs"),
            "main.admin_logbook": ("LogBook", "main.admin_logbook"),
            "main.admin_workflow_new_academic_year": ("New Academic Year Setup", "main.admin_workflow_new_academic_year"),
            "main.admin_system_status": ("System Status", "main.admin_system_status"),
            "main.students": ("Students", "main.students"),
            "main.subjects_list": ("Subjects", "main.subjects_list"),
            "main.programs_list": ("Programs", "main.programs_list"),
            "main.reports_hub": ("Reports", "main.reports_hub"),
            "main.documents_index": ("Documents", "main.documents_index"),
            "main.attendance_mark": ("Attendance", "main.attendance_mark"),
            "main.module_attendance": ("Attendance", "main.module_attendance"),
            "main.module_students": ("Students", "main.module_students"),
            "main.module_subjects": ("Subjects", "main.module_subjects"),
            "main.module_faculty": ("Staff", "main.module_faculty"),
            "main.module_fees": ("Fees Module", "main.module_fees"),
            "main.module_divisions": ("Divisions", "main.module_divisions"),
            "main.module_analytics": ("Analytics", "main.module_analytics"),
        }

        label = None
        ep = None
        if endpoint in mapping:
            label, ep = mapping[endpoint]

        if ep:
            if endpoint not in ("main.module_admin",) and endpoint.startswith("main.") and endpoint not in ("main.dashboard",):
                if endpoint in ("main.student_lifecycle", "main.staff_lifecycle", "main.students_semester_promotion", "main.admin_import_logs", "main.admin_logbook", "main.admin_workflow_new_academic_year", "main.admin_system_status"):
                    items.append({"label": "Admin Module", "url": _safe_url("main.module_admin")})
            items.append({"label": label, "url": _safe_url(ep) if endpoint != ep else None})
        elif endpoint:
            nice = endpoint.split(".")[-1].replace("_", " ").strip().title()
            if endpoint.startswith("main.") and (endpoint.startswith("main.admin") or path.startswith("/admin") or path.startswith("/modules/admin")):
                items.append({"label": "Admin Module", "url": _safe_url("main.module_admin")})
            items.append({"label": nice or "Page", "url": None})

        return {"breadcrumb_items": items}

    @app.context_processor
    def inject_command_palette():
        from werkzeug.routing import BuildError

        try:
            from flask_login import current_user
        except Exception:
            current_user = None

        def _safe_url(ep, **kwargs):
            try:
                return url_for(ep, **kwargs)
            except BuildError:
                return None
            except Exception:
                return None

        role = ""
        is_super = False
        if getattr(current_user, "is_authenticated", False):
            role = (getattr(current_user, "role", "") or "").strip().lower()
            is_super = bool(getattr(current_user, "is_super_admin", False))

        actions = []
        if role:
            actions.append({"id": "dashboard", "label": "Dashboard", "hint": "Home", "url": _safe_url("main.dashboard"), "tags": ["home"]})
            actions.append({"id": "admin_module", "label": "Admin Module", "hint": "Tools and workflows", "url": _safe_url("main.module_admin"), "tags": ["admin", "tools"]})
            actions.append({"id": "logbook", "label": "LogBook", "hint": "All logs in one place", "url": _safe_url("main.admin_logbook"), "tags": ["logs", "audit"]})
            actions.append({"id": "student_lifecycle", "label": "Student Lifecycle", "hint": "Archive, alumni, restore, recycle bin", "url": _safe_url("main.student_lifecycle"), "tags": ["students", "archive", "alumni"]})
            actions.append({"id": "staff_lifecycle", "label": "Staff Lifecycle", "hint": "Archive/restore staff", "url": _safe_url("main.staff_lifecycle"), "tags": ["staff", "archive"]})
            actions.append({"id": "semester_promotion", "label": "Semester Promotion", "hint": "Promote students between semesters", "url": _safe_url("main.students_semester_promotion"), "tags": ["students", "promotion"]})
            actions.append({"id": "workflow_new_ay", "label": "New Academic Year Setup", "hint": "Guided yearly rollover", "url": _safe_url("main.admin_workflow_new_academic_year"), "tags": ["workflow", "setup"]})
            actions.append({"id": "students_list", "label": "Students", "hint": "Search and manage students", "url": _safe_url("main.students"), "tags": ["students", "search"]})
            actions.append({"id": "staff_list", "label": "Staff", "hint": "Search staff and accounts", "url": _safe_url("main.faculty_list"), "tags": ["staff", "users"]})
            actions.append({"id": "reports", "label": "Reports", "hint": "Exports and analytics", "url": _safe_url("main.reports_hub"), "tags": ["reports", "export"]})
            actions.append({"id": "documents", "label": "Documents", "hint": "Manuals and PDFs", "url": _safe_url("main.documents_index"), "tags": ["docs"]})

            if role in ("admin", "principal", "clerk"):
                actions.append({"id": "students_import", "label": "Bulk Import Students", "hint": "Upload Excel", "url": _safe_url("main.students_import"), "tags": ["import", "students"]})
            if role in ("admin", "principal"):
                actions.append({"id": "import_logs", "label": "Import Logs", "hint": "Review bulk imports", "url": _safe_url("main.admin_import_logs"), "tags": ["import", "logs"]})

            if is_super:
                actions.append({"id": "super_student_purge", "label": "Student Purge (Super Admin)", "hint": "Danger Zone", "url": _safe_url("super_admin.students_purge"), "tags": ["danger", "purge"]})

        actions = [a for a in actions if a.get("url")]
        return {"command_palette_actions": actions}

    @app.before_request
    def ensure_rate_key():
        try:
            if not session.get("rlid"):
                session["rlid"] = secrets.token_urlsafe(16)
        except Exception:
            pass

    @app.context_processor
    def inject_i18n():
        # Determine language: query param overrides session, then user preference
        try:
            ql = (request.args.get("lang") or "").strip().lower()
            if ql in {"en", "gu"}:
                session["lang"] = ql
        except Exception:
            pass
        try:
            from flask_login import current_user
            if not session.get("lang") and getattr(current_user, "is_authenticated", False):
                pref = (getattr(current_user, "preferred_lang", None) or "").strip().lower()
                if pref in {"en", "gu"}:
                    session["lang"] = pref
        except Exception:
            pass
        lang = (session.get("lang") or "en").strip().lower()
        tr = {
            "gu": {
                "Dashboard": "ડેશબોર્ડ",
                "Announcements": "જાહેરખબરો",
                "Attendance": "હાજરી",
                "Students": "વિદ્યાર્થીઓ",
                "Subjects": "વિષયો",
                "Materials": "સામગ્રી",
                "Exams": "પરીક્ષાઓ",
                "Staff": "સ્ટાફ",
                "Divisions": "વિભાગો",
                "Fees Module": "ફી મોડ્યુલ",
                "Programs": "પ્રોગ્રામ્સ",
                "Admin Module": "એડમિન મોડ્યુલ",
                "Manage Accounts": "ખાતાઓ મેનેજ કરો",
                "Notice Board": "નોટિસ બોર્ડ",
                "Archive": "આર્કાઇવ",
                "Login": "લૉગિન",
                "Logout": "લૉગઆઉટ",
                "Divisions": "વિભાગો",
                "Per Page": "દર પેજ",
                "Export CSV": "CSV નિકાસ",
                "Reports": "રિપોર્ટ્સ",
                "Program": "પ્રોગ્રામ",
                "Semester": "સેમેસ્ટર",
                "Medium": "માધ્યમ",
                "Refresh": "રિફ્રેશ",
                "Export Fees CSV": "ફી CSV નિકાસ",
                "Enrollment Summary": "એનરોલમેન્ટ સારાંશ",
                "Fees Summary": "ફી સારાંશ",
                "Status": "સ્થિતિ",
                "Count": "ગણતરી",
                "Attendance Compliance": "હાજરી અનુરૂપતા",
                "Subject": "વિષય",
                "Present": "હાજર",
                "Total": "કુલ",
                "Rate %": "દર %",
                "Materials Publishing": "સામગ્રી પ્રકાશન",
                "Subject ID": "વિષય ID",
                "Published": "પ્રકાશિત",
                "Flagged": "ફ્લેગ્ડ",
                "Division Capacity vs Enrolled": "વિભાગ ક્ષમતા સામે નોંધાયા",
                "Division": "વિભાગ",
                "Capacity": "ક્ષમતા",
                "Enrolled": "નોંધાયા",
                "Utilization %": "ઉપયોગ %",
                "Medium Split": "માધ્યમ વિભાજન",
                "Show all": "બધું બતાવો",
                "From": "થી",
                "To": "સુધી",
                "Apply": "અપ્લાય",
                "Latest 10 announcements by default": "મૂળભૂત રીતે તાજેતરના 10 જાહેરખબરો",
                "Attachments:": "જોડાણ:",
                "Posted:": "પોસ્ટેડ:",
                "By:": "દ્વારા:",
                "Program:": "પ્રોગ્રામ:",
                "All": "બધા",
                "Start:": "શરૂઆત:",
                "End:": "અંત:",
                "Prev": "પાછળ",
                "Next": "આગળ",
                "Page": "પેજ",
                "of": "નો",
                "View Archive": "આર્કાઇવ જુઓ",
                "No announcements to show.": "બતાવવા માટે કોઈ જાહેરખબર નથી.",
                "The Group of Parekh Colleges - Mahuva": "દ ગ્રુપ ઓફ પરેખ કોલેજેસ - મહુવા",
                "Managed by Shri Balvant Parekh Education Trust (SBPET)": "શ્રી બલવંત પરેખ એજ્યુકેશન ટ્રસ્ટ (SBPET) દ્વારા સંચાલિત",
                "Notices": "નોટિસ",
                "Manage": "મેનેજ",
                "Dismiss": "ડિસ્મિસ",
                "Academic Year:": "શૈક્ષણિક વર્ષ:",
                "Role-Based Infographics": "ભૂમિકા આધારિત ઇન્ફોગ્રાફિક્સ",
                "Students by Program": "પ્રોગ્રામ મુજબ વિદ્યાર્થીઓ",
                "Fees Collection by Program": "પ્રોગ્રામ મુજબ ફી વસૂલી",
                "Staff Count by Program": "પ્રોગ્રામ મુજબ સ્ટાફ ગણતરી",
                "Annual Income vs Expenses": "વાર્ષિક આવક સામે ખર્ચ",
                "Students by Semester (My Program)": "સેમેસ્ટર મુજબ વિદ્યાર્થીઓ (મારો પ્રોગ્રામ)",
                "Fees Collection by Semester (My Program)": "સેમેસ્ટર મુજબ ફી વસૂલી (મારો પ્રોગ્રામ)",
                "Male/Female Students by Semester": "સેમેસ્ટર મુજબ પુરૂષ/સ્ત્રી વિદ્યાર્થીઓ",
                "Semester Results by Subject (Avg GPA)": "સેમેસ્ટર પરિણામો વિષય મુજબ (સરેરાશ GPA)",
                "Admin Modules": "એડમિન મોડ્યુલ્સ",
                "Open Admin Center": "એડમિન સેન્ટર ખોલો",
                "Create and publish alerts": "અલર્ટ બનાવો અને પ્રકાશિત કરો",
                "Mark, view, and report": "માર્ક કરો, જુઓ અને રિપોર્ટ કરો",
                "Manage student records": "વિદ્યાર્થી રેકોર્ડ મેનેજ કરો",
                "Configure and assign": "કન્ફિગર અને સોંપણી કરો",
                "Share and manage": "શેર કરો અને મેનેજ કરો",
                "Profiles and assignments": "પ્રોફાઇલ અને સોંપણીઓ",
                "Semesters and batches": "સેમેસ્ટર અને બેચ",
                "Collection and reports": "વસૂલી અને રિપોર્ટ્સ",
                "Create and manage programs": "પ્રોગ્રામ્સ બનાવો અને મેનેજ કરો",
                "Create and manage accounts": "એકાઉન્ટ્સ બનાવો અને મેનેજ કરો",
                "Configuration and tools": "કન્ફિગરેશન અને ટૂલ્સ",
                "Assignments": "સોંપણીઓ",
                "Enrollments": "એનલોલમેન્ટ્સ",
                "Redis Active": "રેડિસ સક્રિય",
                "In-memory cache": "ઇન-મેમરી કૅશ",
            }
        }
        def t(s):
            s0 = s or ""
            if lang == "gu":
                return tr.get("gu", {}).get(s0, s0)
            return s0
        return {"lang_code": lang, "t": t}

    @login_manager.user_loader
    def load_user(user_id: str):
        try:
            from .models import User
            return db.session.get(User, int(user_id))
        except Exception:
            return None

    # Blueprints
    from .main.routes import main_bp
    app.register_blueprint(main_bp)

    from .imports import imports_bp
    app.register_blueprint(imports_bp)

    from .exams import exams_bp
    app.register_blueprint(exams_bp)

    from .timetable import timetable_bp
    app.register_blueprint(timetable_bp, url_prefix="/timetable")

    from .faculty import faculty_bp
    app.register_blueprint(faculty_bp, url_prefix="/faculty")

    from .wizard import wizard as wizard_bp
    app.register_blueprint(wizard_bp, url_prefix="/wizard")

    from .super_admin import super_admin as super_admin_bp
    app.register_blueprint(super_admin_bp, url_prefix="/super-admin")

    @app.errorhandler(RequestEntityTooLarge)
    def handle_large_upload(e):
        try:
            limit_bytes = app.config.get("MAX_CONTENT_LENGTH") or (32 * 1024 * 1024)
            limit_mb = max(1, int(limit_bytes / (1024 * 1024)))
            flash(f"Upload exceeds the global size limit (max {limit_mb} MB).", "danger")
        except Exception:
            pass
        # Redirect back if possible; otherwise to index
        try:
            ref = request.referrer
        except Exception:
            ref = None
        return redirect(ref or url_for("main.index")), 413

    @app.errorhandler(RateLimitExceeded)
    def handle_rate_limit(e):
        try:
            from .api_utils import api_error
            return api_error("rate_limited", "Too many requests", 429)
        except Exception:
            return "Too many requests", 429

    @app.errorhandler(HTTPException)
    def handle_http_exception(e):
        try:
            from .api_utils import api_error
            return api_error(str(e.code), e.description or "", e.code)
        except Exception:
            return str(e), e.code

    @app.errorhandler(Exception)
    def handle_unexpected_exception(e):
        error_id = uuid.uuid4().hex[:12]
        try:
            app.logger.exception("Unhandled exception (ref=%s)", error_id)
        except Exception:
            pass
        try:
            path = (request.path or "")
            accept = (request.headers.get("Accept") or "").lower()
            is_api = ("/api/" in path) or path.startswith("/api") or ("application/json" in accept)
        except Exception:
            is_api = False
        if is_api:
            try:
                from .api_utils import api_error
                return api_error("500", f"Internal server error (ref {error_id})", 500)
            except Exception:
                return {"success": False, "error": {"code": "500", "message": f"Internal server error (ref {error_id})"}}, 500
        return f"Internal server error (ref {error_id})", 500

    # UPI config defaults
    app.config.setdefault("UPI_VPA", "college@bank")
    app.config.setdefault("UPI_PAYEE_NAME", "Parekh Colleges")
    # Optional per-program VPA mapping: {"bcom": {"pa": "bcom@bank", "pn": "Commerce"}, ...}
    app.config.setdefault("PROGRAM_UPI_MAP", {})

    # Create tables on first run (dev convenience)
    with app.app_context():
        db.create_all()
        # Minimal migration: ensure new columns exist in dev DB
        try:
            inspector = inspect(db.engine)
            
            # 1. Users table
            user_cols = [c['name'] for c in inspector.get_columns('users')]
            if 'email' not in user_cols:
                with db.engine.begin() as conn:
                    conn.execute("ALTER TABLE users ADD COLUMN email VARCHAR(128)")
            if 'is_active' not in user_cols:
                with db.engine.begin() as conn:
                    conn.execute("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT 1")
            if 'program_id_fk' not in user_cols:
                with db.engine.begin() as conn:
                    conn.execute("ALTER TABLE users ADD COLUMN program_id_fk INTEGER")
            if 'preferred_lang' not in user_cols:
                with db.engine.begin() as conn:
                    conn.execute("ALTER TABLE users ADD COLUMN preferred_lang VARCHAR(8)")

            # 2. CourseAssignments table
            ca_cols = [c['name'] for c in inspector.get_columns('course_assignments')]
            if 'is_active' not in ca_cols:
                with db.engine.begin() as conn:
                    conn.execute("ALTER TABLE course_assignments ADD COLUMN is_active BOOLEAN DEFAULT 1")
            if 'role' not in ca_cols:
                with db.engine.begin() as conn:
                    conn.execute("ALTER TABLE course_assignments ADD COLUMN role VARCHAR(16) DEFAULT 'primary'")
            if 'academic_year' not in ca_cols:
                with db.engine.begin() as conn:
                    conn.execute("ALTER TABLE course_assignments ADD COLUMN academic_year VARCHAR(16)")

            # 3. Students table
            cols = [c['name'] for c in inspector.get_columns('students')]
            if 'father_name' not in cols:
                with db.engine.begin() as conn:
                    conn.execute("ALTER TABLE students ADD COLUMN father_name VARCHAR(64)")
            if 'medium_tag' not in cols:
                with db.engine.begin() as conn:
                    conn.execute("ALTER TABLE students ADD COLUMN medium_tag VARCHAR(32)")

            # 4. Attendance table
            att_cols = [c['name'] for c in inspector.get_columns('attendance')]
            if 'period_no' not in att_cols:
                with db.engine.begin() as conn:
                    conn.execute("ALTER TABLE attendance ADD COLUMN period_no INTEGER")

            # 5. FeeStructures table
            fee_cols = [c['name'] for c in inspector.get_columns('fee_structures')]
            if 'is_frozen' not in fee_cols:
                with db.engine.begin() as conn:
                    conn.execute("ALTER TABLE fee_structures ADD COLUMN is_frozen BOOLEAN")
            if 'medium_tag' not in fee_cols:
                with db.engine.begin() as conn:
                    conn.execute("ALTER TABLE fee_structures ADD COLUMN medium_tag VARCHAR(32)")

            # 6. Subjects table
            subj_cols = [c['name'] for c in inspector.get_columns('subjects')]
            if 'medium_tag' not in subj_cols:
                with db.engine.begin() as conn:
                    conn.execute("ALTER TABLE subjects ADD COLUMN medium_tag VARCHAR(32)")

            # 7. Faculty table
            fac_cols = [c['name'] for c in inspector.get_columns('faculty')]
            if 'medium_expertise' not in fac_cols:
                with db.engine.begin() as conn:
                    conn.execute("ALTER TABLE faculty ADD COLUMN medium_expertise VARCHAR(32)")

            # 8. FeePayments table
            pay_cols = [c['name'] for c in inspector.get_columns('fee_payments')]
            if 'proof_image_path' not in pay_cols:
                with db.engine.begin() as conn:
                    conn.execute("ALTER TABLE fee_payments ADD COLUMN proof_image_path VARCHAR(255)")
            legacy_verified_col = 'verified_by_user_id' in pay_cols
            if 'verified_by_fk' not in pay_cols:
                with db.engine.begin() as conn:
                    conn.execute("ALTER TABLE fee_payments ADD COLUMN verified_by_fk INTEGER")
                    if legacy_verified_col:
                        try:
                            conn.execute(
                                "UPDATE fee_payments "
                                "SET verified_by_fk = verified_by_user_id "
                                "WHERE verified_by_fk IS NULL AND verified_by_user_id IS NOT NULL"
                            )
                        except Exception:
                            pass
            elif legacy_verified_col:
                with db.engine.begin() as conn:
                    try:
                        conn.execute(
                            "UPDATE fee_payments "
                            "SET verified_by_fk = verified_by_user_id "
                            "WHERE verified_by_fk IS NULL AND verified_by_user_id IS NOT NULL"
                        )
                    except Exception:
                        pass
            if 'payer_name' not in pay_cols:
                with db.engine.begin() as conn:
                    conn.execute("ALTER TABLE fee_payments ADD COLUMN payer_name VARCHAR(128)")
            if 'bank_credit_at' not in pay_cols:
                with db.engine.begin() as conn:
                    conn.execute("ALTER TABLE fee_payments ADD COLUMN bank_credit_at DATETIME")
            if 'receipt_no' not in pay_cols:
                with db.engine.begin() as conn:
                    conn.execute("ALTER TABLE fee_payments ADD COLUMN receipt_no VARCHAR(32)")

            # 9. SubjectTypes table
            st_cols = [c['name'] for c in inspector.get_columns('subject_types')]
            if 'type_name' not in st_cols:
                with db.engine.begin() as conn:
                    conn.execute("ALTER TABLE subject_types ADD COLUMN type_name VARCHAR(64)")
            if 'description' not in st_cols:
                with db.engine.begin() as conn:
                    conn.execute("ALTER TABLE subject_types ADD COLUMN description VARCHAR(255)")

            # 10. Trusts table
            trust_cols = [c['name'] for c in inspector.get_columns('trusts')]
            if 'subscription_start_at' not in trust_cols:
                with db.engine.begin() as conn:
                    conn.execute("ALTER TABLE trusts ADD COLUMN subscription_start_at DATETIME")
            if 'subscription_end_at' not in trust_cols:
                with db.engine.begin() as conn:
                    conn.execute("ALTER TABLE trusts ADD COLUMN subscription_end_at DATETIME")
            if 'subscription_grace_days' not in trust_cols:
                with db.engine.begin() as conn:
                    conn.execute("ALTER TABLE trusts ADD COLUMN subscription_grace_days INTEGER DEFAULT 0")
            if 'last_tenure_notice_at' not in trust_cols:
                with db.engine.begin() as conn:
                    conn.execute("ALTER TABLE trusts ADD COLUMN last_tenure_notice_at DATETIME")
            if 'suspended_at' not in trust_cols:
                with db.engine.begin() as conn:
                    conn.execute("ALTER TABLE trusts ADD COLUMN suspended_at DATETIME")
            if 'suspended_reason' not in trust_cols:
                with db.engine.begin() as conn:
                    conn.execute("ALTER TABLE trusts ADD COLUMN suspended_reason TEXT")

            # 11. Announcements table
            ann_cols = [c['name'] for c in inspector.get_columns('announcements')]
            if 'trust_id_fk' not in ann_cols:
                with db.engine.begin() as conn:
                    conn.execute("ALTER TABLE announcements ADD COLUMN trust_id_fk INTEGER")
                try:
                    with db.engine.begin() as conn:
                        conn.execute(
                            "UPDATE announcements SET trust_id_fk = (SELECT institutes.trust_id_fk FROM programs JOIN institutes ON programs.institute_id_fk = institutes.institute_id WHERE programs.program_id = announcements.program_id_fk) WHERE trust_id_fk IS NULL AND program_id_fk IS NOT NULL"
                        )
                except Exception:
                    pass

            # 12. ExamSchemes table
            exam_cols = [c['name'] for c in inspector.get_columns('exam_schemes')]
            if 'is_frozen' not in exam_cols:
                with db.engine.begin() as conn:
                    conn.execute("ALTER TABLE exam_schemes ADD COLUMN is_frozen BOOLEAN DEFAULT 0")
            if 'frozen_at' not in exam_cols:
                with db.engine.begin() as conn:
                    conn.execute("ALTER TABLE exam_schemes ADD COLUMN frozen_at DATETIME")
            if 'frozen_by_fk' not in exam_cols:
                with db.engine.begin() as conn:
                    conn.execute("ALTER TABLE exam_schemes ADD COLUMN frozen_by_fk INTEGER")
            if 'unlock_until' not in exam_cols:
                with db.engine.begin() as conn:
                    conn.execute("ALTER TABLE exam_schemes ADD COLUMN unlock_until DATETIME")
            if 'unlock_by_fk' not in exam_cols:
                with db.engine.begin() as conn:
                    conn.execute("ALTER TABLE exam_schemes ADD COLUMN unlock_by_fk INTEGER")
            if 'unlock_reason' not in exam_cols:
                with db.engine.begin() as conn:
                    conn.execute("ALTER TABLE exam_schemes ADD COLUMN unlock_reason TEXT")

            # 13. SystemMessageReads table
            try:
                table_names = set(inspector.get_table_names())
            except Exception:
                table_names = set()
            if "system_message_reads" not in table_names:
                with db.engine.begin() as conn:
                    conn.execute(
                        """
                        CREATE TABLE IF NOT EXISTS system_message_reads (
                            read_id INTEGER PRIMARY KEY AUTOINCREMENT,
                            message_id_fk INTEGER NOT NULL,
                            user_id_fk INTEGER NOT NULL,
                            read_at DATETIME,
                            CONSTRAINT uq_system_message_read UNIQUE (message_id_fk, user_id_fk)
                        )
                        """
                    )

        except Exception:
            # Best-effort; skip if migration fails
            pass

    return app


def csrf_required(view_func):
    @wraps(view_func)
    def _wrapped(*args, **kwargs):
        try:
            method = (request.method or "GET").upper()
        except Exception:
            method = "GET"
        if method in ("POST", "PUT", "DELETE"):
            try:
                token = (request.form.get("csrf_token") or request.headers.get("X-CSRF-Token") or "").strip()
            except Exception:
                token = ""
            sess_token = (session.get("csrf_token") or "")
            issued_at = session.get("csrf_token_issued_at")
            ttl = current_app.config.get("CSRF_TOKEN_TTL", 7200)
            now = int(time.time())
            # Expired token
            if not issued_at or (ttl > 0 and (now - int(issued_at)) > ttl):
                try:
                    flash("Refresh the Page or login again", "warning")
                except Exception:
                    pass
                try:
                    ref = request.referrer
                except Exception:
                    ref = None
                return redirect(ref or url_for("main.index"))
            # Missing token in request
            if not token:
                try:
                    flash("Refresh the Page or login again", "warning")
                except Exception:
                    pass
                try:
                    ref = request.referrer
                except Exception:
                    ref = None
                return redirect(ref or url_for("main.index"))
            # Mismatch
            if token != sess_token:
                try:
                    flash("Refresh the Page or login again", "warning")
                except Exception:
                    pass
                try:
                    ref = request.referrer
                except Exception:
                    ref = None
                return redirect(ref or url_for("main.index"))
        return view_func(*args, **kwargs)
    return _wrapped
    @app.context_processor
    def inject_i18n():
        # Prefer session setting; fallback to user preference; default to English
        try:
            if not session.get("lang") and getattr(current_user, "is_authenticated", False):
                pref = (getattr(current_user, "preferred_lang", None) or "").strip().lower()
                if pref in {"en", "gu"}:
                    session["lang"] = pref
        except Exception:
            pass
        lang = (session.get("lang") or "en").strip().lower()
        tr = {
            "gu": {
                "Dashboard": "ડેશબોર્ડ",
                "Students": "વિદ્યાર્થીઓ",
                "Program": "પ્રોગ્રામ",
                "Semester": "સેમેસ્ટર",
                "Medium": "માધ્યમ",
                "Add Student": "વિદ્યાર્થી ઉમેરો",
                "Bulk Import Students (Clerk)": "બલ્ક ઇમ્પોર્ટ (ક્લાર્ક)",
                "Announcements": "જાહેરખબરો",
                "Publish and manage college-wide announcements.": "કોલેજ-વ્યાપક જાહેરખબરો પ્રકાશિત કરો અને મેનેજ કરો.",
                "Quick Actions": "ઝડપી ક્રિયાઓ",
                "View Announcements": "જાહેરખબરો જુઓ",
                "Create Announcement": "જાહેરખબર બનાવો",
                "Notice Board": "નોટિસ બોર્ડ",
                "Archive": "આર્કાઇવ",
                "Helpful Links": "મદદરૂપ લિંક્સ",
                "Audience targeting supports program, division, and roles.": "શ્રોતાઓ નિશ્વિત પ્રોગ્રામ, વિભાગ અને ભૂમિકાઓને સપોર્ટ કરે છે.",
                "Dismissals let users hide announcements from their view.": "ડિસ્મિસલ વપરાશકારોને જાહેરખબરો છુપાવવા દે છે.",
                "Use archive to keep the notice board clean.": "નોટિસ બોર્ડ સ્વચ્છ રાખવા આર્કાઇવનો ઉપયોગ કરો.",
                "Advanced links for power users.": "પાવર યુઝર્સ માટે અદ્યતન લિંક્સ.",
                "Manage Accounts": "ખાતાઓ મેનેજ કરો",
                "Fees Module": "ફી મોડ્યુલ",
                "Manage fee heads, enter semester-wise amounts, and view structures.": "ફી હેડ્સ મેનેજ કરો, સેમેસ્ટર મુજબ રકમ દાખલ કરો અને સ્રક્ચર જુઓ.",
                "Fee Heads": "ફી હેડ્સ",
                "Add, rename, or delete heads per program and semester.": "પ્રોગ્રામ અને સેમેસ્ટર પ્રમાણે હેડ્સ ઉમેરો, નામ બદલો અથવા કાઢો.",
                "Manage Fee Heads": "ફી હેડ્સ મેનેજ કરો",
                "Fees Entry": "ફી એન્ટ્રી",
                "Enter and review semester-wise component amounts, then freeze.": "સેમેસ્ટર પ્રમાણે ઘટકોની રકમ દાખલ કરો અને સમીક્ષા કરો, પછી ફ્રીઝ કરો.",
                "Open Fees Entry": "ફી એન્ટ્રી ખોલો",
                "Bulk Import": "બલ્ક ઇમ્પોર્ટ",
                "Download sample and upload semester fees for a program.": "નમૂનો ડાઉનલોડ કરો અને પ્રોગ્રામ માટે સેમેસ્ટર ફી અપલોડ કરો.",
                "Open Bulk Import": "બલ્ક ઇમ્પોર્ટ ખોલો",
                "Structure View": "સ્રક્ચર વ્યૂ",
                "Browse fee structure totals and components across programs.": "પ્રોગ્રામ્સમાં ફી સ્રક્ચરની કુલ અને ઘટકો બ્રાઉઝ કરો.",
                "View Structure": "સ્રક્ચર જુઓ",
                "Quick Payment": "ઝડપી ચુકવણી",
                "Select program and semester, then pay via receipt page.": "પ્રોગ્રામ અને સેમેસ્ટર પસંદ કરો, પછી રસીદ પેજ મારફતે ચુકવો.",
                "Open Quick Payment": "ઝડપી ચુકવણી ખોલો",
                "Program Bank Details": "પ્રોગ્રામ બેંક વિગતો",
                "Manage bank info and UPI QR per program for receipts.": "રસીદ માટે દરેક પ્રોગ્રામની બેંક માહિતી અને UPI QR મેનેજ કરો.",
                "Open Bank Details": "બેંક વિગતો ખોલો",
                "Payment Status": "ચુકવણી સ્થિતિ",
                "View paid/unpaid by program, semester, and medium.": "પ્રોગ્રામ, સેમેસ્ટર અને માધ્યમ મુજબ ચુકવણી થયેલ/બાકી જુઓ.",
                "Open Payment Status": "ચુકવણી સ્થિતિ ખોલો",
                "Verification Queue": "ચકાસણી ક્યૂ",
                "Review UTRs and proofs, then verify or reject payments.": "UTR અને પુરાવાની સમીક્ષા કરો, પછી ચુકવણી ચકાસો અથવા રદ કરો.",
                "Open Verification Queue": "ચકાસણી ક્યૂ ખોલો",
                "Bulk Import Fees": "બલ્ક ઇમ્પોર્ટ ફી",
                "Select a program and semester to begin.": "શરૂઆત માટે પ્રોગ્રામ અને સેમેસ્ટર પસંદ કરો.",
                "Download Sample": "નમૂનો ડાઉનલોડ કરો",
                "The sample includes only the standard heads in the exact sequence below. No additional heads will be accepted by the importer.": "નમૂનામાં નીચે બતાવેલી ચોક્કસ ક્રમમાં માત્ર પ્રમાણભૂત હેડ્સ છે. ઇમ્પોર્ટમાં વધારાના હેડ્સ સ્વીકારવામાં નહીં આવે.",
                "Expected Heads (in order):": "અપેક્ષિત હેડ્સ (ક્રમમાં):",
                "Upload Filled Excel": "ભરેલું એક્સેલ અપલોડ કરો",
                "Excel File (.xlsx)": "એક્સેલ ફાઇલ (.xlsx)",
                "Import Fees": "ફી ઇમ્પોર્ટ કરો",
                "Dry-run (validate only)": "ડ્રાય-રન (માત્ર ચકાસણી)",
                "Validation only — no changes saved.": "માત્ર ચકાસણી — કોઈ ફેરફાર સેવ થયા નથી.",
                "Set Scope": "સ્કોપ સેટ કરો",
                "Tip:": "ટીપ:",
                "If heads are empty for your scope, use Fee Heads to add or the seed-all button (admin/clerk) to pre-create heads for all programs and semesters.": "જો તમારા સ્કોપ માટે હેડ્સ ખાલી હોય, તો ફી હેડ્સ ઉમેરો અથવા 'સીડ-ઓલ' બટનથી તમામ પ્રોગ્રામ અને સેમેસ્ટર માટે હેડ્સ બનાવો.",
                "Seed All Heads": "બધા હેડ્સ સીડ કરો",
                "Staff Module": "સ્ટાફ મોડ્યુલ",
                "Manage staff profiles and teaching assignments.": "સ્ટાફ પ્રોફાઇલ અને શિક્ષણ નિયુક્તિઓ મેનેજ કરો.",
                "View Staff": "સ્ટાફ જુઓ",
                "Add Staff": "સ્ટાફ ઉમેરો",
                "Assign Staff to Divisions": "સ્ટાફને વિભાગોમાં સોંપો",
                "Subjects": "વિષયો",
                "My Attendance Report": "મારી હાજરી રિપોર્ટ",
                "Admin Attendance Report": "એડમિન હાજરી રિપોર્ટ",
                "Power Actions": "પાવર ક્રિયાઓ",
                "Divisions & Sections Module": "વિભાગો અને સેકશન મોડ્યુલ",
                "Manage divisions/sections per program and semester.": "પ્રોગ્રામ અને સેમેસ્ટર પ્રમાણે વિભાગો/સેકશન મેનેજ કરો.",
                "View Divisions": "વિભાગો જુઓ",
                "Add Division": "વિભાગ ઉમેરો",
                "Rebalance Divisions & Roll Nos": "વિભાગો અને રોલ નં બેલેન્સ કરો",
                "Division Planning (Principal)": "વિભાગ આયોજન (પ્રિન્સિપાલ)",
                "Capacity / Division": "ક્ષમતા / વિભાગ",
                "Number of Divisions": "વિભાગોની સંખ્યા",
                "Roll Max / Division": "રોલ મહત્તમ / વિભાગ",
                "Save Planning": "આયોજન સેવ કરો",
                "Existing Plans": "હાલની યોજનાઓ",
                "Divisions": "વિભાગો",
                "Capacity": "ક્ષમતા",
                "Roll Max": "રોલ મહત્તમ",
                "No plans yet. Create one using the form.": "હજુ યોજનાઓ નથી. ફોર્મ વડે બનાવો.",
                "Admin Module": "એડમિન મોડ્યુલ",
                "Administrative tools and reports.": "પ્રશાસકીય સાધનો અને રિપોર્ટ્સ.",
                "Attendance Report": "હાજરી રિપોર્ટ",
                "Manage Accounts": "ખાતાઓ મેનેજ કરો",
                "Programs": "પ્રોગ્રામ્સ",
                "Program Import": "પ્રોગ્રામ ઇમ્પોર્ટ",
                "Clerk Bulk Import Students": "ક્લાર્ક બલ્ક ઇમ્પોર્ટ વિદ્યાર્થીઓ",
                "Offer Electives": "ઇલેક્ટિવ ઓફર કરો",
                "Assign Staff": "સ્ટાફ સોંપો",
                "Core Enrollment": "કોર એનરોલમેન્ટ",
                "Materials": "સામગ્રી",
                "Moderation": "સમીક્ષા",
                "All Downloads": "બધા ડાઉનલોડ્સ",
                "Your Subjects": "તમારા વિષયો",
                "No enrolled subjects found for": " માટે નોંધાયેલા વિષયો મળ્યા નથી",
                "Assigned Subjects": "સોંપાયેલ વિષયો",
                "Manage": "મેનેજ",
                "Share": "શેર",
                "No active assignments found.": "સક્રિય નિયુક્તિઓ મળી નથી.",
                "Select a subject to view or manage materials.": "સામગ્રી જોવા અથવા મેનેજ કરવા વિષય પસંદ કરો.",
                "Select Program": "પ્રોગ્રામ પસંદ કરો",
                "Download Sample Excel": "નમૂના એક્સેલ ડાઉનલોડ કરો",
                "Expected columns: Sr No | Description | Amount | Notes (optional)": "અપેક્ષિત કૉલમ્સ: ક્રમ નં | વર્ણન | રકમ | નોંધ (વૈકલ્પિક)",
                "Expected columns: Sr No | Description | Amount | Medium Tag | Notes (optional)": "અપેક્ષિત કૉલમ્સ: ક્રમ નં | વર્ણન | રકમ | માધ્યમ ટૅગ | નોંધ (વૈકલ્પિક)",
                "View Students": "વિદ્યાર્થીઓ જુઓ",
                "Add Student": "વિદ્યાર્થી ઉમેરો",
                "Bulk Import Students (Clerk)": "બલ્ક ઇમ્પોર્ટ વિદ્યાર્થીઓ (ક્લાર્ક)",
                "Validation only — no changes saved.": "માત્ર ચકાસણી — કોઈ ફેરફાર સેવ થયા નથી.",
                "Please select a program.": "કૃપા કરીને પ્રોગ્રામ પસંદ કરો.",
                "Please upload an Excel file.": "કૃપા કરીને એક્સેલ ફાઇલ અપલોડ કરો.",
                "Failed to save uploaded file.": "અપલોડ કરેલી ફાઇલ સેવ થવામાં નિષ્ફળ.",
                "File must be an Excel (.xlsx/.xls).": "ફાઇલ એક્સેલ (.xlsx/.xls) હોવી જોઈએ.",
                "Select program and semester before uploading.": "અપલોડ કરતા પહેલાં પ્રોગ્રામ અને સેમેસ્ટર પસંદ કરો.",
                "Medium is required for B.Com import. Choose English or Gujarati.": "B.Com ઇમ્પોર્ટ માટે માધ્યમ જરૂરી છે. English અથવા Gujarati પસંદ કરો.",
            }
        }
        def t(s):
            s0 = (s or "")
            if lang == "gu":
                return tr.get("gu", {}).get(s0, s0)
            return s0
        return {"lang_code": lang, "t": t}
