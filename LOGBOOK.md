# Project Logbook

This logbook tracks daily changes, updates, and fixes applied to the CMSv5 ERP system. Use this to monitor progress and rollback changes if necessary.

## [2026-01-23] - PythonAnywhere Deployment & Search Fixes

### Critical Fixes
- **Database Synchronization**: Forced push of local `cms.db` to GitHub and pulled on PythonAnywhere to resolve schema discrepancies (missing `medium_tag` column).
- **Semester Mismatch Fix**: Resolved issue where BCA Sem 4 students appeared as Sem 3 by syncing the correct database state.
- **Missing Subjects**: Restored missing BCA subjects (Sem 2, 4, 6) by syncing the correct database.

### Features & Improvements
- **Client-Side Student Search (Fees Module)**:
  - **Change**: Upgraded the "Quick Payment" search box to load *all* students for the selected semester at once (instead of asking the server for every keystroke).
  - **Benefit**: Instant search results, zero "Server Errors" during typing, and reduced server load.
  - **Files**: `cms_app/templates/fees_receipt_semester.html`, `cms_app/main/routes.py` (added `limit=all` support).

### Admin Access
- **Credential Reset**: Reset Admin password to default (`admin` / `admin123`) via `scripts/seed_users.py` and synced to production.

---

## [2025-XX-XX] - Previous Updates (Example)
- Added `scripts/fix_mismatched_divisions.py` to handle semester promotion issues.
- Implemented `scripts/fix_student_schema.py` to patch database columns.

---

## How to Maintain This Log
1. **Date**: Always start with the date (ISO format preferred).
2. **Category**: Group changes by type (Fix, Feature, Database, etc.).
3. **Details**: Briefly explain *what* changed and *why*.
4. **Files**: List key files modified if helpful for debugging.
