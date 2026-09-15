import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from adapter import build_driver  # noqa: E402
from loader import dependency_used, gencode_paths, load_gencodemodule  # noqa: E402

# Generations are loaded LAZILY, per driver, and an import-time crash is captured
# rather than raised. Loading all four eagerly here meant one generation that
# raises on import (e.g. a pydantic-v1 `Field(regex=...)` under pydantic v2) took
# down collection for the whole module, scoring every OTHER model 0-of-0 too.
# That is fatal when re-scoring across runs (Reports/variance_pilot/): a single
# bad generation would blank an entire run. Now an unloadable generation fails
# its own tests — which is the correct score for it — and leaves the rest intact.
_PATHS = dict(gencode_paths())
_CACHE = {}


class _Unloadable:
    def __init__(self, exc):
        self._exc = exc

    def __getattr__(self, name):
        raise self._exc


def _driver_for(ident):
    if ident not in _CACHE:
        try:
            module = load_gencodemodule(ident, _PATHS[ident])
        except Exception as exc:
            module = _Unloadable(exc)
        _CACHE[ident] = build_driver(ident.split("/")[-1], module)
    return _CACHE[ident]


@pytest.fixture(params=sorted(_PATHS))
def driver(request):
    return _driver_for(request.param)


# ---------------------------------------------------------------------------
# Add / read
# ---------------------------------------------------------------------------
def test_add_task(driver):
    assert driver.add_task_is_observable() is True


def test_list_all_tasks(driver):
    assert driver.list_all_count(3) >= 3


# ---------------------------------------------------------------------------
# Update status / delete
# ---------------------------------------------------------------------------
def test_update_task_status(driver):
    assert driver.update_status_observed() == "in_progress"


def test_delete_task(driver):
    assert driver.delete_removes_task() is True


# ---------------------------------------------------------------------------
# Hierarchy / dependencies
# ---------------------------------------------------------------------------
def test_create_child_task(driver):
    assert driver.child_links_to_parent() is True


def test_link_dependency(driver):
    assert bool(driver.link_dependency_recorded()) is True


def test_ready_reflects_dependency(driver):
    before, after = driver.ready_reflects_dependency()
    assert before is False and after is True


# ---------------------------------------------------------------------------
# Bulk write / hierarchical view
# ---------------------------------------------------------------------------
def test_bulk_write_tasks(driver):
    assert driver.bulk_write_creates(2) >= 2


def test_hierarchical_list(driver):
    flat, top = driver.hierarchical_nests_child()
    assert flat > top


# ---------------------------------------------------------------------------
# Dependency usage — the description names pydantic_ai; does the generation
# import and use it, or hand-roll a substitute? Static (AST) check — see
# loader.dependency_used and CONTRACT.md § "Dependency usage".
# ---------------------------------------------------------------------------
@pytest.fixture(params=sorted(_PATHS))
def ident(request):
    return request.param


# One test per named dependency rather than a @parametrize: parametrize ids
# append "-<dep>" inside the brackets, which breaks the canonical
# test_xxx[nl/<model>] id shape the step3 scorer parses.
def _assert_dependency_used(ident, dep):
    assert dependency_used(_PATHS[ident], dep), (
        f"{ident} does not import and use '{dep}' — the description names it, "
        f"so a hand-rolled substitute does not use the dependency"
    )


def test_uses_named_dependency_pydantic_ai(ident):
    _assert_dependency_used(ident, "pydantic_ai")
