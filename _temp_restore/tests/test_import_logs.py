import io
import pytest
from openpyxl import Workbook

from cms_app.__init__ import db
from cms_app.models import Program, User, ImportLog


def create_admin(app):
    with app.app_context():
        u = User.query.filter_by(username="admin@example.com").first()
        if not u:
            u = User(username="admin@example.com", role="admin")
            db.session.add(u)
            db.session.commit()
        return u


def login(client, username, password="secret"):
    return client.post("/login", data={"username": username, "password": password}, follow_redirects=True)


@pytest.mark.usefixtures("app", "client")
def test_subjects_import_dry_run_logs(client, app):
    admin = create_admin(app)
    # Set a password for admin login
    with app.app_context():
        admin.password_hash = app.jinja_env.globals.get("generate_password_hash", None) or ""
        db.session.commit()
    # Login by posting directly to session (use existing testuser instead)
    login(client, "testuser")
    with app.app_context():
        p = Program.query.filter_by(program_name="BCA").first()
        if not p:
            p = Program(program_name="BCA", program_duration_years=3)
            db.session.add(p)
            db.session.commit()
        pid = p.program_id
    wb = Workbook()
    ws = wb.active
    ws.append(["subject_name", "subject_code", "paper_code", "subject_type", "semester", "theory_credits", "practical_credits", "total_credits"])
    ws.append(["Test Subject", "TS101", "PC101", "MAJOR", 1, 3, 0, 3])
    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)
    resp = client.post(
        "/clerk/subjects/import",
        data={
            "program_id_fk": str(pid),
            "semester": "1",
            "force_semester": "0",
            "dry_run": "1",
            "file": (bio, "subjects.xlsx"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert resp.status_code == 200
    with app.app_context():
        logs = ImportLog.query.filter_by(kind="subjects", program_id_fk=pid, semester=1, dry_run=True).all()
        assert len(logs) >= 1
