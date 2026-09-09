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
    with client.session_transaction() as sess:
        csrf = sess.get("csrf_token", "")
    resp = client.post("/account/settings", data={"action": "set_language", "preferred_lang": "gu", "csrf_token": csrf}, follow_redirects=True)
    assert resp.status_code == 200
    # Fetch a page and ensure <html lang="gu">
    resp2 = client.get("/students")
    assert resp2.status_code == 200
    html = resp2.data.decode("utf-8")
    assert "<html lang=\"gu\">" in html


@pytest.mark.usefixtures("app", "client")
def test_gujarati_p02_dead_block_merged_into_primary(client, app):
    """P0-2: The unreachable nested inject_i18n block that used to live after
    csrf_required()'s ``return _wrapped`` had 97 Gujarati strings that never
    actually rendered.  After the merge, the previously-missing "Verification
    Queue" → ``ચકાસણી ક્યૂ`` translation must appear when a Gujarati-session
    visitor renders a page that invokes ``t('Verification Queue')``.  We use
    ``/modules/fees`` (whose card title already correctly uses the translate
    helper) to avoid Jinja template-caching side effects on the queue page
    template that was modified mid-session during the P0 edit pipeline.
    """
    from cms_app import db
    from cms_app.models import Trust, Institute, Program, User
    from werkzeug.security import generate_password_hash

    with app.app_context():
        admin = User.query.filter_by(username="gu_queue_admin").first()
        if not admin:
            trust = Trust(trust_name="Guj Queue Trust", trust_code="GQTR", is_active=True)
            db.session.add(trust)
            db.session.flush()
            institute = Institute(
                trust_id_fk=trust.trust_id,
                institute_name="Guj Queue Institute",
                institute_code="GQI",
            )
            db.session.add(institute)
            db.session.flush()
            program = Program(
                institute_id_fk=institute.institute_id,
                program_name="Guj Queue Program",
            )
            db.session.add(program)
            db.session.flush()
            admin = User(
                username="gu_queue_admin",
                password_hash=generate_password_hash("secret"),
                role="admin",
                trust_id_fk=trust.trust_id,
                program_id_fk=program.program_id,
            )
            db.session.add(admin)
            db.session.commit()

    login(client, "gu_queue_admin", "secret")
    # Force Gujarati via explicit session set — guaranteed to propagate to the
    # inject_i18n context_processor regardless of query-arg edge cases.
    with client.session_transaction() as sess:
        sess["lang"] = "gu"
    resp = client.get("/modules/fees", follow_redirects=True)
    assert resp.status_code == 200
    text = resp.data.decode("utf-8")
    # ``ચકાસણી ક્યૂ`` is the Gujarati translation of "Verification Queue"
    # (taken from the formerly-dead nested inject_i18n block).  If the
    # merge was not applied this key would not exist and the page would
    # only show the untranslated English string.
    assert "ચકાસણી ક્યૂ" in text, (
        "Gujarati 'Verification Queue' (ચકાસણી ક્યૂ) not found — P0-2 merge "
        "of dead nested inject_i18n block into primary tr['gu'] did not apply."
    )