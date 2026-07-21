import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from adapter import build_driver  # noqa: E402
from loader import dependency_used, gencode_paths, load_gencodemodule  # noqa: E402

_DRIVERS = {
    ident: build_driver(ident.split("/")[-1], load_gencodemodule(ident, path))
    for ident, path in gencode_paths()
}


@pytest.fixture(params=sorted(_DRIVERS))
def driver(request):
    return _DRIVERS[request.param]


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
_PATHS = dict(gencode_paths())


@pytest.fixture(params=sorted(_PATHS))
def ident(request):
    return request.param


NAMED_DEPENDENCIES = ('pydantic_ai',)


@pytest.mark.parametrize("dep", NAMED_DEPENDENCIES)
def test_uses_named_dependency(ident, dep):
    assert dependency_used(_PATHS[ident], dep), (
        f"{ident} does not import and use '{dep}' — the description names it, "
        f"so a hand-rolled substitute does not use the dependency"
    )


# ---------------------------------------------------------------------------
# Diagnostic (deliberately un-parameterised, so step3 does NOT fold it into any
# model's pass@1): confirms deepseek's nine behaviour FAILs share a single root
# cause. Its storage layer persists a row; only the generation's own
# `Task.model_validate(asyncpg.Record)` return path raises — i.e. the failures
# are one blocking marshalling bug cascading, not nine independent defects.
# ---------------------------------------------------------------------------
def test_deepseek_failures_share_one_blocking_bug():
    d = _DRIVERS.get("nl/deepseek")
    if d is None:
        pytest.skip("deepseek generation not present")
    persisted, marshal_raised = d.persists_despite_marshal_bug()
    assert marshal_raised, "expected deepseek's Task.model_validate(row) to raise"
    assert persisted == 1, "expected the INSERT to persist despite the return bug"
