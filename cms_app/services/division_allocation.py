from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field

from sqlalchemy import select

from .. import db
from ..models import Division, Program, ProgramDivisionPlan, Student, StudentSubjectEnrollment


def _division_codes(count: int) -> list[str]:
    codes: list[str] = []
    for index in range(count):
        number = index
        code = ""
        while True:
            code = chr(ord("A") + number % 26) + code
            number = number // 26 - 1
            if number < 0:
                break
        codes.append(code)
    return codes


@dataclass
class AllocationMove:
    enrollment_no: str
    student_name: str
    from_division: str
    to_division: str


@dataclass
class AllocationPreview:
    program: Program
    semester: int
    approved_intake: int
    active_students: int
    division_capacity: int
    planned_divisions: int
    required_divisions: int
    total_capacity: int
    intake_batch_id: int | None = None
    admission_academic_year: str | None = None
    intake_division_capacity: int | None = None
    intake_batch_id: int | None = None
    admission_academic_year: str | None = None
    divisions: list[dict] = field(default_factory=list)
    assignments: list[AllocationMove] = field(default_factory=list)
    moves: list[AllocationMove] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    fingerprint: str = ""

    @property
    def can_apply(self) -> bool:
        return not self.errors


def build_allocation_preview(
    program_id: int,
    semester: int,
    approved_intake: int,
    trust_id: int | None = None,
    *,
    intake_batch_id: int | None = None,
    admission_academic_year: str | None = None,
    intake_division_capacity: int | None = None,
) -> AllocationPreview:
    program = db.session.get(Program, program_id)
    if not program:
        raise ValueError("Program not found.")
    if semester < 1 or semester > 8:
        raise ValueError("Semester is outside the supported range.")
    if approved_intake <= 0:
        raise ValueError("Approved annual intake must be greater than zero.")

    plan = db.session.execute(
        select(ProgramDivisionPlan).filter_by(program_id_fk=program_id, semester=semester)
    ).scalars().first()
    plan_capacity = int(plan.capacity_per_division or 0) if plan else 0
    capacity = int(intake_division_capacity or 0) or plan_capacity
    planned_count = int(plan.num_divisions or 0) if plan else 0

    student_query = (
        select(Student)
        .filter_by(program_id_fk=program_id, current_semester=semester, is_active=True)
        .order_by(Student.enrollment_no.asc())
    )
    if trust_id:
        student_query = student_query.filter(Student.trust_id_fk == trust_id)
    if intake_batch_id:
        student_query = student_query.filter(Student.intake_batch_id_fk == intake_batch_id)
    students = db.session.execute(student_query).scalars().all()

    preview = AllocationPreview(
        program=program,
        semester=semester,
        approved_intake=approved_intake,
        active_students=len(students),
        division_capacity=capacity,
        planned_divisions=planned_count,
        required_divisions=(math.ceil(len(students) / capacity) if capacity else 0),
        total_capacity=capacity * (math.ceil(len(students) / capacity) if capacity else 0),
        intake_batch_id=intake_batch_id,
        admission_academic_year=admission_academic_year,
        intake_division_capacity=intake_division_capacity,
    )
    if not plan:
        preview.errors.append("No approved division plan exists for this program and semester.")
    if intake_batch_id:
        unmapped_query = select(Student).filter_by(
            program_id_fk=program_id,
            current_semester=semester,
            is_active=True,
            intake_batch_id_fk=None,
        )
        if trust_id:
            unmapped_query = unmapped_query.filter(Student.trust_id_fk == trust_id)
        unmapped_count = len(db.session.execute(unmapped_query).scalars().all())
        if unmapped_count:
            preview.warnings.append(
                f"{unmapped_count} active student(s) in this semester have no admission-batch mapping and are excluded."
            )
    if capacity <= 0:
        preview.errors.append("Division capacity must be greater than zero.")
    if intake_division_capacity and plan_capacity and intake_division_capacity != plan_capacity:
        preview.warnings.append(
            f"Stored division rule capacity ({plan_capacity}) differs from this intake's capacity "
            f"({intake_division_capacity}). This allocation uses {intake_division_capacity}."
        )
    if len(students) > approved_intake:
        preview.errors.append(
            f"Active students exceed approved annual intake by {len(students) - approved_intake}."
        )
    if planned_count and preview.required_divisions != planned_count:
        preview.warnings.append(
            f"The stored rule declares {planned_count} division(s), while current enrollment requires "
            f"{preview.required_divisions}. This preview uses {preview.required_divisions} operational division(s)."
        )

    existing = db.session.execute(
        select(Division)
        .filter_by(program_id_fk=program_id, semester=semester)
        .order_by(Division.division_code.asc())
    ).scalars().all()
    existing_by_code = {d.division_code.upper(): d for d in existing}
    operational_count = preview.required_divisions
    codes = _division_codes(operational_count)
    extra_codes = sorted(code for code in existing_by_code if code not in codes)
    if extra_codes:
        preview.warnings.append(
            "Existing divisions outside the approved plan are excluded: " + ", ".join(extra_codes) + "."
        )
    for code in codes:
        division = existing_by_code.get(code)
        if not division:
            preview.errors.append(f"Planned Division {code} has not been created.")
        elif int(division.capacity or 0) != capacity:
            preview.warnings.append(
                f"Division {code} capacity will be aligned from {int(division.capacity or 0)} to {capacity}."
            )

    counts = [len(students) // operational_count + (1 if i < len(students) % operational_count else 0) for i in range(operational_count)] if operational_count else []
    offset = 0
    fingerprint_parts = [str(program_id), str(semester), str(approved_intake), str(capacity), str(planned_count), str(intake_batch_id or ""), str(intake_division_capacity or "")]
    for index, code in enumerate(codes):
        division = existing_by_code.get(code)
        assigned_students = students[offset:offset + counts[index]]
        offset += counts[index]
        preview.divisions.append({"code": code, "division": division, "proposed": len(assigned_students), "capacity": capacity})
        for student in assigned_students:
            current = db.session.get(Division, student.division_id_fk) if student.division_id_fk else None
            current_code = current.division_code if current else "Unassigned"
            fingerprint_parts.extend([student.enrollment_no, str(student.division_id_fk or ""), code])
            assignment = AllocationMove(
                enrollment_no=student.enrollment_no,
                student_name=getattr(student, "display_name", None) or f"{student.surname or ''} {student.student_name or ''}".strip(),
                from_division=current_code,
                to_division=code,
            )
            preview.assignments.append(assignment)
            if not division or student.division_id_fk != division.division_id:
                preview.moves.append(assignment)
    preview.fingerprint = hashlib.sha256("|".join(fingerprint_parts).encode("utf-8")).hexdigest()
    return preview


def apply_allocation(preview: AllocationPreview, expected_fingerprint: str, overrides: dict[str, str] | None = None) -> dict:
    if not preview.can_apply:
        raise ValueError("Allocation cannot be applied until all validation errors are resolved.")
    if not expected_fingerprint or expected_fingerprint != preview.fingerprint:
        raise ValueError("Division data changed after preview. Generate a fresh preview.")

    division_map = {row["code"]: row["division"] for row in preview.divisions}
    student_map = {
        student.enrollment_no: student
        for student in db.session.execute(
            select(Student).filter(
                Student.program_id_fk == preview.program.program_id,
                Student.current_semester == preview.semester,
                Student.is_active.is_(True),
                *([Student.intake_batch_id_fk == preview.intake_batch_id] if preview.intake_batch_id else []),
            )
        ).scalars().all()
    }
    overrides = overrides or {}
    allowed_codes = set(division_map)
    unknown_codes = sorted(set(overrides.values()) - allowed_codes)
    if unknown_codes:
        raise ValueError("Invalid target division: " + ", ".join(unknown_codes))
    final_assignments = {
        assignment.enrollment_no: overrides.get(assignment.enrollment_no, assignment.to_division)
        for assignment in preview.assignments
    }
    final_counts = {code: 0 for code in allowed_codes}
    for target_code in final_assignments.values():
        final_counts[target_code] += 1
    over_capacity = [
        f"{code} ({count}/{preview.division_capacity})"
        for code, count in sorted(final_counts.items())
        if count > preview.division_capacity
    ]
    if over_capacity:
        raise ValueError("Manual allocation exceeds division capacity: " + ", ".join(over_capacity))

    moved = 0
    synced = 0
    for enrollment_no, target_code in final_assignments.items():
        student = student_map.get(enrollment_no)
        division = division_map.get(target_code)
        if not student or not division:
            raise ValueError("Allocation scope changed after preview.")
        if student.division_id_fk == division.division_id:
            continue
        student.division_id_fk = division.division_id
        moved += 1
        enrollments = db.session.execute(
            select(StudentSubjectEnrollment).filter_by(
                student_id_fk=student.enrollment_no,
                semester=preview.semester,
                is_active=True,
            )
        ).scalars().all()
        for enrollment in enrollments:
            if enrollment.division_id_fk != division.division_id:
                enrollment.division_id_fk = division.division_id
                synced += 1
    for row in preview.divisions:
        row["division"].capacity = preview.division_capacity
    db.session.flush()
    return {"students_moved": moved, "subject_enrollments_synced": synced}
