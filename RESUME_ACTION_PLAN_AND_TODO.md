# CMSv5 — Resume-Time Action Plan & TODO

**Purpose:** The FIRST document to open when resuming work on CMSv5.
**Created:** 2026-08-22
**Prerequisites:** Read this file end-to-end BEFORE changing any code.

---

## ⏱️ Reading Order (Resume Checklist)

When you return to the project, follow this sequence:

1. ✅ **THIS FILE** — Resume-time TODO list + context + decision log (10 min)
2. 📄 **[CODEP_CLOUD_EMS_CODEBASE_ANALYSIS.md](file:///c:/project/CMSv5/CODEP_CLOUD_EMS_CODEBASE_ANALYSIS.md)** — Full codebase technical analysis (architecture, DB, security, risks) — **skim section 9 (Risks)** if short on time
3. 📄 **[LOGBOOK.md](file:///c:/project/CMSv5/LOGBOOK.md)** — What was last worked on, known in-progress items, WIP state
4. 📄 **[DEPLOYMENT_RULEBOOK.md](file:///c:/project/CMSv5/DEPLOYMENT_RULEBOOK.md)** — If this session involves deploying, read this first
5. 📄 **[BLUEPRINT_V3.md](file:///c:/project/CMSv5/BLUEPRINT_V3.md)** — For architectural questions / intent
6. 👉 **Then pick the highest-priority TODO item below and start working.**

---

## 🎯 Priority Legend

| Priority | Meaning | SLA |
|----------|---------|-----|
| **P0 🔴 Critical** | Ship blocker / security / data-loss risk | Next session, #1 |
| **P1 🟠 High** | Major risk / major UX pain | This week |
| **P2 🟡 Medium** | Quality / debt / UX improvement | This sprint |
| **P3 🟢 Low** | Nice-to-have | When free |

---

## 📋 P0 🔴 — MUST DO FIRST (Security + Correctness)

These items block any production deployment. Work top-to-bottom.

### TODO-P0-1 — Global CSRF enforcement (Closes finding R1 in analysis doc)
- **Why:** 38/80 POST routes skip `@csrf_required`. Financial + user-takeover impact. See risk explanation in analysis doc §9 R1.
- **How:** Two options (pick A or B):
  - **Option A (Recommended):** Add a single `before_request` global CSRF hook in `create_app()` that validates tokens for every POST/PUT/PATCH/DELETE, with a small whitelist for endpoints that genuinely don't need it (e.g., login if it has legitimate cross-site POST scenarios). Token validation logic already exists in `csrf_required()` — just hoist it.
  - **Option B (Fast patch while A is reviewed):** Manually paste `@csrf_required` decorator onto every unprotected POST route listed below.
- **Unprotected POST routes (apply to all of them):**
  - Auth: `/login`, `/change_password_first`, `/forgot-password`, `/reset-password/<token>`, `/account/settings`, `/api/keep-alive`
  - Fees: `/fees/payment/<enr>/mark-paid` (HIGH — direct financial fraud vector)
  - Users bulk: `/admin/users/bulk/set-active`, `/bulk/force-password-change`, `/bulk/reset-passwords`, `/bulk/assign-role` **(privilege escalation!)**, `/bulk/assign-program`, plus `/new`, `/<id>/edit`, `/<id>/delete`, `/<id>/map-program`
  - Students bulk: `/bulk/set-active`, `/bulk/assign-division`, `/bulk/promote-semester` **(academic integrity!)**, `/bulk/provision-users`, plus `/new`, `/<enr>/edit`, `/<enr>/delete`, `/link-user`, `/unlink-user`
  - Faculty bulk: `/bulk/provision-users`, plus `/new`, `/<id>/edit`, `/<id>/delete`, `/link-user`, `/unlink-user`
  - Subjects bulk & singles: `/bulk/set-active`, `/bulk/assign-faculty`, `/bulk/toggle-elective`, `/bulk-assign`, `/offer/electives`, `/assign`, `/assignments/<id>/deactivate`, `/<id>/edit`, `/new`, `/enroll/core`, `/<id>/delete`, `/<id>/toggle-elective`
  - Announcements: `/<id>/deactivate`, `/<id>/attachments/delete`
  - Exports: `/students/bulk/export`, `/subjects/bulk/export`
- **Files to touch:**
  - [cms_app/__init__.py](file:///c:/project/CMSv5/cms_app/__init__.py) (if Option A — add global before_request after line ~546)
  - [cms_app/main/routes.py](file:///c:/project/CMSv5/cms_app/main/routes.py) (if Option B — each route)
- **Verification:**
  1. `pytest tests/test_password_reset.py tests/test_rate_limit.py` still pass
  2. Add a new test file: `tests/test_csrf_global.py` that hits 2-3 of the previously-unprotected POST routes with a deliberately wrong/missing CSRF token and asserts 302 redirect + "Refresh the Page" flash message, then retries with correct token and asserts 200/302 success.

### TODO-P0-2 — Remove dead / mis-nested `inject_i18n` inside `csrf_required()` (R2)
- **Why:** [cms_app/__init__.py line 1366](file:///c:/project/CMSv5/cms_app/__init__.py#L1366) has `return _wrapped` closing `csrf_required()`. Then **after the return**, lines 1367+ define ANOTHER `@app.context_processor def inject_i18n():` with extra Gujarati translations. This second definition is **unreachable dead code inside the function scope**. The primary `inject_i18n` at line 892 does NOT have these extra strings — so some Gujarati translations are silently missing.
- **How:**
  1. Carefully cut-paste the Gujarati dict entries from the nested (dead) `inject_i18n` into the primary one at line 892.
  2. Merge duplicates / don't double-define.
  3. Delete all lines after the `return _wrapped` of `csrf_required()` that are orphaned inside the function.
  4. `grep "inject_i18n" cms_app/__init__.py` — should yield exactly 1 definition (`def inject_i18n():`) at module level.
- **Files to touch:** [cms_app/__init__.py](file:///c:/project/CMSv5/cms_app/__init__.py)
- **Verification:** Run `tests/test_exports_and_i18n.py` — add an assertion for one of the previously-missing Gujarati strings (e.g., "Manage Fee Heads" → Gujarati equivalent from dead block) with `?lang=gu` and confirm translation now applied.

### TODO-P0-3 — Move payment proof images out of `/static/` into instance storage
- **Why:** Payment proofs contain personal bank/transaction info. They're currently in `cms_app/static/uploads/payment_proofs/`, which means **ANYONE with the URL can browse them** (no session/auth check). There are 6 existing JPEG/PNG proof files already in the folder from 2025.
- **How:**
  1. Add config `PAYMENT_PROOFS_STORAGE_DIR = os.path.join(app.instance_path, "payment_proofs")` alongside `MATERIALS_STORAGE_DIR` in `__init__.py`.
  2. Mirror the materials pattern: remove the before_request block that blocks `/static/materials/` and ALSO block `/static/uploads/payment_proofs/` → 404.
  3. Add a new authenticated route `main.download_payment_proof(payment_id)` that checks `@login_required` + user role (student can view only their own; clerk/admin/principal their trust scope) → sends the file from instance dir.
  4. Migration: write a small script to copy existing files from `static/uploads/payment_proofs/` to `instance/payment_proofs/` (keep filenames the same).
  5. Update `proof_image_path` references everywhere to use the new route via `url_for(...)` instead of direct `/static/uploads/...` URL.
- **Files to touch:**
  - [cms_app/__init__.py](file:///c:/project/CMSv5/cms_app/__init__.py) (config + static block)
  - [cms_app/main/routes.py](file:///c:/project/CMSv5/cms_app/main/routes.py) (new download route, update payment create/list/receipt template links)
  - `cms_app/templates/fees_payment_status.html`, `fees_receipt.html`, `fees_verification_queue.html` (update img src + download links)

---

## 🟠 P1 — HIGH (This Week)

### TODO-P1-1 — Query-level trust isolation (Closes R8)
- **Why:** Trust isolation currently lives ONLY as a before-request middleware check ("is this trust active/subscribed"). Individual SELECT/INSERT/UPDATE queries don't auto-filter by `trust_id_fk` → a missed WHERE clause anywhere leaks cross-tenant data.
- **How:**
  1. Add a marker interface / base mixin (e.g., `class TenantedMixin:` with `trust_id_fk = Column(...)`) for all 10+ tenanted models: `User`, `Faculty`, `Student`, `Program`, `Announcement`, `FeeStructure`, `FeePayment`, `SubjectMaterial`, `Attendance`, `ExamMark`, `StudentSemesterResult`, `LessonPlan*`, `ImportLog`, `DataAuditLog`, `Notification`, `StudentFollowUpTask`, `EnrollmentSyncRequest`.
  2. Add a single `before_cursor_execute` OR a custom `Session` event that — for non-super-admin authenticated requests — transparently appends `WHERE trust_id_fk = current_user.trust_id_fk` to SELECTs on tenanted tables. (Or simpler: build a repository helper `tenanted_query(Model)` that everyone must use + grep-replace existing queries.)
  3. Super-admin bypass: when `current_user.is_super_admin`, scope is limited to `session.get("active_trust_id")` if set, else all trusts.
- **Verification:** Write `tests/test_trust_isolation.py`:
  - Seed 2 trusts, 1 admin user per trust.
  - Admin-A queries `/students` export and asserts Admin-B's student enrollment does NOT appear in CSV.
  - Repeat for `/fees/payments` list and `/faculty` list.

### TODO-P1-2 — Split `main/routes.py` monolith (6500+ lines) into domain modules
- **Why:** Maintainability. New devs can't find anything; merge conflicts constant; tests can't isolate.
- **How:** Create package `cms_app/routes/` with files:
  ```
  cms_app/routes/
    ├─ __init__.py         (re-register all sub-blueprints)
    ├─ auth.py             (login, logout, change_password, forgot/reset, keep-alive)
    ├─ dashboard.py        (dashboard, module_* hub pages)
    ├─ students.py         (CRUD, list, edit, link-user, bulk actions, import flow)
    ├─ faculty.py          (CRUD, link-user, bulk provision)
    ├─ attendance.py       (mark, reports, search, class-insights, notify)
    ├─ fees.py             (structure, heads, payment, receipt, verification, bank)
    ├─ materials.py        (new, edit, publish/flag, moderation, download)
    ├─ lessons.py          (lesson plan import, confirm, topics CRUD, deliveries)
    ├─ programs.py         (programs, divisions, subjects, assignments, electives, enroll/core)
    ├─ announcements.py    (new, edit, deactivate, dismiss, attachments, inbox)
    ├─ reports.py          (reports hub, analytics, nep report, exports)
    ├─ admin_tools.py      (users CRUD/bulk, system_status, logbook, new-academic-year,
    │                       student_lifecycle, staff_lifecycle, import_logs, promotion)
    └─ account.py          (account_settings)
  ```
  Each file registers a nested Blueprint (or just separate views re-registered onto `main_bp`). Keep URL patterns unchanged so templates/routes using `url_for('main.X')` continue to work.
- **First step (quick win before full split):** Move inline `role_required` at `main/routes.py:488-521` to import from `decorators.py` — delete duplicate. (10 lines, 0 risk)

### TODO-P1-3 — Password policy hardening (min 8 chars + optional complexity)
- **Why:** Current min is **6 chars** (`len(new_pass) < 6`), no upper/lower/digit requirements. Industry standard is ≥8 + multi-class.
- **Where:** [cms_app/main/routes.py:4114](file:///c:/project/CMSv5/cms_app/main/routes.py#L4114) (`change_password_first`) and any other password-setting paths (account settings, admin reset-password, users/new bulk reset, seed_users.py script).
- **How:**
  1. Raise min length to 10 (or 8 minimum).
  2. Add class check (3 of 4: upper, lower, digit, symbol).
  3. Show the policy as placeholder text in all 3 password-setting forms.
  4. Add to seed script so test users don't get invalid passwords.
  5. Existing passwords don't need rehash — just enforce at next change.

### TODO-P1-4 — Move bulk imports to background jobs (timeout fix)
- **Why:** Very large xlsx files (5k+ students × 50 columns) take > 30 seconds to parse + insert. In Flask sync WSGI this hits upstream (gunicorn/Nginx) 30s timeout → half-imported state + user sees 502.
- **How (lowest tech cost, no Redis/Celery required for MVP):**
  1. Use `subprocess.Popen` + JSON file as job queue — run import script in background.
  2. Add `ImportJob` model (status: pending/running/done, progress %, log line, started_by, started_at, finished_at, import_log_id FK).
  3. Import button → creates ImportJob → spawns worker process → returns immediately with "Running…" page.
  4. That page polls `/admin/import-jobs/<id>/progress` JSON endpoint for progress bar.
  5. If Redis IS configured (`REDIS_URL`), upgrade to RQ for robustness; else subprocess works fine on single-box PythonAnywhere deployments.

### TODO-P1-5 — Add Security Headers (CSP + HSTS + X-Frame-Options)
- **Why:** Current headers only emit `Server-Timing`, cache-related, and `X-Request-Time`. Missing Clickjacking + XSS + downgrade protections.
- **Where:** Add a new `after_request` handler in `cms_app/__init__.py` (after `_static_cache_headers` is fine).
- **Headers to add:**
  ```
  X-Content-Type-Options: nosniff
  X-Frame-Options: SAMEORIGIN          (or DENY if app never embedded)
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: geolocation=(), camera=(), microphone=()
  Strict-Transport-Security: max-age=31536000; includeSubDomains   (ONLY on HTTPS production env flag)
  Content-Security-Policy: default-src 'self';
      script-src 'self';
      style-src 'self' 'unsafe-inline';       (Bootstrap / in-page <style> tags need inline)
      font-src 'self' data:;
      img-src 'self' data: blob:;
      object-src 'none';
      base-uri 'self';
      frame-ancestors 'self';
      form-action 'self';
      connect-src 'self';
  ```
  Note: Tune `style-src` if removing inline styles is feasible. Never add `unsafe-inline` to `script-src`.

---

## 🟡 P2 — MEDIUM (This Sprint)

### TODO-P2-1 — Sanitize / whitelist HTML in `SystemMessage.content` (R9)
- **Why:** Model comment says **"Supports HTML"**. No sanitizer visible. If any non-super-admin can ever post a SystemMessage (today they can't — only super_admin routes create them), it's stored XSS. Also risk of super-admin accidentally saving malicious HTML.
- **How:**
  1. Add `bleach` to requirements.txt (or `nh3`/`Bleach-allowlist`) — lightweight.
  2. On save (before db flush), run content through `bleach.clean()` with a safe tag allowlist: `['h1','h2','h3','h4','p','br','hr','strong','em','u','ol','ul','li','a','span','div','blockquote','code','pre','table','thead','tbody','tr','th','td','img']` plus attributes `{ 'a': ['href','target','rel'], 'img': ['src','alt','width','height'], '*':['class','style'] }`.
  3. Forbid `style` attribute if not strictly needed; use classes instead.
  4. If bleach dep-added, existing SystemMessage rows need a one-time migration sanitize pass.

### TODO-P2-2 — Audit scripts/ folder: ACTIVE vs ONE-TIME vs OBSOLETE
- **Why:** `scripts/` has ~120 `.py` files plus sub-dirs like `subject_data/`. Many are one-off migrations dating to 2025. New developers can't tell which are still runnable and which are dangerous (e.g., `purge_bcom_variant_students.py`).
- **How:**
  1. Open each script, classify:
     - `ACTIVE` — still used regularly (e.g., `import_students.py`, `import_subjects.py`, `import_faculty.py`, `seed_*.py`, `generate_student_users_csv.py`, `export_rolls.py`, `fix_db.py`, `check_*.py` that report but don't mutate).
     - `ONE-TIME` — migration already applied, safe to archive.
     - `DANGEROUS` — destructive data operations.
  2. Move `ONE-TIME` scripts into `scripts/_archive_one_time/` (add a prefix date like `20250116_purge_bcom_variant_students.py`).
  3. Rename `DANGEROUS` scripts with prefix `DESTROY_` and add a top docstring "REQUIRES env var `CMS_CONFIRM_DESTROY=yes` to run".
  4. Add `scripts/README.md` table: filename, classification, who-to-talk-to-before-running.
  5. Same cleanup for `cms_app/scripts/` subdir (~23 files).

### TODO-P2-3 — Migrate critical ad-hoc scripts to Flask CLI (`flask students import …`)
- **Why:** Discoverability + argparse-style --help + centralized logging. Scripts are often run by non-devs (clerks/admins) who need `--help`.
- **Migrate first:**
  - `import_students.py` → `flask import students <file.xlsx> --program-id X --semester N --dry-run/--apply`
  - `import_subjects.py` → `flask import subjects <file.xlsx> --program-id X --semester N`
  - `import_faculty.py` → `flask import faculty <file.xlsx>`
  - `generate_student_users_csv.py` → `flask users generate-student-csv <out.csv> --program-id X`
  - `seed_fee_heads_all.py` → `flask fees seed-heads --program-id X`
  - `rebalance_divisions.py` → `flask divisions rebalance --program-id X --sem N`
  - `promote_sem1_to_sem2.py` / semester promotion → `flask students promote --program X --from-sem N --to-sem M`

### TODO-P2-4 — Dependency security + Dependabot
- **Why:** Pinned versions are Flask 2.2.5 (2.3/3.x exist), Werkzeug 2.3.7, SQLAlchemy 1.4.49 (2.x exists). CVEs can stack.
- **How:**
  1. Add `pip-audit` to `requirements-dev.txt` (and CI workflow if GitHub Actions is used).
  2. Run `pip-audit` locally — fix any HIGH/CRITICAL by bumping pin.
  3. `.github/workflows/` already has `python-app.yml`. Add a Dependabot config `.github/dependabot.yml` for weekly pip updates + security PRs.
  4. Review whether Flask/SQLAlchemy major upgrades feasible (Flask 3.x has breaking changes — schedule separately).

### TODO-P2-5 — `CHANGELOG.md` + version tags + replace LOGBOOK sprawl
- **Why:** `LOGBOOK.md` is free-text. Human-readable changelog for release notes is missing; no git tags visible.
- **How:**
  1. Create `CHANGELOG.md` using Keep-a-Changelog 1.1 format headings: `## [Unreleased]`, `## [0.1.0] - YYYY-MM-DD`, with Added/Changed/Deprecated/Removed/Fixed/Security sections.
  2. Leave LOGBOOK.md as freeform dev notes; make Changelog the release-authoritative doc.
  3. Tag current HEAD as `v0.1.0-initial-analysis` to anchor first baseline.

### TODO-P2-6 — Password min length: raise from 6 to 10 chars; add complexity rules
(Integrated with P1-3 above — this is the same TODO. P1-3 and P2-6 are ONE task — treat P2-6 as completed when P1-3 ships.)

### TODO-P2-7 — DataAuditLog write for every bulk action + super-admin dangerous ops
- **Why:** `DataAuditLog` model exists but isn't universally written. Bulk user/student/subject actions are irreversible — today if a CSRF or fat-finger happens you can't answer "who ran this 10,000-row delete and from what IP + when".
- **How:**
  1. Create helper `audit_log(action, selection_list=None, counts_dict=None)` that writes a row with actor, role, trust/program/semester scope from session vars, and JSON selection.
  2. Call it at the START of every mutating bulk route.
  3. Write client IP (`request.remote_addr` or `X-Forwarded-For`) in counts JSON.
  4. Super-admin purge: add audit row BEFORE scheduling purge request.

---

## 🟢 P3 — LOW (Nice to have, tackle when free)

### TODO-P3-1 — Service Worker cache version from git SHA (R12)
- Hardcoded v39 string in [cms_app/static/sw.js](file:///c:/project/CMSv5/cms_app/static/sw.js#L2) — always forget to bump.
- Replace with build step or read via `importlib.metadata` or a `VERSION.txt` file.

### TODO-P3-2 — Gujarati i18n coverage to 100%
- ~80 strings translated, 100s more remain in inner pages. Run site-wide audit of every template, extract missing strings, add to dict in `cms_app/__init__.py:inject_i18n` (the correct/primary one, AFTER P0-2 fix merges both dicts).

### TODO-P3-3 — Make psycopg2-binary an optional "postgres" extra (O7)
- Modify `requirements.txt` or add `pyproject.toml` `[project.optional-dependencies]` → `postgres = ["psycopg2-binary==2.9.9"]`.

### TODO-P3-4 — Student PK migration: add int surrogate `student_id`
- Currently `students` PK is `enrollment_no` (string). FKs heavy + joins slower. Add `student_id INTEGER PRIMARY KEY` and transition FK references (attendance, grades, fee_payments, etc.) to use it over time. Backfill enrollment_no as unique non-PK.

### TODO-P3-5 — PWA cache: integrate app version / deploy SHA
- Same idea as P3-1 but used site-wide for `?v=` cache-bust suffix in layout.html (style.css currently hardcoded `?v=6`, fonts unversioned, etc.) — stale CSS/JS after deploys is a common user-reported glitch.

### TODO-P3-6 — Add `robots.txt` + `sitemap.xml` for public index page only
- Prevents `/login`, `/forgot-password`, and authenticated pages from being indexed by search engines while allowing landing homepage to appear.

---

## 🧪 Test Coverage Gaps (Add these test files)

| Test File To Create | What it covers | Priority |
|---------------------|---------------|----------|
| `tests/test_csrf_global.py` | POST without token → reject; POST with wrong token → reject; POST with correct token → pass. Covers login, account settings, user new/delete, student edit, mark-paid, etc. | **P0** |
| `tests/test_trust_isolation.py` | Two seeded trusts, Admin-A cannot see Admin-B students/payments/faculty | **P1** |
| `tests/test_security_headers.py` | Response headers assertions (all P1-5 headers) | P1 |
| `tests/test_payment_proofs_private.py` | Unauthenticated GET of proof URL → 403/404; owner student → 200; wrong student → 403 | **P0 (ships with P0-3)** |
| `tests/test_bulk_actions_audit.py` | Verifies DataAuditLog rows written after bulk endpoints | P2 |
| `tests/test_password_policy.py` | 6-char → rejected; 10-char single-class → rejected; valid strong password → accepted | P1 |
| `tests/test_csrf_login.py` | Specific: login POST with/without token after global CSRF whitelist decision | P0 if login NOT whitelisted |

---

## ✅ Definition of "Ready for Next Milestone" (Exit Criteria)

Before calling the codebase "post-analysis hardened", all of the following MUST be `git commit`'d and `pytest` passing:

- [ ] P0-1 ✅ (Global CSRF — A or B, tests pass)
- [ ] P0-2 ✅ (Dead inject_i18n removed, translations merged, no duplicate defs)
- [ ] P0-3 ✅ (Payment proofs moved; `tests/test_payment_proofs_private.py` passes)
- [ ] P1-1 🔄 (Optional for hardening, Mandatory before multi-tenant SaaS go-live)
- [ ] P1-3 ✅ (Password policy enforced, test_password_policy passes)
- [ ] P1-5 ✅ (Security headers set, test_security_headers passes)
- [ ] `pytest` full suite — 0 failures
- [ ] `pip-audit` — 0 HIGH / CRITICAL
- [ ] This TODO file itself is updated with dates/strikethroughs next to completed items.

---

## 🗂️ Quick Jump Links (Handy while working)

### Core files
- [app.py](file:///c:/project/CMSv5/app.py) — entry point
- [cms_app/__init__.py](file:///c:/project/CMSv5/cms_app/__init__.py) — app factory, CSRF, hooks (**START HERE for P0-1, P0-2, P1-5**)
- [cms_app/models.py](file:///c:/project/CMSv5/cms_app/models.py) — 49 DB tables
- [cms_app/decorators.py](file:///c:/project/CMSv5/cms_app/decorators.py) — role_required + super_admin_required
- [cms_app/main/routes.py](file:///c:/project/CMSv5/cms_app/main/routes.py) — largest file, most unprotected POSTs live here

### Docs
- [CODEP_CLOUD_EMS_CODEBASE_ANALYSIS.md](file:///c:/project/CMSv5/CODEP_CLOUD_EMS_CODEBASE_ANALYSIS.md) — full technical analysis
- [DEPLOYMENT_RULEBOOK.md](file:///c:/project/CMSv5/DEPLOYMENT_RULEBOOK.md) — deploy rules
- [LOGBOOK.md](file:///c:/project/CMSv5/LOGBOOK.md) — WIP notes

### Tests
- [tests/conftest.py](file:///c:/project/CMSv5/tests/conftest.py) — fixtures
- Run tests: `cd c:\project\CMSv5 ; pytest -v`

---

## Next Session Focus — Division Allocation Audit (2026-08-28)

### Observed production inconsistency

The Divisions screen shows students concentrated in Division A while the other configured divisions are empty:

- BCA Semester 1: Division A `79 / 45` (175.6%); Division B `0 / 45`.
- BCA Semester 3: Division A `101 / 67` (150.7%); Divisions B and C `0 / 67`.
- BCA Semester 5: Division A `190 / 67` (283.6%); Divisions B and C `0 / 67`.

### Required investigation

1. Confirm whether the `Enrolled` value counts student division assignments, active subject enrollments, or another source.
2. Audit division creation/allocation rules by programme, semester, medium, academic year, and capacity.
3. Design balanced A/B/C allocation with deterministic roll-number ordering and explicit overflow handling.
4. Define Clerk and Principal RBAC: preview/report permissions versus authority to apply redistribution.
5. Add a dry-run impact report showing current division, proposed division, capacity, and affected student count.
6. Add validation for over-capacity, unassigned students, duplicate allocation, and inconsistent semester/division data.
7. Verify the existing schema before proposing changes; prefer a logic/data-consistency fix if the schema already supports the required rules.

### Safety rule

Do not rebalance or update production student records until the exact counting source is proven, a verified database backup exists, and the dry-run allocation has been reviewed.

## 📝 Decision Log (Add rows when making architectural decisions during TODOs)

| Date | Decision | Made By | Rationale |
|------|----------|---------|-----------|
| 2026-08-22 | CSRF fix approach: **Option A (global before_request)** vs B (per-route decorators) | — | TBD during P0-1 implementation; see TODO-P0-1 |
| 2026-08-22 | Payment proofs storage: **instance/payment_proofs, new download route** | — | Matches materials pattern. |
| — | | | |

---

## Next Session Focus — Simplified Program-Year Division Configuration (2026-09-02)

### Agreed MVP direction

Do not require administrators to maintain a separate division rule for every semester. Use the program admission-year configuration as the source of truth:

- approved annual intake;
- standard class size/division capacity;
- maximum permitted divisions, calculated as `ceil(approved intake / class size)`;
- actual student assignments determine which permitted divisions are operational.

When a new academic year is created, copy the previous program-year settings into a **draft**. The Admin must review and activate the draft; copied values must never become official silently.

Students in later semesters use the configuration belonging to their admission batch. For example, BCA Semester 3 students in 2026-27 use the BCA 2025-26 program-year configuration. Do not require a new Semester 3 division rule merely because they advanced to Semester 3.

### Tomorrow's implementation checklist

- [x] Review existing `program_intake_batches`, division-plan, division-master, student-assignment, and promotion logic before changing code. (2026-09-02)
- [x] Confirm that no new schema change is required; prefer adapting the current intake-batch and division records. (2026-09-02: no migration added)
- [x] Add a new-academic-year draft flow that copies prior-year program intake and class-size settings for review. (2026-09-02)
- [x] Calculate permitted division codes from approved intake and class size. (2026-09-02)
- [x] Derive each student's applicable configuration from program plus admission batch/year. (2026-09-02)
- [x] Treat balanced allocation as a recommendation; preserve deliberate authorized assignments such as A=38 and B=41. (2026-09-02)
- [x] Keep bulk **Assign Division** available without requiring an allocation run, provided a compatible/permitted division exists. (2026-09-02)
- [x] Validate program, semester, admission batch, RBAC, MOI, and capacity before a manual assignment. (2026-09-02)
- [x] Allow Admin, Clerk, Principal, and explicitly assigned Class Coordinator according to existing tenant-scoped RBAC; ordinary Faculty remains unauthorized. (2026-09-02)
- [x] Show only semesters containing active students by default when `Semester = All`. (2026-09-02)
- [x] Hide empty divisions by default and add **Show configured empty divisions**. (2026-09-02)
- [ ] Add **Include closed divisions** after division lifecycle/status is represented; the current `divisions` table has no status field.
- [x] Report utilization per semester/admission batch, keeping these figures separate: (2026-09-02)
  - intake filled percentage and intake remaining percentage;
  - operational division utilization and available class seats;
  - assigned and unassigned student counts.
- [x] If students exist but no applicable configuration/divisions exist, show **Division setup required** and `N/A` utilization; never invent or silently assign divisions. (2026-09-02)
- [x] Retain the detailed Division Management page for operational exceptions and reconciliation. (2026-09-02)
- [ ] Add division lifecycle before exposing close/delete for division-master records.
- [x] Add focused tests for inherited draft settings, empty-division filtering, intake reporting, allocation capacity, and intake actions. (2026-09-02)
- [ ] Add route-level Class Coordinator assignment/RBAC tests.
- [ ] Resolve two pre-existing unrelated full-suite failures (`test_auto_release_subject_assignments_when_semester_has_no_students` and detached fixture state in `test_faculty_dashboard_renders_with_assignments`) before calling the full suite green.

### Safety constraints

- Do not silently activate copied annual settings.
- Do not overwrite an authorized manual division choice merely to make counts mathematically balanced.
- Do not delete historical division records or rewrite attendance during allocation changes.
- Do not deploy schema/data migrations to PythonAnywhere until the local implementation and migration impact are verified against a backup.

---

*End of Resume-Time Action Plan. If you start work, begin at TODO-P0-1. After finishing each TODO, strike through text and move it to a "Completed" section below with a date.*
