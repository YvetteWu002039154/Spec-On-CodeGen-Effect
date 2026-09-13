from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Generic, Optional, TypeVar, Union
from uuid import uuid4


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


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_utc(dt: datetime) -> datetime:
    if not isinstance(dt, datetime):
        raise TypeError("Expected datetime")
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class UtcDateTime:
    cache_ok: bool = True
    impl: DateTime = DateTime()

    def process_bind_param(self, value: Optional[datetime], dialect: Any) -> Optional[datetime]:
        if value is None:
            return None
        return _ensure_utc(value)

    def process_result_value(self, value: Optional[datetime], dialect: Any) -> Optional[datetime]:
        if value is None:
            return None
        return _ensure_utc(value)


class IdMixin:
    id: Mapped[str]

    def __init__(self, id: Optional[str] = None) -> None:
        self.id = Mapped(id or str(uuid4()))


class TimestampMixin:
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]

    def __init__(self, created_at: Optional[datetime] = None, updated_at: Optional[datetime] = None) -> None:
        ca = _ensure_utc(created_at) if created_at is not None else _utcnow()
        ua = _ensure_utc(updated_at) if updated_at is not None else ca
        self.created_at = Mapped(ca)
        self.updated_at = Mapped(ua)

    def touch(self, when: Optional[datetime] = None) -> None:
        self.updated_at.value = _ensure_utc(when) if when is not None else _utcnow()


class AuditEvent(Base, IdMixin):
    conversation_id: Mapped[Optional[str]]
    kind: Mapped[str]
    occurred_at: Mapped[datetime]
    payload: Mapped[Any]
    session_id: Mapped[Optional[str]]
    task_id: Mapped[Optional[str]]

    def __init__(
        self,
        kind: str,
        payload: Any,
        occurred_at: Optional[datetime] = None,
        conversation_id: Optional[str] = None,
        session_id: Optional[str] = None,
        task_id: Optional[str] = None,
        id: Optional[str] = None,
    ) -> None:
        IdMixin.__init__(self, id=id)
        if not isinstance(kind, str) or not kind:
            raise ValueError("kind must be a non-empty string")
        self.kind = Mapped(kind)
        self.payload = Mapped(payload)
        self.occurred_at = Mapped(_ensure_utc(occurred_at) if occurred_at is not None else _utcnow())
        self.conversation_id = Mapped(conversation_id)
        self.session_id = Mapped(session_id)
        self.task_id = Mapped(task_id)


class Conversation(Base, IdMixin):
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
        session_id: str,
        user_message: str,
        turn_index: int,
        started_at: Optional[datetime] = None,
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
        id: Optional[str] = None,
    ) -> None:
        IdMixin.__init__(self, id=id)
        if not isinstance(session_id, str) or not session_id:
            raise ValueError("session_id must be a non-empty string")
        if not isinstance(user_message, str):
            raise TypeError("user_message must be a string")
        if not isinstance(turn_index, int) or turn_index < 0:
            raise ValueError("turn_index must be a non-negative int")

        self.session_id = Mapped(session_id)
        self.user_message = Mapped(user_message)
        self.turn_index = Mapped(turn_index)

        self.started_at = Mapped(_ensure_utc(started_at) if started_at is not None else _utcnow())
        self.ended_at = Mapped(_ensure_utc(ended_at) if ended_at is not None else None)

        self.agent_response = Mapped(agent_response)
        self.llm_calls = Mapped(llm_calls if llm_calls is not None else [])
        self.tool_calls = Mapped(tool_calls if tool_calls is not None else [])

        self.total_cache_read = Mapped(int(total_cache_read))
        self.total_cost_estimate = Mapped(Decimal(str(total_cost_estimate)))
        self.total_duration_ms = Mapped(int(total_duration_ms))
        self.total_input_tokens = Mapped(int(total_input_tokens))
        self.total_llm_calls = Mapped(int(total_llm_calls))
        self.total_output_tokens = Mapped(int(total_output_tokens))
        self.total_tool_calls = Mapped(int(total_tool_calls))

    def end(self, ended_at: Optional[datetime] = None, agent_response: Optional[str] = None) -> None:
        self.ended_at.value = _ensure_utc(ended_at) if ended_at is not None else _utcnow()
        if agent_response is not None:
            self.agent_response.value = agent_response


