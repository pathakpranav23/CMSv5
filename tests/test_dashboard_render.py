import os
import pytest
from cms_app import create_app, db
from cms_app.models import User

@pytest.fixture
def app():
    _old_db = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    try:
        app = create_app()
    finally:
        if _old_db is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = _old_db
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()

@pytest.fixture
def client(app):
    return app.test_client()

def test_dashboard_render(client, app):
    # Create a user to login
    from werkzeug.security import generate_password_hash
    user = User(username='testadmin', role='Admin')
    user.password_hash = generate_password_hash('password')
    db.session.add(user)
    db.session.commit()

    with client:
        client.post('/login', data={'username': 'testadmin', 'password': 'password'})
        response = client.get('/dashboard')
        assert response.status_code == 200

def test_dashboard_clerk_render(client, app):
    from werkzeug.security import generate_password_hash
    user = User(username='testclerk', role='Clerk')
    user.password_hash = generate_password_hash('password')
    db.session.add(user)
    db.session.commit()

    with client:
        client.post('/login', data={'username': 'testclerk', 'password': 'password'})
        response = client.get('/dashboard')
        assert response.status_code == 200
        assert "Pending Verifications" in response.data.decode('utf-8')
