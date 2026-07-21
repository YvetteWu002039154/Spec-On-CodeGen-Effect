import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from adapter import Implementation, Unsupported            # noqa: E402
from loader import gencode_paths, load_gencodemodule  # noqa: E402

_PARAMS = [ident for ident, _ in gencode_paths()]
_PATHS = dict(gencode_paths())
_cache = {}

# The full method set each class box draws in the diagram (grounded in origin).
_ACTION_HANDLER_METHODS = ("execute", "validate_params", "render_template")
_ACTION_OVERRIDES = ("execute", "validate_params")
_CONNECTION_MANAGER_METHODS = (
    "connect", "disconnect", "set_client_filters", "set_client_mode",
    "send_personal_message", "queue_broadcast", "queue_worker_broadcast",
    "queue_progress_broadcast", "queue_task_action_broadcast",
    "start_background_broadcaster", "stop_background_broadcaster",
)
_MONITOR_METHODS = (
    "get_workers_info", "set_task_callback", "set_worker_callback",
    "set_progress_callback", "set_steps_callback", "start_monitoring", "stop",
)
_EVENT_HANDLER_METHODS = (
    "handle_task_event", "handle_worker_event",
    "handle_progress_event", "handle_steps_event",
)
_DATABASE_MANAGER_METHODS = ("get_session", "run_migrations")


def _impl(ident):
    if ident not in _cache:
        try:
            _cache[ident] = Implementation(
                ident, [load_gencodemodule(ident, _PATHS[ident])])
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
# Inheritance links (--|>)
# ---------------------------------------------------------------------------
def test_retry_handler_specializes_action_handler(impl):
    # U1: RetryActionHandler --|> ActionHandler.
    assert _guard(lambda: impl.subclass_link("RetryActionHandler", "ActionHandler")) is True


def test_slack_handler_specializes_action_handler(impl):
    # U2: SlackActionHandler --|> ActionHandler.
    assert _guard(lambda: impl.subclass_link("SlackActionHandler", "ActionHandler")) is True


# ---------------------------------------------------------------------------
# Methods under a class (the operations pyreverse lists in each class box)
# ---------------------------------------------------------------------------
def test_action_handler_method_set(impl):
    # U3: ActionHandler carries execute + validate_params + render_template.
    assert _guard(lambda: impl.has_method_set("ActionHandler", _ACTION_HANDLER_METHODS)) is True


def test_retry_handler_overrides(impl):
    # U4: RetryActionHandler *overrides* execute + validate_params — directly
    # defined, concrete, non-stub (an inherited/abstract one does not count).
    assert _guard(lambda: impl.overrides_method_set("RetryActionHandler", _ACTION_OVERRIDES)) is True


def test_slack_handler_overrides(impl):
    # U5: SlackActionHandler *overrides* execute + validate_params — directly
    # defined, concrete, non-stub (an inherited/abstract one does not count).
    assert _guard(lambda: impl.overrides_method_set("SlackActionHandler", _ACTION_OVERRIDES)) is True


def test_connection_manager_method_set(impl):
    # U6: ConnectionManager carries its connect/disconnect + queue/broadcast set.
    assert _guard(lambda: impl.has_method_set("ConnectionManager", _CONNECTION_MANAGER_METHODS)) is True


def test_celery_monitor_method_set(impl):
    # U7: CeleryEventMonitor carries get_workers_info + the 4 callback setters + start/stop.
    assert _guard(lambda: impl.has_method_set("CeleryEventMonitor", _MONITOR_METHODS)) is True


def test_event_handler_method_set(impl):
    # U8: EventHandler carries the four handle_*_event operations.
    assert _guard(lambda: impl.has_method_set("EventHandler", _EVENT_HANDLER_METHODS)) is True


def test_database_manager_method_set(impl):
    # U9: DatabaseManager carries get_session + run_migrations.
    assert _guard(lambda: impl.has_method_set("DatabaseManager", _DATABASE_MANAGER_METHODS)) is True


def test_environment_db_to_dict(impl):
    # U10: EnvironmentDB exposes to_dict() (representative of the DB models'
    # serialization operation the diagram draws on many *DB classes).
    assert _guard(lambda: impl.has_method_set("EnvironmentDB", ("to_dict",))) is True