class Session(Base, IdMixin):
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
        initiating_user_message: str,
        started_at: Optional[datetime] = None,
        ended_at: Optional[datetime] = None,
        end_reason: Optional[str] = None,
        deleted_at: Optional[datetime] = None,
        total_cache_read: int = 0,
        total_cost_estimate: Union[Decimal, str, int, float] = Decimal("0"),
        total_duration_ms: int = 0,
        total_input_tokens: int = 0,
        total_llm_calls: int = 0,
        total_output_tokens: int = 0,
        total_tool_calls: int = 0,
        turn_count: int = 0,
        id: Optional[str] = None,
    ) -> None:
        IdMixin.__init__(self, id=id)
        if not isinstance(initiating_user_message, str):
            raise TypeError("initiating_user_message must be a string")

        self.initiating_user_message = Mapped(initiating_user_message)
        self.started_at = Mapped(_ensure_utc(started_at) if started_at is not None else _utcnow())
        self.ended_at = Mapped(_ensure_utc(ended_at) if ended_at is not None else None)
        self.end_reason = Mapped(end_reason)
        self.deleted_at = Mapped(_ensure_utc(deleted_at) if deleted_at is not None else None)

        self.total_cache_read = Mapped(int(total_cache_read))
        self.total_cost_estimate = Mapped(Decimal(str(total_cost_estimate)))
        self.total_duration_ms = Mapped(int(total_duration_ms))
        self.total_input_tokens = Mapped(int(total_input_tokens))
        self.total_llm_calls = Mapped(int(total_llm_calls))
        self.total_output_tokens = Mapped(int(total_output_tokens))
        self.total_tool_calls = Mapped(int(total_tool_calls))
        self.turn_count = Mapped(int(turn_count))

    def end(self, end_reason: Optional[str] = None, ended_at: Optional[datetime] = None) -> None:
        self.ended_at.value = _ensure_utc(ended_at) if ended_at is not None else _utcnow()
        if end_reason is not None:
            self.end_reason.value = end_reason

    def soft_delete(self, when: Optional[datetime] = None) -> None:
        self.deleted_at.value = _ensure_utc(when) if when is not None else _utcnow()


class Task(Base, IdMixin):
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
        kind: str,
        payload: Any,
        status: str,
        scheduled_at: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
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
        id: Optional[str] = None,
    ) -> None:
        IdMixin.__init__(self, id=id)
        if not isinstance(kind, str) or not kind:
            raise ValueError("kind must be a non-empty string")
        if not isinstance(status, str) or not status:
            raise ValueError("status must be a non-empty string")
        if not isinstance(attempts, int) or attempts < 0:
            raise ValueError("attempts must be a non-negative int")
        if not isinstance(max_attempts, int) or max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if attempts > max_attempts:
            raise ValueError("attempts cannot exceed max_attempts")

        self.kind = Mapped(kind)
        self.payload = Mapped(payload)
        self.status = Mapped(status)

        self.created_at = Mapped(_ensure_utc(created_at) if created_at is not None else _utcnow())
        self.scheduled_at = Mapped(_ensure_utc(scheduled_at) if scheduled_at is not None else self.created_at.value)

        self.priority = Mapped(int(priority))
        self.attempts = Mapped(int(attempts))
        self.max_attempts = Mapped(int(max_attempts))
        self.dedup_key = Mapped(dedup_key)

        self.started_at = Mapped(_ensure_utc(started_at) if started_at is not None else None)
        self.finished_at = Mapped(_ensure_utc(finished_at) if finished_at is not None else None)
        self.last_error = Mapped(last_error)
        self.last_heartbeat_at = Mapped(_ensure_utc(last_heartbeat_at) if last_heartbeat_at is not None else None)
        self.lease_expires_at = Mapped(_ensure_utc(lease_expires_at) if lease_expires_at is not None else None)
        self.locked_by = Mapped(locked_by)


