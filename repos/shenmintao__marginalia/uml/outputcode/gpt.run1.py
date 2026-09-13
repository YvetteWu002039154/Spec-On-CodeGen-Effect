from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Generic, Optional, TypeVar, Union
from uuid import uuid4


T = TypeVar("T")


class Mapped(Generic[T]):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return uuid4().hex


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

    def __init__(self, id: Optional[str] = None) -> None:
        self.id = id if id is not None else _new_id()


class TimestampMixin:
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]

    def __init__(
        self,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        now = _utcnow()
        self.created_at = created_at if created_at is not None else now
        self.updated_at = updated_at if updated_at is not None else now

    def touch(self, at: Optional[datetime] = None) -> None:
        self.updated_at = at if at is not None else _utcnow()


class UtcDateTime:
    cache_ok: bool = True
    impl: DateTime = DateTime()

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        if not isinstance(value, datetime):
            raise TypeError("UtcDateTime expects a datetime or None")
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        if not isinstance(value, datetime):
            raise TypeError("UtcDateTime expects a datetime or None")
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
        kind: str,
        occurred_at: Optional[datetime] = None,
        payload: Any = None,
        conversation_id: Optional[str] = None,
        session_id: Optional[str] = None,
        task_id: Optional[str] = None,
        id: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        IdMixin.__init__(self, id=id)
        TimestampMixin.__init__(self, created_at=created_at, updated_at=updated_at)
        self.conversation_id = conversation_id
        self.kind = kind
        self.occurred_at = occurred_at if occurred_at is not None else _utcnow()
        self.payload = payload
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
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        IdMixin.__init__(self, id=id)
        TimestampMixin.__init__(self, created_at=created_at, updated_at=updated_at)
        self.session_id = session_id
        self.user_message = user_message
        self.turn_index = int(turn_index)
        self.started_at = started_at if started_at is not None else _utcnow()
        self.agent_response = agent_response
        self.ended_at = ended_at
        self.llm_calls = llm_calls if llm_calls is not None else []
        self.tool_calls = tool_calls if tool_calls is not None else []
        self.total_cache_read = int(total_cache_read)
        self.total_cost_estimate = total_cost_estimate if isinstance(total_cost_estimate, Decimal) else Decimal(str(total_cost_estimate))
        self.total_duration_ms = int(total_duration_ms)
        self.total_input_tokens = int(total_input_tokens)
        self.total_llm_calls = int(total_llm_calls)
        self.total_output_tokens = int(total_output_tokens)
        self.total_tool_calls = int(total_tool_calls)


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
        initiating_user_message: str,
        started_at: Optional[datetime] = None,
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
        id: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        IdMixin.__init__(self, id=id)
        TimestampMixin.__init__(self, created_at=created_at, updated_at=updated_at)
        self.deleted_at = deleted_at
        self.end_reason = end_reason
        self.ended_at = ended_at
        self.initiating_user_message = initiating_user_message
        self.started_at = started_at if started_at is not None else _utcnow()
        self.total_cache_read = int(total_cache_read)
        self.total_cost_estimate = total_cost_estimate if isinstance(total_cost_estimate, Decimal) else Decimal(str(total_cost_estimate))
        self.total_duration_ms = int(total_duration_ms)
        self.total_input_tokens = int(total_input_tokens)
        self.total_llm_calls = int(total_llm_calls)
        self.total_output_tokens = int(total_output_tokens)
        self.total_tool_calls = int(total_tool_calls)
        self.turn_count = int(turn_count)


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
        kind: str,
        payload: Any,
        status: str,
        scheduled_at: Optional[datetime] = None,
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
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        IdMixin.__init__(self, id=id)
        TimestampMixin.__init__(self, created_at=created_at, updated_at=updated_at)
        self.kind = kind
        self.payload = payload
        self.status = status
        self.scheduled_at = scheduled_at if scheduled_at is not None else _utcnow()
        self.priority = int(priority)
        self.attempts = int(attempts)
        self.max_attempts = int(max_attempts)
        self.dedup_key = dedup_key
        self.started_at = started_at
        self.finished_at = finished_at
        self.last_error = last_error
        self.last_heartbeat_at = last_heartbeat_at
        self.lease_expires_at = lease_expires_at
        self.locked_by = locked_by


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
        object_id: str,
        object_kind: str,
        outcome: str,
        task_kind: str,
        completed_at: Optional[datetime] = None,
        detail: Optional[Any] = None,
        task_run_id: Optional[str] = None,
        id: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        IdMixin.__init__(self, id=id)
        TimestampMixin.__init__(self, created_at=created_at, updated_at=updated_at)
        self.completed_at = completed_at if completed_at is not None else _utcnow()
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
        name: str,
        is_system: bool = False,
        parent_id: Optional[str] = None,
        deleted_at: Optional[datetime] = None,
        description: Optional[Any] = None,
        extra: Optional[str] = None,
        summary: Optional[str] = None,
        tags: Optional[Any] = None,
        id: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        IdMixin.__init__(self, id=id)
        TimestampMixin.__init__(self, created_at=created_at, updated_at=updated_at)
        self.deleted_at = deleted_at
        self.description = description
        self.extra = extra
        self.is_system = bool(is_system)
        self.name = name
        self.parent_id = parent_id
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
        name: str,
        facet: str,
        alias_of: Optional[str] = None,
        doc_count: int = 0,
        last_reaffirmed_at: Optional[datetime] = None,
        last_used_at: Optional[datetime] = None,
        reaffirm_count: int = 0,
        id: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        IdMixin.__init__(self, id=id)
        TimestampMixin.__init__(self, created_at=created_at, updated_at=updated_at)
        self.alias_of = alias_of
        self.doc_count = int(doc_count)
        self.facet = facet
        self.last_reaffirmed_at = last_reaffirmed_at
        self.last_used_at = last_used_at
        self.name = name
        self.reaffirm_count = int(reaffirm_count)


class TagAlias(Base, IdMixin, TimestampMixin):
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
        updated_at: Optional[datetime] = None,
    ) -> None:
        IdMixin.__init__(self, id=id)
        TimestampMixin.__init__(self, created_at=created_at, updated_at=updated_at)
        self.created_at = created_at if created_at is not None else self.created_at
        self.from_name = from_name
        self.note = note
        self.to_tag_id = to_tag_id


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
        name: str,
        filter_spec: Any,
        deleted_at: Optional[datetime] = None,
        description: Optional[Any] = None,
        extra: Optional[str] = None,
        summary: Optional[str] = None,
        tags: Optional[Any] = None,
        id: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        IdMixin.__init__(self, id=id)
        TimestampMixin.__init__(self, created_at=created_at, updated_at=updated_at)
        self.deleted_at = deleted_at
        self.description = description
        self.extra = extra
        self.filter_spec = filter_spec
        self.name = name
        self.summary = summary
        self.tags = tags


