# Annual Enrollment History, Historical Audit, and Academic-Year Rollover Plan

**Product:** CodeP-CloudEMS
**Decision date:** 2026-09-02
**Target roles:** Trust Admin, Principal, Clerk, authorized auditors

## 1. Objective

The application must answer institutional audit questions by **operating academic year**, independently of division allocation. Examples include:

- total students studying during an academic year;
- new admissions versus continuing students;
- program-wise and semester-wise student strength;
- SC, ST, SEBC/OBC, EWS, OPEN/General and other configured category totals;
- female, male and other/declared gender totals;
- program × category × gender combinations;
- MOI, admission type, retention, discontinuation, transfer and completion statistics.

`students.admission_academic_year` identifies when a student entered a program. It does **not** prove that the student was studying in every later year. The current `students.is_active`, program, semester, gender and category fields describe current state and cannot, by themselves, reproduce an exact historical audit.

## 2. Product terminology

The official **user-facing term is `Annual Enrollment History`**.

Use this wording on pages, navigation items, buttons, help text, reports, exports, validation messages and audit screens. Avoid showing the word `census` to Trust Admins, Principals, Clerks, Faculty, students or auditors because it may sound governmental or unclear in the context of normal academic administration.

Approved interface labels include:

- **Annual Enrollment History**
- **Academic-Year Enrollment**
- **View Previous Academic Year**
- **Prepare New Academic Year**
- **Historical Year — Read-only**

The term `annual census` may remain in internal code, database comments or technical architecture where it describes the yearly verified snapshot. It must not become the default product label.

## 3. Recommended additive annual enrollment history

Add a year-scoped annual enrollment record without replacing the existing `students` profile.

Suggested entity: `student_academic_enrollments`

Each row represents one student's verified participation in one operating academic year. Collectively, these records form the student's **Annual Enrollment History**.

| Field | Purpose |
|---|---|
| annual enrollment ID | Stable record identifier |
| student/enrollment ID | Student identity |
| academic year ID | Operating year being audited |
| admission academic year | Original admission cohort |
| trust and institute IDs | Tenant and college scope |
| program ID | Program studied in this operating year |
| semester | Current semester for this year |
| status | new, continuing, repeat, readmitted, transferred, discontinued, completed |
| gender snapshot | Audit-year value |
| category snapshot | Audit-year SC/ST/SEBC/EWS/OPEN value |
| MOI snapshot | Audit-year medium |
| admission type | regular, lateral, transfer, readmission, other |
| confirmed by / at | Annual Enrollment History approval evidence |
| created / updated timestamps | Operational traceability |

The uniqueness rule should normally be one student + one academic year + one institutional/program enrollment. Multi-program or transfer cases require explicit separate records rather than silent overwrites.

For reproducible audits, relevant demographic dimensions are stored as annual snapshots. Corrections after confirmation require a reason and an audit-log entry.

## 4. Academic-year master and lifecycle

Introduce or formalize an `academic_years` master scoped to the Trust or Institute according to product policy.

Recommended lifecycle:

1. **Draft** — configuration is being prepared; no ordinary operations.
2. **Review** — promotion, Annual Enrollment History, subjects, staff, timetable and fees are validated.
3. **Open/Active** — normal teaching and operational transactions are allowed.
4. **Locked** — corrections require elevated authority and a reason.
5. **Closed/Archived** — read-only institutional history.

Only one operating year should be the default active year for an institute at a time. Historical years remain selectable but read-only.

## 5. Dashboard academic-year selector

Trust Admin and Principal dashboards should provide a clearly visible academic-year selector.

### Active-year mode

- shows current operational data;
- allows permitted actions for the user's role;
- labels the year as **Active**;
- provides a controlled **Prepare next academic year** action.

### Historical-year mode

- displays an explicit **Historical · Read-only** banner;
- disables create, edit, delete, import, attendance marking, promotion and payment actions;
- enables audit dashboards and approved exports;
- retains filters for institute, program, semester, category, gender, MOI and status;
- every report identifies the selected academic year and data-finalization status.

### Role scope

- **Trust Admin:** view consolidated Trust totals and drill down into authorized institutes/programs; prepare Trust-wide defaults; cannot bypass tenant boundaries.
- **Principal:** view and manage the active year only within the mapped institute/program scope; historical years are read-only.
- **Clerk:** operate student enrollment/import/promotion tasks assigned for the active year; historical exports require policy-based permission.
- **Faculty:** access only assigned active-year classes and authorized historical teaching records; no institution-wide audit data.
- **Auditor/read-only role:** access finalized reports and exports only, with no operational mutation.

## 6. Preparing the next academic year

The dashboard may expose one prominent action such as **Prepare 2027-28**, but it must launch a reviewed wizard—not perform an irreversible one-click reset.

Recommended flow:

1. Create 2027-28 in **Draft** status.
2. Select the source year, normally 2026-27.
3. Preview all proposed carry-forward settings.
4. Promote eligible continuing students into draft Annual Enrollment History records.
5. Identify graduating, discontinued, transferred, repeat and unresolved students.
6. Review program intake, class size and permitted division settings.
7. Review subject offerings and curriculum/scheme applicability.
8. Review proposed Faculty subject allocations.
9. Review timetable, fees, materials and announcement carry-forward choices.
10. Display blocking validation errors and warnings.
11. Principal/Trust Admin approves the preview according to RBAC.
12. Activate the year only after confirmation; write a complete audit manifest.

