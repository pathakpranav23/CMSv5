import pytest
from cms_app.models import User
from werkzeug.security import generate_password_hash
from cms_app import db

def test_forgot_password_no_link_leak(client, app):
    # Create a user
    with app.app_context():
        u = User.query.filter_by(username="reset_test_user").first()
        if not u:
            u = User(username="reset_test_user", password_hash=generate_password_hash("password"))
            db.session.add(u)
            db.session.commit()

    # Request password reset
    # We need to make sure we don't hit the rate limit from other tests, 
    # but since tests run in isolation or sequence, and this is a new user, it should be fine.
    # Also the rate limit key depends on IP (local) and route.
    # To be safe, we can clear the rate limit counters if we could access them, but they are module level in routes.py
    # However, pytest fixtures usually reset state or use new app instances? 
    # conftest.py creates 'app' with scope='session', so module variables might persist.
    # But let's try.
    
    response = client.post("/forgot-password", data={"username": "reset_test_user"}, follow_redirects=True)
    
    # Assertions
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    
    # Check that the success message is shown
    assert "Request sent to Administration. Please contact the Principal or Clerk office." in html
    
    # Check that the reset link is NOT shown
    assert "Dev reset link:" not in html
    
    # Verify that an announcement was created
    from cms_app.models import Announcement
    with app.app_context():
        # Look for the announcement created for this user
        # The message should contain the username
        ann = Announcement.query.filter(Announcement.message.contains("reset_test_user")).first()
        assert ann is not None
        assert ann.title == "Password Reset Request"
        
        # Verify audience
        roles = [aud.role for aud in ann.audiences]
        assert "principal" in roles
        assert "clerk" in roles
