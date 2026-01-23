from functools import wraps
from flask import flash, redirect, url_for, current_app
from flask_login import current_user

def role_required(*roles):
    """
    Decorator to ensure the current user has one of the allowed roles.
    Must be placed *after* @login_required.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return current_app.login_manager.unauthorized()
            
            user_role = (getattr(current_user, "role", "") or "").strip().lower()
            allowed = {r.strip().lower() for r in roles}
            
            if user_role not in allowed:
                # Optional: flash a message if you want
                try:
                    flash("You do not have permission to access this resource.", "danger")
                except Exception:
                    pass
                return redirect(url_for("main.dashboard"))
            
            return func(*args, **kwargs)
        return wrapper
    return decorator