The operation must be idempotent: retrying after an interruption must not duplicate annual enrollment, subject, fee or assignment records.

## 7. Copy, start-empty, and preserve policy

### Copy as drafts by default

- program-year approved intake and standard class size;
- applicable curriculum/scheme references;
- subject catalogue into year-specific subject offerings;
- Faculty allocations as **proposed/draft**, never automatically final;
- timetable structure/period definitions and optionally timetable slots as drafts;
- fee structures as drafts requiring finance review;
- reusable report settings and institutional calendar templates;
- selected learning materials when the owner explicitly chooses carry-forward.

### Start empty for the new year

- attendance sessions and attendance entries;
- assessment marks/results and grade publication state;
- fee payments, receipts and payment verification events;
- year-specific announcements and notification deliveries;
- lesson-plan delivery/completion logs;
- operational follow-up tasks;
- audit approvals and freeze/lock state.

“Start empty” means the new academic year has no records in these scopes. It must **never** delete or reset the previous year's rows.

### Preserve permanently

- student and staff identity/profile records;
- admission cohort and Annual Enrollment History records;
- previous attendance, results, payments, receipts and approvals;
- historical subject/Faculty/timetable mappings;
- audit logs, import logs and rollover manifests;
- locked/closed academic-year reports and exports;
- uploaded evidence governed by retention policy.

## 8. Faculty subject allocation in rollover

Previous-year Faculty allocations are useful recommendations, not authoritative assignments for the new year.

The rollover preview should show:

- previous Faculty;
- proposed Faculty;
- subject offering, program, semester and MOI;
- workload before and after;
- missing/inactive Faculty;
- conflicts and unassigned subjects;
- action: keep, change, remove, assign later.

Activation must be blocked when mandatory subject offerings have no authorized Faculty allocation, unless an elevated user records an approved exception.

## 9. Audit reporting

For a selected historical year, reports should include:

- studying students, new admissions and continuing students;
- program/semester/category/gender/MOI breakdowns;
- intake versus actual new admissions;
- promotion, repetition, transfer, discontinuation and completion totals;
- data-quality exceptions such as missing category/gender/admission year;
- Annual Enrollment History confirmation status, approver and timestamp;
- CSV/XLSX/PDF export with Trust, institute, selected year and generation metadata.

Dashboard totals must be computed from Annual Enrollment History records for the selected year, not from today's `students.is_active` value.

Annual Enrollment History also snapshots permanent address, home city/town/village, and home district. This supports Mahuva-versus-outside analysis and place-wise counts such as Kalsar. Classification uses structured location fields; free-text addresses remain searchable but are not automatically classified.

The history screen must not require horizontal scrolling. It uses responsive cards and view-specific filters for students, faculty, and subjects while retaining the selected academic-year context.

## 10. Safety and deployment rules

- Use additive, reversible migrations; do not repurpose `students` or `divisions` columns.
- Backfill Annual Enrollment History only through a reviewed preview; never infer exceptions silently.
- Do not overwrite historical demographic snapshots during profile corrections.
- Never implement rollover as delete-and-copy.
- Never reset attendance, marks, payments or receipts in place.
- Require tenant/program RBAC at query and mutation boundaries.
- Create an audit manifest containing source year, target year, counts, warnings, approver and created record IDs.
- Test locally against a verified database copy before PythonAnywhere migration.

## 11. MVP delivery sequence

1. Academic-year master and dashboard selector.
2. Annual Enrollment History table and current-year generation preview.
3. Historical read-only audit dashboard and exports.
4. Draft next-year creation and Annual Enrollment History review.
5. Draft subject offerings and Faculty reallocation review.
6. Optional timetable, fee and material carry-forward modules.
7. Year lock/close workflow and auditor role.

The existing program intake and division work can continue as the program/cohort configuration source. Division allocation is not required for the institutional Annual Enrollment History reports described here.

## 12. Implementation status — 2026-09-02

Implemented in the first safe MVP slice:

- additive `academic_years` lifecycle model;
- additive `student_academic_enrollments` Annual Enrollment History model;
- Trust Admin/Principal dashboard academic-year selector;
- historical selections open a clearly marked read-only reporting workspace;
- current-year history preparation from authorized active student profiles;
- program, category, gender and enrollment-status summaries;
- student-level Annual Enrollment History table and CSV export metadata;
- next-year Draft preparation from reviewed source-year records;
- continuing-student proposals advance two semesters without changing live student profiles;
- completion candidates are excluded from automatic carry-forward and reported;
- proposed divisions remain unassigned for deliberate allocation;
- focused RBAC, rollover-safety and dashboard regression tests.

Deferred intentionally until every dependent module is explicitly year-aware:

- activating a Draft as the live academic year;
- bulk confirmation and exception resolution;
- automatic application of promoted semesters to live student profiles;
- copying faculty assignments, timetable, fees and materials from Draft into active operation;
- year-aware historical views for attendance, examinations, fees and lesson delivery.

This boundary prevents a partially migrated application from mixing current and historical values or appearing to reset data that must remain preserved.
