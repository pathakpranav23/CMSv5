"""P7-D migration: Add ``trust_id_fk`` columns to three log tables.

SQLite has limited ``ALTER TABLE`` support, so each ALTER is guarded by a
column-exists check and run through raw ``db.engine``.  After adding the
columns we backfill trust values for historic rows using the same
``_backfill_trust_for_log`` resolution order documented in
``cms_app.tenant.py`` (direct column → program_id_fk → actor/changed_by
user → student).

Columns added
-------------
* ``password_change_log.trust_id_fk``   (was missing)
* ``import_logs.trust_id_fk``           (was missing)
* ``subject_material_logs.trust_id_fk`` (was missing)

``data_audit_log.trust_id_fk`` was already present in the schema (verified
against ``cms_app.models.DataAuditLog``) so no ALTER is needed for it.

Run locally once after deploying P7:

    $ env FLASK_APP=app.py python -c "from cms_app.scripts.add_trust_id_columns_to_logs import run; run()"
"""

from __future__ import annotations

import os
import sys

from sqlalchemy import text


def _column_exists(engine, table: str, column: str) -> bool:
    from sqlalchemy import inspect as sa_inspect
    insp = sa_inspect(engine)
    try:
        cols = [c["name"] for c in insp.get_columns(table)]
    except Exception:
        return False
    return column in cols


def add_trust_id_to_password_change_log(engine):
    """Add trust_id_fk column + index + backfill to password_change_log."""
    table = "password_change_log"
    col = "trust_id_fk"
    if _column_exists(engine, table, col):
        return 0
    with engine.begin() as conn:
        def _do(sql_text):
            if isinstance(sql_text, str):
                conn.execute(text(sql_text))
            else:
                conn.execute(sql_text)
        _do(f"ALTER TABLE {table} ADD COLUMN {col} INTEGER")
        try:
            _do(f"CREATE INDEX ix_{table}_{col} ON {table}({col})")
        except Exception:
            pass
        conn.execute(
            text(
                f"""
                UPDATE {table}
                SET trust_id_fk = COALESCE(
                    (SELECT users.trust_id_fk FROM users
                     WHERE users.user_id = {table}.changed_by_user_id_fk),
                    (SELECT users.trust_id_fk FROM users
                     WHERE users.user_id = {table}.user_id_fk)
                )
                WHERE {table}.trust_id_fk IS NULL
                """
            )
        )
    return 1


def add_trust_id_to_import_logs(engine):
    table = "import_logs"
    col = "trust_id_fk"
    if _column_exists(engine, table, col):
        return 0
    with engine.begin() as conn:
        def _do(sql_text):
            if isinstance(sql_text, str):
                conn.execute(text(sql_text))
            else:
                conn.execute(sql_text)
        _do(f"ALTER TABLE {table} ADD COLUMN {col} INTEGER")
        try:
            _do(f"CREATE INDEX ix_{table}_{col} ON {table}({col})")
        except Exception:
            pass
        conn.execute(
            text(
                f"""
                UPDATE {table}
                SET trust_id_fk = COALESCE(
                    (SELECT institutes.trust_id_fk
                     FROM programs
                     JOIN institutes ON programs.institute_id_fk = institutes.institute_id
                     WHERE programs.program_id = {table}.program_id_fk),
                    (SELECT users.trust_id_fk FROM users
                     WHERE users.user_id = {table}.user_id_fk)
                )
                WHERE {table}.trust_id_fk IS NULL
                """
            )
        )
    return 1


def add_trust_id_to_subject_material_logs(engine):
    table = "subject_material_logs"
    col = "trust_id_fk"
    if _column_exists(engine, table, col):
        return 0
    with engine.begin() as conn:
        def _do(sql_text):
            if isinstance(sql_text, str):
                conn.execute(text(sql_text))
            else:
                conn.execute(sql_text)
        _do(f"ALTER TABLE {table} ADD COLUMN {col} INTEGER")
        try:
            _do(f"CREATE INDEX ix_{table}_{col} ON {table}({col})")
        except Exception:
            pass
        conn.execute(
            text(
                f"""
                UPDATE {table}
                SET trust_id_fk = COALESCE(
                    (SELECT users.trust_id_fk FROM users
                     WHERE users.user_id = {table}.actor_user_id_fk),
                    (SELECT institutes.trust_id_fk
                     FROM subject_materials
                     JOIN subjects ON subjects.subject_id = subject_materials.subject_id_fk
                     JOIN programs ON programs.program_id = subjects.program_id_fk
                     JOIN institutes ON institutes.institute_id = programs.institute_id_fk
                     WHERE subject_materials.material_id = {table}.material_id_fk)
                )
                WHERE {table}.trust_id_fk IS NULL
                """
            )
        )
    return 1


def run(app=None, engine=None) -> dict:
    if engine is None:
        if app is None:
            # Fall back to importing the app if no engine/app was provided.
            here = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.abspath(os.path.join(here, "..", ".."))
            sys.path.insert(0, project_root)
            try:
                from app import create_app  # type: ignore
            except Exception:
                from app import app as _app  # type: ignore
                app = _app
            else:
                app = create_app()
        engine = app.extensions["sqlalchemy"].db.engine
    applied = 0
    results = {}
    for name, fn in (
        ("password_change_log", add_trust_id_to_password_change_log),
        ("import_logs", add_trust_id_to_import_logs),
        ("subject_material_logs", add_trust_id_to_subject_material_logs),
    ):
        n = fn(engine)
        applied += n
        results[name] = "ALTER applied + backfilled" if n else "column already present"
    results["_total_migrations_applied"] = applied
    return results


if __name__ == "__main__":
    import json as _json
    print(_json.dumps(run(), indent=2, default=str))
