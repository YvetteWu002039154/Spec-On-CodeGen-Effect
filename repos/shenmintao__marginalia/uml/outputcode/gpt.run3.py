from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional, TypeVar, Generic, Union


T = TypeVar("T")


class Mapped(Generic[T]):
    def __init__(self, value: Optional[T] = None):
        self.value = value

    def __repr__(self) -> str:
        return f"Mapped({self.value!r})"


class MetaData:
    def __init__(self) -> None:
        self.tables: Dict[str, Any] = {}

    def __repr__(self) -> str:
        return f"MetaData(tables={list(self.tables.keys())!r})"


class DateTime:
    pass


class Base:
    metadata: MetaData = MetaData()
    type_annotation_map: Dict[Any, Any] = {}


class IdMixin:
    id: Mapped[str]

    def __init__(self, id: str):
        if not isinstance(id, str) or not id:
            raise ValueError("id must be a non-empty string")
        self.id = Mapped(id)


class TimestampMixin:
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]

    def __init__(self, created_at: Optional[datetime] = None, updated_at: Optional[datetime] = None):
        now = datetime.now(timezone.utc)
        self.created_at = Mapped(created_at or now)
        self.updated_at = Mapped(updated_at or self.created_at.value)

    def touch(self, at: Optional[datetime] = None) -> None:
        self.updated_at.value = at or datetime.now(timezone.utc)


