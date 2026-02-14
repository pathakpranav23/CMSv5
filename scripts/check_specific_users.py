import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cms_app import create_app, db
from cms_app.models import User
from sqlalchemy import select

def check_users():
    app = create_app()
    with app.app_context():
        users = db.session.execute(
            select(User).where(User.username.in_(['Principal', 'Admin']))
        ).scalars().all()
        for u in users:
            print(f"User: {u.username}, ProgramID: {u.program_id_fk}, TrustID: {u.trust_id_fk}")

if __name__ == "__main__":
    check_users()
