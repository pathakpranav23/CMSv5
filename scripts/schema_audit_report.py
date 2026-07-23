import argparse
import json
import os
import sys
from pathlib import Path

from sqlalchemy import inspect as sa_inspect


def _project_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _ensure_project_root_on_path() -> None:
    root = _project_root()
    if root not in sys.path:
        sys.path.insert(0, root)


def _sqlite_url_from_path(db_path: str) -> str:
    p = Path(db_path).expanduser().resolve()
    return f"sqlite:///{p.as_posix()}"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="schema_audit_report")
    parser.add_argument("--db", dest="db_path", default=None)
    parser.add_argument("--database-url", dest="database_url", default=None)
    parser.add_argument("--json", dest="json_output", action="store_true")
    parser.add_argument("--include-extras", dest="include_extras", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    _ensure_project_root_on_path()

    if args.database_url:
        os.environ["DATABASE_URL"] = args.database_url
    elif args.db_path:
        os.environ["DATABASE_URL"] = _sqlite_url_from_path(args.db_path)

    from cms_app import create_app, db

    app = create_app()

    ignore_actual_tables = {"alembic_version", "sqlite_sequence"}
    ignore_missing_tables = set()

    report: dict = {
        "database_url": app.config.get("SQLALCHEMY_DATABASE_URI"),
        "missing_tables": [],
        "tables": {},
        "actual_only_tables": [],
        "summary": {
            "expected_tables": 0,
            "actual_tables": 0,
            "tables_with_missing_columns": 0,
            "missing_columns_total": 0,
        },
    }

    with app.app_context():
        inspector = sa_inspect(db.engine)
        actual_tables = set(inspector.get_table_names())
        expected_tables = set(db.metadata.tables.keys())

        report["summary"]["expected_tables"] = len(expected_tables)
        report["summary"]["actual_tables"] = len(actual_tables)

        for t in sorted(expected_tables):
            expected_cols = sorted({c.name for c in db.metadata.tables[t].columns})
            if t not in actual_tables and t not in ignore_missing_tables:
                report["missing_tables"].append(t)
                continue

            actual_cols = sorted({c["name"] for c in inspector.get_columns(t)})
            missing_cols = sorted(set(expected_cols) - set(actual_cols))
            extra_cols = sorted(set(actual_cols) - set(expected_cols))

            if missing_cols:
                report["summary"]["tables_with_missing_columns"] += 1
                report["summary"]["missing_columns_total"] += len(missing_cols)

            entry: dict = {
                "missing_columns": missing_cols,
            }
            if args.include_extras:
                entry["extra_columns"] = extra_cols
            report["tables"][t] = entry

        report["actual_only_tables"] = sorted(
            [t for t in (actual_tables - expected_tables) if t not in ignore_actual_tables]
        )

    if args.json_output:
        sys.stdout.write(json.dumps(report, indent=2, sort_keys=True))
        sys.stdout.write("\n")
    else:
        sys.stdout.write(f"DB: {report['database_url']}\n")
        sys.stdout.write(f"Expected tables: {report['summary']['expected_tables']}\n")
        sys.stdout.write(f"Actual tables: {report['summary']['actual_tables']}\n")
        if report["missing_tables"]:
            sys.stdout.write("\nMissing tables:\n")
            for t in report["missing_tables"]:
                sys.stdout.write(f"- {t}\n")

        sys.stdout.write("\nMissing columns:\n")
        any_missing = False
        for t in sorted(report["tables"].keys()):
            missing = report["tables"][t].get("missing_columns") or []
            if not missing:
                continue
            any_missing = True
            sys.stdout.write(f"- {t}: {', '.join(missing)}\n")
        if not any_missing:
            sys.stdout.write("- none\n")

        if report["actual_only_tables"] and args.include_extras:
            sys.stdout.write("\nActual-only tables:\n")
            for t in report["actual_only_tables"]:
                sys.stdout.write(f"- {t}\n")

        sys.stdout.write("\nSummary:\n")
        sys.stdout.write(f"- Tables with missing columns: {report['summary']['tables_with_missing_columns']}\n")
        sys.stdout.write(f"- Missing columns total: {report['summary']['missing_columns_total']}\n")

    has_mismatch = bool(report["missing_tables"]) or (report["summary"]["missing_columns_total"] > 0)
    return 2 if has_mismatch else 0


if __name__ == "__main__":
    raise SystemExit(main())

