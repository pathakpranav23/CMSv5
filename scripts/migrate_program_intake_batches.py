"""Guarded, idempotent SQLite migration for annual program intake records."""
from __future__ import annotations

import argparse
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path


TABLE_SQL = """
CREATE TABLE IF NOT EXISTS program_intake_batches (
    intake_batch_id INTEGER PRIMARY KEY AUTOINCREMENT,
    program_id_fk INTEGER NOT NULL,
    admission_academic_year VARCHAR(16) NOT NULL,
    approved_intake INTEGER NOT NULL CHECK (approved_intake > 0),
    default_division_capacity INTEGER NOT NULL CHECK (default_division_capacity > 0),
    medium_tag VARCHAR(32) NOT NULL DEFAULT '',
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    approved_by_user_id_fk INTEGER,
    approved_at DATETIME,
    created_at DATETIME,
    updated_at DATETIME,
    FOREIGN KEY(program_id_fk) REFERENCES programs(program_id),
    FOREIGN KEY(approved_by_user_id_fk) REFERENCES users(user_id),
    CONSTRAINT uq_program_intake_batch_scope UNIQUE(program_id_fk, admission_academic_year, medium_tag)
)
"""


def columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')}


def migrate(database: Path, apply: bool, backup_dir: Path) -> None:
    database = database.resolve()
    if not database.is_file():
        raise SystemExit(f"Database not found: {database}")
    connection = sqlite3.connect(str(database))
    try:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        missing = {"students", "programs", "users"} - tables
        if missing:
            raise SystemExit("Migration aborted; required tables missing: " + ", ".join(sorted(missing)))
        student_columns = columns(connection, "students")
        baseline_foreign_key_errors = list(connection.execute("PRAGMA foreign_key_check"))
        actions = []
        if "program_intake_batches" not in tables:
            actions.append("create program_intake_batches")
        if "admission_academic_year" not in student_columns:
            actions.append("add students.admission_academic_year (nullable)")
        if "intake_batch_id_fk" not in student_columns:
            actions.append("add students.intake_batch_id_fk (nullable)")
        print(f"Database: {database}")
        print("Planned changes:")
        for action in actions or ["none; schema is already current"]:
            print(f"  - {action}")
        print(f"Existing students preserved: {connection.execute('SELECT COUNT(*) FROM students').fetchone()[0]}")
        if not apply:
            print("Dry run only. Re-run with --apply after reviewing the target and backup location.")
            return

        backup_dir = backup_dir.expanduser().resolve()
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = backup_dir / f"{database.name}.before_intake_migration_{stamp}"
        connection.commit()
        shutil.copy2(database, backup)
        if not backup.is_file() or backup.stat().st_size != database.stat().st_size:
            raise SystemExit("Migration aborted; backup verification failed.")
        print(f"Verified backup: {backup}")

        connection.execute("PRAGMA foreign_keys=ON")
        with connection:
            connection.execute(TABLE_SQL)
            current = columns(connection, "students")
            if "admission_academic_year" not in current:
                connection.execute("ALTER TABLE students ADD COLUMN admission_academic_year VARCHAR(16)")
            if "intake_batch_id_fk" not in current:
                connection.execute("ALTER TABLE students ADD COLUMN intake_batch_id_fk INTEGER REFERENCES program_intake_batches(intake_batch_id)")
        verified_columns = columns(connection, "students")
        verified_tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "program_intake_batches" not in verified_tables or not {"admission_academic_year", "intake_batch_id_fk"}.issubset(verified_columns):
            raise SystemExit("Migration verification failed; restore the reported backup.")
        foreign_key_errors = list(connection.execute("PRAGMA foreign_key_check"))
        if len(foreign_key_errors) > len(baseline_foreign_key_errors):
            raise SystemExit(
                "Migration verification failed; foreign-key issues increased from "
                f"{len(baseline_foreign_key_errors)} to {len(foreign_key_errors)}. Restore the reported backup."
            )
        if foreign_key_errors:
            print(f"Warning: {len(foreign_key_errors)} pre-existing foreign-key issue(s) remain; the migration added none.")
        print("Migration completed. No student rows were mapped or modified.")
    finally:
        connection.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--backup-dir", type=Path, default=Path("private_backups"))
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    migrate(args.database, args.apply, args.backup_dir)
