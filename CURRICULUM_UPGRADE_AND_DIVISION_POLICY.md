# Curriculum Upgrade Commercial Policy and Division Rules

## Product terminology

- **Curriculum scheme** means a regulatory structure such as CBCS, NEP 2020, or a later university revision. A scheme is versioned only when the governing academic structure materially changes.
- **Admission batch** means students admitted to a program in one academic year. It is an operational grouping, not a separately configured curriculum scheme.
- **Division plan** means the classroom allocation for a program and semester.

Several admission batches may use the same curriculum scheme. Existing students must remain on their original scheme when a new scheme becomes effective.

## Commercial policy

The recurring SaaS subscription includes routine operations under an already configured scheme: academic-year rollover, annual admissions, student import, semester promotion, division allocation, faculty assignment, routine corrections, and standard reports.

A materially new regulatory structure is a separately scoped **Curriculum Upgrade Service**. Chargeable work may include scheme configuration, subject and credit mapping, assessment-rule changes, coexistence of old and new schemes, data migration, reports/transcripts, validation, training, and deployment support. Existing customer data and standard exports must never be withheld to force an upgrade purchase.

Recommended delivery levels:

1. Customer self-service configuration and import.
2. Assisted configuration, migration, validation, and training.
3. Custom regulatory implementation requiring application or report development.

Contracts should distinguish minor corrections from material structural revisions and price the latter by base setup, programs affected, migration complexity, custom rules/reports, training, and deployment support.

## Division decision rules

Allocation is controlled in this order:

1. Count active eligible students in the selected trust, program, and current semester.
2. Compare that count with the approved annual intake supplied for the relevant admission batch.
3. Load the approved division count and capacity for the program and semester.
4. Calculate `required divisions = ceiling(active students / division capacity)`.
5. Block application when active students exceed approved intake, the plan is missing, or planned classroom capacity is insufficient.

For legacy deployments that have not yet run the additive migration, approved intake remains available as an explicit preview/apply input. It must never be inferred from enrollment numbers.

## Implemented additive intake storage

The application now supports `program_intake_batches` and nullable `students.admission_academic_year` / `students.intake_batch_id_fk`. Existing students remain unmapped until an authorized import or reviewed mapping supplies an admission year. Allocation using a stored batch counts only students explicitly mapped to that batch and reports unmapped students separately.

For SQLite/PythonAnywhere, run a dry run first:

```bash
python scripts/migrate_program_intake_batches.py --database /absolute/path/to/cms.db --backup-dir ~/private_backups
```

After verifying the exact database path and output, apply it:

```bash
python scripts/migrate_program_intake_batches.py --database /absolute/path/to/cms.db --backup-dir ~/private_backups --apply
```

The migration creates and verifies a backup, is idempotent, preserves all student rows, and does not map any student automatically.

## Allocation policy

- Use one deterministic balanced algorithm for import correction, promotion, and explicit rebalancing.
- Never silently create divisions beyond an approved plan.
- Count only active students whose program and current semester match the division scope.
- Preserve tenant and program RBAC.
- Preview counts and student moves before applying.
- Apply student and current-semester active subject-enrollment changes in one transaction.
- Historical attendance is not rewritten when students move.
- Principal/Admin configure the plan; Clerk/Admin may apply an approved allocation; Faculty is read-only and may report roster discrepancies.

## Paid future enhancement

When annual intake history is required, add an admission-batch/intake record keyed by program and academic year and map students through an explicit admission year. This is separate from curriculum-scheme versioning.
# First-time opening cohorts

When an institution begins using the application with students already in later semesters, the system must not create fictitious historical approved-intake records. Instead, the authorized Admin/Principal uses **Preview old-student batches** for one program at a time.

For students whose admission academic year is blank, the preview uses the current academic session, current semester, and official program duration to propose:

- batch admission academic year;
- batch completion academic year;
- current study year;
- affected student count.

For a three-year BCA program in session 2026-27, semesters 1-2 propose 2026-27 to 2028-29, semesters 3-4 propose 2025-26 to 2027-28, and semesters 5-6 propose 2024-25 to 2026-27.

Confirmed admission years are never overwritten. Invalid or missing semesters are placed in manual review. Applying the preview changes only blank `students.admission_academic_year` values; it does not change divisions, intake approvals, attendance, fees, results, or subject enrollments. Historical students remain unlinked from `program_intake_batches` unless the institution separately records a genuine historical sanctioned intake.

## SBPET MVP student-import modes

The student import form must distinguish **New admissions** from **Existing/continuing students** before accepting a file.

- New admissions require a program, current admission academic year, exact starting semester, MOI, and an active approved-intake record. Imported students are linked to that intake record and the import is blocked if the approved intake would be exceeded.
- Existing students require a program, historical admission academic year, exact current semester, MOI, and optional current division. They do not require or consume a historical approved-intake record and remain unlinked from `program_intake_batches` unless a genuine historical approval is recorded separately.
- Form values are the authoritative scope for a single-class import. Conflicting semester, admission-year, MOI, or division values in spreadsheet rows are rejected for review rather than silently overridden.
- The report shows batch admission year and calculated batch completion year using the configured program duration. Invalid program-duration and semester combinations must be corrected before import.
- Student imports are additive by default. Absence from an uploaded file must never delete an existing student.

## MVP module boundaries

The Divisions page is limited to operational division work: select one program, select an approved admission-year intake, choose a semester, preview the required divisions, and maintain a reviewed semester rule. It must not display combined capacity across semesters or programs.

Sanctioned annual intake is maintained on a separate **Approved Program Intakes** page for Admin/Principal. Existing-student admission-year onboarding belongs to student import/onboarding. The underlying intake and opening-cohort services remain available, but they are not presented as ordinary division actions.
