import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from adapter import (  # noqa: E402
    build_driver, SUCCESS_TOKENS, FAILURE_TOKENS, RETRY_TOKENS,
    _has_token, _has_heartbeat, _has_status, _has_retry_field,
)
from loader import dependency_used, gencode_paths, load_gencodemodule  # noqa: E402

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
# Task execution insights (state, retry, orphans)
# ---------------------------------------------------------------------------
def test_task_state_vocabulary(driver):
    toks = driver.task_state_tokens()
    assert _has_token(toks, SUCCESS_TOKENS)
    assert _has_token(toks, FAILURE_TOKENS)
    assert _has_token(toks, RETRY_TOKENS)


def test_task_retry_counter(driver):
    assert _has_retry_field(driver.retry_counter_fields())


def test_orphan_detection(driver):
    assert driver.orphan_capability() is True


# ---------------------------------------------------------------------------
# Daily statistics
# ---------------------------------------------------------------------------
def test_daily_stats_count_fields(driver):
    fields = driver.daily_stats_count_fields()
    assert _has_token(fields, SUCCESS_TOKENS)
    assert _has_token(fields, FAILURE_TOKENS)


def test_daily_stats_accumulation(driver):
    before, after = driver.stats_success_increment()
    assert after == before + 1


# ---------------------------------------------------------------------------
# Worker health monitoring
# ---------------------------------------------------------------------------
def test_worker_health_fields(driver):
    fields = driver.worker_health_fields()
    assert _has_status(fields)
    assert _has_heartbeat(fields)


# ---------------------------------------------------------------------------
# Real-time WebSocket connection registry
# ---------------------------------------------------------------------------
def test_connection_disconnect_idempotent(driver):
    assert driver.disconnect_removes_idempotent() is True


# ---------------------------------------------------------------------------
# Auto-migrations
# ---------------------------------------------------------------------------
def test_auto_migration_runner(driver):
    assert driver.migration_runner() is True


# ---------------------------------------------------------------------------
# Dependency usage — the description names celery, alembic; does the generation
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


def test_uses_named_dependency_celery(ident):
    _assert_dependency_used(ident, "celery")


def test_uses_named_dependency_alembic(ident):
    _assert_dependency_used(ident, "alembic")
