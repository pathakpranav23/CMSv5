import os
import sys

# Ensure project root is on sys.path when running from scripts/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from cms_app import create_app, db
from cms_app.models import Program, FeeStructure
from cms_app.main.routes import _normalize_component_slug, _slugify_component, _FEE_NAME_BY_SLUG
from sqlalchemy import select


def main():
    if len(sys.argv) < 3:
        print("Usage: python scripts/debug_fee_structure_program_semester.py <program_id> <semester>")
        return
    program_id = int(sys.argv[1])
    semester = int(sys.argv[2])

    app = create_app()
    with app.app_context():
        prog = db.session.get(Program, program_id)
        if not prog:
            print(f"Program {program_id} not found")
            return
        rows = db.session.execute(
            select(FeeStructure)
            .filter_by(program_id_fk=prog.program_id, semester=semester)
            .order_by(FeeStructure.component_name.asc())
        ).scalars().all()
        print(f"Program: {prog.program_name} (id={prog.program_id}), Semester={semester}")
        print(f"Rows: {len(rows)}")
        print("")
        # Dump raw rows
        for r in rows:
            comp = (r.component_name or '').strip()
            slug = _normalize_component_slug(_slugify_component(comp))
            display = _FEE_NAME_BY_SLUG.get(slug, comp)
            amt = float(r.amount or 0.0)
            print(f"row: component='{comp}', slug='{slug}', display='{display}', amount={amt}, active={bool(getattr(r,'is_active',True))}, frozen={bool(getattr(r,'is_frozen',False))}")

        # Show dedup behaviour by slug
        by_slug = {}
        for r in rows:
            comp = (r.component_name or '').strip()
            slug = _normalize_component_slug(_slugify_component(comp))
            amt = float(r.amount or 0.0)
            display = _FEE_NAME_BY_SLUG.get(slug, comp)
            prev = by_slug.get(slug)
            if not prev or amt > prev['amount']:
                by_slug[slug] = { 'component': display, 'amount': amt }
        total = sum(v['amount'] for v in by_slug.values())
        print("")
        print("Dedup-by-slug summary:")
        for k, v in sorted(by_slug.items()):
            print(f"  {k}: {v['component']} -> {v['amount']}")
        print(f"Total (dedup highest per slug) = {total}")


if __name__ == "__main__":
    main()
