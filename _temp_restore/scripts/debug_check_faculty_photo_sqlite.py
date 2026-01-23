import sys
import os
import json
import sqlite3

PHOTO_KEYS = {"photo", "photo url", "image", "picture", "profile photo", "photo link"}
EMPID_KEYS = {"emp id", "employee id", "empid", "employee code", "id"}


def pick(extra: dict, keys):
    for key in extra.keys():
        lk = (key or "").strip().lower()
        if lk in keys:
            return extra.get(key) or ""
    return ""


def main(empid: str):
    db_path = os.path.join(os.path.dirname(__file__), "..", "cms.db")
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT faculty_id, full_name, extra_data FROM faculty")
        for faculty_id, full_name, extra_data in cur.fetchall():
            try:
                extra = json.loads(extra_data or "{}")
            except Exception:
                extra = {}
            emp = pick(extra, EMPID_KEYS)
            if emp == empid:
                photo_url = pick(extra, PHOTO_KEYS)
                print("faculty_id=", faculty_id)
                print("full_name=", full_name)
                print("emp_id=", emp)
                print("photo_url=", photo_url)
                if photo_url.startswith("/static/"):
                    static_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "cms_app", "static"))
                    rel = photo_url[len("/static/"):]
                    path = os.path.join(static_folder, rel.replace("/", os.sep))
                    print("photo_path=", path)
                    print("exists=", os.path.exists(path))
                return
        print("not_found")
    finally:
        conn.close()


if __name__ == "__main__":
    target_empid = sys.argv[1] if len(sys.argv) > 1 else ""
    main(target_empid)