import os
import sys

# Ensure project root is on sys.path when running from scripts/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from cms_app import create_app, db
from cms_app.models import FeeStructure


from sqlalchemy import select, delete, func

def main():
    app = create_app()
    with app.app_context():
        total_before = db.session.execute(select(func.count()).select_from(FeeStructure)).scalar_one()
        deleted = db.session.execute(delete(FeeStructure)).rowcount or 0
        db.session.commit()
        print(f"Cleared fee_structures table. before={total_before}, deleted={deleted}")


if __name__ == "__main__":
    main()