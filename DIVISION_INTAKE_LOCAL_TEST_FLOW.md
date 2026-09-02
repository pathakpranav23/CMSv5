# Annual Intake and Division Allocation — Local Verification Flow

## Local test environment

- URL: `http://127.0.0.1:5055/`
- Database: `C:\project\CMSv5\cms.db`
- This local database is separate from PythonAnywhere.
- Before testing, run the guarded intake migration and retain its verified backup.

## What the workflow must prove

Division planning is based on three independent values:

1. Active students belonging to the selected admission batch.
2. Approved annual intake for that program and admission year.
3. Capacity of each planned division.

The system must not treat subject enrollment rows as division enrollment, and it must not silently count students from another admission batch.

## Role-by-role test flow

### 1. Principal or Admin — configure the approved structure

1. Sign in as Principal or Admin.
2. Open **Administration → Divisions**.
3. As Admin, select the program first. Until a program is selected, the page must not show aggregate capacity, intake rules, planning forms, or allocation actions. Principal remains locked to the program mapped to that account.
4. In **Annual Intake Setup**, create or update an admission batch, for example:
   - Admission academic year: `2026-27`
   - Approved annual intake: the sanctioned program intake
   - Default division capacity: the permitted capacity per division
   - Status: `Active`
5. Save the intake record and confirm it appears in the list.
6. Confirm the admission-year choices shown in allocation belong only to the selected program. Changing the program must reload its own intake years and division information.
7. Configure the semester division plan:
   - Semester
   - Division capacity
   - Planned number of divisions
   - Optional roll-number ceiling
8. Save and confirm the required division codes exist, such as A, B, and C.

Expected RBAC: Principal/Admin can maintain approved intake and division structure. Clerk cannot change these policy values.

### 2. Clerk — import and identify students correctly

1. Sign in as Clerk.
2. Import students using the current template.
3. Supply **Admission Academic Year** for each student.
4. Use dry-run validation before committing the import.
5. Confirm students are linked only to the matching program intake batch.
6. Leave the division blank when allocation has not yet been approved; the system should keep the student unassigned instead of guessing.

Expected RBAC: Clerk can manage operational student data and allocation, but cannot redefine sanctioned intake or program structure.

### 3. Principal or Clerk — review the allocation preview

1. Return to **Divisions**.
2. Choose the program, semester, and admission batch.
3. Open the division allocation preview.
4. Verify the summary values:
   - Active students in the selected batch
   - Approved intake
   - Division capacity
   - Required divisions
   - Planned divisions
5. Review excluded or unmapped students separately.
6. Confirm the proposed distribution is balanced and does not cross capacity.
7. Treat an approved-intake overrun, insufficient capacity, or batch mismatch as a blocking error.

Expected RBAC: Principal can review. Clerk/Admin can apply. Faculty cannot access this workflow.

### 4. Clerk or Admin — apply the proposal

1. After review, apply the allocation.
2. Confirm the success summary reports assigned and moved students.
3. Reopen the preview and confirm no unexplained pending movements remain.
4. Confirm the Divisions list displays **active assigned students**, not subject-enrollment counts.

### 5. Faculty — verify downstream behavior

1. Sign in as a faculty member assigned to one of the affected subject/division combinations.
2. Open Attendance and load that class roster.
3. Confirm only students assigned to that division appear.
4. Confirm faculty can mark attendance but cannot edit intake, create divisions, or reallocate students.

### 6. Promotion/regression check

1. Promote a small test selection through the authorized promotion workflow.
2. Confirm the old semester division assignment is cleared or marked unassigned as designed.
3. Preview the next-semester allocation.
4. Apply it as Clerk/Admin and verify the students appear in the correct new division.

## Required negative checks

- A student without an admission year must be shown as unmapped, not guessed into a cohort.
- A student from `2025-26` must not affect the `2026-27` intake calculation.
- Inactive students must not inflate active division utilization.
- Subject enrollment counts must not be used as the division headcount.
- Clerk must be denied access to intake-policy edits.
- Principal must not see the Apply action unless that permission is explicitly granted later.
- Faculty must be denied all division-planning and allocation mutations.

## Production deployment gate

Do not change PythonAnywhere until local testing passes. Before production:

1. Back up the live database.
2. Confirm the WSGI `DATABASE_URL` target.
3. Run the migration in dry-run mode against that exact target.
4. Review preserved-row and schema output.
5. Apply the migration once.
6. Reload the PythonAnywhere web app.
7. Repeat the RBAC smoke checks above with test accounts.
