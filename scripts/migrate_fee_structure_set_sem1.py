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
        # Set semester=1 for all fee components where semester is NULL
        rows = FeeStructure.query.filter(FeeStructure.semester.is_(None)).all()
        for r in rows:
            r.semester = 1
        db.session.commit()
        print(f"Updated {len(rows)} fee components to semester=1.")


if __name__ == "__main__":
    main()