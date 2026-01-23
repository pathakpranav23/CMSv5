import io
import pytest

from cms_app.__init__ import db
from cms_app.models import Program, User


def login(client, username="testuser", password="secret"):
    return client.post("/login", data={"username": username, "password": password}, follow_redirects=True)


@pytest.mark.usefixtures("app", "client")
def test_students_export_csv_headers(client):
    login(client)
    resp = client.get("/students/export.csv")
    assert resp.status_code == 200
    text = resp.data.decode("utf-8")
    assert "EnrollmentNo" in text
    assert ",Surname," in text


@pytest.mark.usefixtures("app", "client")
def test_subjects_export_csv_headers(client, app):
    login(client)
    with app.app_context():
        # Ensure a program exists so subjects page resolves filters
        if not Program.query.filter_by(program_name="BCA").first():
            p = Program(program_name="BCA", program_duration_years=3)
            db.session.add(p)
            db.session.commit()
    resp = client.get("/subjects/export.csv")
    assert resp.status_code == 200
    text = resp.data.decode("utf-8")
    assert "SubjectCode" in text
    assert ",SubjectName," in text


@pytest.mark.usefixtures("app", "client")
def test_language_preference_gujarati(client, app):
    # Ensure test user exists and login
    login(client)
    resp = client.post("/account/settings", data={"action": "set_language", "preferred_lang": "gu"}, follow_redirects=True)
    assert resp.status_code == 200
    # Fetch a page and ensure <html lang="gu">
    resp2 = client.get("/students")
    assert resp2.status_code == 200
    html = resp2.data.decode("utf-8")
    assert "<html lang=\"gu\">" in html