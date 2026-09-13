import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    JSON,
    Numeric,
    String,
    TypeDecorator,
    MetaData,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class UtcDateTime(TypeDecorator):
    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: Optional[datetime], dialect) -> Optional[datetime]:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def process_result_value(self, value: Optional[datetime], dialect) -> Optional[datetime]:
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


class Base(DeclarativeBase):
    metadata: MetaData = MetaData()
    type_annotation_map: dict[Any, Any] = {}


class IdMixin:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class AuditEvent(Base, IdMixin):
    __tablename__ = "audit_event"

    conversation_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    kind: Mapped[str] = mapped_column(String)
    occurred_at: Mapped[datetime] = mapped_column(UtcDateTime)
    payload: Mapped[Any] = mapped_column(JSON)
    session_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    task_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class Conversation(Base, IdMixin):
    __tablename__ = "conversation"

    agent_response: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    llm_calls: Mapped[Any] = mapped_column(JSON)
    session_id: Mapped[str] = mapped_column(String)
    started_at: Mapped[datetime] = mapped_column(UtcDateTime)
    tool_calls: Mapped[Any] = mapped_column(JSON)
    total_cache_read: Mapped[int] = mapped_column(Integer, default=0)
    total_cost_estimate: Mapped[Decimal] = mapped_column(Numeric(12, 6))
    total_duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    total_input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_llm_calls: Mapped[int] = mapped_column(Integer, default=0)
    total_output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tool_calls: Mapped[int] = mapped_column(Integer, default=0)
    turn_index: Mapped[int] = mapped_column(Integer)
    user_message: Mapped[str] = mapped_column(String)


class Session(Base, IdMixin):
    __tablename__ = "session"

    deleted_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    end_reason: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    initiating_user_message: Mapped[str] = mapped_column(String)
    started_at: Mapped[datetime] = mapped_column(UtcDateTime)
    total_cache_read: Mapped[int] = mapped_column(Integer, default=0)
    total_cost_estimate: Mapped[Decimal] = mapped_column(Numeric(12, 6))
    total_duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    total_input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_llm_calls: Mapped[int] = mapped_column(Integer, default=0)
    total_output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tool_calls: Mapped[int] = mapped_column(Integer, default=0)
    turn_count: Mapped[int] = mapped_column(Integer, default=0)


class Catalog(Base, IdMixin):
    __tablename__ = "catalog"

    deleted_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    description: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    extra: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    name: Mapped[str] = mapped_column(String)
    parent_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    tags: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)


class EntryRelation(Base, IdMixin):
    __tablename__ = "entry_relation"

    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=lambda: datetime.now(timezone.utc))
    entry_a_id: Mapped[str] = mapped_column(String)
    entry_b_id: Mapped[str] = mapped_column(String)
    last_observed_at: Mapped[datetime] = mapped_column(UtcDateTime)
    note: Mapped[str] = mapped_column(String)
    observation_count: Mapped[int] = mapped_column(Integer, default=0)
    source_kind: Mapped[str] = mapped_column(String)
    vetted: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    vetted_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    vetted_observation_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    vetted_reason: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class EntryTag(Base, IdMixin):
    __tablename__ = "entry_tag"

    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=lambda: datetime.now(timezone.utc))
    entry_id: Mapped[str] = mapped_column(String)
    last_reaffirmed_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    reaffirm_count: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String)
    tag_id: Mapped[str] = mapped_column(String)


class File(Base, IdMixin):
    __tablename__ = "file"

    deleted_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    description: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    extra: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    ingest_status: Mapped[str] = mapped_column(String)
    ingested_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    kind: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    original_ext: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    sha256: Mapped[str] = mapped_column(String)
    size_bytes: Mapped[int] = mapped_column(Integer)
    storage_key: Mapped[str] = mapped_column(String)
    summary: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class FileEntry(Base, IdMixin):
    __tablename__ = "file_entry"

    catalog_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    display_name: Mapped[str] = mapped_column(String)
    extra: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    file_id: Mapped[str] = mapped_column(String)
    folder_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    lifecycle: Mapped[str] = mapped_column(String)
    purge_after: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)


class Folder(Base, IdMixin):
    __tablename__ = "folder"

    deleted_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    name: Mapped[str] = mapped_column(String)
    parent_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class Journal(Base, IdMixin):
    __tablename__ = "journal"

    conversation_id: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=lambda: datetime.now(timezone.utc))
    entry_ids: Mapped[Any] = mapped_column(JSON)
    invalidated_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    invalidated_by_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    invalidated_reason: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    note: Mapped[str] = mapped_column(String)
    source_kind: Mapped[str] = mapped_column(String)
    summarized_journal_ids: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    superseded_by_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    tags: Mapped[Any] = mapped_column(JSON)


class Tag(Base, IdMixin):
    __tablename__ = "tag"

    alias_of: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    doc_count: Mapped[int] = mapped_column(Integer, default=0)
    facet: Mapped[str] = mapped_column(String)
    last_reaffirmed_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    reaffirm_count: Mapped[int] = mapped_column(Integer, default=0)


class TagAlias(Base, IdMixin):
    __tablename__ = "tag_alias"

    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=lambda: datetime.now(timezone.utc))
    from_name: Mapped[str] = mapped_column(String)
    note: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    to_tag_id: Mapped[str] = mapped_column(String)


class Task(Base, IdMixin):
    __tablename__ = "task"

    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=lambda: datetime.now(timezone.utc))
    dedup_key: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    kind: Mapped[str] = mapped_column(String)
    last_error: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    last_heartbeat_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    lease_expires_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    locked_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    max_attempts: Mapped[int] = mapped_column(Integer, default=1)
    payload: Mapped[Any] = mapped_column(JSON)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    scheduled_at: Mapped[datetime] = mapped_column(UtcDateTime)
    started_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    status: Mapped[str] = mapped_column(String, default="pending")


class TaskOutcome(Base, IdMixin):
    __tablename__ = "task_outcome"

    completed_at: Mapped[datetime] = mapped_column(UtcDateTime)
    detail: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    object_id: Mapped[str] = mapped_column(String)
    object_kind: Mapped[str] = mapped_column(String)
    outcome: Mapped[str] = mapped_column(String)
    task_kind: Mapped[str] = mapped_column(String)
    task_run_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class View(Base, IdMixin):
    __tablename__ = "view"

    deleted_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    description: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    extra: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    filter_spec: Mapped[Any] = mapped_column(JSON)
    name: Mapped[str] = mapped_column(String)
    summary: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    tags: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)