class UtcDateTime:
    cache_ok: bool = True
    impl: DateTime = DateTime()

    def process_bind_param(self, value: Optional[datetime], dialect: Any) -> Optional[datetime]:
        if value is None:
            return None
        if not isinstance(value, datetime):
            raise TypeError("value must be a datetime or None")
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def process_result_value(self, value: Optional[datetime], dialect: Any) -> Optional[datetime]:
        if value is None:
            return None
        if not isinstance(value, datetime):
            raise TypeError("value must be a datetime or None")
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class AuditEvent(Base, IdMixin, TimestampMixin):
    conversation_id: Mapped[Optional[str]]
    kind: Mapped[str]
    occurred_at: Mapped[datetime]
    payload: Mapped[Any]
    session_id: Mapped[Optional[str]]
    task_id: Mapped[Optional[str]]

    def __init__(
        self,
        id: str,
        kind: str,
        occurred_at: datetime,
        payload: Any,
        conversation_id: Optional[str] = None,
        session_id: Optional[str] = None,
        task_id: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        IdMixin.__init__(self, id=id)
        TimestampMixin.__init__(self, created_at=created_at, updated_at=updated_at)
        if not isinstance(kind, str) or not kind:
            raise ValueError("kind must be a non-empty string")
        if not isinstance(occurred_at, datetime):
            raise TypeError("occurred_at must be a datetime")
        self.conversation_id = Mapped(conversation_id)
        self.kind = Mapped(kind)
        self.occurred_at = Mapped(occurred_at)
        self.payload = Mapped(payload)
        self.session_id = Mapped(session_id)
        self.task_id = Mapped(task_id)


class Conversation(Base, IdMixin, TimestampMixin):
    agent_response: Mapped[Optional[str]]
    ended_at: Mapped[Optional[datetime]]
    llm_calls: Mapped[Any]
    session_id: Mapped[str]
    started_at: Mapped[datetime]
    tool_calls: Mapped[Any]
    total_cache_read: Mapped[int]
    total_cost_estimate: Mapped[Decimal]
    total_duration_ms: Mapped[int]
    total_input_tokens: Mapped[int]
    total_llm_calls: Mapped[int]
    total_output_tokens: Mapped[int]
    total_tool_calls: Mapped[int]
    turn_index: Mapped[int]
    user_message: Mapped[str]

    def __init__(
        self,
        id: str,
        session_id: str,
        started_at: datetime,
        user_message: str,
        turn_index: int,
        agent_response: Optional[str] = None,
        ended_at: Optional[datetime] = None,
        llm_calls: Any = None,
        tool_calls: Any = None,
        total_cache_read: int = 0,
        total_cost_estimate: Union[Decimal, str, int, float] = Decimal("0"),
        total_duration_ms: int = 0,
        total_input_tokens: int = 0,
        total_llm_calls: int = 0,
        total_output_tokens: int = 0,
        total_tool_calls: int = 0,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        IdMixin.__init__(self, id=id)
        TimestampMixin.__init__(self, created_at=created_at, updated_at=updated_at)
        if not isinstance(session_id, str) or not session_id:
            raise ValueError("session_id must be a non-empty string")
        if not isinstance(started_at, datetime):
            raise TypeError("started_at must be a datetime")
        if not isinstance(user_message, str):
            raise TypeError("user_message must be a string")
        if not isinstance(turn_index, int) or turn_index < 0:
            raise ValueError("turn_index must be a non-negative int")
        self.session_id = Mapped(session_id)
        self.started_at = Mapped(started_at)
        self.user_message = Mapped(user_message)
        self.turn_index = Mapped(turn_index)
        self.agent_response = Mapped(agent_response)
        self.ended_at = Mapped(ended_at)
        self.llm_calls = Mapped(llm_calls if llm_calls is not None else [])
        self.tool_calls = Mapped(tool_calls if tool_calls is not None else [])
        self.total_cache_read = Mapped(int(total_cache_read))
        self.total_cost_estimate = Mapped(Decimal(str(total_cost_estimate)))
        self.total_duration_ms = Mapped(int(total_duration_ms))
        self.total_input_tokens = Mapped(int(total_input_tokens))
        self.total_llm_calls = Mapped(int(total_llm_calls))
        self.total_output_tokens = Mapped(int(total_output_tokens))
        self.total_tool_calls = Mapped(int(total_tool_calls))


class Session(Base, IdMixin, TimestampMixin):
    deleted_at: Mapped[Optional[datetime]]
    end_reason: Mapped[Optional[str]]
    ended_at: Mapped[Optional[datetime]]
    initiating_user_message: Mapped[str]
    started_at: Mapped[datetime]
    total_cache_read: Mapped[int]
    total_cost_estimate: Mapped[Decimal]
    total_duration_ms: Mapped[int]
    total_input_tokens: Mapped[int]
    total_llm_calls: Mapped[int]
    total_output_tokens: Mapped[int]
    total_tool_calls: Mapped[int]
    turn_count: Mapped[int]

    def __init__(
        self,
        id: str,
        initiating_user_message: str,
        started_at: datetime,
        deleted_at: Optional[datetime] = None,
        end_reason: Optional[str] = None,
        ended_at: Optional[datetime] = None,
        total_cache_read: int = 0,
        total_cost_estimate: Union[Decimal, str, int, float] = Decimal("0"),
        total_duration_ms: int = 0,
        total_input_tokens: int = 0,
        total_llm_calls: int = 0,
        total_output_tokens: int = 0,
        total_tool_calls: int = 0,
        turn_count: int = 0,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        IdMixin.__init__(self, id=id)
        TimestampMixin.__init__(self, created_at=created_at, updated_at=updated_at)
        if not isinstance(initiating_user_message, str):
            raise TypeError("initiating_user_message must be a string")
        if not isinstance(started_at, datetime):
            raise TypeError("started_at must be a datetime")
        if not isinstance(turn_count, int) or turn_count < 0:
            raise ValueError("turn_count must be a non-negative int")
        self.deleted_at = Mapped(deleted_at)
        self.end_reason = Mapped(end_reason)
        self.ended_at = Mapped(ended_at)
        self.initiating_user_message = Mapped(initiating_user_message)
        self.started_at = Mapped(started_at)
        self.total_cache_read = Mapped(int(total_cache_read))
        self.total_cost_estimate = Mapped(Decimal(str(total_cost_estimate)))
        self.total_duration_ms = Mapped(int(total_duration_ms))
        self.total_input_tokens = Mapped(int(total_input_tokens))
        self.total_llm_calls = Mapped(int(total_llm_calls))
        self.total_output_tokens = Mapped(int(total_output_tokens))
        self.total_tool_calls = Mapped(int(total_tool_calls))
        self.turn_count = Mapped(int(turn_count))


class Task(Base, IdMixin, TimestampMixin):
    attempts: Mapped[int]
    created_at: Mapped[datetime]
    dedup_key: Mapped[Optional[str]]
    finished_at: Mapped[Optional[datetime]]
    kind: Mapped[str]
    last_error: Mapped[Optional[str]]
    last_heartbeat_at: Mapped[Optional[datetime]]
    lease_expires_at: Mapped[Optional[datetime]]
    locked_by: Mapped[Optional[str]]
    max_attempts: Mapped[int]
    payload: Mapped[Any]
    priority: Mapped[int]
    scheduled_at: Mapped[datetime]
    started_at: Mapped[Optional[datetime]]
    status: Mapped[str]

    def __init__(
        self,
        id: str,
        kind: str,
        payload: Any,
        status: str,
        scheduled_at: datetime,
        priority: int = 0,
        attempts: int = 0,
        max_attempts: int = 1,
        dedup_key: Optional[str] = None,
        started_at: Optional[datetime] = None,
        finished_at: Optional[datetime] = None,
        last_error: Optional[str] = None,
        last_heartbeat_at: Optional[datetime] = None,
        lease_expires_at: Optional[datetime] = None,
        locked_by: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        IdMixin.__init__(self, id=id)
        TimestampMixin.__init__(self, created_at=created_at, updated_at=updated_at)
        if not isinstance(kind, str) or not kind:
            raise ValueError("kind must be a non-empty string")
        if not isinstance(status, str) or not status:
            raise ValueError("status must be a non-empty string")
        if not isinstance(scheduled_at, datetime):
            raise TypeError("scheduled_at must be a datetime")
        if not isinstance(priority, int):
            raise TypeError("priority must be an int")
        if not isinstance(attempts, int) or attempts < 0:
            raise ValueError("attempts must be a non-negative int")
        if not isinstance(max_attempts, int) or max_attempts < 1:
            raise ValueError("max_attempts must be an int >= 1")
        self.attempts = Mapped(int(attempts))
        self.dedup_key = Mapped(dedup_key)
        self.finished_at = Mapped(finished_at)
        self.kind = Mapped(kind)
        self.last_error = Mapped(last_error)
        self.last_heartbeat_at = Mapped(last_heartbeat_at)
        self.lease_expires_at = Mapped(lease_expires_at)
        self.locked_by = Mapped(locked_by)
        self.max_attempts = Mapped(int(max_attempts))
        self.payload = Mapped(payload)
        self.priority = Mapped(int(priority))
        self.scheduled_at = Mapped(scheduled_at)
        self.started_at = Mapped(started_at)
        self.status = Mapped(status)


class TaskOutcome(Base, IdMixin, TimestampMixin):
    completed_at: Mapped[datetime]
    detail: Mapped[Optional[Any]]
    object_id: Mapped[str]
    object_kind: Mapped[str]
    outcome: Mapped[str]
    task_kind: Mapped[str]
    task_run_id: Mapped[Optional[str]]

    def __init__(
        self,
        id: str,
        completed_at: datetime,
        object_id: str,
        object_kind: str,
        outcome: str,
        task_kind: str,
        detail: Optional[Any] = None,
        task_run_id: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        IdMixin.__init__(self, id=id)
        TimestampMixin.__init__(self, created_at=created_at, updated_at=updated_at)
        if not isinstance(completed_at, datetime):
            raise TypeError("completed_at must be a datetime")
        for name, val in (("object_id", object_id), ("object_kind", object_kind), ("outcome", outcome), ("task_kind", task_kind)):
            if not isinstance(val, str) or not val:
                raise ValueError(f"{name} must be a non-empty string")
        self.completed_at = Mapped(completed_at)
        self.detail = Mapped(detail)
        self.object_id = Mapped(object_id)
        self.object_kind = Mapped(object_kind)
        self.outcome = Mapped(outcome)
        self.task_kind = Mapped(task_kind)
        self.task_run_id = Mapped(task_run_id)


class Catalog(Base, IdMixin, TimestampMixin):
    deleted_at: Mapped[Optional[datetime]]
    description: Mapped[Optional[Any]]
    extra: Mapped[Optional[str]]
    is_system: Mapped[bool]
    name: Mapped[str]
    parent_id: Mapped[Optional[str]]
    summary: Mapped[Optional[str]]
    tags: Mapped[Optional[Any]]

    def __init__(
        self,
        id: str,
        name: str,
        is_system: bool,
        parent_id: Optional[str] = None,
        deleted_at: Optional[datetime] = None,
        description: Optional[Any] = None,
        extra: Optional[str] = None,
        summary: Optional[str] = None,
        tags: Optional[Any] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        IdMixin.__init__(self, id=id)
        TimestampMixin.__init__(self, created_at=created_at, updated_at=updated_at)
        if not isinstance(name, str) or not name:
            raise ValueError("name must be a non-empty string")
        if not isinstance(is_system, bool):
            raise TypeError("is_system must be a bool")
        self.deleted_at = Mapped(deleted_at)
        self.description = Mapped(description)
        self.extra = Mapped(extra)
        self.is_system = Mapped(is_system)
        self.name = Mapped(name)
        self.parent_id = Mapped(parent_id)
        self.summary = Mapped(summary)
        self.tags = Mapped(tags)


class Tag(Base, IdMixin, TimestampMixin):
    alias_of: Mapped[Optional[str]]
    doc_count: Mapped[int]
    facet: Mapped[str]
    last_reaffirmed_at: Mapped[Optional[datetime]]
    last_used_at: Mapped[Optional[datetime]]
    name: Mapped[str]
    reaffirm_count: Mapped[int]

    def __init__(
        self,
        id: str,
        name: str,
        facet: str,
        doc_count: int = 0,
        reaffirm_count: int = 0,
        alias_of: Optional[str] = None,
        last_reaffirmed_at: Optional[datetime] = None,
        last_used_at: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        IdMixin.__init__(self, id=id)
        TimestampMixin.__init__(self, created_at=created_at, updated_at=updated_at)
        if not isinstance(name, str) or not name:
            raise ValueError("name must be a non-empty string")
        if not isinstance(facet, str) or not facet:
            raise ValueError("facet must be a non-empty string")
        if not isinstance(doc_count, int) or doc_count < 0:
            raise ValueError("doc_count must be a non-negative int")
        if not isinstance(reaffirm_count, int) or reaffirm_count < 0:
            raise ValueError("reaffirm_count must be a non-negative int")
        self.alias_of = Mapped(alias_of)
        self.doc_count = Mapped(int(doc_count))
        self.facet = Mapped(facet)
        self.last_reaffirmed_at = Mapped(last_reaffirmed_at)
        self.last_used_at = Mapped(last_used_at)
        self.name = Mapped(name)
        self.reaffirm_count = Mapped(int(reaffirm_count))


class TagAlias(Base, IdMixin, TimestampMixin):
    created_at: Mapped[datetime]
    from_name: Mapped[str]
    note: Mapped[Optional[str]]
    to_tag_id: Mapped[str]

    def __init__(
        self,
        id: str,
        from_name: str,
        to_tag_id: str,
        created_at: Optional[datetime] = None,
        note: Optional[str] = None,
        updated_at: Optional[datetime] = None,
    ):
        IdMixin.__init__(self, id=id)
        TimestampMixin.__init__(self, created_at=created_at, updated_at=updated_at)
        if not isinstance(from_name, str) or not from_name:
            raise ValueError("from_name must be a non-empty string")
        if not isinstance(to_tag_id, str) or not to_tag_id:
            raise ValueError("to_tag_id must be a non-empty string")
        self.from_name = Mapped(from_name)
        self.note = Mapped(note)
        self.to_tag_id = Mapped(to_tag_id)


class View(Base, IdMixin, TimestampMixin):
    deleted_at: Mapped[Optional[datetime]]
    description: Mapped[Optional[Any]]
    extra: Mapped[Optional[str]]
    filter_spec: Mapped[Any]
    name: Mapped[str]
    summary: Mapped[Optional[str]]
    tags: Mapped[Optional[Any]]

    def __init__(
        self,
        id: str,
        name: str,
        filter_spec: Any,
        deleted_at: Optional[datetime] = None,
        description: Optional[Any] = None,
        extra: Optional[str] = None,
        summary: Optional[str] = None,
        tags: Optional[Any] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        IdMixin.__init__(self, id=id)
        TimestampMixin.__init__(self, created_at=created_at, updated_at=updated_at)
        if not isinstance(name, str) or not name:
            raise ValueError("name must be a non-empty string")
        self.deleted_at = Mapped(deleted_at)
        self.description = Mapped(description)
        self.extra = Mapped(extra)
        self.filter_spec = Mapped(filter_spec)
        self.name = Mapped(name)
        self.summary = Mapped(summary)
        self.tags = Mapped(tags)


class EntryTag(Base, IdMixin, TimestampMixin):
    created_at: Mapped[datetime]
    entry_id: Mapped[str]
    last_reaffirmed_at: Mapped[Optional[datetime]]
    reaffirm_count: Mapped[int]
    source: Mapped[str]
    tag_id: Mapped[str]

    def __init__(
        self,
        id: str,
        entry_id: str,
        tag_id: str,
        source: str,
        created_at: Optional[datetime] = None,
        last_reaffirmed_at: Optional[datetime] = None,
        reaffirm_count: int = 0,
        updated_at: Optional[datetime] = None,
    ):
        IdMixin.__init__(self, id=id)
        TimestampMixin.__init__(self, created_at=created_at, updated_at=updated_at)
        for name, val in (("entry_id", entry_id), ("tag_id", tag_id), ("source", source)):
            if not isinstance(val, str) or not val:
                raise ValueError(f"{name} must be a non-empty string")
        if not isinstance(reaffirm_count, int) or reaffirm_count < 0:
            raise ValueError("reaffirm_count must be a non-negative int")
        self.entry_id = Mapped(entry_id)
        self.tag_id = Mapped(tag_id)
        self.source = Mapped(source)
        self.last_reaffirmed_at = Mapped(last_reaffirmed_at)
        self.reaffirm_count = Mapped(int(reaffirm_count))


class EntryRelation(Base, IdMixin, TimestampMixin):
    created_at: Mapped[datetime]
    entry_a_id: Mapped[str]
    entry_b_id: Mapped[str]
    last_observed_at: Mapped[datetime]
    note: Mapped[str]
    observation_count: Mapped[int]
    source_kind: Mapped[str]
    vetted: Mapped[Optional[bool]]
    vetted_at: Mapped[Optional[datetime]]
    vetted_observation_count: Mapped[Optional[int]]
    vetted_reason: Mapped[Optional[str]]

    def __init__(
        self,
        id: str,
        entry_a_id: str,
        entry_b_id: str,
        last_observed_at: datetime,
        note: str,
        observation_count: int,
        source_kind: str,
        vetted: Optional[bool] = None,
        vetted_at: Optional[datetime] = None,
        vetted_observation_count: Optional[int] = None,
        vetted_reason: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        IdMixin.__init__(self, id=id)
        TimestampMixin.__init__(self, created_at=created_at, updated_at=updated_at)
        for name, val in (("entry_a_id", entry_a_id), ("entry_b_id", entry_b_id), ("note", note), ("source_kind", source_kind)):
            if not isinstance(val, str) or not val:
                raise ValueError(f"{name} must be a non-empty string")
        if not isinstance(last_observed_at, datetime):
            raise TypeError("last_observed_at must be a datetime")
        if not isinstance(observation_count, int) or observation_count < 0:
            raise ValueError("observation_count must be a non-negative int")
        if vetted_observation_count is not None and (not isinstance(vetted_observation_count, int) or vetted_observation_count < 0):
            raise ValueError("vetted_observation_count must be a non-negative int or None")
        self.entry_a_id = Mapped(entry_a_id)
        self.entry_b_id = Mapped(entry_b_id)
        self.last_observed_at = Mapped(last_observed_at)
        self.note = Mapped(note)
        self.observation_count = Mapped(int(observation_count))
        self.source_kind = Mapped(source_kind)
        self.vetted = Mapped(vetted)
        self.vetted_at = Mapped(vetted_at)
        self.vetted_observation_count = Mapped(vetted_observation_count)
        self.vetted_reason = Mapped(vetted_reason)


class Journal(Base, IdMixin, TimestampMixin):
    conversation_id: Mapped[str]
    created_at: Mapped[datetime]
    entry_ids: Mapped[Any]
    invalidated_at: Mapped[Optional[datetime]]
    invalidated_by_id: Mapped[Optional[str]]
    invalidated_reason: Mapped[Optional[str]]
    note: Mapped[str]
    source_kind: Mapped[str]
    summarized_journal_ids: Mapped[Optional[Any]]
    superseded_by_id: Mapped[Optional[str]]
    tags: Mapped[Any]

    def __init__(
        self,
        id: str,
        conversation_id: str,
        note: str,
        source_kind: str,
        entry_ids: Any,
        tags: Any,
        created_at: Optional[datetime] = None,
        summarized_journal_ids: Optional[Any] = None,
        invalidated_at: Optional[datetime] = None,
        invalidated_by_id: Optional[str] = None,
        invalidated_reason: Optional[str] = None,
        superseded_by_id: Optional[str] = None,
        updated_at: Optional[datetime] = None,
    ):
        IdMixin.__init__(self, id=id)
        TimestampMixin.__init__(self, created_at=created_at, updated_at=updated_at)
        for name, val in (("conversation_id", conversation_id), ("note", note), ("source_kind", source_kind)):
            if not isinstance(val, str) or not val:
                raise ValueError(f"{name} must be a non-empty string")
        self.conversation_id = Mapped(conversation_id)
        self.note = Mapped(note)
        self.source_kind = Mapped(source_kind)
        self.entry_ids = Mapped(entry_ids)
        self.tags = Mapped(tags)
        self.summarized_journal_ids = Mapped(summarized_journal_ids)
        self.invalidated_at = Mapped(invalidated_at)
        self.invalidated_by_id = Mapped(invalidated_by_id)
        self.invalidated_reason = Mapped(invalidated_reason)
        self.superseded_by_id = Mapped(superseded_by_id)


class File(Base, IdMixin, TimestampMixin):
    deleted_at: Mapped[Optional[datetime]]
    description: Mapped[Optional[Any]]
    extra: Mapped[Optional[str]]
    ingest_status: Mapped[str]
    ingested_at: Mapped[Optional[datetime]]
    kind: Mapped[Optional[str]]
    mime_type: Mapped[Optional[str]]
    original_ext: Mapped[Optional[str]]
    sha256: Mapped[str]
    size_bytes: Mapped[int]
    storage_key: Mapped[str]
    summary: Mapped[Optional[str]]

    def __init__(
        self,
        id: str,
        sha256: str,
        size_bytes: int,
        storage_key: str,
        ingest_status: str,
        deleted_at: Optional[datetime] = None,
        ingested_at: Optional[datetime] = None,
        kind: Optional[str] = None,
        mime_type: Optional[str] = None,
        original_ext: Optional[str] = None,
        description: Optional[Any] = None,
        extra: Optional[str] = None,
        summary: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        IdMixin.__init__(self, id=id)
        TimestampMixin.__init__(self, created_at=created_at, updated_at=updated_at)
        for name, val in (("sha256", sha256), ("storage_key", storage_key), ("ingest_status", ingest_status)):
            if not isinstance(val, str) or not val:
                raise ValueError(f"{name} must be a non-empty string")
        if not isinstance(size_bytes, int) or size_bytes < 0:
            raise ValueError("size_bytes must be a non-negative int")
        self.deleted_at = Mapped(deleted_at)
        self.description = Mapped(description)
        self.extra = Mapped(extra)
        self.ingest_status = Mapped(ingest_status)
        self.ingested_at = Mapped(ingested_at)
        self.kind = Mapped(kind)
        self.mime_type = Mapped(mime_type)
        self.original_ext = Mapped(original_ext)
        self.sha256 = Mapped(sha256)
        self.size_bytes = Mapped(int(size_bytes))
        self.storage_key = Mapped(storage_key)
        self.summary = Mapped(summary)


class Folder(Base, IdMixin, TimestampMixin):
    deleted_at: Mapped[Optional[datetime]]
    name: Mapped[str]
    parent_id: Mapped[Optional[str]]

    def __init__(
        self,
        id: str,
        name: str,
        parent_id: Optional[str] = None,
        deleted_at: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        IdMixin.__init__(self, id=id)
        TimestampMixin.__init__(self, created_at=created_at, updated_at=updated_at)
        if not isinstance(name, str) or not name:
            raise ValueError("name must be a non-empty string")
        self.deleted_at = Mapped(deleted_at)
        self.name = Mapped(name)
        self.parent_id = Mapped(parent_id)


class FileEntry(Base, IdMixin, TimestampMixin):
    catalog_id: Mapped[Optional[str]]
    deleted_at: Mapped[Optional[datetime]]
    display_name: Mapped[str]
    extra: Mapped[Optional[str]]
    file_id: Mapped[str]
    folder_id: Mapped[Optional[str]]
    lifecycle: Mapped[str]
    purge_after: Mapped[Optional[datetime]]

    def __init__(
        self,
        id: str,
        file_id: str,
        display_name: str,
        lifecycle: str,
        catalog_id: Optional[str] = None,
        folder_id: Optional[str] = None,
        deleted_at: Optional[datetime] = None,
        purge_after: Optional[datetime] = None,
        extra: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        IdMixin.__init__(self, id=id)
        TimestampMixin.__init__(self, created_at=created_at, updated_at=updated_at)
        for name, val in (("file_id", file_id), ("display_name", display_name), ("lifecycle", lifecycle)):
            if not isinstance(val, str) or not val:
                raise ValueError(f"{name} must be a non-empty string")
        self.catalog_id = Mapped(catalog_id)
        self.deleted_at = Mapped(deleted_at)
        self.display_name = Mapped(display_name)
        self.extra = Mapped(extra)
        self.file_id = Mapped(file_id)
        self.folder_id = Mapped(folder_id)
        self.lifecycle = Mapped(lifecycle)
        self.purge_after = Mapped(purge_after)