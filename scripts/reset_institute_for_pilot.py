"""Safely clear pilot data for one institute while preserving academic setup.

This tool is intentionally SQLite-only because the current PythonAnywhere deployment
uses SQLite.  It is dry-run by default.  It never deletes trusts, institutes,
programs, divisions, subjects, faculty/staff accounts, assignments, timetables, fee
structures, or bank configuration.

It DOES delete the agreed pilot data for the selected institute: students/accounts,
enrollments, attendance, lesson plans, marks/results, materials, announcements,
notifications, imports, follow-up/sync workflow data, and fee payments/receipts.
Their referenced uploads are removed only when --delete-uploads is explicitly given;
that flag also creates a separate upload backup. Audit history is retained; student
actors in existing audit rows are anonymised by setting their actor id to NULL.

Run a preview first.  An apply run creates a timestamped SQLite backup before it
opens the delete transaction.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


CONFIRMATION = "RESET SBPET MAHUVA PILOT DATA"


def _placeholders(values: Iterable[object]) -> str:
    return ",".join("?" for _ in values)


def _rows(connection: sqlite3.Connection, sql: str, params: Iterable[object] = ()) -> list[sqlite3.Row]:
    return list(connection.execute(sql, tuple(params)).fetchall())


def _ids(rows: Iterable[sqlite3.Row], key: str) -> list[object]:
    return [row[key] for row in rows if row[key] is not None]


def _count(connection: sqlite3.Connection, table: str, where: str = "", params: Iterable[object] = ()) -> int:
    suffix = f" WHERE {where}" if where else ""
    return int(connection.execute(f"SELECT COUNT(*) FROM {table}{suffix}", tuple(params)).fetchone()[0])


def _delete(connection: sqlite3.Connection, table: str, where: str, params: Iterable[object]) -> int:
    cursor = connection.execute(f"DELETE FROM {table} WHERE {where}", tuple(params))
    return max(cursor.rowcount, 0)


def _table_names(connection: sqlite3.Connection) -> set[str]:
    return {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}


def _require_tables(connection: sqlite3.Connection) -> None:
    required = {
        "trusts", "institutes", "programs", "students", "users", "attendance",
        "student_subject_enrollments", "fee_payments", "fees_records", "notifications",
        "data_audit_log",
    }
    missing = sorted(required - _table_names(connection))
    if missing:
        raise RuntimeError("Database is not at the required application schema. Missing: " + ", ".join(missing))


def _in_where(column: str, values: list[object]) -> tuple[str, list[object]]:
    if not values:
        return "1 = 0", []
    return f"{column} IN ({_placeholders(values)})", list(values)


def _or_where(parts: list[tuple[str, list[object]]]) -> tuple[str, list[object]]:
    valid = [(sql, values) for sql, values in parts if sql != "1 = 0"]
    if not valid:
        return "1 = 0", []
    return "(" + " OR ".join(f"({sql})" for sql, _ in valid) + ")", [value for _, values in valid for value in values]


def _safe_paths(values: Iterable[object], allowed_roots: list[Path], prefixes: list[tuple[str, Path]] | None = None) -> list[Path]:
    """Resolve only referenced files located inside an explicit application storage root."""
    safe: list[Path] = []
    for raw in values:
        if not raw:
            continue
        value = str(raw).replace("\\", "/").strip()
        candidate = Path(value).expanduser()
        if prefixes:
            for prefix, root in prefixes:
                if value.startswith(prefix):
                    candidate = root / value[len(prefix):].lstrip("/")
                    break
        for root in allowed_roots:
            root = root.resolve()
            possible = candidate if candidate.is_absolute() else (root / candidate)
            try:
                resolved = possible.resolve()
                resolved.relative_to(root)
            except (OSError, ValueError):
                continue
            safe.append(resolved)
            break
    return list(dict.fromkeys(safe))


def _backup_database(source: Path, backup_dir: Path) -> Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    destination = backup_dir / f"cms.db.before_pilot_reset_{stamp}"
    with sqlite3.connect(source) as source_connection, sqlite3.connect(destination) as backup_connection:
        source_connection.backup(backup_connection)
    with sqlite3.connect(destination) as verification_connection:
        integrity = verification_connection.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok":
        raise RuntimeError(f"Backup integrity check failed for {destination}: {integrity}")
    return destination


def _backup_uploads(paths: list[Path], backup_dir: Path) -> Path:
    """Copy only the selected uploaded files before they are removed."""
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    destination = backup_dir / f"uploads.before_pilot_reset_{stamp}"
    destination.mkdir(parents=True, exist_ok=False)
    copied = 0
    for path in paths:
        if not path.exists():
            continue
        target = destination / f"{copied:04d}_{path.name}"
        if path.is_dir():
            shutil.copytree(path, target)
        else:
            shutil.copy2(path, target)
        copied += 1
    (destination / "README.txt").write_text(
        f"Backup of {copied} pilot-reset upload paths created {datetime.now(timezone.utc).isoformat()}\n",
        encoding="utf-8",
    )
    return destination


def _context(connection: sqlite3.Connection, trust_name: str, institute_name: str) -> dict[str, object]:
    trust_rows = _rows(connection, "SELECT trust_id, trust_name FROM trusts WHERE lower(trim(trust_name)) = lower(trim(?))", [trust_name])
    if len(trust_rows) != 1:
        raise RuntimeError(f"Expected exactly one Trust named {trust_name!r}; found {len(trust_rows)}.")
    trust_id = int(trust_rows[0]["trust_id"])
    institute_rows = _rows(
        connection,
        "SELECT institute_id, institute_name FROM institutes "
        "WHERE trust_id_fk = ? AND lower(trim(institute_name)) = lower(trim(?))",
        [trust_id, institute_name],
    )
    if len(institute_rows) != 1:
        raise RuntimeError(f"Expected exactly one Institute named {institute_name!r} under the selected Trust; found {len(institute_rows)}.")
    institute_id = int(institute_rows[0]["institute_id"])
    program_ids = _ids(_rows(connection, "SELECT program_id FROM programs WHERE institute_id_fk = ?", [institute_id]), "program_id")
    division_ids = _ids(_rows(connection, f"SELECT division_id FROM divisions WHERE program_id_fk IN ({_placeholders(program_ids)})", program_ids), "division_id") if program_ids else []
    subject_ids = _ids(_rows(connection, f"SELECT subject_id FROM subjects WHERE program_id_fk IN ({_placeholders(program_ids)})", program_ids), "subject_id") if program_ids else []

    # Institute scope is deliberately based on its programs, not its entire Trust.
    # A Trust may own more than one institute, and a reset must never cross that boundary.
    student_where, student_params = _in_where("program_id_fk", program_ids)
    student_rows = _rows(connection, f"SELECT enrollment_no, user_id_fk, photo_url FROM students WHERE {student_where}", student_params)
    student_ids = _ids(student_rows, "enrollment_no")
    student_user_ids = _ids(student_rows, "user_id_fk")
    orphan_student_user_rows = _rows(
        connection,
        f"SELECT user_id FROM users WHERE lower(role) = 'student' AND program_id_fk IN ({_placeholders(program_ids)})",
        program_ids,
    ) if program_ids else []
    student_user_ids = list(dict.fromkeys(student_user_ids + _ids(orphan_student_user_rows, "user_id")))

    return {
        "trust_id": trust_id,
        "institute_id": institute_id,
        "program_ids": program_ids,
        "division_ids": division_ids,
        "subject_ids": subject_ids,
        "student_rows": student_rows,
        "student_ids": student_ids,
        "student_user_ids": student_user_ids,
    }


def _preview(connection: sqlite3.Connection, scope: dict[str, object]) -> dict[str, int]:
    student_ids = scope["student_ids"]
    subject_ids = scope["subject_ids"]
    program_ids = scope["program_ids"]
    trust_id = scope["trust_id"]
    report: dict[str, int] = {
        "students": len(student_ids),
        "student accounts": len(scope["student_user_ids"]),
    }
    targets = {
        "attendance": _or_where([_in_where("student_id_fk", student_ids), _in_where("subject_id_fk", subject_ids)]),
        "subject enrollments": _or_where([_in_where("student_id_fk", student_ids), _in_where("subject_id_fk", subject_ids)]),
        "grades": _or_where([_in_where("student_id_fk", student_ids), _in_where("subject_id_fk", subject_ids)]),
        "exam marks": _or_where([_in_where("student_id_fk", student_ids), _in_where("subject_id_fk", subject_ids)]),
        "semester results": _or_where([_in_where("student_id_fk", student_ids), _in_where("program_id_fk", program_ids)]),
        "credit logs": _or_where([_in_where("student_id_fk", student_ids), _in_where("subject_id_fk", subject_ids)]),
        "fee payments": _or_where([_in_where("enrollment_no", student_ids), _in_where("program_id_fk", program_ids)]),
        "fee records": _in_where("student_id_fk", student_ids),
        "notifications": _in_where("student_id_fk", student_ids),
        "follow-up tasks": _or_where([_in_where("student_id_fk", student_ids), _in_where("program_id_fk", program_ids)]),
        "import logs": _in_where("program_id_fk", program_ids),
        "enrollment sync requests": _or_where([_in_where("subject_id_fk", subject_ids), _in_where("division_id_fk", scope["division_ids"])]),
        "student purge requests": _in_where("program_id_fk", program_ids),
    }
    table_map = {
        "attendance": "attendance", "subject enrollments": "student_subject_enrollments", "grades": "grades",
        "exam marks": "exam_marks", "semester results": "student_semester_results", "credit logs": "student_credit_log",
        "fee payments": "fee_payments", "fee records": "fees_records", "notifications": "notifications",
        "follow-up tasks": "student_follow_up_tasks", "import logs": "import_logs",
        "enrollment sync requests": "enrollment_sync_requests", "student purge requests": "student_purge_requests",
    }
    present = _table_names(connection)
    for label, (where, params) in targets.items():
        report[label] = _count(connection, table_map[label], where, params) if table_map[label] in present else 0

    material_where, material_params = _in_where("subject_id_fk", subject_ids)
    report["materials"] = _count(connection, "subject_materials", material_where, material_params) if "subject_materials" in present else 0
    plan_where, plan_params = _or_where([_in_where("subject_id_fk", subject_ids), _in_where("division_id_fk", scope["division_ids"])])
    report["lesson plans"] = _count(connection, "lesson_plans", plan_where, plan_params) if "lesson_plans" in present else 0
    # Trust-wide announcements may be shared with another institute.  They are not
    # safely attributable to this one institute in the current schema, so preserve them.
    announcement_where, announcement_params = _in_where("program_id_fk", program_ids)
    report["announcements"] = _count(connection, "announcements", announcement_where, announcement_params) if "announcements" in present else 0
    return report


def _apply(connection: sqlite3.Connection, scope: dict[str, object], app_root: Path) -> tuple[dict[str, int], list[Path]]:
    """Perform one transaction. Any missing dependent table causes a rollback."""
    tables = _table_names(connection)
    students = scope["student_ids"]
    student_users = scope["student_user_ids"]
    programs = scope["program_ids"]
    subjects = scope["subject_ids"]
    divisions = scope["division_ids"]
    trust_id = scope["trust_id"]
    deleted: dict[str, int] = {}
    uploads: list[Path] = []

    def delete_if_present(label: str, table: str, where: str, params: list[object]) -> None:
        deleted[label] = _delete(connection, table, where, params) if table in tables else 0

    attendance_where, attendance_params = _or_where([_in_where("student_id_fk", students), _in_where("subject_id_fk", subjects)])
    enrollment_where, enrollment_params = _or_where([_in_where("student_id_fk", students), _in_where("subject_id_fk", subjects)])
    result_where, result_params = _or_where([_in_where("student_id_fk", students), _in_where("program_id_fk", programs)])
    mark_where, mark_params = _or_where([_in_where("student_id_fk", students), _in_where("subject_id_fk", subjects)])
    payment_where, payment_params = _or_where([_in_where("enrollment_no", students), _in_where("program_id_fk", programs)])
    plan_where, plan_params = _or_where([_in_where("subject_id_fk", subjects), _in_where("division_id_fk", divisions)])
    material_where, material_params = _in_where("subject_id_fk", subjects)
    announcement_where, announcement_params = _or_where([("trust_id_fk = ?", [trust_id]), _in_where("program_id_fk", programs)])

    payment_rows = _rows(connection, f"SELECT payment_id, proof_image_path FROM fee_payments WHERE {payment_where}", payment_params) if "fee_payments" in tables else []
    payment_ids = _ids(payment_rows, "payment_id")
    material_rows = _rows(connection, f"SELECT material_id, file_path FROM subject_materials WHERE {material_where}", material_params) if "subject_materials" in tables else []
    material_ids = _ids(material_rows, "material_id")
    revision_paths = _rows(connection, f"SELECT file_path FROM material_revisions WHERE material_id_fk IN ({_placeholders(material_ids)})", material_ids) if material_ids and "material_revisions" in tables else []
    draft_rows = _rows(connection, f"SELECT file_path FROM lesson_plan_import_drafts WHERE {plan_where}", plan_params) if "lesson_plan_import_drafts" in tables else []
    plan_rows = _rows(connection, f"SELECT plan_id FROM lesson_plans WHERE {plan_where}", plan_params) if "lesson_plans" in tables else []
    plan_ids = _ids(plan_rows, "plan_id")
    unit_rows = _rows(connection, f"SELECT unit_id FROM lesson_plan_units WHERE plan_id_fk IN ({_placeholders(plan_ids)})", plan_ids) if plan_ids and "lesson_plan_units" in tables else []
    unit_ids = _ids(unit_rows, "unit_id")
    topic_rows = _rows(connection, f"SELECT topic_id FROM lesson_plan_topics WHERE unit_id_fk IN ({_placeholders(unit_ids)})", unit_ids) if unit_ids and "lesson_plan_topics" in tables else []
    topic_ids = _ids(topic_rows, "topic_id")
    announcement_rows = _rows(connection, f"SELECT announcement_id FROM announcements WHERE {announcement_where}", announcement_params) if "announcements" in tables else []
    announcement_ids = _ids(announcement_rows, "announcement_id")

    # Child records must be removed before their parents while SQLite FK enforcement is enabled.
    notification_where, notification_params = _or_where([_in_where("student_id_fk", students), _in_where("payment_id_fk", payment_ids)])
    delete_if_present("notifications", "notifications", notification_where, notification_params)
    delete_if_present("fee payments", "fee_payments", payment_where, payment_params)
    delete_if_present("fee records", "fees_records", _in_where("student_id_fk", students)[0], _in_where("student_id_fk", students)[1])
    delete_if_present("attendance", "attendance", attendance_where, attendance_params)
    delete_if_present("subject enrollments", "student_subject_enrollments", enrollment_where, enrollment_params)
    delete_if_present("grades", "grades", mark_where, mark_params)
    delete_if_present("exam marks", "exam_marks", mark_where, mark_params)
    delete_if_present("semester results", "student_semester_results", result_where, result_params)
    delete_if_present("credit logs", "student_credit_log", mark_where, mark_params)
    delete_if_present("alumni", "alumni", _in_where("enrollment_no", students)[0], _in_where("enrollment_no", students)[1])
    follow_where, follow_params = _or_where([_in_where("student_id_fk", students), _in_where("program_id_fk", programs)])
    delete_if_present("follow-up tasks", "student_follow_up_tasks", follow_where, follow_params)
    sync_where, sync_params = _or_where([_in_where("subject_id_fk", subjects), _in_where("division_id_fk", divisions)])
    delete_if_present("enrollment sync requests", "enrollment_sync_requests", sync_where, sync_params)
    purge_where, purge_params = _in_where("program_id_fk", programs)
    delete_if_present("student purge requests", "student_purge_requests", purge_where, purge_params)
    delete_if_present("import logs", "import_logs", _in_where("program_id_fk", programs)[0], _in_where("program_id_fk", programs)[1])

    delete_if_present("material logs", "subject_material_logs", _in_where("material_id_fk", material_ids)[0], _in_where("material_id_fk", material_ids)[1])
    delete_if_present("material revisions", "material_revisions", _in_where("material_id_fk", material_ids)[0], _in_where("material_id_fk", material_ids)[1])
    delete_if_present("materials", "subject_materials", material_where, material_params)

    delete_if_present("lesson deliveries", "lesson_plan_deliveries", _in_where("topic_id_fk", topic_ids)[0], _in_where("topic_id_fk", topic_ids)[1])
    delete_if_present("lesson topics", "lesson_plan_topics", _in_where("unit_id_fk", unit_ids)[0], _in_where("unit_id_fk", unit_ids)[1])
    delete_if_present("lesson units", "lesson_plan_units", _in_where("plan_id_fk", plan_ids)[0], _in_where("plan_id_fk", plan_ids)[1])
    delete_if_present("lesson plans", "lesson_plans", plan_where, plan_params)
    delete_if_present("lesson import drafts", "lesson_plan_import_drafts", plan_where, plan_params)

    dismiss_where, dismiss_params = _or_where([_in_where("announcement_id_fk", announcement_ids), _in_where("user_id_fk", student_users)])
    delete_if_present("announcement dismissals", "announcement_dismissals", dismiss_where, dismiss_params)
    recipient_where, recipient_params = _or_where([_in_where("announcement_id_fk", announcement_ids), _in_where("student_id_fk", students)])
    delete_if_present("announcement recipients", "announcement_recipients", recipient_where, recipient_params)
    delete_if_present("announcement audiences", "announcement_audience", _in_where("announcement_id_fk", announcement_ids)[0], _in_where("announcement_id_fk", announcement_ids)[1])
    delete_if_present("announcement revisions", "announcement_revisions", _in_where("announcement_id_fk", announcement_ids)[0], _in_where("announcement_id_fk", announcement_ids)[1])
    delete_if_present("announcements", "announcements", announcement_where, announcement_params)

    delete_if_present("system message reads", "system_message_reads", _in_where("user_id_fk", student_users)[0], _in_where("user_id_fk", student_users)[1])
    delete_if_present("password change logs", "password_change_log", _or_where([_in_where("user_id_fk", student_users), _in_where("changed_by_user_id_fk", student_users)])[0], _or_where([_in_where("user_id_fk", student_users), _in_where("changed_by_user_id_fk", student_users)])[1])
    if "data_audit_log" in tables and student_users:
        connection.execute(f"UPDATE data_audit_log SET actor_user_id_fk = NULL WHERE actor_user_id_fk IN ({_placeholders(student_users)})", student_users)
    delete_if_present("students", "students", _in_where("program_id_fk", programs)[0], _in_where("program_id_fk", programs)[1])
    delete_if_present("student accounts", "users", _in_where("user_id", student_users)[0], _in_where("user_id", student_users)[1])

    # Add the retained audit marker last, inside the same transaction as all deletes.
    marker_counts = ", ".join(f"{name}={count}" for name, count in sorted(deleted.items()))
    connection.execute(
        "INSERT INTO data_audit_log (action, actor_user_id_fk, actor_role, trust_id_fk, selection_json, counts_json, created_at) "
        "VALUES (?, NULL, ?, ?, ?, ?, ?)",
        (
            "pilot_reset",
            "system",
            trust_id,
            '{"scope":"institution pilot reset","academic_setup":"preserved"}',
            '{"deleted":"' + marker_counts.replace('"', "'") + '"}',
            datetime.now(timezone.utc).isoformat(),
        ),
    )

    static_root = app_root / "cms_app" / "static"
    instance_root = app_root / "instance"
    uploads.extend(_safe_paths(
        _ids(payment_rows, "proof_image_path"),
        [static_root / "uploads" / "payment_proofs"],
        [("uploads/payment_proofs/", static_root / "uploads" / "payment_proofs")],
    ))
    uploads.extend(_safe_paths(
        _ids(material_rows, "file_path") + _ids(revision_paths, "file_path"),
        [instance_root / "materials", static_root / "materials"],
        [
            ("private/materials/", instance_root / "materials"),
            ("/static/materials/", static_root / "materials"),
            ("static/materials/", static_root / "materials"),
        ],
    ))
    uploads.extend(_safe_paths(_ids(draft_rows, "file_path"), [instance_root / "lesson_plan_imports"]))
    uploads.extend(_safe_paths(
        _ids(scope["student_rows"], "photo_url"),
        [static_root / "student_photos"],
        [("/static/student_photos/", static_root / "student_photos")],
    ))
    for announcement_id in announcement_ids:
        uploads.append((static_root / "uploads" / "announcements" / str(announcement_id)).resolve())
    return deleted, uploads


def _remove_uploads(paths: list[Path], app_root: Path) -> tuple[int, list[str]]:
    removed = 0
    warnings: list[str] = []
    allowed_roots = [
        (app_root / "instance").resolve(),
        (app_root / "cms_app" / "static" / "student_photos").resolve(),
        (app_root / "cms_app" / "static" / "materials").resolve(),
        (app_root / "cms_app" / "static" / "uploads" / "payment_proofs").resolve(),
        (app_root / "cms_app" / "static" / "uploads" / "announcements").resolve(),
    ]
    for path in paths:
        try:
            resolved = path.resolve()
            if not any(resolved.is_relative_to(root) for root in allowed_roots):
                warnings.append(f"Skipped unsafe path: {path}")
                continue
            if resolved.is_dir():
                shutil.rmtree(resolved)
                removed += 1
            elif resolved.is_file():
                resolved.unlink()
                removed += 1
        except FileNotFoundError:
            continue
        except OSError as exc:
            warnings.append(f"Could not remove {path}: {exc}")
    return removed, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Preview or apply a guarded institute pilot-data reset.")
    parser.add_argument("--database", required=True, help="Absolute path to the target SQLite cms.db")
    parser.add_argument("--trust", required=True, help="Exact Trust name")
    parser.add_argument("--institute", required=True, help="Exact Institute name under that Trust")
    parser.add_argument("--app-root", default=str(Path(__file__).resolve().parents[1]), help="Application root; normally ~/mysite")
    parser.add_argument("--backup-dir", default=None, help="Directory for the mandatory pre-reset database backup")
    parser.add_argument("--apply", action="store_true", help="Perform the reset. Omit for a read-only preview.")
    parser.add_argument("--delete-uploads", action="store_true", help="Also back up and remove the selected uploaded files after the database reset.")
    parser.add_argument("--confirm", default="", help=f"Required with --apply: {CONFIRMATION!r}")
    args = parser.parse_args()

    database = Path(args.database).expanduser().resolve()
    app_root = Path(args.app_root).expanduser().resolve()
    backup_dir = Path(args.backup_dir).expanduser().resolve() if args.backup_dir else app_root / "private_backups"
    if not database.is_file():
        raise FileNotFoundError(f"SQLite database not found: {database}")
    if args.apply and args.confirm != CONFIRMATION:
        raise RuntimeError(f"Refusing to delete data. Use --confirm {CONFIRMATION!r} exactly.")

    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 30000")
        connection.execute("PRAGMA foreign_keys = ON")
        _require_tables(connection)
        scope = _context(connection, args.trust, args.institute)
        print(f"Target: Trust #{scope['trust_id']} / Institute #{scope['institute_id']}")
        print(f"Academic setup preserved: {len(scope['program_ids'])} programs, {len(scope['division_ids'])} divisions, {len(scope['subject_ids'])} subjects.")
        print("\nDeletion preview:")
        for label, count in _preview(connection, scope).items():
            print(f"  {label}: {count}")
        if not args.apply:
            print("\nDry run only: no backup and no data changed. Review the counts, then rerun with --apply and the exact confirmation phrase.")
            return 0

    # The backup is intentionally completed before the delete transaction is opened.
    backup_path = _backup_database(database, backup_dir)
    print(f"\nVerified pre-reset backup created: {backup_path}")
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 30000")
        connection.execute("PRAGMA foreign_keys = ON")
        _require_tables(connection)
        scope = _context(connection, args.trust, args.institute)
        with connection:
            deleted, uploads = _apply(connection, scope, app_root)
        print("\nReset committed. Deleted rows:")
        for label, count in sorted(deleted.items()):
            print(f"  {label}: {count}")
        if args.delete_uploads:
            upload_backup = _backup_uploads(uploads, backup_dir)
            print(f"Referenced uploads backed up: {upload_backup}")
            removed, warnings = _remove_uploads(uploads, app_root)
            print(f"Referenced upload paths removed after commit: {removed}")
            for warning in warnings:
                print(f"WARNING: {warning}")
        else:
            print(f"Referenced upload paths retained (use --delete-uploads to back up and remove {len(uploads)} paths).")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"RESET ABORTED: {exc}", file=sys.stderr)
        raise SystemExit(1)
