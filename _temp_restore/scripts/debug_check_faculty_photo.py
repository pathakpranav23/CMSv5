import sys
import os
import json

from cms_app import create_app, db
from cms_app.models import Faculty
from sqlalchemy import select

PHOTO_KEYS = {"photo", "photo url", "image", "picture", "profile photo", "photo link"}
EMPID_KEYS = {"emp id", "employee id", "empid", "employee code", "id"}


def pick_photo(extra: dict):
    for key in extra.keys():
        lk = (key or "").strip().lower()
        if lk in PHOTO_KEYS:
            return extra.get(key) or ""
    return ""


def pick_empid(extra: dict):
    for key in extra.keys():
        lk = (key or "").strip().lower()
        if lk in EMPID_KEYS:
            return extra.get(key) or ""
    return ""


def main(empid: str):
    app = create_app()
    with app.app_context():
        rows = db.session.execute(
            select(Faculty)
        ).scalars().all()
        for f in rows:
            try:
                extra = json.loads(f.extra_data or "{}")
            except Exception:
                extra = {}
            emp = pick_empid(extra)
            if emp == empid:
                photo_url = pick_photo(extra)
                print("faculty_id=", f.faculty_id)
                print("full_name=", f.full_name)
                print("emp_id=", emp)
                print("photo_url=", photo_url)
                if photo_url.startswith("/static/"):
                    rel = photo_url[len("/static/"):]
                    path = os.path.join(app.static_folder, rel.replace("/", os.sep))
                    print("photo_path=", path)
                    print("exists=", os.path.exists(path))
                return
        print("not_found")


if __name__ == "__main__":
    target_empid = sys.argv[1] if len(sys.argv) > 1 else ""
    main(target_empid)
