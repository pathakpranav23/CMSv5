"""P0-3 migration: Move fee payment proofs out of /static/ into instance_path.

Fee payment proofs (bank-account screenshots, UTR confirmations, PDFs, etc.)
are personal financial PII and must NOT be downloadable by any URL.  They
previously lived under ``cms_app/static/uploads/payment_proofs/`` — reachable
by any unauthenticated visitor who knew (or guessed) the filename.  As of
P0-3 they are stored in ``app.config['PAYMENT_PROOFS_STORAGE_DIR']`` (default:
``<instance_path>/payment_proofs``) and served ONLY through the authenticated
``main.download_payment_proof`` route, which checks owner/trust scope.

This one-shot migration does two things:

1. **Files**: Copy every existing file from the legacy
   ``cms_app/static/uploads/payment_proofs/`` directory into the new
   ``PAYMENT_PROOFS_STORAGE_DIR`` directory.  We *copy* (not move) so that if
   the migration is interrupted or you run it twice, neither the legacy files
   nor the migrated copies are lost.
2. **Database rows**: Any ``fee_payments.proof_image_path`` value that still
   starts with ``uploads/payment_proofs/`` (the old storage prefix) is
   re-written in place to just the file *basename* so the new download route
   can serve it with ``send_from_directory``.

Rollback-safe
-------------
If you need to roll back the app code but keep data safe:
* Files remain both in ``static/uploads/payment_proofs`` and in
  ``<instance_path>/payment_proofs`` after this script finishes; there is
  no destructive filesystem operation.
* The UPDATE is idempotent — run it again any number of times on the same
  DB and it will correctly no-op on rows already normalized.

Run once after deploying P0-3:

    $ env FLASK_APP=app.py python -c \\
        "from cms_app.scripts.migrate_payment_proofs_to_instance import run; run()"
"""

from __future__ import annotations

import os
import shutil


def _copy_proofs(legacy_dir: str, instance_dir: str) -> tuple[int, int]:
    copied = 0
    total = 0
    if not os.path.isdir(legacy_dir):
        return copied, total
    os.makedirs(instance_dir, exist_ok=True)
    for name in sorted(os.listdir(legacy_dir)):
        src = os.path.join(legacy_dir, name)
        if not os.path.isfile(src):
            continue
        total += 1
        dst = os.path.join(instance_dir, name)
        if os.path.exists(dst) and os.path.getsize(dst) == os.path.getsize(src):
            # Already copied; skip to keep the script idempotent / cheap on
            # second runs where the DB is the only thing that still needs work.
            continue
        # copy2 preserves mtime/metadata so admin filesystem inspection still
        # shows when each proof was originally uploaded.
        shutil.copy2(src, dst)
        copied += 1
    return copied, total


def run() -> None:
    from cms_app import create_app
    from cms_app import db
    from sqlalchemy import text, bindparam, String, select

    app = create_app()
    with app.app_context():
        legacy_dir = os.path.join(app.root_path, "static", "uploads", "payment_proofs")
        instance_dir = app.config["PAYMENT_PROOFS_STORAGE_DIR"]
        print(f"[P0-3] Legacy payment-proofs dir : {legacy_dir}")
        print(f"[P0-3] Instance payment-proofs dir: {instance_dir}")

        copied, total = _copy_proofs(legacy_dir, instance_dir)
        print(f"[P0-3] Copied {copied}/{total} proof files to instance dir.")

        # 1. Discover which rows still carry the old "uploads/payment_proofs/"
        #    prefix.  We do this with a LIKE rather than a Python-side scan so
        #    large fee_payments tables still complete instantly.
        legacy_prefix = os.path.join("uploads", "payment_proofs").replace("\\", "/") + "/"
        # Construct a platform-specific LIKE prefix as well, since prior
        # _save_payment_proof used .replace("\\", "/") but some manual DB
        # edits might have left backslashes in.
        legacy_prefix_alt = os.path.join("uploads", "payment_proofs") + os.sep

        detect_sql = text(
            "SELECT payment_id, proof_image_path FROM fee_payments "
            "WHERE proof_image_path IS NOT NULL AND "
            "     (proof_image_path LIKE :like1 OR proof_image_path LIKE :like2)"
        )
        detect_sql = detect_sql.bindparams(
            bindparam("like1", type_=String),
            bindparam("like2", type_=String),
        )
        rows = db.session.execute(
            detect_sql,
            {"like1": legacy_prefix + "%", "like2": legacy_prefix_alt + "%"},
        ).all()
        print(f"[P0-3] fee_payments rows still referencing legacy path: {len(rows)}")

        updated = 0
        skipped = 0
        for payment_id, path in rows:
            if not path:
                continue
            # Normalize separators for a consistent strip operation
            normalized = path.replace("\\", "/")
            if normalized.startswith(legacy_prefix):
                basename = normalized[len(legacy_prefix):]
            else:
                # Unexpected prefix shape; leave alone so admins can spot-check
                skipped += 1
                continue
            if not basename or basename in {".", ".."} or "/" in basename:
                skipped += 1
                continue
            db.session.execute(
                text("UPDATE fee_payments SET proof_image_path = :basename WHERE payment_id = :pid"),
                {"basename": basename, "pid": payment_id},
            )
            updated += 1
        db.session.commit()
        print(f"[P0-3] Updated {updated} rows; skipped {skipped} rows with unusual paths.")
        print("[P0-3] Migration complete. Run the test suite (pytest -q) to confirm green.")


if __name__ == "__main__":
    run()
