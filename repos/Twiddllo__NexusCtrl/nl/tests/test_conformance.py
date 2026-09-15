import os
import sys

import psutil
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
# Server Monitoring
# ---------------------------------------------------------------------------
# N1
def test_performance_history_retained(driver):
    assert driver.history_length_after(3) >= 3


# ---------------------------------------------------------------------------
# Agent Capabilities  (the remote target machine)
# ---------------------------------------------------------------------------
# N2
def test_metrics_collection(driver):
    m = driver.metrics()
    assert m["dims"] >= {"cpu", "ram", "network"}
    assert abs(m["ram_percent"] - psutil.virtual_memory().percent) <= 10


# N3
def test_view_active_processes(driver):
    assert os.getpid() in driver.process_pids()


# N4
def test_runs_as_background_service(driver):
    assert driver.has_background_service() is True


# N5
def test_responds_to_remote_kill(driver):
    assert driver.kill_missing_reports_failure() is True


# ---------------------------------------------------------------------------
# Task Management  (the controller / local machine)
# ---------------------------------------------------------------------------
# N6
def test_task_create(driver):
    assert driver.create_task_exists("critical") is True


# N7
def test_manage_multiple_tasks(driver):
    assert driver.tracked_task_count(3) == 3


# N8
def test_task_priority_vocabulary(driver):
    assert {"critical", "high", "medium", "low"} <= driver.priority_tokens()


# N9
def test_task_completion_tracked(driver):
    assert driver.completion_token() in {"completed", "done", "complete", "finished"}


# ---------------------------------------------------------------------------
# Server Control  (the controller / local machine)
# ---------------------------------------------------------------------------
# N10
def test_server_status_online_offline(driver):
    assert {"online", "offline"} <= driver.server_status_tokens()
