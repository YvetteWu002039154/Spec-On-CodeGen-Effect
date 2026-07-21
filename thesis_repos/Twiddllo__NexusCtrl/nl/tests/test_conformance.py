"""NL conformance suite: 10 behaviors × 4 generations, no skip / no N/A.

A capability a generation does not expose is a behavioral FAILURE, not N/A.
Tests may not use pytest.skip or mark.xfail. Every test run produces only PASS
(behavior works) or FAIL (capability wrong or missing).
"""

import os
import sys

import psutil
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
