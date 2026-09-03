# Annual Enrollment History — User Guide

## Purpose

Annual Enrollment History records which students studied in each academic year. It supports historical audits without changing today's student profiles or deleting previous attendance, results, payments or receipts.

## Trust Admin

1. Open the Dashboard.
2. Use the **Academic year** selector in the page header.
3. Select the active year for normal operations.
4. Select an earlier year to open **Historical year — read-only** reporting.
5. Use **Export CSV** to download the authorized Annual Enrollment History.
6. Before the first rollover, open the active year and select **Prepare Current-Year History**.
7. Review totals by program, category, gender and enrollment status.
8. Open **Prepare New Academic Year** only after the active-year history is available.

The Trust Admin may view all authorized programs within the trust. The system must not expose another trust's students.

## Principal

The Principal follows the same flow but sees only the program/institute scope permitted by RBAC. A Principal cannot use the year selector to widen access beyond that scope.

## Preparing the next year

1. Open **New Academic Year Setup**.
2. Confirm the displayed source and target years.
3. Select **Prepare [year] Draft**.
4. Review proposed continuing students in Annual Enrollment History.
5. Review completion candidates separately; they are not carried into the new year automatically.
6. Review copied intake settings as drafts.
7. Review divisions, subjects, faculty allocation, timetable and fees.
8. Resolve validation warnings before activation.

Preparing a draft does not change the student's current semester or division. Proposed students move two semesters forward in the draft, and their divisions remain unassigned until reviewed.

## What “start empty” means

The new year begins with no new-year attendance, marks, payments, receipts, announcements, notification deliveries, lesson delivery logs or follow-up tasks. Previous-year records remain unchanged and accessible through their original academic year.

Never delete old records to start a new year.

## Historical reporting

The report provides:

- total students studying in the selected year;
- program-wise strength;
- category distribution;
- gender distribution;
- new, continuing, repeating, transferred, discontinued and completed status;
- student-level export with the selected year and generation metadata.

When no Annual Enrollment History exists, the application displays an explicit empty state. It does not substitute today's student totals into a historical report.

## Confirming, closing, and reopening history

1. Review the lifecycle validation summary for the selected academic year.
2. Resolve every missing-semester error. Missing admission year, gender, category, and structured location are reporting-quality warnings.
3. Select **Confirm Annual History** to freeze all draft records in the user's authorized scope. Filters do not limit this action.
4. An Admin may select **Close Annual History** only after no draft records remain for the tenant and academic year.
5. A closed year is read-only. If a correction is formally authorized, an Admin may select **Reopen for Correction**, make the correction, and confirm and close the history again.

Principal users can review and confirm records only inside their permitted program/institute scope. Closing and reopening are Admin-only actions. Every lifecycle transition is recorded in the audit log.

## Current MVP limitation

## Location reporting

Student profiles provide separate **Home City / Town / Village**, **Home District**, and **Permanent Address** fields. Annual Enrollment History stores year-specific snapshots of these values so later profile changes do not silently rewrite confirmed historical reports.

Use **Location search** to find a city, town, village, district, or text in the permanent address, such as `Kalsar`. Use **Mahuva / Outside Mahuva** for a regional comparison and the **City / Town / Village** summary for place-wise counts. The **Students**, **Faculty**, and **Subjects** tabs change the type of academic-year data being reviewed.

Reliable Mahuva-versus-outside totals require the structured Home City / Town / Village field. The application does not guess a city from an unstructured address. Older records without structured location data appear as **Location not structured**. For existing draft history, update or re-import student locations and run **Prepare Current-Year History** again. Draft location snapshots are refreshed; confirmed historical records remain unchanged.

The MVP prepares the academic year and continuing-student draft. Final activation, bulk confirmation, exception handling for repeaters/transfers, and copying each operational configuration must remain reviewed steps until their validation workflows are implemented.
