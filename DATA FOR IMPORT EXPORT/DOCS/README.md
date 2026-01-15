# Parekh Colleges Management System (PCMS) - MVP

This is a minimal Flask-based web application scaffold for the Parekh Colleges Management System (PCMS), aligned with the blueprint exported to Markdown.

## Features
- Flask application factory with SQLite dev database (PostgreSQL-ready via `DATABASE_URL`).
- SQLAlchemy models reflecting core entities: Programs, Subject Types, Divisions, Users, Students, Subjects, Credit Structure, Assignments, Attendance, Grades, Credit Log, Fees.
- Bootstrap 5 UI with basic pages: Home, Dashboard, Students.
  - Students page now renders real data after import.

## Getting Started (Windows)
1. Create a virtual environment:
   ```powershell
   py -3 -m venv venv
   .\venv\Scripts\Activate.ps1
   ```
2. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
3. Run the app:
   ```powershell
   python app.py
   ```
4. Open in browser: `http://127.0.0.1:5000/`

## Configure Database
- Dev default: SQLite file `cms.db` (auto-created on first run).
- Production/Cloud: Set `DATABASE_URL` environment variable (e.g., PostgreSQL: `postgresql+psycopg2://user:pass@host:port/dbname`).
  ```powershell
  $env:DATABASE_URL = "postgresql+psycopg2://postgres:postgres@localhost:5432/pcms"
  ```

## Importing Bulk Student Data (Excel)

The university-provided Excel files are supported for bulk import:

- `c:\project\CMSv5\BCA Sem 3 Bulk Student Data 2025 V2.xlsx`
- `c:\project\CMSv5\BCA Sem 5 Bulk Student Data 2025.xlsx`

Steps:

1. Ensure dependencies are installed (includes `openpyxl`):
   ```powershell
   pip install -r requirements.txt
   ```
2. Run the importer (from the project root):
   ```powershell
   python .\scripts\import_students.py
   ```
3. Open `http://127.0.0.1:5000/students` to view imported data.

How it works:
- Detects Program (`BCA`) and Semester (`Sem 3`, `Sem 5`) from filenames.
- Creates missing `Program` and `Division` records.
- Inserts/updates `Student` entries keyed by `enrollment_no`.
- Maps common header names: Enrollment No, Name, Surname, Division, Semester, Mobile, DOB.

## Next Steps
- Add authentication and role-based access (Flask-Login).
- Implement data views and CRUD for Programs, Students, Subjects, Attendance, Grades.
- Add migrations (Flask-Migrate) and seed scripts.
- Wire real data to templates and tables.