class TaskOutcome(Base, IdMixin):
    completed_at: Mapped[datetime]
    detail: Mapped[Optional[Any]]
    object_id: Mapped[str]
    object_kind: Mapped[str]
    outcome: Mapped[str]
    task_kind: Mapped[str]
    task_run_id: Mapped[Optional[str]]

    def __init__(
        self,
        object_id: str,
        object_kind: str,
        outcome: str,
        task_kind: str,
        completed_at: Optional[datetime] = None,
        detail: Optional[Any] = None,
        task_run_id: Optional[str] = None,
        id: Optional[str] = None,
    ) -> None:
        IdMixin.__init__(self, id=id)
        if not isinstance(object_id, str) or not object_id:
            raise ValueError("object_id must be a non-empty string")
        if not isinstance(object_kind, str) or not object_kind:
            raise ValueError("object_kind must be a non-empty string")
        if not isinstance(outcome, str) or not outcome:
            raise ValueError("outcome must be a non-empty string")
        if not isinstance(task_kind, str) or not task_kind:
            raise ValueError("task_kind must be a non-empty string")

        self.object_id = Mapped(object_id)
        self.object_kind = Mapped(object_kind)
        self.outcome = Mapped(outcome)
        self.task_kind = Mapped(task_kind)
        self.task_run_id = Mapped(task_run_id)
        self.detail = Mapped(detail)
        self.completed_at = Mapped(_ensure_utc(completed_at) if completed_at is not None else _utcnow())


class Catalog(Base, IdMixin):
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
        name: str,
        is_system: bool = False,
        parent_id: Optional[str] = None,
        deleted_at: Optional[datetime] = None,
        description: Optional[Any] = None,
        extra: Optional[str] = None,
        summary: Optional[str] = None,
        tags: Optional[Any] = None,
        id: Optional[str] = None,
    ) -> None:
        IdMixin.__init__(self, id=id)
        if not isinstance(name, str) or not name:
            raise ValueError("name must be a non-empty string")
        self.name = Mapped(name)
        self.is_system = Mapped(bool(is_system))
        self.parent_id = Mapped(parent_id)
        self.deleted_at = Mapped(_ensure_utc(deleted_at) if deleted_at is not None else None)
        self.description = Mapped(description)
        self.extra = Mapped(extra)
        self.summary = Mapped(summary)
        self.tags = Mapped(tags)

    def soft_delete(self, when: Optional[datetime] = None) -> None:
        self.deleted_at.value = _ensure_utc(when) if when is not None else _utcnow()


class View(Base, IdMixin):
    deleted_at: Mapped[Optional[datetime]]
    description: Mapped[Optional[Any]]
    extra: Mapped[Optional[str]]
    filter_spec: Mapped[Any]
    name: Mapped[str]
    summary: Mapped[Optional[str]]
    tags: Mapped[Optional[Any]]

    def __init__(
        self,
        name: str,
        filter_spec: Any,
        deleted_at: Optional[datetime] = None,
        description: Optional[Any] = None,
        extra: Optional[str] = None,
        summary: Optional[str] = None,
        tags: Optional[Any] = None,
        id: Optional[str] = None,
    ) -> None:
        IdMixin.__init__(self, id=id)
        if not isinstance(name, str) or not name:
            raise ValueError("name must be a non-empty string")
        self.name = Mapped(name)
        self.filter_spec = Mapped(filter_spec)
        self.deleted_at = Mapped(_ensure_utc(deleted_at) if deleted_at is not None else None)
        self.description = Mapped(description)
        self.extra = Mapped(extra)
        self.summary = Mapped(summary)
        self.tags = Mapped(tags)

    def soft_delete(self, when: Optional[datetime] = None) -> None:
        self.deleted_at.value = _ensure_utc(when) if when is not None else _utcnow()


