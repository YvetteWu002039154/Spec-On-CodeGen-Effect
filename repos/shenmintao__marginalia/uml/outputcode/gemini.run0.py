from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
import uuid

from sqlalchemy import Boolean, DateTime, Integer, JSON, MetaData, Numeric, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator


class UtcDateTime(TypeDecorator):
    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Any) -> datetime | None:
        if value is not None:
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)
        return value

    def process_result_value(self, value: datetime | None, dialect: Any) -> datetime | None:
        if value is not None:
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)
        return value


class Base(DeclarativeBase):
    metadata = MetaData()
    type_annotation_map = {
        datetime: UtcDateTime(timezone=True),
        Any: JSON,
        dict[Any, Any]: JSON,
        Decimal: Numeric(precision=10, scale=4)
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
    
    conversation_id: Mapped[str | None]
    kind: Mapped[str]
    occurred_at: Mapped[datetime]
    payload: Mapped[Any]
    session_id: Mapped[str | None]
    task_id: Mapped[str | None]


class Catalog(Base, IdMixin):
    __tablename__ = "catalog"
    
    deleted_at: Mapped[datetime | None]
    description: Mapped[Any | None]
    extra: Mapped[str | None]
    is_system: Mapped[bool]
    name: Mapped[str]
    parent_id: Mapped[str | None]
    summary: Mapped[str | None]
    tags: Mapped[Any | None]


class Conversation(Base, IdMixin):
    __tablename__ = "conversation"
    
    agent_response: Mapped[str | None]
    ended_at: Mapped[datetime | None]
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
    vetted: Mapped[bool | None]
    vetted_at: Mapped[datetime | None]
    vetted_observation_count: Mapped[int | None]
    vetted_reason: Mapped[str | None]


class EntryTag(Base, IdMixin):
    __tablename__ = "entry_tag"
    
    created_at: Mapped[datetime]
    entry_id: Mapped[str]
    last_reaffirmed_at: Mapped[datetime | None]
    reaffirm_count: Mapped[int]
    source: Mapped[str]
    tag_id: Mapped[str]


class File(Base, IdMixin):
    __tablename__ = "file"
    
    deleted_at: Mapped[datetime | None]
    description: Mapped[Any | None]
    extra: Mapped[str | None]
    ingest_status: Mapped[str]
    ingested_at: Mapped[datetime | None]
    kind: Mapped[str | None]
    mime_type: Mapped[str | None]
    original_ext: Mapped[str | None]
    sha256: Mapped[str]
    size_bytes: Mapped[int]
    storage_key: Mapped[str]
    summary: Mapped[str | None]


class FileEntry(Base, IdMixin):
    __tablename__ = "file_entry"
    
    catalog_id: Mapped[str | None]
    deleted_at: Mapped[datetime | None]
    display_name: Mapped[str]
    extra: Mapped[str | None]
    file_id: Mapped[str]
    folder_id: Mapped[str | None]
    lifecycle: Mapped[str]
    purge_after: Mapped[datetime | None]


class Folder(Base, IdMixin):
    __tablename__ = "folder"
    
    deleted_at: Mapped[datetime | None]
    name: Mapped[str]
    parent_id: Mapped[str | None]


class Journal(Base, IdMixin):
    __tablename__ = "journal"
    
    conversation_id: Mapped[str]
    created_at: Mapped[datetime]
    entry_ids: Mapped[Any]
    invalidated_at: Mapped[datetime | None]
    invalidated_by_id: Mapped[str | None]
    invalidated_reason: Mapped[str | None]
    note: Mapped[str]
    source_kind: Mapped[str]
    summarized_journal_ids: Mapped[Any | None]
    superseded_by_id: Mapped[str | None]
    tags: Mapped[Any]


class Session(Base, IdMixin):
    __tablename__ = "session"
    
    deleted_at: Mapped[datetime | None]
    end_reason: Mapped[str | None]
    ended_at: Mapped[datetime | None]
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
    
    alias_of: Mapped[str | None]
    doc_count: Mapped[int]
    facet: Mapped[str]
    last_reaffirmed_at: Mapped[datetime | None]
    last_used_at: Mapped[datetime | None]
    name: Mapped[str]
    reaffirm_count: Mapped[int]


class TagAlias(Base, IdMixin):
    __tablename__ = "tag_alias"
    
    created_at: Mapped[datetime]
    from_name: Mapped[str]
    note: Mapped[str | None]
    to_tag_id: Mapped[str]


class Task(Base, IdMixin):
    __tablename__ = "task"
    
    attempts: Mapped[int]
    created_at: Mapped[datetime]
    dedup_key: Mapped[str | None]
    finished_at: Mapped[datetime | None]
    kind: Mapped[str]
    last_error: Mapped[str | None]
    last_heartbeat_at: Mapped[datetime | None]
    lease_expires_at: Mapped[datetime | None]
    locked_by: Mapped[str | None]
    max_attempts: Mapped[int]
    payload: Mapped[Any]
    priority: Mapped[int]
    scheduled_at: Mapped[datetime]
    started_at: Mapped[datetime | None]
    status: Mapped[str]


class TaskOutcome(Base, IdMixin):
    __tablename__ = "task_outcome"
    
    completed_at: Mapped[datetime]
    detail: Mapped[Any | None]
    object_id: Mapped[str]
    object_kind: Mapped[str]
    outcome: Mapped[str]
    task_kind: Mapped[str]
    task_run_id: Mapped[str | None]


class View(Base, IdMixin):
    __tablename__ = "view"
    
    deleted_at: Mapped[datetime | None]
    description: Mapped[Any | None]
    extra: Mapped[str | None]
    filter_spec: Mapped[Any]
    name: Mapped[str]
    summary: Mapped[str | None]
    tags: Mapped[Any | None]