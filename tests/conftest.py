import os
import sys
import tempfile
import pytest

# --- SA2 compatibility shim -------------------------------------------------
# Flask-SQLAlchemy 2.5.1 needs sqlalchemy.__all__ attributes and walks them in
# _include_sqlalchemy, colliding with its own descriptors.  The local shim
# patches the relevant behaviour before cms_app is imported (harmless on SA1.4).
import tests._sa2_compat  # noqa: F401  (side-effect import)
# ---------------------------------------------------------------------------

# --- TEST mode signal for create_app() ---------------------------------------
# Ensures create_app() skips its embedded db.create_all() + schema migration so
# the session-level fixture can run db.create_all() cleanly and print the
# fresh-schema inspection line.
os.environ["CMS_TEST_MODE"] = "1"
# ---------------------------------------------------------------------------

# --- Pre-import DB override -------------------------------------------------
# The default env may point to a live PostgreSQL; tests always use a throwaway
# SQLite DB regardless of external env.  Set this BEFORE cms_app imports so
# create_app() resolves the correct URI at import time.
_BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_TEST_DB = os.path.join(_BASE, "test.db")
try:
    if os.path.exists(_TEST_DB):
        os.remove(_TEST_DB)
except Exception:
    pass
os.environ["DATABASE_URL"] = "sqlite:///" + _TEST_DB.replace("\\", "/")
# ---------------------------------------------------------------------------

from cms_app import create_app, db
from cms_app.models import User
from cms_app.route_overrides import route_overrides_bp
from werkzeug.security import generate_password_hash


@pytest.fixture(scope="session")
def temp_db_path():
    return _TEST_DB


@pytest.fixture(scope="session")
def app(temp_db_path):
    app = create_app()
    app.register_blueprint(route_overrides_bp)
    app.config["TESTING"] = True
    app.config["RATELIMIT_ENABLED"] = True
    with app.app_context():
        from cms_app import models  # ensure models are registered
        db.create_all()
        from sqlalchemy import inspect
        print("TEST DB URI:", app.config.get("SQLALCHEMY_DATABASE_URI"))
        print("TEST TABLES:", inspect(db.engine).get_table_names())

        if not User.query.filter_by(username="testuser").first():
            u = User(username="testuser", password_hash=generate_password_hash("secret"), role="admin")
            db.session.add(u)
            db.session.commit()
    return app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def patch_cache_app(app):
    from cms_app import cache
    if not hasattr(cache, "app"):
        cache.app = app
    try:
        cache.clear()
    except Exception:
        pass
    yield
    try:
        cache.clear()
    except Exception:
        pass

