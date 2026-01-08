import os
import sys

# Ensure project root is on sys.path when running from scripts/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from cms_app import create_app, db
from cms_app.models import FeeStructure


def main():
    app = create_app()
    with app.app_context():
        total_before = db.session.query(FeeStructure).count()
        deleted = db.session.query(FeeStructure).delete(synchronize_session=False)
        db.session.commit()
        print(f"Cleared fee_structures table. before={total_before}, deleted={deleted}")


if __name__ == "__main__":
    main()