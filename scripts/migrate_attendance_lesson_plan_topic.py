"""Add the optional lesson-plan topic link to attendance, safely and idempotently.

Run this exact script against both local and PythonAnywhere databases after deploying
the matching application commit.  It does not update or delete existing attendance.
"""

import argparse
import os
import sqlite3
import sys


def resolve_path(value: str) -> str:
    value = (value or "cms.db").strip()
    if value.startswith("sqlite:///"):
        return value.removeprefix("sqlite:///")
    return value


def migrate(database: str) -> None:
    db_path = resolve_path(database)
    if not os.path.isfile(db_path):
        raise FileNotFoundError(f"SQLite database not found: {db_path}")
    with sqlite3.connect(db_path) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(attendance)")}
        if "lesson_plan_topic_id_fk" not in columns:
            connection.execute(
                "ALTER TABLE attendance ADD COLUMN lesson_plan_topic_id_fk "
                "INTEGER REFERENCES lesson_plan_topics(topic_id)"
            )
            connection.commit()
            print("Added attendance.lesson_plan_topic_id_fk")
        else:
            print("attendance.lesson_plan_topic_id_fk already exists; no change made")
        connection.execute(
            "CREATE INDEX IF NOT EXISTS ix_attendance_lesson_plan_topic_id_fk "
            "ON attendance (lesson_plan_topic_id_fk)"
        )
        verified = {row[1] for row in connection.execute("PRAGMA table_info(attendance)")}
        if "lesson_plan_topic_id_fk" not in verified:
            raise RuntimeError("Migration did not create lesson_plan_topic_id_fk")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Safely link attendance rows to lesson-plan topics.")
    parser.add_argument("--database", default=os.environ.get("DATABASE_URL", "cms.db"), help="SQLite path or sqlite:/// URL")
    args = parser.parse_args()
    try:
        migrate(args.database)
    except Exception as exc:
        print(f"Migration failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
