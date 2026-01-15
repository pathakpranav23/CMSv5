import os
import sys

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from cms_app import create_app, db
from cms_app.models import Program, ProgramBankDetails
from sqlalchemy import select


SEED_DETAILS = {
    # Shared HDFC account for BA/BBA/DFD
    "BA": {
        "bank_name": "HDFC Bank",
        "account_name": "SHRI BALVANT PAREKH EDUCATION TRUST",
        "account_number": "09571880000031",
        "ifsc": "HDFC0000957",
        "branch": "Mahuva",
    },
    "BBA": {
        "bank_name": "HDFC Bank",
        "account_name": "SHRI BALVANT PAREKH EDUCATION TRUST",
        "account_number": "09571880000031",
        "ifsc": "HDFC0000957",
        "branch": "Mahuva",
    },
    "DFD": {
        "bank_name": "HDFC Bank",
        "account_name": "SHRI BALVANT PAREKH EDUCATION TRUST",
        "account_number": "09571880000031",
        "ifsc": "HDFC0000957",
        "branch": "Mahuva",
    },
    # BCA has distinct HDFC account
    "BCA": {
        "bank_name": "HDFC Bank",
        "account_name": "SMT K B PAREKH CLG OF COMP SCIENCE",
        "account_number": "09571880000058",
        "ifsc": "HDFC0000957",
        "branch": "Mahuva",
    },
    # BCOM
    "BCOM": {
        "bank_name": "HDFC Bank",
        "account_name": "Shree Parekh Commerce College",
        "account_number": "50100552581921",
        "ifsc": "HDFC0000957",
        "branch": "Mahuva",
    },
    # MCOM should use BCOM details (explicitly seed for visibility)
    "MCOM": {
        "bank_name": "HDFC Bank",
        "account_name": "Shree Parekh Commerce College",
        "account_number": "50100552581921",
        "ifsc": "HDFC0000957",
        "branch": "Mahuva",
    },
    # BSC and PG DMLT share HDFC account
    "BSC": {
        "bank_name": "HDFC Bank",
        "account_name": "Shree Parekh Science College",
        "account_number": "50100552770898",
        "ifsc": "HDFC0000957",
        "branch": "Mahuva",
    },
    "PG DMLT": {
        "bank_name": "HDFC Bank",
        "account_name": "Shree Parekh Science College",
        "account_number": "50100552770898",
        "ifsc": "HDFC0000957",
        "branch": "Mahuva",
    },
    # LAW/LLB uses Axis
    "LLB": {
        "bank_name": "AXIS Bank",
        "account_name": "Shree Parekh Law College",
        "account_number": "924010072722822",
        "ifsc": "UTIB0001049",
        "branch": "Mahuva",
    },
    # MSC(IT) intentionally omitted per requirement
}


def upsert_details(app):
    with app.app_context():
        programs = db.session.execute(
            select(Program).order_by(Program.program_name.asc())
        ).scalars().all()
        prog_by_name = { (p.program_name or "").strip().upper(): p for p in programs }
        created, updated, skipped = 0, 0, []
        for name, detail in SEED_DETAILS.items():
            key = name.strip().upper()
            p = prog_by_name.get(key)
            if not p:
                skipped.append(name)
                continue
            row = db.session.execute(
                select(ProgramBankDetails).filter_by(program_id_fk=p.program_id)
            ).scalars().first()
            if row:
                row.bank_name = detail["bank_name"]
                row.account_name = detail["account_name"]
                row.account_number = detail["account_number"]
                row.ifsc = detail["ifsc"].upper()
                row.branch = detail["branch"]
                row.active = True
                updated += 1
            else:
                row = ProgramBankDetails(
                    program_id_fk=p.program_id,
                    bank_name=detail["bank_name"],
                    account_name=detail["account_name"],
                    account_number=detail["account_number"],
                    ifsc=detail["ifsc"].upper(),
                    branch=detail["branch"],
                    active=True,
                )
                db.session.add(row)
                created += 1
        db.session.commit()
        print(f"Seed complete. Created: {created}, Updated: {updated}, Skipped (program missing): {skipped}")


if __name__ == "__main__":
    app = create_app()
    upsert_details(app)
