# Faculty Attendance Insights Development Plan

## Goal

Give Faculty an assigned-subject and division dashboard that identifies attendance risk early and enables safe follow-up, without exposing administrative student-management actions.

## Implementation Status

- **Phase 1 and 2 baseline complete:** Faculty Class Insights calculates the defined attendance segments for an assigned subject and division, and presents the scoped dashboard.
- **Phase 3 baseline complete:** Faculty can privately notify selected, account-linked students from an assigned-class insight using approved templates or a short custom message. Delivery is recorded in the student inbox and audit log.
- **Phase 2 export complete:** Faculty can export the current assigned class and insight filter as an attendance-only CSV; the export is audit logged and contains no contact or account data.
- **Unreachable-student Clerk follow-up complete:** Faculty can flag an account-less student in an assigned class; the Clerk receives a tenant- and programme-scoped operational task and records progress or resolution. Faculty sees the resulting status in Class Insights.
- **Pending:** institution configuration and broader reports.

## Phase 1: Attendance Rules and Scope

Use completed attendance sessions for the current academic year only. Every result must be restricted to the current Faculty member's assigned subject, semester, division, programme, and tenant.

| Insight | Rule | Faculty action |
| --- | --- | --- |
| No attendance yet | 0% attendance after at least one completed session | Notify selected students or verify the attendance record |
| Critical attendance | 1-25% attendance | Send urgent reminder |
| Low attendance | 26-50% attendance | Send warning or follow up |
| Borderline attendance | Below the institution threshold, initially 60% | Notify and monitor |
| Recent absentees | Absent in the last 5 completed sessions | Send class follow-up |
| Consecutive absences | Absent for 5 or more consecutive completed sessions | Escalation or reminder |
| Attendance not marked | Expected class or session has no attendance record | Faculty self-reminder; not a student list |
| No account or unreachable | No linked account, email, or enabled notification channel | Faculty flags the case for Clerk or Admin follow-up |
| Material not opened | Requires material-view tracking | Future phase; do not infer from current data |
| Assessment follow-up | Requires reliable internal assessment or assignment data | Future phase |

## Phase 2: Faculty Class Insights Dashboard

Create a **Class Insights** page launched from an assigned subject.

Show summary cards for:

- No attendance yet
- Critical attendance
- Low attendance
- Borderline attendance
- Recent absentees
- Consecutive absences
- Attendance pending

Selecting a card opens a filtered, read-only student list containing:

- Student name, roll number, and division
- Attended and held session counts
- Attendance percentage
- Last attended date
- Current absence streak
- Account or notification delivery status

Faculty must not see student lifecycle, account creation, division assignment, semester promotion, or master-data export controls here.

## Phase 3: Faculty Actions

For a filtered insight list, Faculty can:

- Notify selected students
- Notify the full assigned class or division
- Send an attendance-reminder template
- Share a catch-up material
- View attendance history
- Export an attendance-only report for the assigned class

For unreachable students, Faculty can only flag a case. Clerk or Admin receives and resolves the follow-up task; Faculty cannot create accounts or alter contact information.

## Phase 4: Subject-Scoped Notification Workflow

Build a notification composer with:

- Subject and division locked from the assigned context
- Recipient count shown before sending
- Templates for low attendance, consecutive absence, revision session, and material reminder
- In-app notification as the primary delivery channel; optional email where enabled
- Individual delivery without exposing recipient lists
- Audit log capturing sender, recipients, template or custom content, time, and delivery status

## Phase 5: Roles and Data Protection

| Role | Access |
| --- | --- |
| Faculty | Assigned-subject and division insights; read-only attendance data; permitted communication actions |
| Clerk | Receives unreachable-student follow-ups and resolves account or contact issues; does not alter academic attendance |
| Principal and Admin | Programme or institution insight reports, configuration, and audit visibility |
| Student | Own attendance and received notifications only |

Every route must enforce assignment, programme, division, academic year, and tenant scope on the server. Hiding UI controls alone is not authorization.

## Phase 6: Configuration and Edge Cases

Institute-level settings:

- Borderline attendance threshold: default 60%
- Recent-absentee window: default 5 sessions
- Consecutive-absence threshold: default 5 sessions
- Minimum completed sessions before risk alerts: default 1
- Optional email notification delivery

Handle new enrolments, transferred students, cancelled sessions, missing timetables, and subsequently corrected attendance records.

## Phase 7: Testing and Rollout

Verify that:

- Faculty can see only insights for assigned classes.
- Faculty cannot invoke student administration endpoints directly.
- Clerk can resolve unreachable cases without altering academic attendance.
- Risk counts remain correct at every threshold and after attendance corrections.
- Notifications reach only selected, eligible students.
- Audit logs record actions without exposing other students' data.

## Recommended Delivery Order

1. Attendance calculations and Faculty Class Insights dashboard
2. Filtered insight lists and attendance-only export
3. Notify-selected and class notification workflow
4. Unreachable-student Clerk follow-up
5. Institution configuration, reports, and audit refinement