class Tag(Base, IdMixin):
    alias_of: Mapped[Optional[str]]
    doc_count: Mapped[int]
    facet: Mapped[str]
    last_reaffirmed_at: Mapped[Optional[datetime]]
    last_used_at: Mapped[Optional[datetime]]
    name: Mapped[str]
    reaffirm_count: Mapped[int]

    def __init__(
        self,
        name: str,
        facet: str,
        alias_of: Optional[str] = None,
        doc_count: int = 0,
        reaffirm_count: int = 0,
        last_reaffirmed_at: Optional[datetime] = None,
        last_used_at: Optional[datetime] = None,
        id: Optional[str] = None,
    ) -> None:
        IdMixin.__init__(self, id=id)
        if not isinstance(name, str) or not name:
            raise ValueError("name must be a non-empty string")
        if not isinstance(facet, str) or not facet:
            raise ValueError("facet must be a non-empty string")
        if not isinstance(doc_count, int) or doc_count < 0:
            raise ValueError("doc_count must be a non-negative int")
        if not isinstance(reaffirm_count, int) or reaffirm_count < 0:
            raise ValueError("reaffirm_count must be a non-negative int")

        self.name = Mapped(name)
        self.facet = Mapped(facet)
        self.alias_of = Mapped(alias_of)
        self.doc_count = Mapped(int(doc_count))
        self.reaffirm_count = Mapped(int(reaffirm_count))
        self.last_reaffirmed_at = Mapped(_ensure_utc(last_reaffirmed_at) if last_reaffirmed_at is not None else None)
        self.last_used_at = Mapped(_ensure_utc(last_used_at) if last_used_at is not None else None)


class TagAlias(Base, IdMixin):
    created_at: Mapped[datetime]
    from_name: Mapped[str]
    note: Mapped[Optional[str]]
    to_tag_id: Mapped[str]

    def __init__(
        self,
        from_name: str,
        to_tag_id: str,
        created_at: Optional[datetime] = None,
        note: Optional[str] = None,
        id: Optional[str] = None,
    ) -> None:
        IdMixin.__init__(self, id=id)
        if not isinstance(from_name, str) or not from_name:
            raise ValueError("from_name must be a non-empty string")
        if not isinstance(to_tag_id, str) or not to_tag_id:
            raise ValueError("to_tag_id must be a non-empty string")
        self.from_name = Mapped(from_name)
        self.to_tag_id = Mapped(to_tag_id)
        self.note = Mapped(note)
        self.created_at = Mapped(_ensure_utc(created_at) if created_at is not None else _utcnow())


class EntryTag(Base, IdMixin):
    created_at: Mapped[datetime]
    entry_id: Mapped[str]
    last_reaffirmed_at: Mapped[Optional[datetime]]
    reaffirm_count: Mapped[int]
    source: Mapped[str]
    tag_id: Mapped[str]

    def __init__(
        self,
        entry_id: str,
        tag_id: str,
        source: str,
        created_at: Optional[datetime] = None,
        last_reaffirmed_at: Optional[datetime] = None,
        reaffirm_count: int = 0,
        id: Optional[str] = None,
    ) -> None:
        IdMixin.__init__(self, id=id)
        if not isinstance(entry_id, str) or not entry_id:
            raise ValueError("entry_id must be a non-empty string")
        if not isinstance(tag_id, str) or not tag_id:
            raise ValueError("tag_id must be a non-empty string")
        if not isinstance(source, str) or not source:
            raise ValueError("source must be a non-empty string")
        if not isinstance(reaffirm_count, int) or reaffirm_count < 0:
            raise ValueError("reaffirm_count must be a non-negative int")

        self.entry_id = Mapped(entry_id)
        self.tag_id = Mapped(tag_id)
        self.source = Mapped(source)
        self.created_at = Mapped(_ensure_utc(created_at) if created_at is not None else _utcnow())
        self.last_reaffirmed_at = Mapped(_ensure_utc(last_reaffirmed_at) if last_reaffirmed_at is not None else None)
        self.reaffirm_count = Mapped(int(reaffirm_count))


