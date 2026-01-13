import pytest
from flask import url_for
from cms_app.models import User, Program, ProgramBankDetails
from cms_app import db
from werkzeug.security import generate_password_hash

@pytest.fixture(autouse=True)
def patch_cache_app(app):
    from cms_app import cache
    if not hasattr(cache, "app"):
        cache.app = app
    yield
    # No teardown needed as cache is global

def test_fees_bank_details_caching(client, app):
    # Create user and data
    with app.app_context():
        if not User.query.filter_by(username="admin_cache").first():
            u = User(username="admin_cache", password_hash=generate_password_hash("secret"), role="admin")
            db.session.add(u)
            
            p = Program(program_name="BCA")
            db.session.add(p)
            db.session.flush()
            
            bd = ProgramBankDetails(
                program_id_fk=p.program_id,
                bank_name="Test Bank",
                account_name="Test Account",
                account_number="1234567890",
                ifsc="TEST0001234",
                branch="Test Branch"
            )
            db.session.add(bd)
            db.session.commit()

    # Login
    client.post("/login", data={"username": "admin_cache", "password": "secret"}, follow_redirects=True)

    # Access page
    resp = client.get("/fees/bank-details")
    assert resp.status_code == 200
    assert b"Test Bank" in resp.data

    # Access again (should be cached)
    resp2 = client.get("/fees/bank-details")
    assert resp2.status_code == 200

def test_dashboard_caching(client, app):
    # Login as admin
    with app.app_context():
        if not User.query.filter_by(username="admin_dash").first():
            u = User(username="admin_dash", password_hash=generate_password_hash("secret"), role="admin")
            db.session.add(u)
            db.session.commit()

    client.post("/login", data={"username": "admin_dash", "password": "secret"}, follow_redirects=True)
    
    # First access
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    
    # Second access (cached)
    resp2 = client.get("/dashboard")
    assert resp2.status_code == 200

def test_reports_hub_caching(client, app):
    # Login as admin
    with app.app_context():
        if not User.query.filter_by(username="admin_rep").first():
            u = User(username="admin_rep", password_hash=generate_password_hash("secret"), role="admin")
            db.session.add(u)
            db.session.commit()

    client.post("/login", data={"username": "admin_rep", "password": "secret"}, follow_redirects=True)
    
    # First access
    resp = client.get("/reports")
    assert resp.status_code == 200
    
    # Second access (cached)
    resp2 = client.get("/reports")
    assert resp2.status_code == 200
