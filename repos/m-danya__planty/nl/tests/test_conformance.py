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