class EntryRelation(Base, IdMixin):
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
        entry_a_id: str,
        entry_b_id: str,
        note: str,
        source_kind: str,
        created_at: Optional[datetime] = None,
        last_observed_at: Optional[datetime] = None,
        observation_count: int = 0,
        vetted: Optional[bool] = None,
        vetted_at: Optional[datetime] = None,
        vetted_observation_count: Optional[int] = None,
        vetted_reason: Optional[str] = None,
        id: Optional[str] = None,
    ) -> None:
        IdMixin.__init__(self, id=id)
        if not isinstance(entry_a_id, str) or not entry_a_id:
            raise ValueError("entry_a_id must be a non-empty string")
        if not isinstance(entry_b_id, str) or not entry_b_id:
            raise ValueError("entry_b_id must be a non-empty string")
        if not isinstance(note, str):
            raise TypeError("note must be a string")
        if not isinstance(source_kind, str) or not source_kind:
            raise ValueError("source_kind must be a non-empty string")
        if not isinstance(observation_count, int) or observation_count < 0:
            raise ValueError("observation_count must be a non-negative int")
        if vetted_observation_count is not None and (not isinstance(vetted_observation_count, int) or vetted_observation_count < 0):
            raise ValueError("vetted_observation_count must be a non-negative int or None")

        ca = _ensure_utc(created_at) if created_at is not None else _utcnow()
        loa = _ensure_utc(last_observed_at) if last_observed_at is not None else ca

        self.entry_a_id = Mapped(entry_a_id)
        self.entry_b_id = Mapped(entry_b_id)
        self.note = Mapped(note)
        self.source_kind = Mapped(source_kind)
        self.created_at = Mapped(ca)
        self.last_observed_at = Mapped(loa)
        self.observation_count = Mapped(int(observation_count))
        self.vetted = Mapped(vetted)
        self.vetted_at = Mapped(_ensure_utc(vetted_at) if vetted_at is not None else None)
        self.vetted_observation_count = Mapped(vetted_observation_count)
        self.vetted_reason = Mapped(vetted_reason)


class Journal(Base, IdMixin):
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
        conversation_id: str,
        note: str,
        source_kind: str,
        entry_ids: Any,
        tags: Any,
        created_at: Optional[datetime] = None,
        invalidated_at: Optional[datetime] = None,
        invalidated_by_id: Optional[str] = None,
        invalidated_reason: Optional[str] = None,
        summarized_journal_ids: Optional[Any] = None,
        superseded_by_id: Optional[str] = None,
        id: Optional[str] = None,
    ) -> None:
        IdMixin.__init__(self, id=id)
        if not isinstance(conversation_id, str) or not conversation_id:
            raise ValueError("conversation_id must be a non-empty string")
        if not isinstance(note, str):
            raise TypeError("note must be a string")
        if not isinstance(source_kind, str) or not source_kind:
            raise ValueError("source_kind must be a non-empty string")

        self.conversation_id = Mapped(conversation_id)
        self.note = Mapped(note)
        self.source_kind = Mapped(source_kind)
        self.entry_ids = Mapped(entry_ids)
        self.tags = Mapped(tags)
        self.created_at = Mapped(_ensure_utc(created_at) if created_at is not None else _utcnow())

        self.invalidated_at = Mapped(_ensure_utc(invalidated_at) if invalidated_at is not None else None)
        self.invalidated_by_id = Mapped(invalidated_by_id)
        self.invalidated_reason = Mapped(invalidated_reason)
        self.summarized_journal_ids = Mapped(summarized_journal_ids)
        self.superseded_by_id = Mapped(superseded_by_id)


