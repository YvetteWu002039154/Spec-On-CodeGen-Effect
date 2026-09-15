import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from structure import Implementation, Unsupported            # noqa: E402
from loader import gencode_paths, load_gencodemodules  # noqa: E402

_PARAMS = [ident for ident, _ in gencode_paths()]
_PATHS = dict(gencode_paths())
_cache = {}

_MANAGER_METHODS = frozenset({"create_user", "create_superuser"})
_AUTH_VOCAB = ("USER_TYPE", "GENDER", "USERNAME_FIELD", "REQUIRED_FIELDS")


def _impl(ident):
    if ident not in _cache:
        try:
            _cache[ident] = Implementation(
                ident, load_gencodemodules(ident, _PATHS[ident]))
        except Exception as exc:
            # A generation that does not load exposes no structure at all: build
            # an empty implementation so every behavior FAILS (this track never
            # skips / marks N/A -- a module that does not load is a failure).
            impl = Implementation(ident, [])
            impl._load_error = exc
            _cache[ident] = impl
    return _cache[ident]


@pytest.fixture(params=_PARAMS)
def impl(request):
    return _impl(request.param)


def _guard(fn):
    try:
        return fn()
    except Unsupported as exc:
        pytest.fail(f"structure not present: {exc}")


# ---------------------------------------------------------------------------
# Methods under a class
# ---------------------------------------------------------------------------
def test_manager_defines_create_user_and_superuser(impl):
    # U1: CustomUserManager carries create_user + create_superuser.
    assert _MANAGER_METHODS <= _guard(lambda: impl.methods("CustomUserManager"))


# ---------------------------------------------------------------------------
# Composition link (--*) and CustomUser class-level vocabulary
# ---------------------------------------------------------------------------
def test_customuser_objects_is_manager(impl):
    # U2: CustomUserManager --* CustomUser : objects (the diagram's one link).
    assert _guard(impl.objects_is_manager) is True


def test_customuser_auth_vocabulary_present(impl):
    # U3: CustomUser declares USER_TYPE / GENDER / USERNAME_FIELD / REQUIRED_FIELDS.
    for attr in _AUTH_VOCAB:
        assert _guard(lambda a=attr: impl.has_attr("CustomUser", a)) is True


# ---------------------------------------------------------------------------
# Association links (--> : attr) — target type by reflection
# ---------------------------------------------------------------------------
def test_student_associations(impl):
    # U4: Student --> CustomUser (admin), Course (course), Session (session).
    assert "CustomUser" in _guard(lambda: impl.attr_refs("Student", "admin"))
    assert "Course" in _guard(lambda: impl.attr_refs("Student", "course"))
    assert "Session" in _guard(lambda: impl.attr_refs("Student", "session"))


def test_staff_associations(impl):
    # U5: Staff --> CustomUser (admin), Course (course).
    assert "CustomUser" in _guard(lambda: impl.attr_refs("Staff", "admin"))
    assert "Course" in _guard(lambda: impl.attr_refs("Staff", "course"))


def test_subject_associations(impl):
    # U6: Subject --> Course (course), Staff (staff).
    assert "Course" in _guard(lambda: impl.attr_refs("Subject", "course"))
    assert "Staff" in _guard(lambda: impl.attr_refs("Subject", "staff"))


def test_attendance_associations(impl):
    # U7: Attendance --> Session (session), Subject (subject).
    assert "Session" in _guard(lambda: impl.attr_refs("Attendance", "session"))
    assert "Subject" in _guard(lambda: impl.attr_refs("Attendance", "subject"))


def test_attendance_report_associations(impl):
    # U8: AttendanceReport --> Attendance (attendance), Student (student); has status.
    assert "Attendance" in _guard(lambda: impl.attr_refs("AttendanceReport", "attendance"))
    assert "Student" in _guard(lambda: impl.attr_refs("AttendanceReport", "student"))
    assert _guard(lambda: impl.has_attr("AttendanceReport", "status")) is True


def test_student_result_associations(impl):
    # U9: StudentResult --> Student (student), Subject (subject); has test + exam.
    assert "Student" in _guard(lambda: impl.attr_refs("StudentResult", "student"))
    assert "Subject" in _guard(lambda: impl.attr_refs("StudentResult", "subject"))
    assert _guard(lambda: impl.has_attr("StudentResult", "test")) is True
    assert _guard(lambda: impl.has_attr("StudentResult", "exam")) is True


def test_session_year_span(impl):
    # U10: Session carries start_year and end_year.
    assert _guard(lambda: impl.has_attr("Session", "start_year")) is True
    assert _guard(lambda: impl.has_attr("Session", "end_year")) is True
