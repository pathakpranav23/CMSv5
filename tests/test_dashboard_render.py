import pytest
from cms_app import create_app, db
from cms_app.models import User

@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

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
