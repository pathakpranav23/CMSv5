from datetime import date, timedelta
import random
from typing import Optional
from sqlalchemy import select

from cms_app import create_app, db
from cms_app.models import Program, Division, Student, Subject, Attendance, StudentSubjectEnrollment


def seed(year: Optional[int] = None, weekdays_only: bool = False, use_enrollments: bool = False) -> None:
    """Seed dummy attendance for BCA Semesters 3 and 5 for September.

    - Creates one attendance row per student per subject per day in September.
    - Status is randomly chosen from A/P/L.
    - Skips inserting if a record for (student, subject, date) already exists.
    """
    app = create_app()
    with app.app_context():
        bca = db.session.execute(select(Program).filter_by(program_name="BCA")).scalars().first()
        if not bca:
            print("BCA program not found. Aborting.")
            return

        target_semesters = [3, 5]
        divs = (
            db.session.execute(
                select(Division)
                .filter(Division.program_id_fk == bca.program_id)
                .filter(Division.semester.in_(target_semesters))
                .order_by(Division.semester, Division.division_code)
            ).scalars().all()
        )
        div_map = {d.division_id: d for d in divs}
        div_ids = list(div_map.keys())

        students = (
            db.session.execute(
                select(Student)
                .filter(Student.division_id_fk.in_(div_ids))
                .order_by(Student.enrollment_no)
            ).scalars().all()
        )

        subjects_by_sem = {
            3: db.session.execute(select(Subject).filter_by(program_id_fk=bca.program_id, semester=3).order_by(Subject.subject_name)).scalars().all(),
            5: db.session.execute(select(Subject).filter_by(program_id_fk=bca.program_id, semester=5).order_by(Subject.subject_name)).scalars().all(),
        }

        # If using enrollments, build per-student subject lists for active enrollments in Sem 3/5
        subjects_by_student = {}
        if use_enrollments:
            enr_rows = (
                db.session.execute(
                    select(StudentSubjectEnrollment)
                    .filter(StudentSubjectEnrollment.student_id_fk.in_([s.enrollment_no for s in students]))
                    .filter(StudentSubjectEnrollment.is_active == True)
                    .filter(StudentSubjectEnrollment.semester.in_(target_semesters))
                ).scalars().all()
            )
            sid_to_subjects = {}
            for r in enr_rows:
                sid_to_subjects.setdefault(r.student_id_fk, set()).add(r.subject_id_fk)
            # Fetch subject objects once
            all_subject_ids = {sid for sids in sid_to_subjects.values() for sid in sids}
            sub_map = {s.subject_id: s for s in db.session.execute(select(Subject).filter(Subject.subject_id.in_(list(all_subject_ids)))).scalars().all()}
            for stu in students:
                subjects_by_student[stu.enrollment_no] = [sub_map[sid] for sid in sid_to_subjects.get(stu.enrollment_no, set()) if sid in sub_map]

        # Determine September of the provided year or current year.
        today = date.today()
        yr = year or today.year
        start = date(yr, 9, 1)
        end = date(yr, 9, 30)

        statuses = ["A", "P", "L"]
        created = 0
        skipped = 0

        d = start
        while d <= end:
            # Skip weekends if requested (Mon-Fri only)
            if weekdays_only and d.weekday() >= 5:
                d += timedelta(days=1)
                continue
            for stu in students:
                div = div_map.get(stu.division_id_fk)
                sem = (div.semester if div else stu.current_semester) or None
                if sem not in target_semesters:
                    continue
                if use_enrollments:
                    subjects = subjects_by_student.get(stu.enrollment_no, [])
                    # Fallback to semester subjects if no enrollment found
                    if not subjects:
                        subjects = subjects_by_sem.get(sem, [])
                else:
                    subjects = subjects_by_sem.get(sem, [])
                for sub in subjects:
                    # Avoid duplicates on reruns
                    exists = db.session.execute(select(Attendance).filter_by(
                        student_id_fk=stu.enrollment_no,
                        subject_id_fk=sub.subject_id,
                        date_marked=d,
                    )).scalars().first()
                    if exists:
                        skipped += 1
                        continue
                    st = random.choice(statuses)
                    att = Attendance(
                        student_id_fk=stu.enrollment_no,
                        subject_id_fk=sub.subject_id,
                        division_id_fk=stu.division_id_fk,
                        date_marked=d,
                        status=st,
                        semester=sem,
                        period_no=1,
                    )
                    db.session.add(att)
                    created += 1
            d += timedelta(days=1)

        db.session.commit()
        print(
            f"Created {created} rows, skipped {skipped}. Seeded September {yr} for BCA Sem 3 & 5."
        )


if __name__ == "__main__":
    import sys
    y = None
    weekdays = False
    use_enr = False
    args = sys.argv[1:]
    for a in args:
        a = (a or "").strip().lower()
        if a.isdigit():
            try:
                y = int(a)
            except Exception:
                pass
        elif a in ("--weekdays", "-w"):
            weekdays = True
        elif a in ("--use-enrollments", "--use-enr", "-e"):
            use_enr = True
    seed(year=y, weekdays_only=weekdays, use_enrollments=use_enr)