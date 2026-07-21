"""Structure-conformance suite for `marginalia` **UML track**.

One shared test body runs against the 4 UML generations, via the adapter.
Expected structure comes only from CONTRACT.md, derived from the
class diagram ``uml/input/classes.puml`` (a pyreverse extraction of the origin
``src/marginalia/db/models/`` layer). The diagram records classes, the members
under each class, the two ``TypeDecorator`` hooks under ``UtcDateTime``, and the
``Mapped[T]`` inner types — and each test pins one such fact (Un) by reflection,
never by running behavior. A class/member a generation omits is a FAILURE, as
is a present-but-wrong type or missing method; this track does not skip / mark
N/A.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from adapter import Implementation, Unsupported            # noqa: E402
from loader import gencode_paths, load_gencodemodule  # noqa: E402

_PARAMS = [ident for ident, _ in gencode_paths()]
_PATHS = dict(gencode_paths())
_cache = {}

# Entities that inherit the declarative Base in the origin (all of them do).
_BASE_ENTITIES = ("Task", "File", "Folder", "Catalog", "Conversation", "Session")
# Entities that inherit IdMixin in the origin (EntryTag does NOT — composite PK).
_ID_ENTITIES = ("Task", "File", "Folder", "Catalog", "Conversation", "Session")

# UtcDateTime's TypeDecorator hook pair (the only methods the diagram draws).
_UTC_METHODS = frozenset({"process_bind_param", "process_result_value"})
# Task's async-queue field set.
_TASK_FIELDS = frozenset({
    "kind", "payload", "status", "priority", "attempts", "max_attempts",
    "dedup_key", "scheduled_at", "lease_expires_at", "locked_by", "last_error",
    "last_heartbeat_at", "started_at", "finished_at", "created_at",
})
# File's content-addressing field set.
_FILE_FIELDS = frozenset({
    "sha256", "size_bytes", "storage_key", "mime_type", "original_ext", "kind",
    "ingest_status", "ingested_at", "summary", "description", "extra",
    "deleted_at",
})
# Conversation's rolling-counter field set.
_CONV_FIELDS = frozenset({
    "session_id", "turn_index", "user_message", "agent_response", "tool_calls",
    "llm_calls", "total_input_tokens", "total_output_tokens", "total_cache_read",
    "total_tool_calls", "total_llm_calls", "total_duration_ms",
    "total_cost_estimate", "started_at", "ended_at",
})


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
# Inheritance convergence (mixins drawn as standalone superclasses)
# ---------------------------------------------------------------------------
def test_entities_share_declarative_base(impl):
    # U1: the ORM entities converge on a common declarative Base class.
    assert "Base" in _guard(lambda: impl.common_ancestor_names(_BASE_ENTITIES))


def test_entities_share_id_mixin(impl):
    # U2: the id-bearing entities converge on the IdMixin (identity mixin).
    assert "IdMixin" in _guard(lambda: impl.common_ancestor_names(_ID_ENTITIES))


# ---------------------------------------------------------------------------
# Methods under a class (only UtcDateTime carries any)
# ---------------------------------------------------------------------------
def test_utcdatetime_hook_pair(impl):
    # U3: UtcDateTime defines the TypeDecorator hooks process_bind_param /
    # process_result_value.
    assert _UTC_METHODS <= _guard(lambda: impl.methods("UtcDateTime"))


# ---------------------------------------------------------------------------
# Members under a class
# ---------------------------------------------------------------------------
def test_base_infrastructure_members(impl):
    # U4: Base carries `metadata` and `type_annotation_map`.
    assert {"metadata", "type_annotation_map"} <= _guard(lambda: impl.members("Base"))


def test_timestamp_mixin_members(impl):
    # U5: TimestampMixin carries `created_at` and `updated_at`.
    assert {"created_at", "updated_at"} <= _guard(lambda: impl.members("TimestampMixin"))


def test_task_queue_field_set(impl):
    # U6: Task carries its full async-queue field set.
    assert _TASK_FIELDS <= _guard(lambda: impl.members("Task"))


def test_file_content_field_set(impl):
    # U7: File carries its content-addressing field set.
    assert _FILE_FIELDS <= _guard(lambda: impl.members("File"))


def test_conversation_counter_field_set(impl):
    # U8: Conversation carries its rolling-counter field set.
    assert _CONV_FIELDS <= _guard(lambda: impl.members("Conversation"))


# ---------------------------------------------------------------------------
# Member types (Mapped[T] inner type — association-like)
# ---------------------------------------------------------------------------
def test_conversation_cost_is_decimal(impl):
    # U9: Conversation.total_cost_estimate is typed Mapped[Decimal].
    assert "Decimal" in _guard(lambda: impl.attr_refs("Conversation", "total_cost_estimate"))


def test_catalog_is_system_is_bool(impl):
    # U10: Catalog.is_system is typed Mapped[bool].
    assert "bool" in _guard(lambda: impl.attr_refs("Catalog", "is_system"))
