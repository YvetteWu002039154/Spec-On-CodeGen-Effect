import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import DateTime, MetaData, String, Numeric, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator


class UtcDateTime(TypeDecorator):
    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: Optional[datetime], dialect: Any) -> Optional[datetime]:
        if value is not None:
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)
        return value

    def process_result_value(self, value: Optional[datetime], dialect: Any) -> Optional[datetime]:
        if value is not None:
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)
        return value


class Base(DeclarativeBase):
    metadata = MetaData()
    type_annotation_map = {
        datetime: UtcDateTime(),
        Any: JSON,
        dict[Any, Any]: JSON,
        Decimal: Numeric(18, 6)
    }


class IdMixin:
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )


class AuditEvent(Base, IdMixin):
    __tablename__ = "audit_event"

    conversation_id: Mapped[Optional[str]]
    kind: Mapped[str]
    occurred_at: Mapped[datetime]
    payload: Mapped[Any]
    session_id: Mapped[Optional[str]]
    task_id: Mapped[Optional[str]]


class Catalog(Base, IdMixin):
    __tablename__ = "catalog"

    deleted_at: Mapped[Optional[datetime]]
    description: Mapped[Optional[Any]]
    extra: Mapped[Optional[str]]
    is_system: Mapped[bool]
    name: Mapped[str]
    parent_id: Mapped[Optional[str]]
    summary: Mapped[Optional[str]]
    tags: Mapped[Optional[Any]]


class Conversation(Base, IdMixin):
    __tablename__ = "conversation"

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


class EntryRelation(Base, IdMixin):
    __tablename__ = "entry_relation"

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


class EntryTag(Base, IdMixin):
    __tablename__ = "entry_tag"

    created_at: Mapped[datetime]
    entry_id: Mapped[str]
    last_reaffirmed_at: Mapped[Optional[datetime]]
    reaffirm_count: Mapped[int]
    source: Mapped[str]
    tag_id: Mapped[str]


class File(Base, IdMixin):
    __tablename__ = "file"

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


class FileEntry(Base, IdMixin):
    __tablename__ = "file_entry"

    catalog_id: Mapped[Optional[str]]
    deleted_at: Mapped[Optional[datetime]]
    display_name: Mapped[str]
    extra: Mapped[Optional[str]]
    file_id: Mapped[str]
    folder_id: Mapped[Optional[str]]
    lifecycle: Mapped[str]
    purge_after: Mapped[Optional[datetime]]


class Folder(Base, IdMixin):
    __tablename__ = "folder"

    deleted_at: Mapped[Optional[datetime]]
    name: Mapped[str]
    parent_id: Mapped[Optional[str]]


class Journal(Base, IdMixin):
    __tablename__ = "journal"

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


class Session(Base, IdMixin):
    __tablename__ = "session"

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


class Tag(Base, IdMixin):
    __tablename__ = "tag"

    alias_of: Mapped[Optional[str]]
    doc_count: Mapped[int]
    facet: Mapped[str]
    last_reaffirmed_at: Mapped[Optional[datetime]]
    last_used_at: Mapped[Optional[datetime]]
    name: Mapped[str]
    reaffirm_count: Mapped[int]


class TagAlias(Base, IdMixin):
    __tablename__ = "tag_alias"

    created_at: Mapped[datetime]
    from_name: Mapped[str]
    note: Mapped[Optional[str]]
    to_tag_id: Mapped[str]


class Task(Base, IdMixin):
    __tablename__ = "task"

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


class TaskOutcome(Base, IdMixin):
    __tablename__ = "task_outcome"

    completed_at: Mapped[datetime]
    detail: Mapped[Optional[Any]]
    object_id: Mapped[str]
    object_kind: Mapped[str]
    outcome: Mapped[str]
    task_kind: Mapped[str]
    task_run_id: Mapped[Optional[str]]


class View(Base, IdMixin):
    __tablename__ = "view"

    deleted_at: Mapped[Optional[datetime]]
    description: Mapped[Optional[Any]]
    extra: Mapped[Optional[str]]
    filter_spec: Mapped[Any]
    name: Mapped[str]
    summary: Mapped[Optional[str]]
    tags: Mapped[Optional[Any]]