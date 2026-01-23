import os
import sys

# Ensure project root
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from cms_app import create_app, db
from scripts.import_subjects import upsert_subjects


def main():
    app = create_app()
    with app.app_context():
        path = r"c:\project\CMSv5\B.Com\Bcom English Semester 3 Subject Detail.xlsx"
        if not os.path.exists(path):
            print(f"Missing file: {path}")
            return
        # Force semester override to 3 due to mislabeled sheet content
        upsert_subjects("BCom (English)", path, default_semester=3, force_default_semester=True)
        db.session.commit()
        print("Re-imported BCom (English) Sem 3 with forced semester override.")


if __name__ == "__main__":
    main()