# World-Class Multi-Tenant SaaS ERP Blueprint (CMSv5)

## 1. Vision
To build a world-class, multi-tenant Academic ERP/SaaS capable of serving Universities, Groups of Colleges, and Schools. The system emphasizes rapid onboarding, strict data integrity (NEP 2020 compliance), and a user-friendly "Wizard" approach to complex academic configurations.

## 2. Core Differentiator: The Onboarding Wizard
To solve the complexity of setting up an academic institution from scratch, CMSv5 features a guided **Onboarding Wizard**. This wizard ensures that dependencies are met in the correct order (e.g., Staff must exist before assigning subjects; Divisions must exist before enrolling students).

### Wizard Flow (Phase 1 Roadmap)

**Step 1: Institute Profile & Trust Structure**
*   **Goal:** Define the legal entity and branding.
*   **Inputs:** Trust Name, College Name(s), Logo, Address, Contact Info.
*   **Output:** Tenant configuration and Report Headers.

**Step 2: Staff Management & Bulk Import**
*   **Goal:** Populate the system with faculty and admin staff.
*   **Why here?** Subjects and Class Teachers cannot be assigned without Staff.
*   **Features:**
    *   Single Entry Form.
    *   **Bulk CSV Import** (Name, Email, Role, Designation).
    *   Role Assignment (Principal, HOD, Faculty, Clerk, Accountant).

**Step 3: Program & Medium of Instruction**
*   **Goal:** Define what the institute teaches.
*   **Features:**
    *   Add Program (e.g., "Bachelor of Commerce").
    *   **Select Medium(s):** English, Gujarati, Hindi, etc.
    *   **Architecture Note:** If multiple mediums are selected, the system creates **distinct Program entries** (e.g., "B.Com - English", "B.Com - Gujarati") to allow separate Fee Structures and Subject Lists.
    *   Define Duration (Years/Semesters).

**Step 4: Academic Structure & Divisions**
*   **Goal:** Define the physical/logical grouping of students.
*   **Features:**
    *   Configure Semesters for each Program.
    *   **Manage Divisions:** Create Divisions (A, B, C) per Semester/Medium.
    *   Define Intake Capacity per Division.

**Step 5: Subject Catalog & Allocation**
*   **Goal:** Define the curriculum (NEP 2020 Compliant).
*   **Features:**
    *   Create Subjects (Major, Minor, MDC, AEC, SEC, IKS).
    *   Define Credit Structure (Theory/Practical).
    *   **Subject Assignment:** Map Subjects to Staff (Faculty) for specific Divisions.

**Step 6: Student Enrollment**
*   **Goal:** Bring students into the system.
*   **Features:**
    *   **Bulk CSV Import:** Map students directly to Program, Semester, Medium, and Division.
    *   Generate Enrollment Numbers (if not provided).

---

## 3. Comprehensive Module List (The "Sweet 16")

1.  **Trust & Multi-Tenant Structure:** Centralized management for groups of colleges.
2.  **College Information:** Manage metadata, branding, and contact details.
3.  **Course (Program) Management:** Handling multiple mediums (Eng/Guj) and program lifecycles.
4.  **Staff Management:** Roles for Principal, Coordinator, Faculty, Clerk, Accountant, IT Officer, NSS/NCC Coordinators.
5.  **Student Management:** Medium-wise enrollment, profiles, and history.
6.  **Subject Management:** Align to staff, bulk assignment, multi-program assignment (e.g., English Faculty teaching BCA & BBA).
7.  **Division Management:** Capacity planning and sectioning per Program/Semester.
8.  **Attendance Management:** Daily tracking, aggregate reports, and mobile-friendly roster.
    *   **New:** Bulk Timetable Import (CSV) to auto-generate class schedules.
9.  **Exam Management:** Exam schemes, marks entry, hall tickets, result processing (GPA/CGPA).
    *   **New:** Bulk External Marks Import (Excel) for University results.
10. **Reports Management:** NEP reports, demographic analysis, academic performance.
11. **Inventory Management:** Asset tracking for labs, library, and campus infrastructure.
    *   **New:** Bulk Library/Asset Import (CSV) for rapid cataloging.
12. **Fees Management:** Structure definition, collection, receipts, and dues tracking.
13. **Announcement (Notice Board):** Targeted communication (Role/Program/Semester based).
14. **Material Management:** Digital content distribution and access control.
15. **HR Management:** Leave tracking, payroll basics, and service books for staff.
16. **World Class Analysis:** Dashboard for "Bird's Eye View" of institute health (Admissions, Finance, Academics).

## 4. Technical Architecture
*   **Frontend:** HTML5, Bootstrap 5 (Mobile First), Jinja2 Templates.
*   **Backend:** Python (Flask), SQLAlchemy ORM.
*   **Database:** PostgreSQL (Production) / SQLite (Dev).
*   **Deployment:** Dockerized / Cloud-Native (PythonAnywhere/AWS).
