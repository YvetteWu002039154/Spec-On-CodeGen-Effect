import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from adapter import build_driver  # noqa: E402
from loader import gencode_paths, load_gencodemodule  # noqa: E402

_DRIVERS = {
    ident: build_driver(ident.split("/")[-1], load_gencodemodule(ident, path))
    for ident, path in gencode_paths()
}


@pytest.fixture(params=sorted(_DRIVERS))
def driver(request):
    return _DRIVERS[request.param]


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
