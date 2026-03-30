# Pilot Go-Live Checklist (Phase 1) — First Trust

Scope: 2 Institutes, 4 Programs, ~700 Students

## Institutes & Programs

- [ ] Institute 1: Smt. K. B. Parekh College of Computer Science
  - [ ] Program: BCA
- [ ] Institute 2: Shree H. K. Parekh College of Commerce and Management
  - [ ] Program: BBA
  - [ ] Program: B.Com (Gujarati Medium)
  - [ ] Program: B.Com (English Medium)

---

## 1) Trust Admin / SU Master Checklist (Do Once)

### A) Tenant Structure

- [ ] Trust exists and is active
- [ ] Add Institute 1 (exact name)
- [ ] Add Institute 2 (exact name)
- [ ] Create programs and map correctly:
  - [ ] BCA → Institute 1
  - [ ] BBA → Institute 2
  - [ ] B.Com (Gujarati Medium) → Institute 2
  - [ ] B.Com (English Medium) → Institute 2

### B) Roles & Users

- [ ] Institute 1 users
  - [ ] Principal (role=principal)
  - [ ] Clerk (role=clerk)
  - [ ] Faculty accounts created (role=faculty) for all staff teaching BCA pilot
- [ ] Institute 2 users
  - [ ] Principal (role=principal)
  - [ ] Clerk (role=clerk)
  - [ ] Faculty accounts created (role=faculty) for all staff teaching BBA/B.Com GU/B.Com EN pilot
- [ ] Optional: Trust admin account (role=admin)

### C) Scoping Verification

- [ ] Principal/Clerk only operate inside their institute/program scope
- [ ] Faculty can access their program context without cross-program leakage
- [ ] Super Admin can switch trust workspace safely

### Go/No-Go Gate A

- [ ] Each program exists under the correct institute
- [ ] All pilot users can login successfully

---

## 2) Institute 1 Checklist (BCA)

### Clerk — Academic Structure

- [ ] Create divisions for BCA (semester/year wise as per college)
- [ ] Import subjects semester-wise for BCA
- [ ] Verify subject type mapping (core/elective/practical) and semester tagging

### Clerk — Staff & Mapping

- [ ] Verify faculty list for BCA
- [ ] Faculty ↔ Subject mapping (CourseAssignment) complete for BCA
- [ ] Semester Coordinator(s) assigned for BCA

### Clerk — Timetable

- [ ] Configure timetable settings for BCA
- [ ] Add minimum viable timetable (pilot-ready)

### Clerk — Student Import

- [ ] Import BCA students in batches (semester-wise or division-wise)
- [ ] Validate after each batch:
  - [ ] Enrollment numbers unique
  - [ ] Program correct
  - [ ] Semester correct
  - [ ] Division correct
  - [ ] Active status correct

### Go/No-Go Gate B (BCA Ready)

- [ ] For each active semester: divisions + subjects + mappings exist
- [ ] Random sample: 20 students appear in attendance list

---

## 3) Institute 2 Checklist (BBA + B.Com GU + B.Com EN)

Note: Treat B.Com (Gujarati) and B.Com (English) as separate operational streams.

### Clerk — Academic Structure

- [ ] BBA: Create divisions (semester/year wise)
- [ ] BBA: Import subjects semester-wise
- [ ] B.Com (Gujarati): Create divisions (semester/year wise)
- [ ] B.Com (Gujarati): Import subjects semester-wise
- [ ] B.Com (English): Create divisions (semester/year wise)
- [ ] B.Com (English): Import subjects semester-wise
- [ ] Verify medium tagging and prevent GU/EN mixing

### Clerk — Staff & Mapping

- [ ] Verify faculty list for commerce institute
- [ ] BBA: Faculty ↔ Subject mapping complete
- [ ] B.Com (Gujarati): Faculty ↔ Subject mapping complete
- [ ] B.Com (English): Faculty ↔ Subject mapping complete
- [ ] Semester Coordinators assigned per program (and per medium where relevant)

### Clerk — Timetable

- [ ] Configure timetable settings per program
- [ ] Add minimum viable timetables:
  - [ ] BBA
  - [ ] B.Com (Gujarati)
  - [ ] B.Com (English)

### Clerk — Student Import

- [ ] Import students in 3 separate batches:
  - [ ] BBA
  - [ ] B.Com (Gujarati)
  - [ ] B.Com (English)
- [ ] Validate after each batch:
  - [ ] Enrollment numbers unique
  - [ ] Program correct
  - [ ] Semester correct
  - [ ] Division correct
  - [ ] Medium correct (GU/EN)
  - [ ] Active status correct

### Go/No-Go Gate C (Commerce Ready)

- [ ] Random sample: 20 students per program appear in attendance list
- [ ] Medium separation confirmed in lists and filters

---

## 4) Week-1 Operations (Daily Use)

### Attendance (Days 1–5)

- [ ] Faculty starts daily attendance marking for all pilot divisions
- [ ] Clerk resolves edge cases daily (division changes, late admissions, wrong semesters)
- [ ] Principal spot-checks defaulters/at-risk list for sanity

### Go/No-Go Gate D (Attendance Stable)

- [ ] Attendance % calculations match expectations for a sample class
- [ ] No persistent “students not showing in attendance” issues

---

## 5) Fees Go-Live (Days 3–7)

### Setup

- [ ] Define fee heads per program/category
- [ ] Create fee structures per program (and per medium where needed)
- [ ] Configure bank/UPI details for the institute/programs

### Operations

- [ ] Students submit payment proof
- [ ] Clerk verifies daily (approve/reject)
- [ ] Receipts generated and stored
- [ ] Exports/defaulter reports generated and usable

### Go/No-Go Gate E (Fees Stable)

- [ ] Receipt generation works reliably
- [ ] Verification queue workflow is manageable
- [ ] Exports usable for accounts team

---

## 6) Exams Pilot (Week 2)

### Start Small

- [ ] Choose 1–2 programs/semesters for the first scheme (simpler first)
- [ ] Create exam scheme for chosen scope

### Marks Entry

- [ ] Clerk enters marks (logged)
- [ ] Principal/Admin uses Freeze/Unlock governance:
  - [ ] Freeze scheme after entry
  - [ ] Unlock only with reason (time window)
  - [ ] Monitor PASS↔FAIL flips flagged (spot-check failed/borderline students only)

### Results

- [ ] Calculate results
- [ ] Verify result view and exports/reporting

### Go/No-Go Gate F (Exams Stable)

- [ ] One exam scheme completed end-to-end without manual fixes

---

## Key Risks to Watch

- [ ] GU vs EN mixing in B.Com streams (strict separation)
- [ ] Faculty-subject mapping completeness (prevents attendance/exams issues)
- [ ] Division correctness (attendance lists depend on it)

