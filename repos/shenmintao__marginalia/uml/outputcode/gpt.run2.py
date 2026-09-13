from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional, TypeVar, Generic, Union
from uuid import uuid4


T = TypeVar("T")


class Mapped(Generic[T]):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return uuid4().hex


@dataclass
class Base:
    metadata: Any = None
    type_annotation_map: Dict[Any, Any] = field(default_factory=dict)


@dataclass
class IdMixin:
    id: str = field(default_factory=_new_id)


@dataclass
class TimestampMixin:
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    def touch(self) -> None:
        self.updated_at = _utcnow()


class UtcDateTime:
    cache_ok: bool = True
    impl: Any = datetime

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        if not isinstance(value, datetime):
            raise TypeError("UtcDateTime expects a datetime value")
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        if not isinstance(value, datetime):
            raise TypeError("UtcDateTime expects a datetime value")
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


@dataclass
class AuditEvent(Base, IdMixin, TimestampMixin):
    conversation_id: Optional[str] = None
    kind: str = ""
    occurred_at: datetime = field(default_factory=_utcnow)
    payload: Any = None
    session_id: Optional[str] = None
    task_id: Optional[str] = None


@dataclass
class Conversation(Base, IdMixin, TimestampMixin):
    agent_response: Optional[str] = None
    ended_at: Optional[datetime] = None
    llm_calls: Any = field(default_factory=list)
    session_id: str = ""
    started_at: datetime = field(default_factory=_utcnow)
    tool_calls: Any = field(default_factory=list)
    total_cache_read: int = 0
    total_cost_estimate: Decimal = field(default_factory=lambda: Decimal("0"))
    total_duration_ms: int = 0
    total_input_tokens: int = 0
    total_llm_calls: int = 0
    total_output_tokens: int = 0
    total_tool_calls: int = 0
    turn_index: int = 0
    user_message: str = ""


@dataclass
class Session(Base, IdMixin, TimestampMixin):
    deleted_at: Optional[datetime] = None
    end_reason: Optional[str] = None
    ended_at: Optional[datetime] = None
    initiating_user_message: str = ""
    started_at: datetime = field(default_factory=_utcnow)
    total_cache_read: int = 0
    total_cost_estimate: Decimal = field(default_factory=lambda: Decimal("0"))
    total_duration_ms: int = 0
    total_input_tokens: int = 0
    total_llm_calls: int = 0
    total_output_tokens: int = 0
    total_tool_calls: int = 0
    turn_count: int = 0


@dataclass
class Task(Base, IdMixin, TimestampMixin):
    attempts: int = 0
    created_at: datetime = field(default_factory=_utcnow)
    dedup_key: Optional[str] = None
    finished_at: Optional[datetime] = None
    kind: str = ""
    last_error: Optional[str] = None
    last_heartbeat_at: Optional[datetime] = None
    lease_expires_at: Optional[datetime] = None
    locked_by: Optional[str] = None
    max_attempts: int = 0
    payload: Any = None
    priority: int = 0
    scheduled_at: datetime = field(default_factory=_utcnow)
    started_at: Optional[datetime] = None
    status: str = ""


@dataclass
class TaskOutcome(Base, IdMixin, TimestampMixin):
    completed_at: datetime = field(default_factory=_utcnow)
    detail: Optional[Any] = None
    object_id: str = ""
    object_kind: str = ""
    outcome: str = ""
    task_kind: str = ""
    task_run_id: Optional[str] = None


@dataclass
class Catalog(Base, IdMixin, TimestampMixin):
    deleted_at: Optional[datetime] = None
    description: Optional[Any] = None
    extra: Optional[str] = None
    is_system: bool = False
    name: str = ""
    parent_id: Optional[str] = None
    summary: Optional[str] = None
    tags: Optional[Any] = None


@dataclass
class Tag(Base, IdMixin, TimestampMixin):
    alias_of: Optional[str] = None
    doc_count: int = 0
    facet: str = ""
    last_reaffirmed_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    name: str = ""
    reaffirm_count: int = 0


@dataclass
class TagAlias(Base, IdMixin, TimestampMixin):
    created_at: datetime = field(default_factory=_utcnow)
    from_name: str = ""
    note: Optional[str] = None
    to_tag_id: str = ""


@dataclass
class View(Base, IdMixin, TimestampMixin):
    deleted_at: Optional[datetime] = None
    description: Optional[Any] = None
    extra: Optional[str] = None
    filter_spec: Any = None
    name: str = ""
    summary: Optional[str] = None
    tags: Optional[Any] = None


@dataclass
class EntryTag(Base, IdMixin, TimestampMixin):
    created_at: datetime = field(default_factory=_utcnow)
    entry_id: str = ""
    last_reaffirmed_at: Optional[datetime] = None
    reaffirm_count: int = 0
    source: str = ""
    tag_id: str = ""


@dataclass
class EntryRelation(Base, IdMixin, TimestampMixin):
    created_at: datetime = field(default_factory=_utcnow)
    entry_a_id: str = ""
    entry_b_id: str = ""
    last_observed_at: datetime = field(default_factory=_utcnow)
    note: str = ""
    observation_count: int = 0
    source_kind: str = ""
    vetted: Optional[bool] = None
    vetted_at: Optional[datetime] = None
    vetted_observation_count: Optional[int] = None
    vetted_reason: Optional[str] = None


@dataclass
class Journal(Base, IdMixin, TimestampMixin):
    conversation_id: str = ""
    created_at: datetime = field(default_factory=_utcnow)
    entry_ids: Any = field(default_factory=list)
    invalidated_at: Optional[datetime] = None
    invalidated_by_id: Optional[str] = None
    invalidated_reason: Optional[str] = None
    note: str = ""
    source_kind: str = ""
    summarized_journal_ids: Optional[Any] = None
    superseded_by_id: Optional[str] = None
    tags: Any = field(default_factory=list)


@dataclass
class File(Base, IdMixin, TimestampMixin):
    deleted_at: Optional[datetime] = None
    description: Optional[Any] = None
    extra: Optional[str] = None
    ingest_status: str = ""
    ingested_at: Optional[datetime] = None
    kind: Optional[str] = None
    mime_type: Optional[str] = None
    original_ext: Optional[str] = None
    sha256: str = ""
    size_bytes: int = 0
    storage_key: str = ""
    summary: Optional[str] = None


@dataclass
class Folder(Base, IdMixin, TimestampMixin):
    deleted_at: Optional[datetime] = None
    name: str = ""
    parent_id: Optional[str] = None


@dataclass
class FileEntry(Base, IdMixin, TimestampMixin):
    catalog_id: Optional[str] = None
    deleted_at: Optional[datetime] = None
    display_name: str = ""
    extra: Optional[str] = None
    file_id: str = ""
    folder_id: Optional[str] = None
    lifecycle: str = ""
    purge_after: Optional[datetime] = None