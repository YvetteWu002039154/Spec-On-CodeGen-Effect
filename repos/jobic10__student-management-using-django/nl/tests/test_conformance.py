import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from adapter import build_driver  # noqa: E402
from loader import gencode_paths, load_gencodemodule  # noqa: E402

_PATHS = dict(gencode_paths())
_CACHE = {}


class _Unloadable:
    """Stand-in for a generation that raised on import.

    Building all four drivers eagerly meant one unloadable generation took down
    collection for the whole module — scoring every OTHER model 0-of-0 too, and,
    having no [impl_id] in its name, the crash was dropped by the scorer rather
    than counted. Loading lazily and capturing the exception makes an unloadable
    generation fail its own tests (the correct score for it) and leaves the rest
    intact. See Reports/variance_pilot/: across runs, one bad generation would
    otherwise blank an entire run.
    """

    def __init__(self, exc):
        self._exc = exc

    def __getattr__(self, name):
        raise self._exc


def _driver_for(ident):
    if ident not in _CACHE:
        try:
            module = load_gencodemodule(ident, _PATHS[ident])
        except Exception as exc:                          # noqa: BLE001
            module = _Unloadable(exc)
        _CACHE[ident] = build_driver(ident.split("/")[-1], module)
    return _CACHE[ident]


@pytest.fixture(params=sorted(_PATHS))
def driver(request):
    return _driver_for(request.param)


# ---------------------------------------------------------------------------
# Manage entities (Admin: add course/staff/student/subject/session)
# ---------------------------------------------------------------------------
def test_add_course(driver):
    assert driver.add_course_name() == "Physics"


def test_add_staff(driver):
    assert driver.staff_present() is True


def test_add_student(driver):
    assert driver.student_present() is True


def test_add_subject(driver):
    assert driver.add_subject_name() == "Algebra"


def test_add_session(driver):
    assert driver.add_session() is True


# ---------------------------------------------------------------------------
# Attendance & results (Staff take attendance / add result)
# ---------------------------------------------------------------------------
def test_take_attendance(driver):
    assert driver.attendance_present() is True


def test_add_result(driver):
    assert driver.result_marks() == 80.0


# ---------------------------------------------------------------------------
# Leave workflow (apply -> review/approve)
# ---------------------------------------------------------------------------
def test_apply_leave_is_pending(driver):
    assert driver.leave_pending() == "pending"


def test_review_leave_approves(driver):
    assert driver.leave_approved() == "approved"


# ---------------------------------------------------------------------------
# Feedback workflow (send -> review/reply)
# ---------------------------------------------------------------------------
def test_feedback_reply_stored(driver):
    assert driver.feedback_reply() == "thanks"
