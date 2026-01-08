import os
import sys
from typing import List

# Ensure project root is on sys.path when running from scripts/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from cms_app import create_app, db
from cms_app.models import FeeStructure
from sqlalchemy import func


TARGET_COMPONENTS: List[str] = [
    "Tutation Fee",
    "Tutation Fee Total",
    "University Aminitys Fee",
    "University Enrollment Fee",
]


def main():
    app = create_app()
    with app.app_context():
        total_deleted = 0
        for name in TARGET_COMPONENTS:
            # Match case-insensitively and ignore leading/trailing spaces
            rows = (
                FeeStructure.query
                .filter(func.upper(func.trim(FeeStructure.component_name)) == name.upper())
                .all()
            )
            count = len(rows)
            for r in rows:
                db.session.delete(r)
            db.session.commit()
            print(f"Deleted {count} rows for component '{name}'.")
            total_deleted += count
        print(f"Total deleted rows: {total_deleted}")


if __name__ == "__main__":
    main()