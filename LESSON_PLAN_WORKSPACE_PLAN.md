# Lesson Plan Workspace Plan

## Goal

Convert Faculty DOCX/Excel import drafts into a subject-, division-, academic-year-scoped lesson plan that tracks planned and actual topic delivery.

## Data model

`LessonPlan` owns one Faculty assignment context and has a draft/active/locked status. It contains ordered `LessonPlanUnit` records, each containing ordered `LessonPlanTopic` records. A delivery record stores actual date, duration, status, evidence link, and revision/defer note without overwriting the planned topic.

## Faculty workspace

Header: subject, programme, semester, division, academic year, plan status, planned/delivered hours, and syllabus completion.

Unit coverage shows planned versus delivered hours, status, and next topic. A selected unit shows ordered topics with planned duration/date, actual delivery, status, evidence, and actions to mark delivered, defer/revise, attach material, or add a draft topic.

## Import workflow

Faculty selects an assigned class and uploads either `.xlsx` or `.docx`; type is detected from the file. Both routes create a private import draft. Faculty reviews extracted/validated rows, corrects mapping, and confirms conversion to a Lesson Plan draft. No import may overwrite delivered topics.

## Roles

Faculty may create/edit only plans for active assignments. Principal/Admin have read/report and optional review/lock access. Clerk has no academic editing access. Students may see only explicitly published coverage and resources.

## Delivery order

1. Add LessonPlan, Unit, Topic, and Delivery schema.
2. Convert reviewed import draft into editable plan.
3. Build Faculty Lesson Plan Workspace and delivery actions.
4. Add materials, assessment, extra-class, and student-facing integrations.
