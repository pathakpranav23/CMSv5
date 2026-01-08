import os
import sys
from typing import Optional

# Ensure project root is on sys.path when running from scripts/
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from cms_app import create_app, db
from cms_app.models import Program, Faculty


def normalize_name(s: Optional[str]) -> str:
    s = (s or "").strip()
    s = s.replace(".", "").replace("_", " ").replace("-", " ")
    return s.upper()


def is_generic_bcom(name: str) -> bool:
    n = normalize_name(name)
    # Exclude language variants
    if "ENGLISH" in n or "GUJARATI" in n or "(E)" in n or "(G)" in n:
        return False
    # Accept forms like BCOM, B COM, B.COM, BCom
    return n.replace(" ", "") == "BCOM"


def ensure_program(name: str) -> Program:
    prog = Program.query.filter(Program.program_name.ilike(name)).first()
    if not prog:
        prog = Program(program_name=name, program_duration_years=3)
        db.session.add(prog)
        db.session.flush()
    return prog


def copy_faculty_to_program(src_fac: Faculty, dest_prog: Program) -> str:
    # Try to find an existing faculty in destination by email first, then by name
    existing = None
    if src_fac.email:
        existing = (
            Faculty.query
            .filter(Faculty.program_id_fk == dest_prog.program_id, Faculty.email == src_fac.email)
            .first()
        )
    if (existing is None) and src_fac.full_name:
        existing = (
            Faculty.query
            .filter(Faculty.program_id_fk == dest_prog.program_id, Faculty.full_name == src_fac.full_name)
            .first()
        )

    if existing:
        # Update destination record with source details (conservative on user link)
        existing.full_name = src_fac.full_name
        if src_fac.email:
            existing.email = src_fac.email
        if src_fac.mobile:
            existing.mobile = src_fac.mobile
        if src_fac.designation:
            existing.designation = src_fac.designation
        if src_fac.department:
            existing.department = src_fac.department
        if src_fac.extra_data:
            existing.extra_data = src_fac.extra_data
        # Link User if not already linked
        if (existing.user_id_fk is None) and (src_fac.user_id_fk is not None):
            existing.user_id_fk = src_fac.user_id_fk
        return "updated"
    else:
        # Create a new faculty row in destination program
        new_fac = Faculty(
            user_id_fk=src_fac.user_id_fk,
            program_id_fk=dest_prog.program_id,
            full_name=src_fac.full_name,
            email=src_fac.email,
            mobile=src_fac.mobile,
            designation=src_fac.designation,
            department=src_fac.department,
            extra_data=src_fac.extra_data,
        )
        db.session.add(new_fac)
        return "created"


def copy_bcom_faculty_to_variants():
    # Locate source generic BCOM program
    src_prog: Optional[Program] = None
    for p in Program.query.order_by(Program.program_name.asc()).all():
        if is_generic_bcom(p.program_name or ""):
            src_prog = p
            break

    if not src_prog:
        print("No generic BCOM program found. Skipping staff copy.")
        return

    # Ensure destination programs exist
    dest_eng = ensure_program("BCom (English)")
    dest_guj = ensure_program("BCom (Gujarati)")

    # Copy all faculty from BCOM into each destination program
    src_faculty = Faculty.query.filter(Faculty.program_id_fk == src_prog.program_id).all()
    created_eng = updated_eng = 0
    created_guj = updated_guj = 0
    for f in src_faculty:
        res_eng = copy_faculty_to_program(f, dest_eng)
        if res_eng == "created":
            created_eng += 1
        elif res_eng == "updated":
            updated_eng += 1
        res_guj = copy_faculty_to_program(f, dest_guj)
        if res_guj == "created":
            created_guj += 1
        elif res_guj == "updated":
            updated_guj += 1

    db.session.commit()
    print(
        f"Copied BCOM staff -> BCom (English): created={created_eng}, updated={updated_eng}; "
        f"-> BCom (Gujarati): created={created_guj}, updated={updated_guj}"
    )


def import_bcom_subjects():
    # Import subjects for English and Gujarati semesters 3 and 5
    from scripts.import_subjects import upsert_subjects

    eng_s3 = r"c:\project\CMSv5\B.Com\Bcom English Semester 3 Subject Detail.xlsx"
    eng_s5 = r"c:\project\CMSv5\B.Com\Bcom English Semester 5 Subject Detail.xlsx"
    guj_s3 = r"c:\project\CMSv5\B.Com\BCom Gujarati Semester 3 Subject Detail.xlsx"
    guj_s5 = r"c:\project\CMSv5\B.Com\BCom Gujarati Semester 5 Subject Detail.xlsx"

    if os.path.exists(eng_s3):
        upsert_subjects("BCom (English)", eng_s3, 3)
        db.session.commit()
        print(f"Imported BCom (English) subjects Sem 3: {eng_s3}")
    else:
        print(f"Missing file: {eng_s3}")

    if os.path.exists(eng_s5):
        upsert_subjects("BCom (English)", eng_s5, 5)
        db.session.commit()
        print(f"Imported BCom (English) subjects Sem 5: {eng_s5}")
    else:
        print(f"Missing file: {eng_s5}")

    if os.path.exists(guj_s3):
        upsert_subjects("BCom (Gujarati)", guj_s3, 3)
        db.session.commit()
        print(f"Imported BCom (Gujarati) subjects Sem 3: {guj_s3}")
    else:
        print(f"Missing file: {guj_s3}")

    if os.path.exists(guj_s5):
        upsert_subjects("BCom (Gujarati)", guj_s5, 5)
        db.session.commit()
        print(f"Imported BCom (Gujarati) subjects Sem 5: {guj_s5}")
    else:
        print(f"Missing file: {guj_s5}")


def main():
    app = create_app()
    with app.app_context():
        copy_bcom_faculty_to_variants()
        import_bcom_subjects()


if __name__ == "__main__":
    main()