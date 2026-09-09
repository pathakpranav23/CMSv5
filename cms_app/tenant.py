"""Tenant (Trust) isolation helpers for CMSv5.

Canonical module that the rest of the app should go through for:
  * Determining the effective trust of the current request
    (SA workspace aware).
  * Scope-fencing SQLAlchemy Core selects so they only return rows
    owned by the caller's trust.
  * A lightweight write-side ownership guard helper that redirects
    with a danger flash on mismatch (used for cross-trust
    POST/PUT/DELETE routes).

The JOIN/filter patterns here are mechanical translations of the
shapes already validated in the P1-P6 endpoint edits.  Any change in
this module should be accompanied by a re-run of
``tests/test_trust_isolation.py`` and
``tests/test_trust_scope_bank_details.py``.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Optional, Union

from flask import abort, flash, redirect, session, url_for
from flask_login import current_user
from sqlalchemy import false, select
from sqlalchemy.sql import Select

from . import db
from .models import (
    CourseAssignment,
    Division,
    Faculty,
    Institute,
    Program,
    ProgramBankDetails,
    Student,
    Subject,
    SubjectMaterial,
    Trust,
    User,
)


# ============================================================
# 1. Effective trust resolution
# ============================================================

def effective_trust_id() -> Optional[int]:
    """Return the trust id the *current request* should be scoped to.

    Super admins can select an "active trust" via the workspace
    picker; a regular user is always scoped to ``User.trust_id_fk``.
    Callers that need an explicit trust context (e.g. the services
    package) should pass it manually instead of relying on the
    request context; a helper ``trust_id_of_user()`` exists for that.
    """

    if not getattr(current_user, "is_authenticated", False):
        return None
    if getattr(current_user, "is_super_admin", False):
        try:
            return int(session.get("active_trust_id") or 0) or None
        except Exception:
            return None
    return getattr(current_user, "trust_id_fk", None)


# Legacy alias retained so the ~130 existing call sites inside
# main/routes.py don't require a mass rename during the P7 rollout.
def _effective_trust_id() -> Optional[int]:
    """Canonical implementation.  Re-exports :func:`effective_trust_id`."""
    return effective_trust_id()


def trust_id_of_user(user_id: Union[int, User]) -> Optional[int]:
    """Return ``User.trust_id_fk`` for any user id / user instance.

    Used by the :func:`scoped_select` path for user-anchored entities
    and by write-side helpers when operating on rows that don't have
    a direct ``trust_id_fk`` column yet (e.g. legacy log tables).
    """

    if isinstance(user_id, User):
        return getattr(user_id, "trust_id_fk", None)
    try:
        u = db.session.get(User, int(user_id))
    except Exception:
        return None
    if u is None:
        return None
    return getattr(u, "trust_id_fk", None)


# ============================================================
# 2. Write-side ownership guard
# ============================================================

def _require_same_trust(
    obj,
    fallback_redirect_endpoint: str = "main.index",
    message: str = "You are not authorized to access that resource.",
):
    """Return ``None`` if ``obj`` belongs to the caller's trust.

    Otherwise return a redirect response with a danger flash so the
    caller can simply ``rv = _require_same_trust(x); if rv: return rv``.

    Resolution order used when ``obj`` does not expose a direct
    ``trust_id_fk`` column:

        1. ``obj.trust_id_fk`` (direct column on Program/Faculty/Student/…)
        2. ``Program → Institute.trust_id_fk`` (if ``institute_id_fk``)
        3. ``User → User.trust_id_fk`` (if ``user_id_fk``)
    """

    caller = effective_trust_id()
    if caller is None:
        return None

    target: Optional[int] = getattr(obj, "trust_id_fk", None)
    if target is None:
        inst_id = getattr(obj, "institute_id_fk", None)
        if inst_id is not None:
            try:
                target = db.session.execute(
                    select(Institute.trust_id_fk).where(Institute.institute_id == inst_id)
                ).scalar_one_or_none()
            except Exception:
                target = None
        else:
            usr_id = getattr(obj, "user_id_fk", None)
            if usr_id is not None:
                target = trust_id_of_user(usr_id)

    try:
        if target is None or int(target) != int(caller):
            flash(message, "danger")
            return redirect(url_for(fallback_redirect_endpoint))
    except Exception:
        flash(message, "danger")
        return redirect(url_for(fallback_redirect_endpoint))
    return None


# ============================================================
# 3. Scope-fencing: scoped_select helper
# ============================================================

_JOIN_PATH_BY_ENTITY = {}  # populated lazily below after all classes defined


def _register_join(entity_cls, path_spec):
    """Record the JOIN/filter spec for an entity.

    ``path_spec`` is a list of ``(JoinLeftClass, OnClauseFn(select, effective_trust_id)
    -> (JoinedLeft, WhereExpression))`` tuples describing how to walk the graph from
    ``entity_cls`` to ``Institute.trust_id_fk``.  Because SQLAlchemy 1.4 Core selects
    don't expose an object-oriented ``.join()`` style that chains to the last JOIN
    target automatically, we construct the path imperatively: apply JOIN sequentially
    and return a WHERE clause that constrains the *last* joined Institute.
    """

    _JOIN_PATH_BY_ENTITY[entity_cls] = path_spec


def _path_program():
    return [(Program, lambda q, tid: (
        q.join(Institute, Program.institute_id_fk == Institute.institute_id),
        Institute.trust_id_fk == tid,
    ))]


def _path_program_anchor(anchor_cls, anchor_to_program_fk):
    """Entity → Program → Institute → Trust.  Works for any row with program_id_fk."""
    return [
        (anchor_cls, lambda q, tid: (
            q.join(Program, getattr(anchor_cls, anchor_to_program_fk) == Program.program_id),
            None,
        )),
        (Program, lambda q, tid: (
            q.join(Institute, Program.institute_id_fk == Institute.institute_id),
            Institute.trust_id_fk == tid,
        )),
    ]


def _path_student_anchor(anchor_cls, anchor_to_student_fk):
    """Entity → Student → Program → Institute → Trust."""
    return [
        (anchor_cls, lambda q, tid: (
            q.join(Student, getattr(anchor_cls, anchor_to_student_fk) == Student.enrollment_no),
            None,
        )),
        (Student, lambda q, tid: (
            q.join(Program, Student.program_id_fk == Program.program_id),
            None,
        )),
        (Program, lambda q, tid: (
            q.join(Institute, Program.institute_id_fk == Institute.institute_id),
            Institute.trust_id_fk == tid,
        )),
    ]


def _path_subject_anchor(anchor_cls, anchor_to_subject_fk):
    """Entity → Subject → Program → Institute → Trust."""
    return [
        (anchor_cls, lambda q, tid: (
            q.join(Subject, getattr(anchor_cls, anchor_to_subject_fk) == Subject.subject_id),
            None,
        )),
        (Subject, lambda q, tid: (
            q.join(Program, Subject.program_id_fk == Program.program_id),
            None,
        )),
        (Program, lambda q, tid: (
            q.join(Institute, Program.institute_id_fk == Institute.institute_id),
            Institute.trust_id_fk == tid,
        )),
    ]


def _path_faculty_anchor(anchor_cls, anchor_to_faculty_user_fk):
    """Entity → Faculty.user_id_fk → Faculty → Program → Institute → Trust.

    Used for CourseAssignment where ``faculty_id_fk`` points at ``User.user_id``
    (not a Faculty PK — Faculty.faculty_id is separate).  Walk Faculty via its
    user_id_fk FK.
    """
    return [
        (anchor_cls, lambda q, tid: (
            q.join(Faculty, getattr(anchor_cls, anchor_to_faculty_user_fk) == Faculty.user_id_fk),
            None,
        )),
        (Faculty, lambda q, tid: (
            q.join(Program, Faculty.program_id_fk == Program.program_id),
            None,
        )),
        (Program, lambda q, tid: (
            q.join(Institute, Program.institute_id_fk == Institute.institute_id),
            Institute.trust_id_fk == tid,
        )),
    ]


def _path_direct_trust_column(entity_cls):
    """Entities that already carry ``trust_id_fk`` can short-circuit."""
    return [(entity_cls, lambda q, tid: (q, getattr(entity_cls, "trust_id_fk") == tid))]


# Register all 6 priority-7 entities, plus the commonly-seen extensions.
_register_join(Program, _path_program())
_register_join(ProgramBankDetails, _path_program_anchor(ProgramBankDetails, "program_id_fk"))
_register_join(Division, _path_program_anchor(Division, "program_id_fk"))
_register_join(Subject, _path_program_anchor(Subject, "program_id_fk"))
_register_join(Faculty, _path_direct_trust_column(Faculty) + _path_program_anchor(Faculty, "program_id_fk"))
_register_join(Student, _path_direct_trust_column(Student) + _path_program_anchor(Student, "program_id_fk"))
_register_join(CourseAssignment, _path_subject_anchor(CourseAssignment, "subject_id_fk"))
_register_join(SubjectMaterial, _path_subject_anchor(SubjectMaterial, "subject_id_fk"))
_register_join(User, _path_direct_trust_column(User))
_register_join(Institute, _path_direct_trust_column(Institute))
_register_join(Trust, _path_direct_trust_column(Trust))


def scoped_select(entity_cls, trust_id: Optional[int] = None) -> Select:
    """Return a SQLAlchemy ``select(entity_cls)`` fenced to ``trust_id``.

    If ``trust_id`` is ``None`` the request context is consulted via
    :func:`effective_trust_id`.  If *that* also returns ``None`` (SA with
    no active workspace, or anonymous caller) the return value is simply
    ``select(entity_cls)`` — no scope applied, global view by design.

    If any JOIN fails at construction time the query is collapsed to
    ``select(entity_cls).where(false())`` so no rows leak, matching the
    safety pattern now used throughout the P1-P6 edits.
    """

    q: Select = select(entity_cls)
    tid = trust_id if trust_id is not None else effective_trust_id()
    if tid is None:
        return q

    path = _JOIN_PATH_BY_ENTITY.get(entity_cls)
    if not path:
        # Unknown entity: return an intentionally-empty query rather than
        # risk returning unfiltered rows.  Callers can fall back to an
        # explicit manual JOIN if they need support for a new model.
        return q.where(false())

    where_fragments = []
    try:
        for _marker, fn in path:
            step_q, where_expr = fn(q, tid)
            q = step_q
            if where_expr is not None:
                where_fragments.append(where_expr)
    except Exception:
        return select(entity_cls).where(false())

    if where_fragments:
        # Pick the *last* where expression added.  In multi-step paths the
        # last is Institute.trust_id_fk == tid; the earlier direct-column
        # direct-match filters are intentionally appended too, so when both
        # a direct trust_id_fk AND the join path exist we AND them to be safe.
        try:
            q = q.where(*where_fragments)
        except Exception:
            return select(entity_cls).where(false())
    return q


# ============================================================
# 4. Log-table trust backfill helpers (used by the P7-D migration)
# ============================================================

def _backfill_trust_for_log(log_row) -> Optional[int]:
    """Derive a trust id from any log row, using the cheapest available FK.

    Resolution order (matched to the patterns used in the 3 log tables being
    migrated in P7-D):

        1. Direct ``trust_id_fk`` column (already true of DataAuditLog today)
        2. Program → Institute.trust_id_fk (for ImportLog / DataAuditLog with program_id_fk)
        3. Actor user → User.trust_id_fk (for PasswordChangeLog / MaterialLog / ImportLog)
        4. Student → Student.trust_id_fk (for attendance/fee-payment rows later)
    """

    direct = getattr(log_row, "trust_id_fk", None)
    if direct is not None:
        return int(direct)

    prog_id = getattr(log_row, "program_id_fk", None)
    if prog_id is not None:
        try:
            prog_trust = db.session.execute(
                select(Institute.trust_id_fk)
                .join(Program, Program.institute_id_fk == Institute.institute_id)
                .where(Program.program_id == prog_id)
            ).scalar_one_or_none()
            if prog_trust is not None:
                return int(prog_trust)
        except Exception:
            pass

    for attr in ("actor_user_id_fk", "changed_by_user_id_fk", "user_id_fk", "created_by_user_id"):
        usr_id = getattr(log_row, attr, None)
        if usr_id is not None:
            usr_trust = trust_id_of_user(usr_id)
            if usr_trust is not None:
                return int(usr_trust)

    for attr in ("enrollment_no", "student_id_fk"):
        enr = getattr(log_row, attr, None)
        if enr:
            try:
                stu = db.session.get(Student, enr)
                stu_trust = getattr(stu, "trust_id_fk", None) if stu is not None else None
                if stu_trust is not None:
                    return int(stu_trust)
            except Exception:
                pass
    return None
