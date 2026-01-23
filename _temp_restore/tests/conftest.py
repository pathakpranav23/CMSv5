import os
import tempfile
import pytest

from cms_app.__init__ import create_app, db
from cms_app.models import User
from werkzeug.security import generate_password_hash


@pytest.fixture(scope="session")
def temp_db_path():
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    path = os.path.join(base, "test.db")
    uri_path = path.replace("\\", "/")
    os.environ["DATABASE_URL"] = f"sqlite:///{uri_path}"
    return path


@pytest.fixture(scope="session")
def app(temp_db_path):
    app = create_app()
    app.config["TESTING"] = True
    app.config["RATELIMIT_ENABLED"] = True
    with app.app_context():
        from cms_app import models  # ensure models are registered
        db.create_all()
        from sqlalchemy import inspect
        try:
            print("TEST DB URI:", app.config.get("SQLALCHEMY_DATABASE_URI"))
            print("TEST TABLES:", inspect(db.engine).get_table_names())
        except Exception:
            pass
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
    yield
