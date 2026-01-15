import os
import sys
from typing import Dict, List, Tuple

# Ensure project root is on sys.path when running from scripts/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from cms_app import create_app, db
from cms_app.models import Program, FeeStructure
from cms_app.main.routes import _slugify_component, _normalize_component_slug, _FEE_NAME_BY_SLUG, _CANON_SLUGS
from sqlalchemy import select


def freeze_program_semester(prog: Program, semester: int) -> Tuple[int, int, int]:
    """Freeze canonical components for a program+semester.

    - For each canonical slug present among rows, pick the row with the highest amount.
    - Rename component_name to canonical display name when available.
    - Mark duplicates (same slug) as inactive to avoid confusion.
    - Set is_frozen=True and is_active=True for the chosen row.

    Returns: (frozen_count, deactivated_dupe_count, total_rows)
    """
    rows: List[FeeStructure] = db.session.execute(
        select(FeeStructure).filter_by(program_id_fk=prog.program_id, semester=semester)
    ).scalars().all()
    by_slug: Dict[str, List[FeeStructure]] = {}
    for r in rows:
        nm = (r.component_name or "").strip()
        slug = _normalize_component_slug(_slugify_component(nm))
        if slug not in by_slug:
            by_slug[slug] = []
        by_slug[slug].append(r)

    frozen = 0
    deactivated = 0
    for slug, group in by_slug.items():
        if slug not in _CANON_SLUGS:
            # Skip non-canonical extras for now; could include later if desired
            continue
        # Pick the row with highest amount (safest in case of duplicates)
        best = max(group, key=lambda r: float(r.amount or 0.0))
        # Rename to canonical display name for consistency
        display_name = _FEE_NAME_BY_SLUG.get(slug, (best.component_name or "").strip())
        try:
            best.component_name = display_name
        except Exception:
            pass
        # Freeze and activate
        try:
            setattr(best, "is_frozen", True)
            best.is_active = True
        except Exception:
            pass
        frozen += 1
        # Deactivate other duplicates to avoid confusion
        for r in group:
            if r is not best:
                try:
                    r.is_active = False
                except Exception:
                    pass
                deactivated += 1

    db.session.commit()
    return frozen, deactivated, len(rows)


def main():
    app = create_app()
    with app.app_context():
        programs = db.session.execute(
            select(Program).order_by(Program.program_name.asc())
        ).scalars().all()
        total_frozen = 0
        total_deactivated = 0
        combos = 0
        for prog in programs:
            # Get distinct semesters for this program
            sems = db.session.execute(
                select(FeeStructure.semester).distinct().where(
                    FeeStructure.program_id_fk == prog.program_id,
                    FeeStructure.semester.is_not(None)
                )
            ).scalars().all()
            for sem in sems:
                f, d, n = freeze_program_semester(prog, sem)
                combos += 1
                total_frozen += f
                total_deactivated += d
                print(f"Frozen {f} canonical heads, deactivated {d} duplicates for {prog.program_name} semester {sem} (rows={n}).")
        print(f"Completed. Program-semester combos processed={combos}, total_frozen={total_frozen}, total_deactivated={total_deactivated}.")


if __name__ == "__main__":
    main()
