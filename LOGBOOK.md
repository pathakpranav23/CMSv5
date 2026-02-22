# Project Logbook

This logbook tracks daily changes, updates, and fixes applied to the CMSv5 ERP system. Use this to monitor progress and rollback changes if necessary.

## [2026-02-22] - Student Imports (BCA/BBA/BA/BSc) and DB Sync

### Schema & Model Updates
- Added `aadhar_no` and `category` fields to the `Student` model and database schema to support future category-wise analytics.
- Updated `scripts/fix_student_schema.py` to patch the `students` table with the new columns on existing databases.

### Bulk Student Imports
- **BCA**:
  - BCA Sem 4 import updated to:
    - Read Division directly from Excel (no more roll-range based division logic).
    - Import Aadhar and Category (nullable) from the updated Sem 4 Excel.
  - BCA Sem 6 import aligned to the same pattern (Division + Aadhar + Category from Excel).
- **BBA**:
  - Wired BBA Semester 4 and Semester 6 student imports using the generic bulk importer and dedicated runner `scripts/run_import_bba_students.py`.
  - Data files: `BULK_Student_Import BBA Sem 4 Data Feb 2026.xlsx`, `BULK_Student_Import BBA Sem 6 Data Feb 2026.xlsx`.
- **BA/BSc**:
  - Prepared and imported BA/BSc Sem 2/4/6 students via updated bulk import logic and Excel templates.
- Generic bulk importer `scripts/import_students.py` extended to support:
  - Header mapping for Aadhar (`Aadhar Card Number`, `Aadhaar No`, etc.) and Category (`Category`, `Caste Category`, etc.).
  - Optional population of `students.aadhar_no` and `students.category` for all programs.

### Templates & UX
- Updated expectations for the bulk student import sample to match the new Excel template (`Template for Bulk Student Import.xlsx`), including Division, Aadhar, and Category columns.
- Verified Sem 4 BCA division distribution against Excel using `scripts/inspect_bca_sem4_division.py` and `scripts/check_bca_sem6_divisions.py` for QA.

### Deployment & DB Strategy
- Adopted a clear deployment pattern for dev/staging:
  - Commit code and schema scripts to GitHub.
  - On PythonAnywhere, `git pull` to sync code.
  - Overwrite remote `cms.db` with the tested local `cms.db` when large schema/data changes are made (non-production), instead of complex SQL migrations.
- Resolved a production 500 error (`no such column: students.aadhar_no`) by ensuring remote `cms.db` was replaced with the locally migrated database.

---

## [2026-01-23] - PythonAnywhere Deployment & Search Fixes

### Critical Fixes
- Database Synchronization: Forced push of local `cms.db` to GitHub and pulled on PythonAnywhere to resolve schema discrepancies (missing `medium_tag` column).
- Semester Mismatch Fix: Resolved issue where BCA Sem 4 students appeared as Sem 3 by syncing the correct database state.
- Missing Subjects: Restored missing BCA subjects (Sem 2, 4, 6) by syncing the correct database.

### Features & Improvements
- Client-Side Student Search (Fees Module):
  - Change: Upgraded the "Quick Payment" search box to load all students for the selected semester at once (instead of asking the server for every keystroke).
  - Benefit: Instant search results, zero "Server Errors" during typing, and reduced server load.
- Files: `cms_app/templates/fees_receipt_semester.html`, `cms_app/main/routes.py` (added `limit=all` support).

### Admin Access
- Credential Reset: Reset Admin password to default (`admin` / `admin123`) via `scripts/seed_users.py` and synced to production.
- Attendance Marking Fixes:
  - Resolved an issue where admins could not mark attendance due to missing context (subject, division, date) in the POST request. Added hidden fields to `attendance_mark.html` to preserve this data.
  - Added Program Selector for Admins in `attendance_mark.html`. Previously, admins could not filter subjects by program, causing confusion and potential roster loading issues. Now, changing the program reloads the subject list contextually.


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
