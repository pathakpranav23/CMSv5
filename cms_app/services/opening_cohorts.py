from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass, field

from sqlalchemy import select

from .. import db
from ..models import Program, Student


ACADEMIC_YEAR_RE = re.compile(r"^(\d{4})-(\d{2})$")


def _academic_year(start_year: int) -> str:
    return f"{start_year}-{(start_year + 1) % 100:02d}"


def _parse_academic_year(value: str) -> int:
    match = ACADEMIC_YEAR_RE.fullmatch((value or "").strip())
    if not match or int(match.group(2)) != (int(match.group(1)) + 1) % 100:
        raise ValueError("Select a valid current academic session, for example 2026-27.")
    return int(match.group(1))


@dataclass
class OpeningCohortGroup:
    admission_academic_year: str
    completion_academic_year: str
    current_stage: str
    semesters: list[int] = field(default_factory=list)
    students: list[Student] = field(default_factory=list)


@dataclass
class OpeningCohortPreview:
    program: Program
    current_academic_year: str
    duration_years: int
    proposed_groups: list[OpeningCohortGroup]
    preserved_students: list[Student]
    exceptions: list[dict]
    fingerprint: str

    @property
    def proposed_count(self) -> int:
        return sum(len(group.students) for group in self.proposed_groups)


def build_opening_cohort_preview(program_id: int, current_academic_year: str, trust_id: int | None) -> OpeningCohortPreview:
    current_start = _parse_academic_year(current_academic_year)
    program = db.session.get(Program, int(program_id))
    if not program:
        raise ValueError("Program was not found.")
    duration = max(int(program.program_duration_years or 0), 1)
    maximum_semester = duration * 2
    query = select(Student).where(
        Student.program_id_fk == program.program_id,
        Student.is_active.is_(True),
    ).order_by(Student.current_semester.asc(), Student.enrollment_no.asc())
    if trust_id:
        query = query.where(Student.trust_id_fk == trust_id)
    students = db.session.execute(query).scalars().all()

    groups: dict[tuple[str, str, int], OpeningCohortGroup] = {}
    preserved: list[Student] = []
    exceptions: list[dict] = []
    fingerprint_parts = [str(program.program_id), current_academic_year, str(duration)]
    for student in students:
        fingerprint_parts.extend([
            student.enrollment_no,
            str(student.current_semester or ""),
            student.admission_academic_year or "",
        ])
        if (student.admission_academic_year or "").strip():
            preserved.append(student)
            continue
        try:
            semester = int(student.current_semester or 0)
        except (TypeError, ValueError):
            semester = 0
        if semester < 1 or semester > maximum_semester:
            exceptions.append({
                "student": student,
                "reason": f"Semester must be between 1 and {maximum_semester} for this {duration}-year program.",
            })
            continue
        study_year = int(math.ceil(semester / 2.0))
        admission_start = current_start - (study_year - 1)
        completion_start = admission_start + duration - 1
        admission_year = _academic_year(admission_start)
        completion_year = _academic_year(completion_start)
        key = (admission_year, completion_year, study_year)
        group = groups.setdefault(
            key,
            OpeningCohortGroup(
                admission_academic_year=admission_year,
                completion_academic_year=completion_year,
                current_stage=f"Year {study_year}",
            ),
        )
        group.students.append(student)
        if semester not in group.semesters:
            group.semesters.append(semester)

    proposed_groups = sorted(groups.values(), key=lambda row: row.admission_academic_year, reverse=True)
    for group in proposed_groups:
        group.semesters.sort()
    fingerprint = hashlib.sha256("|".join(fingerprint_parts).encode("utf-8")).hexdigest()
    return OpeningCohortPreview(
        program=program,
        current_academic_year=current_academic_year,
        duration_years=duration,
        proposed_groups=proposed_groups,
        preserved_students=preserved,
        exceptions=exceptions,
        fingerprint=fingerprint,
    )


def apply_opening_cohort_preview(preview: OpeningCohortPreview, fingerprint: str) -> int:
    if not fingerprint or fingerprint != preview.fingerprint:
        raise ValueError("Student data changed after the preview. Generate a fresh preview before applying.")
    updated = 0
    for group in preview.proposed_groups:
        for preview_student in group.students:
            student = db.session.get(Student, preview_student.enrollment_no)
            if student and not (student.admission_academic_year or "").strip():
                student.admission_academic_year = group.admission_academic_year
                # Historical opening cohorts are deliberately not linked to an
                # approved-intake record unless the institution creates one.
                student.intake_batch_id_fk = None
                updated += 1
    return updated
