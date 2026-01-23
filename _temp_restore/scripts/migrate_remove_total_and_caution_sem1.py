import os
import sys

# Ensure project root is on sys.path when running from scripts/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from cms_app import create_app, db
from cms_app.models import FeeStructure
from sqlalchemy import func, or_, select
import re


def main():
    """
    Remove Semester 1 FeeStructure rows across ALL programs for:
    - "Total Fee" / "Total Fees" (case-insensitive, trimmed)
    - "Caution Manoy (Deposit)" (case-insensitive, trimmed)
    """
    app = create_app()
    with app.app_context():
        # Normalize targets to uppercase for comparison on TRIM(UPPER(component_name))
        total_fee_targets = ["TOTAL FEE", "TOTAL FEES"]
        caution_target = "CAUTION MANOY (DEPOSIT)"

        # Build base filter for semester 1

        # Delete explicit Total Fee/Fees
        deleted_total_exact = 0
        if total_fee_targets:
            conds = [func.upper(func.trim(FeeStructure.component_name)) == t for t in total_fee_targets]
            rows_total = db.session.execute(
                select(FeeStructure).where(
                    FeeStructure.semester == 1,
                    or_(*conds),
                )
            ).scalars().all()
            for r in rows_total:
                db.session.delete(r)
            db.session.commit()
            deleted_total_exact = len(rows_total)
            print(f"Deleted {deleted_total_exact} rows for explicit Total Fee/Fees in semester 1.")

        # Delete any other rows containing 'TOTAL' variants (e.g., GRAND TOTAL, TUTATION FEE TOTAL)
        rows_total_like = db.session.execute(
            select(FeeStructure).where(
                FeeStructure.semester == 1,
                func.upper(func.trim(FeeStructure.component_name)).like('%TOTAL%'),
            )
        ).scalars().all()
        # Avoid double-counting those already deleted
        deleted_total_like = 0
        for r in rows_total_like:
            # If already deleted, skip; otherwise delete
            try:
                db.session.delete(r)
                deleted_total_like += 1
            except Exception:
                pass
        db.session.commit()
        print(f"Deleted {deleted_total_like} rows for TOTAL variants in semester 1.")

        # Delete Caution Manoy (Deposit) exact
        rows_caution_exact = db.session.execute(
            select(FeeStructure).where(
                FeeStructure.semester == 1,
                func.upper(func.trim(FeeStructure.component_name)) == caution_target,
            )
        ).scalars().all()
        for r in rows_caution_exact:
            db.session.delete(r)
        db.session.commit()
        deleted_caution_exact = len(rows_caution_exact)
        print(f"Deleted {deleted_caution_exact} rows for 'Caution Manoy (Deposit)' in semester 1.")

        # Delete other caution-money misspellings
        pat_caution = re.compile(r"\bCAUTION\b.*\b(MONEY|MANOY|MONOY)\b", re.IGNORECASE)
        rows_caution_like = db.session.execute(
            select(FeeStructure).where(
                FeeStructure.semester == 1,
                func.upper(FeeStructure.component_name).like('%CAUTION%'),
            )
        ).scalars().all()
        deleted_caution_like = 0
        for r in rows_caution_like:
            name = (r.component_name or '').strip()
            if pat_caution.search(name):
                try:
                    db.session.delete(r)
                    deleted_caution_like += 1
                except Exception:
                    pass
        db.session.commit()
        print(f"Deleted {deleted_caution_like} rows for CAUTION MONEY variants in semester 1.")

        total_deleted = deleted_total_exact + deleted_total_like + deleted_caution_exact + deleted_caution_like
        print(f"Total deleted rows: {total_deleted}")


if __name__ == "__main__":
    main()
