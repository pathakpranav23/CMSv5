import os
import sys
# Ensure project root is on sys.path for local imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from cms_app import create_app
from cms_app.models import db, Faculty, CourseAssignment, Subject, Division, User


def find_faculty_by_name(name_query: str):
    # Try case-insensitive contains match; fallback to stripping common prefixes like 'Dr '
    q = Faculty.query.filter(Faculty.full_name.ilike(f"%{name_query}%")).all()
    if q:
        return q[0]
    name_trim = name_query.replace("Dr ", "").strip()
    q = Faculty.query.filter(Faculty.full_name.ilike(f"%{name_trim}%")).all()
    return q[0] if q else None


def find_faculty_by_email(email_query: str):
    # First, try direct match on Faculty.email
    fac = Faculty.query.filter(Faculty.email.ilike(email_query)).first()
    if fac:
        return fac
    # Next, try linked User by username (often email)
    user = User.query.filter(User.username.ilike(email_query)).first()
    if user:
        fac = Faculty.query.filter_by(user_id_fk=user.user_id).first()
        if fac:
            return fac
    return None


def main():
    query_arg = "Mahimn Pandya"
    if len(sys.argv) > 1:
        query_arg = sys.argv[1]

    app = create_app()
    with app.app_context():
        # Decide search mode: email vs name
        if "@" in query_arg:
            fac = find_faculty_by_email(query_arg)
        else:
            fac = find_faculty_by_name(query_arg)
        if not fac:
            print(f"Faculty not found for query: {query_arg}")
            return

        # Resolve linked user id for CourseAssignment mapping
        user_id = fac.user_id_fk
        user = User.query.get(user_id) if user_id else None
        if not user:
            print(f"No linked user account for faculty '{fac.full_name}'. Cannot lookup assignments.")
            return

        assignments = CourseAssignment.query.filter_by(faculty_id_fk=user.user_id, is_active=True).all()
        if not assignments:
            print(f"No active subject assignments found for {fac.full_name} (user_id={user.user_id}).")
            return

        results = []
        for a in assignments:
            subj = Subject.query.get(a.subject_id_fk)
            div = Division.query.get(a.division_id_fk) if a.division_id_fk else None
            results.append({
                "subject_id": a.subject_id_fk,
                "subject_name": getattr(subj, "subject_name", None),
                "subject_code": getattr(subj, "subject_code", None),
                "semester": getattr(subj, "semester", None),
                "division": getattr(div, "division_code", None),
                "academic_year": a.academic_year,
            })

        print(f"Faculty: {fac.full_name} (user_id={user.user_id})")
        print(f"Assigned subjects: {len(results)}")
        for i, r in enumerate(results, start=1):
            div_txt = f" | Division: {r['division']}" if r.get("division") else ""
            code_txt = f" [{r['subject_code']}]" if r.get("subject_code") else ""
            sem_txt = f" | Sem: {r['semester']}" if r.get("semester") else ""
            print(f"{i}. {r['subject_name']}{code_txt}{sem_txt}{div_txt} | AY: {r['academic_year']}")


if __name__ == "__main__":
    main()