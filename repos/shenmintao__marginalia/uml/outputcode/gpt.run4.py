from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional, TypeVar, Generic


T = TypeVar("T")


class Mapped(Generic[T]):
    pass


class MetaData:
    def __init__(self) -> None:
        self.tables: Dict[str, Any] = {}


class DateTime:
    pass


class Base:
    metadata: MetaData = MetaData()
    type_annotation_map: Dict[Any, Any] = {}


class IdMixin:
    id: Mapped[str]

    def __init__(self, id: str) -> None:
        if not isinstance(id, str) or not id:
            raise ValueError("id must be a non-empty string")
        self.id = id


class TimestampMixin:
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]

    def __init__(self, created_at: Optional[datetime] = None, updated_at: Optional[datetime] = None) -> None:
        now = datetime.now(timezone.utc)
        self.created_at = created_at if created_at is not None else now
        self.updated_at = updated_at if updated_at is not None else self.created_at
        if not isinstance(self.created_at, datetime) or not isinstance(self.updated_at, datetime):
            raise TypeError("created_at and updated_at must be datetime instances")
        if self.updated_at < self.created_at:
            raise ValueError("updated_at cannot be earlier than created_at")


class UtcDateTime:
    cache_ok: bool = True
    impl: DateTime = DateTime()

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        if not isinstance(value, datetime):
            raise TypeError("value must be a datetime or None")
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def process_result_value(self, value: Any, dialect: Any) -> Any:
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
    ) -> None:
        IdMixin.__init__(self, id=id)
        TimestampMixin.__init__(self, created_at=created_at, updated_at=updated_at)
        if not isinstance(kind, str) or not kind:
            raise ValueError("kind must be a non-empty string")
        if not isinstance(occurred_at, datetime):
            raise TypeError("occurred_at must be a datetime")
        self.kind = kind
        self.occurred_at = occurred_at
        self.payload = payload
        self.conversation_id = conversation_id
        self.session_id = session_id
        self.task_id = task_id


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
        llm_calls: Any,
        tool_calls: Any,
        total_cache_read: int,
        total_cost_estimate: Decimal,
        total_duration_ms: int,
        total_input_tokens: int,
        total_llm_calls: int,
        total_output_tokens: int,
        total_tool_calls: int,
        agent_response: Optional[str] = None,
        ended_at: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        IdMixin.__init__(self, id=id)
        TimestampMixin.__init__(self, created_at=created_at, updated_at=updated_at)
        if not isinstance(session_id, str) or not session_id:
            raise ValueError("session_id must be a non-empty string")
        if not isinstance(started_at, datetime):
            raise TypeError("started_at must be a datetime")
        if ended_at is not None and not isinstance(ended_at, datetime):
            raise TypeError("ended_at must be a datetime or None")
        if ended_at is not None and ended_at < started_at:
            raise ValueError("ended_at cannot be earlier than started_at")
        if not isinstance(user_message, str):
            raise TypeError("user_message must be a string")
        if not isinstance(turn_index, int) or turn_index < 0:
            raise ValueError("turn_index must be a non-negative int")
        for name, val in [
            ("total_cache_read", total_cache_read),
            ("total_duration_ms", total_duration_ms),
            ("total_input_tokens", total_input_tokens),
            ("total_llm_calls", total_llm_calls),
            ("total_output_tokens", total_output_tokens),
            ("total_tool_calls", total_tool_calls),
        ]:
            if not isinstance(val, int) or val < 0:
                raise ValueError(f"{name} must be a non-negative int")
        if not isinstance(total_cost_estimate, Decimal):
            raise TypeError("total_cost_estimate must be a Decimal")
        if total_cost_estimate < Decimal("0"):
            raise ValueError("total_cost_estimate must be non-negative")

        self.session_id = session_id
        self.started_at = started_at
        self.ended_at = ended_at
        self.user_message = user_message
        self.agent_response = agent_response
        self.turn_index = turn_index
        self.llm_calls = llm_calls
        self.tool_calls = tool_calls
        self.total_cache_read = total_cache_read
        self.total_cost_estimate = total_cost_estimate
        self.total_duration_ms = total_duration_ms
        self.total_input_tokens = total_input_tokens
        self.total_llm_calls = total_llm_calls
        self.total_output_tokens = total_output_tokens
        self.total_tool_calls = total_tool_calls


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
        total_cache_read: int,
        total_cost_estimate: Decimal,
        total_duration_ms: int,
        total_input_tokens: int,
        total_llm_calls: int,
        total_output_tokens: int,
        total_tool_calls: int,
        turn_count: int,
        deleted_at: Optional[datetime] = None,
        ended_at: Optional[datetime] = None,
        end_reason: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        IdMixin.__init__(self, id=id)
        TimestampMixin.__init__(self, created_at=created_at, updated_at=updated_at)
        if not isinstance(initiating_user_message, str):
            raise TypeError("initiating_user_message must be a string")
        if not isinstance(started_at, datetime):
            raise TypeError("started_at must be a datetime")
        if deleted_at is not None and not isinstance(deleted_at, datetime):
            raise TypeError("deleted_at must be a datetime or None")
        if ended_at is not None and not isinstance(ended_at, datetime):
            raise TypeError("ended_at must be a datetime or None")
        if ended_at is not None and ended_at < started_at:
            raise ValueError("ended_at cannot be earlier than started_at")
        for name, val in [
            ("total_cache_read", total_cache_read),
            ("total_duration_ms", total_duration_ms),
            ("total_input_tokens", total_input_tokens),
            ("total_llm_calls", total_llm_calls),
            ("total_output_tokens", total_output_tokens),
            ("total_tool_calls", total_tool_calls),
            ("turn_count", turn_count),
        ]:
            if not isinstance(val, int) or val < 0:
                raise ValueError(f"{name} must be a non-negative int")
        if not isinstance(total_cost_estimate, Decimal):
            raise TypeError("total_cost_estimate must be a Decimal")
        if total_cost_estimate < Decimal("0"):
            raise ValueError("total_cost_estimate must be non-negative")
        if end_reason is not None and not isinstance(end_reason, str):
            raise TypeError("end_reason must be a string or None")

        self.deleted_at = deleted_at
        self.end_reason = end_reason
        self.ended_at = ended_at
        self.initiating_user_message = initiating_user_message
        self.started_at = started_at
        self.total_cache_read = total_cache_read
        self.total_cost_estimate = total_cost_estimate
        self.total_duration_ms = total_duration_ms
        self.total_input_tokens = total_input_tokens
        self.total_llm_calls = total_llm_calls
        self.total_output_tokens = total_output_tokens
        self.total_tool_calls = total_tool_calls
        self.turn_count = turn_count


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
        priority: int,
        scheduled_at: datetime,
        status: str,
        attempts: int,
        max_attempts: int,
        dedup_key: Optional[str] = None,
        started_at: Optional[datetime] = None,
        finished_at: Optional[datetime] = None,
        last_error: Optional[str] = None,
        last_heartbeat_at: Optional[datetime] = None,
        lease_expires_at: Optional[datetime] = None,
        locked_by: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        IdMixin.__init__(self, id=id)
        TimestampMixin.__init__(self, created_at=created_at, updated_at=updated_at)
        if not isinstance(kind, str) or not kind:
            raise ValueError("kind must be a non-empty string")
        if not isinstance(priority, int):
            raise TypeError("priority must be an int")
        if not isinstance(scheduled_at, datetime):
            raise TypeError("scheduled_at must be a datetime")
        if not isinstance(status, str) or not status:
            raise ValueError("status must be a non-empty string")
        if not isinstance(attempts, int) or attempts < 0:
            raise ValueError("attempts must be a non-negative int")
        if not isinstance(max_attempts, int) or max_attempts < 0:
            raise ValueError("max_attempts must be a non-negative int")
        if attempts > max_attempts:
            raise ValueError("attempts cannot exceed max_attempts")
        for name, dt in [
            ("started_at", started_at),
            ("finished_at", finished_at),
            ("last_heartbeat_at", last_heartbeat_at),
            ("lease_expires_at", lease_expires_at),
        ]:
            if dt is not None and not isinstance(dt, datetime):
                raise TypeError(f"{name} must be a datetime or None")
        if started_at is not None and started_at < scheduled_at:
            pass
        if finished_at is not None and started_at is not None and finished_at < started_at:
            raise ValueError("finished_at cannot be earlier than started_at")
        if last_error is not None and not isinstance(last_error, str):
            raise TypeError("last_error must be a string or None")
        if locked_by is not None and not isinstance(locked_by, str):
            raise TypeError("locked_by must be a string or None")
        if dedup_key is not None and not isinstance(dedup_key, str):
            raise TypeError("dedup_key must be a string or None")

        self.attempts = attempts
        self.dedup_key = dedup_key
        self.finished_at = finished_at
        self.kind = kind
        self.last_error = last_error
        self.last_heartbeat_at = last_heartbeat_at
        self.lease_expires_at = lease_expires_at
        self.locked_by = locked_by
        self.max_attempts = max_attempts
        self.payload = payload
        self.priority = priority
        self.scheduled_at = scheduled_at
        self.started_at = started_at
        self.status = status


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
    ) -> None:
        IdMixin.__init__(self, id=id)
        TimestampMixin.__init__(self, created_at=created_at, updated_at=updated_at)
        if not isinstance(completed_at, datetime):
            raise TypeError("completed_at must be a datetime")
        for name, val in [
            ("object_id", object_id),
            ("object_kind", object_kind),
            ("outcome", outcome),
            ("task_kind", task_kind),
        ]:
            if not isinstance(val, str) or not val:
                raise ValueError(f"{name} must be a non-empty string")
        if task_run_id is not None and (not isinstance(task_run_id, str) or not task_run_id):
            raise ValueError("task_run_id must be a non-empty string or None")

        self.completed_at = completed_at
        self.detail = detail
        self.object_id = object_id
        self.object_kind = object_kind
        self.outcome = outcome
        self.task_kind = task_kind
        self.task_run_id = task_run_id


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
        deleted_at: Optional[datetime] = None,
        description: Optional[Any] = None,
        extra: Optional[str] = None,
        parent_id: Optional[str] = None,
        summary: Optional[str] = None,
        tags: Optional[Any] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        IdMixin.__init__(self, id=id)
        TimestampMixin.__init__(self, created_at=created_at, updated_at=updated_at)
        if not isinstance(name, str) or not name:
            raise ValueError("name must be a non-empty string")
        if not isinstance(is_system, bool):
            raise TypeError("is_system must be a bool")
        if deleted_at is not None and not isinstance(deleted_at, datetime):
            raise TypeError("deleted_at must be a datetime or None")
        if extra is not None and not isinstance(extra, str):
            raise TypeError("extra must be a string or None")
        if parent_id is not None and not isinstance(parent_id, str):
            raise TypeError("parent_id must be a string or None")
        if summary is not None and not isinstance(summary, str):
            raise TypeError("summary must be a string or None")

        self.deleted_at = deleted_at
        self.description = description
        self.extra = extra
        self.is_system = is_system
        self.name = name
        self.parent_id = parent_id
        self.summary = summary
        self.tags = tags


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
    ) -> None:
        IdMixin.__init__(self, id=id)
        TimestampMixin.__init__(self, created_at=created_at, updated_at=updated_at)
        if not isinstance(name, str) or not name:
            raise ValueError("name must be a non-empty string")
        if deleted_at is not None and not isinstance(deleted_at, datetime):
            raise TypeError("deleted_at must be a datetime or None")
        if extra is not None and not isinstance(extra, str):
            raise TypeError("extra must be a string or None")
        if summary is not None and not isinstance(summary, str):
            raise TypeError("summary must be a string or None")

        self.deleted_at = deleted_at
        self.description = description
        self.extra = extra
        self.filter_spec = filter_spec
        self.name = name
        self.summary = summary
        self.tags = tags


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
        doc_count: int,
        reaffirm_count: int,
        alias_of: Optional[str] = None,
        last_reaffirmed_at: Optional[datetime] = None,
        last_used_at: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
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
        if alias_of is not None and not isinstance(alias_of, str):
            raise TypeError("alias_of must be a string or None")
        if last_reaffirmed_at is not None and not isinstance(last_reaffirmed_at, datetime):
            raise TypeError("last_reaffirmed_at must be a datetime or None")
        if last_used_at is not None and not isinstance(last_used_at, datetime):
            raise TypeError("last_used_at must be a datetime or None")

        self.alias_of = alias_of
        self.doc_count = doc_count
        self.facet = facet
        self.last_reaffirmed_at = last_reaffirmed_at
        self.last_used_at = last_used_at
        self.name = name
        self.reaffirm_count = reaffirm_count


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
    ) -> None:
        IdMixin.__init__(self, id=id)
        TimestampMixin.__init__(self, created_at=created_at, updated_at=updated_at)
        if not isinstance(from_name, str) or not from_name:
            raise ValueError("from_name must be a non-empty string")
        if not isinstance(to_tag_id, str) or not to_tag_id:
            raise ValueError("to_tag_id must be a non-empty string")
        if note is not None and not isinstance(note, str):
            raise TypeError("note must be a string or None")

        self.from_name = from_name
        self.note = note
        self.to_tag_id = to_tag_id


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
        reaffirm_count: int,
        created_at: Optional[datetime] = None,
        last_reaffirmed_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        IdMixin.__init__(self, id=id)
        TimestampMixin.__init__(self, created_at=created_at, updated_at=updated_at)
        if not isinstance(entry_id, str) or not entry_id:
            raise ValueError("entry_id must be a non-empty string")
        if not isinstance(tag_id, str) or not tag_id:
            raise ValueError("tag_id must be a non-empty string")
        if not isinstance(source, str) or not source:
            raise ValueError("source must be a non-empty string")
        if not isinstance(reaffirm_count, int) or reaffirm_count < 0:
            raise ValueError("reaffirm_count must be a non-negative int")
        if last_reaffirmed_at is not None and not isinstance(last_reaffirmed_at, datetime):
            raise TypeError("last_reaffirmed_at must be a datetime or None")

        self.entry_id = entry_id
        self.last_reaffirmed_at = last_reaffirmed_at
        self.reaffirm_count = reaffirm_count
        self.source = source
        self.tag_id = tag_id


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
    ) -> None:
        IdMixin.__init__(self, id=id)
        TimestampMixin.__init__(self, created_at=created_at, updated_at=updated_at)
        for name, val in [("entry_a_id", entry_a_id), ("entry_b_id", entry_b_id), ("source_kind", source_kind)]:
            if not isinstance(val, str) or not val:
                raise ValueError(f"{name} must be a non-empty string")
        if entry_a_id == entry_b_id:
            raise ValueError("entry_a_id and entry_b_id must be different")
        if not isinstance(last_observed_at, datetime):
            raise TypeError("last_observed_at must be a datetime")
        if not isinstance(note, str):
            raise TypeError("note must be a string")
        if not isinstance(observation_count, int) or observation_count < 0:
            raise ValueError("observation_count must be a non-negative int")
        if vetted_at is not None and not isinstance(vetted_at, datetime):
            raise TypeError("vetted_at must be a datetime or None")
        if vetted_observation_count is not None and (not isinstance(vetted_observation_count, int) or vetted_observation_count < 0):
            raise ValueError("vetted_observation_count must be a non-negative int or None")
        if vetted_reason is not None and not isinstance(vetted_reason, str):
            raise TypeError("vetted_reason must be a string or None")

        self.entry_a_id = entry_a_id
        self.entry_b_id = entry_b_id
        self.last_observed_at = last_observed_at
        self.note = note
        self.observation_count = observation_count
        self.source_kind = source_kind
        self.vetted = vetted
        self.vetted_at = vetted_at
        self.vetted_observation_count = vetted_observation_count
        self.vetted_reason = vetted_reason


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
        entry_ids: Any,
        note: str,
        source_kind: str,
        tags: Any,
        summarized_journal_ids: Optional[Any] = None,
        invalidated_at: Optional[datetime] = None,
        invalidated_by_id: Optional[str] = None,
        invalidated_reason: Optional[str] = None,
        superseded_by_id: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        IdMixin.__init__(self, id=id)
        TimestampMixin.__init__(self, created_at=created_at, updated_at=updated_at)
        if not isinstance(conversation_id, str) or not conversation_id:
            raise ValueError("conversation_id must be a non-empty string")
        if not isinstance(note, str):
            raise TypeError("note must be a string")
        if not isinstance(source_kind, str) or not source_kind:
            raise ValueError("source_kind must be a non-empty string")
        if invalidated_at is not None and not isinstance(invalidated_at, datetime):
            raise TypeError("invalidated_at must be a datetime or None")
        if invalidated_by_id is not None and not isinstance(invalidated_by_id, str):
            raise TypeError("invalidated_by_id must be a string or None")
        if invalidated_reason is not None and not isinstance(invalidated_reason, str):
            raise TypeError("invalidated_reason must be a string or None")
        if superseded_by_id is not None and not isinstance(superseded_by_id, str):
            raise TypeError("superseded_by_id must be a string or None")

        self.conversation_id = conversation_id
        self.entry_ids = entry_ids
        self.invalidated_at = invalidated_at
        self.invalidated_by_id = invalidated_by_id
        self.invalidated_reason = invalidated_reason
        self.note = note
        self.source_kind = source_kind
        self.summarized_journal_ids = summarized_journal_ids
        self.superseded_by_id = superseded_by_id
        self.tags = tags


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
        description: Optional[Any] = None,
        extra: Optional[str] = None,
        ingested_at: Optional[datetime] = None,
        kind: Optional[str] = None,
        mime_type: Optional[str] = None,
        original_ext: Optional[str] = None,
        summary: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        IdMixin.__init__(self, id=id)
        TimestampMixin.__init__(self, created_at=created_at, updated_at=updated_at)
        if not isinstance(sha256, str) or not sha256:
            raise ValueError("sha256 must be a non-empty string")
        if not isinstance(size_bytes, int) or size_bytes < 0:
            raise ValueError("size_bytes must be a non-negative int")
        if not isinstance(storage_key, str) or not storage_key:
            raise ValueError("storage_key must be a non-empty string")
        if not isinstance(ingest_status, str) or not ingest_status:
            raise ValueError("ingest_status must be a non-empty string")
        if deleted_at is not None and not isinstance(deleted_at, datetime):
            raise TypeError("deleted_at must be a datetime or None")
        if extra is not None and not isinstance(extra, str):
            raise TypeError("extra must be a string or None")
        if ingested_at is not None and not isinstance(ingested_at, datetime):
            raise TypeError("ingested_at must be a datetime or None")
        for name, val in [("kind", kind), ("mime_type", mime_type), ("original_ext", original_ext), ("summary", summary)]:
            if val is not None and not isinstance(val, str):
                raise TypeError(f"{name} must be a string or None")

        self.deleted_at = deleted_at
        self.description = description
        self.extra = extra
        self.ingest_status = ingest_status
        self.ingested_at = ingested_at
        self.kind = kind
        self.mime_type = mime_type
        self.original_ext = original_ext
        self.sha256 = sha256
        self.size_bytes = size_bytes
        self.storage_key = storage_key
        self.summary = summary


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
    ) -> None:
        IdMixin.__init__(self, id=id)
        TimestampMixin.__init__(self, created_at=created_at, updated_at=updated_at)
        if not isinstance(name, str) or not name:
            raise ValueError("name must be a non-empty string")
        if parent_id is not None and not isinstance(parent_id, str):
            raise TypeError("parent_id must be a string or None")
        if deleted_at is not None and not isinstance(deleted_at, datetime):
            raise TypeError("deleted_at must be a datetime or None")

        self.deleted_at = deleted_at
        self.name = name
        self.parent_id = parent_id


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
        extra: Optional[str] = None,
        purge_after: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        IdMixin.__init__(self, id=id)
        TimestampMixin.__init__(self, created_at=created_at, updated_at=updated_at)
        if not isinstance(file_id, str) or not file_id:
            raise ValueError("file_id must be a non-empty string")
        if not isinstance(display_name, str) or not display_name:
            raise ValueError("display_name must be a non-empty string")
        if not isinstance(lifecycle, str) or not lifecycle:
            raise ValueError("lifecycle must be a non-empty string")
        if catalog_id is not None and not isinstance(catalog_id, str):
            raise TypeError("catalog_id must be a string or None")
        if folder_id is not None and not isinstance(folder_id, str):
            raise TypeError("folder_id must be a string or None")
        if deleted_at is not None and not isinstance(deleted_at, datetime):
            raise TypeError("deleted_at must be a datetime or None")
        if extra is not None and not isinstance(extra, str):
            raise TypeError("extra must be a string or None")
        if purge_after is not None and not isinstance(purge_after, datetime):
            raise TypeError("purge_after must be a datetime or None")

        self.catalog_id = catalog_id
        self.deleted_at = deleted_at
        self.display_name = display_name
        self.extra = extra
        self.file_id = file_id
        self.folder_id = folder_id
        self.lifecycle = lifecycle
        self.purge_after = purge_after