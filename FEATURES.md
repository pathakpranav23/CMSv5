# CMSv5 Feature Map

This document outlines the core functionalities of the CMSv5 ERP system, organized by module. Use this to quickly locate features and understand the system's capabilities.

## 1. Dashboard (Home)
- **Role-Based Views**: Tailored dashboards for Admin, Principal, Clerk, Faculty, and Students.
- **Quick Stats**: Student counts, pending fees, upcoming exams (varies by role).

## 2. Academics Module
- **Program Management**: Create/Edit programs (BCA, BCom, etc.).
- **Subject Management**:
  - Add/Edit Subjects per Program & Semester.
  - **Subject Allocation**: Bulk assign electives to students (Grid View & CSV Upload).
- **Divisions**: Manage class divisions (A, B, C).
- **Attendance**: (Planned/Partial) Daily attendance tracking.

## 3. Student Management
- **Student List**: View, Search, and Filter students by Program, Semester, Division.
- **Profile Editing**: Update personal details, contact info, and photos.
- **Bulk Import**: Import students via Excel/CSV (`scripts/import_students.py`).
- **Semester Promotion**: Move students to the next semester (batch operation).

## 4. Fees Module
- **Receipt Generation**:
  - **Semester Fees**: Generate receipts for standard semester fees.
  - **Quick Payment**: Instant search & pay for walk-in students.
- **Payment Verification**: Verify online/offline payments (UTR tracking).
- **Reports**:
  - Daily Collection Report.
  - Pending Fees List.
  - Bankwise/Mode-wise summaries.

## 5. Examination Module
- **Exam Scheme**: Define credit rules, passing marks, and exam types (Internal/External).
- **Marks Entry**:
  - **Faculty View**: Enter marks for assigned subjects.
  - **Locking**: Freeze marks after entry.
- **Result Processing**: Calculate SGPA/CGPA (Automatic).
- **Reports**:
  - Student Marksheets (PDF).
  - Tabulation Registers (TR).
  - Hall Tickets.

## 6. User & Role Management
- **Users**: Manage accounts for Staff and Students.
- **Roles**: Admin, Principal, Clerk, Faculty, Student.
- **Permissions**: Role-based access control (RBAC) enforced on all routes.

## 7. System & Maintenance
- **Database Management**: SQLite database (Production: `cms.db`).
- **Scripts**:
  - `seed_users.py`: Reset/Create default users.
  - `fix_schema_*.py`: Database repair tools.
  - `import_*.py`: Bulk data loaders.