class File(Base, IdMixin):
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
        sha256: str,
        size_bytes: int,
        storage_key: str,
        ingest_status: str,
        deleted_at: Optional[datetime] = None,
        description: Optional[Any] = None,
        extra: Optional[str] = None,
        ingested_at: Optional[datetime] = None,
        kind: Optional[str] = None,
        mime_type: Optional[str] = None,
        original_ext: Optional[str] = None,
        summary: Optional[str] = None,
        id: Optional[str] = None,
    ) -> None:
        IdMixin.__init__(self, id=id)
        if not isinstance(sha256, str) or not sha256:
            raise ValueError("sha256 must be a non-empty string")
        if not isinstance(storage_key, str) or not storage_key:
            raise ValueError("storage_key must be a non-empty string")
        if not isinstance(ingest_status, str) or not ingest_status:
            raise ValueError("ingest_status must be a non-empty string")
        if not isinstance(size_bytes, int) or size_bytes < 0:
            raise ValueError("size_bytes must be a non-negative int")

        self.sha256 = Mapped(sha256)
        self.size_bytes = Mapped(int(size_bytes))
        self.storage_key = Mapped(storage_key)
        self.ingest_status = Mapped(ingest_status)

        self.deleted_at = Mapped(_ensure_utc(deleted_at) if deleted_at is not None else None)
        self.description = Mapped(description)
        self.extra = Mapped(extra)
        self.ingested_at = Mapped(_ensure_utc(ingested_at) if ingested_at is not None else None)
        self.kind = Mapped(kind)
        self.mime_type = Mapped(mime_type)
        self.original_ext = Mapped(original_ext)
        self.summary = Mapped(summary)

    def soft_delete(self, when: Optional[datetime] = None) -> None:
        self.deleted_at.value = _ensure_utc(when) if when is not None else _utcnow()


class Folder(Base, IdMixin):
    deleted_at: Mapped[Optional[datetime]]
    name: Mapped[str]
    parent_id: Mapped[Optional[str]]

    def __init__(
        self,
        name: str,
        parent_id: Optional[str] = None,
        deleted_at: Optional[datetime] = None,
        id: Optional[str] = None,
    ) -> None:
        IdMixin.__init__(self, id=id)
        if not isinstance(name, str) or not name:
            raise ValueError("name must be a non-empty string")
        self.name = Mapped(name)
        self.parent_id = Mapped(parent_id)
        self.deleted_at = Mapped(_ensure_utc(deleted_at) if deleted_at is not None else None)

    def soft_delete(self, when: Optional[datetime] = None) -> None:
        self.deleted_at.value = _ensure_utc(when) if when is not None else _utcnow()


class FileEntry(Base, IdMixin):
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
        file_id: str,
        display_name: str,
        lifecycle: str,
        catalog_id: Optional[str] = None,
        folder_id: Optional[str] = None,
        deleted_at: Optional[datetime] = None,
        extra: Optional[str] = None,
        purge_after: Optional[datetime] = None,
        id: Optional[str] = None,
    ) -> None:
        IdMixin.__init__(self, id=id)
        if not isinstance(file_id, str) or not file_id:
            raise ValueError("file_id must be a non-empty string")
        if not isinstance(display_name, str) or not display_name:
            raise ValueError("display_name must be a non-empty string")
        if not isinstance(lifecycle, str) or not lifecycle:
            raise ValueError("lifecycle must be a non-empty string")

        self.file_id = Mapped(file_id)
        self.display_name = Mapped(display_name)
        self.lifecycle = Mapped(lifecycle)
        self.catalog_id = Mapped(catalog_id)
        self.folder_id = Mapped(folder_id)
        self.deleted_at = Mapped(_ensure_utc(deleted_at) if deleted_at is not None else None)
        self.extra = Mapped(extra)
        self.purge_after = Mapped(_ensure_utc(purge_after) if purge_after is not None else None)

    def soft_delete(self, when: Optional[datetime] = None) -> None:
        self.deleted_at.value = _ensure_utc(when) if when is not None else _utcnow()