import sys
import argparse
from sqlalchemy import text

from cms_app import create_app, db
from cms_app.models import Student


def main():
    parser = argparse.ArgumentParser(description="Safely update a student's enrollment number and cascade references.")
    parser.add_argument("old_enrollment", help="Existing enrollment number")
    parser.add_argument("new_enrollment", help="New enrollment number to set")
    parser.add_argument("--update-username", action="store_true", help="Also update Users.username if it exactly matches the old enrollment number")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        old_enr = args.old_enrollment.strip()
        new_enr = args.new_enrollment.strip()

        if not old_enr or not new_enr:
            print("ERROR: Both old and new enrollment numbers are required.")
            sys.exit(1)
        if old_enr == new_enr:
            print("ERROR: Old and new enrollment numbers are the same; nothing to update.")
            sys.exit(1)

        # Validate student exists and target doesn't collide
        current = Student.query.get(old_enr)
        if not current:
            print(f"ERROR: No student found with enrollment_no='{old_enr}'.")
            sys.exit(1)
        collision = Student.query.get(new_enr)
        if collision:
            print(f"ERROR: A student already exists with enrollment_no='{new_enr}'. Choose a different value.")
            sys.exit(1)

        print(f"Updating enrollment_no from '{old_enr}' to '{new_enr}' ...")

        # Best‑effort: disable FK enforcement for SQLite to allow manual cascading
        try:
            db.session.execute(text("PRAGMA foreign_keys = OFF"))
        except Exception:
            pass

        counts = {}
        # Cascade updates in dependent tables that reference students.enrollment_no
        updates = [
            ("attendance", "student_id_fk"),
            ("grades", "student_id_fk"),
            ("student_credit_log", "student_id_fk"),
            ("fees_records", "student_id_fk"),
        ]
        for table, col in updates:
            stmt = text(f"UPDATE {table} SET {col} = :new WHERE {col} = :old")
            res = db.session.execute(stmt, {"new": new_enr, "old": old_enr})
            counts[table] = res.rowcount

        # Update the student primary key itself
        res_student = db.session.execute(
            text("UPDATE students SET enrollment_no = :new WHERE enrollment_no = :old"),
            {"new": new_enr, "old": old_enr},
        )
        counts["students"] = res_student.rowcount

        # Optionally update Users.username when it exactly matches the old enrollment
        if args.update_username:
            res_users = db.session.execute(
                text("UPDATE users SET username = :new WHERE username = :old"),
                {"new": new_enr, "old": old_enr},
            )
            counts["users"] = res_users.rowcount

        db.session.commit()

        # Re‑enable FK enforcement (best‑effort)
        try:
            db.session.execute(text("PRAGMA foreign_keys = ON"))
        except Exception:
            pass

        print("Update complete.")
        for t, c in counts.items():
            print(f"  {t}: {c} rows updated")


if __name__ == "__main__":
    main()