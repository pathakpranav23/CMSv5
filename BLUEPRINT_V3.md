# CMSv5 ERP: World-Class Multi-Tenant Architecture (Blueprint V3)

**Version:** 3.0 (SaaS / Multi-Tenant Edition)  
**Date:** January 2026  
**Status:** In Development (Phase 1)

---

## 1. Executive Summary
CMSv5 is evolving from a single-college CMS into a **multi-tenant, world-class ERP platform** designed for educational trusts, groups of colleges, and universities. The new architecture supports hierarchical tenancy (`Trust` -> `Institute`), centralized management, and a seamless onboarding experience.

## 2. Core Architecture: Multi-Tenancy
The system now enforces a strict hierarchy to support SaaS operations:

1.  **Trust (Tenant)**: The top-level entity (e.g., "Shree Balvant Parekh Education Trust").
    *   Owns branding (Logo, Vision, Mission).
    *   Manages subscription and global settings.
2.  **Institute**: Individual colleges or schools under the Trust (e.g., "Parekh Commerce College").
    *   Has specific Affiliations (GTU, VNSGU) and AICTE codes.
    *   Operates independently for daily academic tasks.
3.  **Program**: Academic degrees (BCA, B.Com) offered by an Institute.
    *   Defines Medium (English/Gujarati), Duration, and Evaluation Rules.

### Database Schema Updates
*   **Trusts Table**: `trust_id`, `name`, `branding_assets`.
*   **Institutes Table**: `institute_id`, `trust_id_fk`, `affiliation_details`.
*   **Users Table**: Global users linked to specific scopes (Trust Admin vs. Institute Admin).

---

## 3. Onboarding Wizard (The "First 5 Minutes" Experience)
To ensure rapid adoption, a 6-step **Onboarding Wizard** guides new tenants from zero to fully configured:

*   **Step 1: Trust & Institute Profile**: Set up branding, address, and affiliation details.
*   **Step 2: Staff Import**: Bulk upload Faculty and Admin accounts via CSV.
*   **Step 3: Program Definition**: Create programs (e.g., BCA, B.Com) and set Mediums.
*   **Step 4: Academic Structure**: Configure Semesters and Division counts.
*   **Step 5: Subject Catalog**: Define or bulk-import subjects for the current term.
*   **Step 6: Student Enrollment**: Bulk upload student data to go live immediately.

---

## 4. Key Functional Modules (Phase 1)

### A. Academics & Timetable
*   **Flexible Structure**: Supports NEP 2020 (Major/Minor/MDC) and traditional semester systems.
*   **Timetable**: Automated conflict checking and faculty load balancing.
*   **Attendance**: Mobile-friendly daily tracking with compliance reports.

### B. Examination & Results
*   **Credit-Based Rules**: Dynamic passing logic based on credit types (Core vs. Elective).
*   **Grading**: Auto-calculation of SGPA/CGPA.
*   **Reports**:
    *   Hall Tickets.
    *   Tabulation Registers (TR).
    *   Marksheets (PDF).

### C. Admissions (Gujarat Context)
*   **GCAS Integration**: Ready for Gujarat Common Admission Service data import.
*   **Digital Gujarat**: Scholarship data compatibility.

---

## 5. Technical Roadmap
*   **Backend**: Flask (Python) + SQLAlchemy.
*   **Database**: SQLite (Dev) -> PostgreSQL (Production).
*   **Frontend**: Jinja2 + Bootstrap 5 (Responsive).
*   **Deployment**: PythonAnywhere (Phase 1), Docker/Cloud (Phase 2).

---

## 6. Next Steps
1.  Finalize **Onboarding Wizard** implementation (Steps 3-6).
2.  Deploy to **PythonAnywhere** for UAT.
3.  Begin **Timetable Module** development.
