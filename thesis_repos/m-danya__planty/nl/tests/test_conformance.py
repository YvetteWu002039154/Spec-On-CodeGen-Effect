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
# Task creation
# ---------------------------------------------------------------------------
def test_task_carries_its_title(driver):
    assert driver.created_task_title("Write thesis") == "Write thesis"


def test_new_task_is_not_completed(driver):
    assert driver.new_task_is_completed() is False


# ---------------------------------------------------------------------------
# Completion lifecycle
# ---------------------------------------------------------------------------
def test_completing_marks_task_done(driver):
    assert driver.completed_after_complete() is True


def test_reopening_marks_task_open(driver):
    assert driver.open_after_reopen() is False


# ---------------------------------------------------------------------------
# Container grouping
# ---------------------------------------------------------------------------
def test_add_task_to_container_lists_it(driver):
    assert driver.container_count_after_add() == 1


def test_remove_task_from_container_empties_it(driver):
    assert driver.container_count_after_remove() == 0


# ---------------------------------------------------------------------------
# Priority (Todoist-inspired)
# ---------------------------------------------------------------------------
def test_priority_scale_has_at_least_four_levels(driver):
    assert driver.priority_level_count() >= 4
