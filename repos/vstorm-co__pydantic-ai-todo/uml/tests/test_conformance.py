import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from structure import Implementation, Unsupported            # noqa: E402
from loader import gencode_paths, load_gencodemodules  # noqa: E402

_PARAMS = [ident for ident, _ in gencode_paths()]
_PATHS = dict(gencode_paths())
_cache = {}

# The six fields the diagram draws on Todo / TodoItem.
_TODO_FIELDS = frozenset({"id", "content", "status", "active_form",
                          "parent_id", "depends_on"})
# The two fields on TodoStatusUpdate.
_UPDATE_FIELDS = frozenset({"todo_id", "status"})
# The async storage CRUD method set (drawn on every Async*Storage class).
_CRUD = frozenset({"add_todo", "get_todo", "get_todos", "remove_todo",
                   "set_todos", "update_todo"})
# The persistent backends add lifecycle methods.
_LIFECYCLE = frozenset({"initialize", "close"})
# The full TodoEventEmitter method set.
_EMITTER = frozenset({"emit", "off", "on", "on_created", "on_completed",
                      "on_updated", "on_deleted", "on_status_changed"})
# The TodoCapability method set.
_CAPABILITY = frozenset({"get_instructions", "get_serialization_name",
                         "get_toolset"})


def _impl(ident):
    if ident not in _cache:
        try:
            _cache[ident] = Implementation(
                ident, load_gencodemodules(ident, _PATHS[ident]))
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
# Composition links (--* : attr)
# ---------------------------------------------------------------------------
def test_todo_event_event_type_refs_enum(impl):
    # U1: TodoEventType --* TodoEvent (attribute `event_type`).
    assert "TodoEventType" in _guard(lambda: impl.attr_refs("TodoEvent", "event_type"))


def test_todo_event_todo_refs_todo(impl):
    # U2: Todo --* TodoEvent (attribute `todo`).
    assert "Todo" in _guard(lambda: impl.attr_refs("TodoEvent", "todo"))


# ---------------------------------------------------------------------------
# Attributes under a class
# ---------------------------------------------------------------------------
def test_todo_has_fields(impl):
    # U3: Todo carries {id, content, status, active_form, parent_id, depends_on}.
    assert _TODO_FIELDS <= _guard(lambda: impl.fields("Todo"))


def test_todo_item_has_fields(impl):
    # U4: TodoItem carries the same six fields.
    assert _TODO_FIELDS <= _guard(lambda: impl.fields("TodoItem"))


def test_status_update_has_fields(impl):
    # U5: TodoStatusUpdate carries {todo_id, status}.
    assert _UPDATE_FIELDS <= _guard(lambda: impl.fields("TodoStatusUpdate"))


# ---------------------------------------------------------------------------
# Methods under a class
# ---------------------------------------------------------------------------
def test_memory_storage_crud(impl):
    # U6: AsyncMemoryStorage defines the full async CRUD method set.
    assert _CRUD <= _guard(lambda: impl.methods("AsyncMemoryStorage"))


def test_postgres_storage_crud_lifecycle(impl):
    # U7: AsyncPostgresStorage defines CRUD plus initialize/close.
    assert (_CRUD | _LIFECYCLE) <= _guard(lambda: impl.methods("AsyncPostgresStorage"))


def test_redis_storage_crud_lifecycle(impl):
    # U8: AsyncRedisStorage defines CRUD plus initialize/close.
    assert (_CRUD | _LIFECYCLE) <= _guard(lambda: impl.methods("AsyncRedisStorage"))


def test_event_emitter_method_set(impl):
    # U9: TodoEventEmitter defines the full listener/emit method set.
    assert _EMITTER <= _guard(lambda: impl.methods("TodoEventEmitter"))


def test_capability_method_set(impl):
    # U10: TodoCapability defines get_instructions/get_serialization_name/get_toolset.
    assert _CAPABILITY <= _guard(lambda: impl.methods("TodoCapability"))