class EntryTag(Base, IdMixin, TimestampMixin):
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
        updated_at: Optional[datetime] = None,
    ) -> None:
        IdMixin.__init__(self, id=id)
        TimestampMixin.__init__(self, created_at=created_at, updated_at=updated_at)
        self.created_at = created_at if created_at is not None else self.created_at
        self.entry_id = entry_id
        self.last_reaffirmed_at = last_reaffirmed_at
        self.reaffirm_count = int(reaffirm_count)
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
        updated_at: Optional[datetime] = None,
    ) -> None:
        IdMixin.__init__(self, id=id)
        TimestampMixin.__init__(self, created_at=created_at, updated_at=updated_at)
        self.created_at = created_at if created_at is not None else self.created_at
        self.entry_a_id = entry_a_id
        self.entry_b_id = entry_b_id
        self.last_observed_at = last_observed_at if last_observed_at is not None else _utcnow()
        self.note = note
        self.observation_count = int(observation_count)
        self.source_kind = source_kind
        self.vetted = vetted
        self.vetted_at = vetted_at
        self.vetted_observation_count = vetted_observation_count if vetted_observation_count is None else int(vetted_observation_count)
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
        updated_at: Optional[datetime] = None,
    ) -> None:
        IdMixin.__init__(self, id=id)
        TimestampMixin.__init__(self, created_at=created_at, updated_at=updated_at)
        self.conversation_id = conversation_id
        self.created_at = created_at if created_at is not None else self.created_at
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
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        IdMixin.__init__(self, id=id)
        TimestampMixin.__init__(self, created_at=created_at, updated_at=updated_at)
        self.deleted_at = deleted_at
        self.description = description
        self.extra = extra
        self.ingest_status = ingest_status
        self.ingested_at = ingested_at
        self.kind = kind
        self.mime_type = mime_type
        self.original_ext = original_ext
        self.sha256 = sha256
        self.size_bytes = int(size_bytes)
        self.storage_key = storage_key
        self.summary = summary


class Folder(Base, IdMixin, TimestampMixin):
    deleted_at: Mapped[Optional[datetime]]
    name: Mapped[str]
    parent_id: Mapped[Optional[str]]

    def __init__(
        self,
        name: str,
        parent_id: Optional[str] = None,
        deleted_at: Optional[datetime] = None,
        id: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        IdMixin.__init__(self, id=id)
        TimestampMixin.__init__(self, created_at=created_at, updated_at=updated_at)
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
        file_id: str,
        display_name: str,
        lifecycle: str,
        catalog_id: Optional[str] = None,
        folder_id: Optional[str] = None,
        deleted_at: Optional[datetime] = None,
        extra: Optional[str] = None,
        purge_after: Optional[datetime] = None,
        id: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        IdMixin.__init__(self, id=id)
        TimestampMixin.__init__(self, created_at=created_at, updated_at=updated_at)
        self.catalog_id = catalog_id
        self.deleted_at = deleted_at
        self.display_name = display_name
        self.extra = extra
        self.file_id = file_id
        self.folder_id = folder_id
        self.lifecycle = lifecycle
        self.purge_after = purge_after


__all__ = [
    "Mapped",
    "MetaData",
    "DateTime",
    "Base",
    "IdMixin",
    "TimestampMixin",
    "UtcDateTime",
    "AuditEvent",
    "Conversation",
    "Session",
    "Task",
    "TaskOutcome",
    "Catalog",
    "Tag",
    "TagAlias",
    "View",
    "EntryTag",
    "EntryRelation",
    "Journal",
    "File",
    "Folder",
    "FileEntry",
]