import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from cms_app import create_app, db  # noqa: E402
from scripts.import_students import import_excel  # noqa: E402


def main():
    app = create_app()
    with app.app_context():
        files = [
            (
                r"c:\project\CMSv5\DATA FOR IMPORT EXPORT\BBA\BULK_Student_Import BBA Sem 4 Data Feb 2026.xlsx",
                4,
            ),
            (
                r"c:\project\CMSv5\DATA FOR IMPORT EXPORT\BBA\BULK_Student_Import BBA Sem 6 Data Feb 2026.xlsx",
                6,
            ),
        ]

        for path, sem in files:
            if not os.path.exists(path):
                print(f"File not found: {path}")
                continue
            print(f"\n=== Importing BBA Semester {sem} from ===")
            print(path)
            import_excel(path, program_name="BBA", semester_hint=sem, dry_run=False)


if __name__ == "__main__":
    main()

