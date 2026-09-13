from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    TypeDecorator,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class UtcDateTime(TypeDecorator):
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return value.astimezone(timezone.utc).replace(tzinfo=None)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return value.replace(tzinfo=timezone.utc)
        return value


class Base(DeclarativeBase):
    metadata = Base.metadata
    type_annotation_map: dict[Any, Any] = {
        datetime: UtcDateTime,
    }


class IdMixin:
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
    )


class AuditEvent(Base):
    __tablename__ = "audit_event"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    conversation_id: Mapped[str | None]
    kind: Mapped[str]
    occurred_at: Mapped[datetime]
    payload: Mapped[Any] = mapped_column(JSON)
    session_id: Mapped[str | None]
    task_id: Mapped[str | None]


class Catalog(Base):
    __tablename__ = "catalog"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    deleted_at: Mapped[datetime | None]
    description: Mapped[Any | None] = mapped_column(JSON)
    extra: Mapped[str | None]
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    name: Mapped[str]
    parent_id: Mapped[str | None] = mapped_column(
        ForeignKey("catalog.id"), nullable=True
    )
    summary: Mapped[str | None]
    tags: Mapped[Any | None] = mapped_column(JSON)


class Conversation(Base):
    __tablename__ = "conversation"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    agent_response: Mapped[str | None]
    ended_at: Mapped[datetime | None]
    llm_calls: Mapped[Any] = mapped_column(JSON)
    session_id: Mapped[str]
    started_at: Mapped[datetime]
    tool_calls: Mapped[Any] = mapped_column(JSON)
    total_cache_read: Mapped[int] = mapped_column(Integer, default=0)
    total_cost_estimate: Mapped[Decimal] = mapped_column(Numeric(12, 6), default=0)
    total_duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    total_input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_llm_calls: Mapped[int] = mapped_column(Integer, default=0)
    total_output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tool_calls: Mapped[int] = mapped_column(Integer, default=0)
    turn_index: Mapped[int]
    user_message: Mapped[str]


class EntryRelation(Base):
    __tablename__ = "entry_relation"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    created_at: Mapped[datetime]
    entry_a_id: Mapped[str]
    entry_b_id: Mapped[str]
    last_observed_at: Mapped[datetime]
    note: Mapped[str] = mapped_column(String, default="")
    observation_count: Mapped[int] = mapped_column(Integer, default=0)
    source_kind: Mapped[str]
    vetted: Mapped[bool | None]
    vetted_at: Mapped[datetime | None]
    vetted_observation_count: Mapped[int | None]
    vetted_reason: Mapped[str | None]


class EntryTag(Base):
    __tablename__ = "entry_tag"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    created_at: Mapped[datetime]
    entry_id: Mapped[str]
    last_reaffirmed_at: Mapped[datetime | None]
    reaffirm_count: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str]
    tag_id: Mapped[str]


class File(Base):
    __tablename__ = "file"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    deleted_at: Mapped[datetime | None]
    description: Mapped[Any | None] = mapped_column(JSON)
    extra: Mapped[str | None]
    ingest_status: Mapped[str]
    ingested_at: Mapped[datetime | None]
    kind: Mapped[str | None]
    mime_type: Mapped[str | None]
    original_ext: Mapped[str | None]
    sha256: Mapped[str]
    size_bytes: Mapped[int] = mapped_column(Integer)
    storage_key: Mapped[str]
    summary: Mapped[str | None]


class FileEntry(Base):
    __tablename__ = "file_entry"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    catalog_id: Mapped[str | None]
    deleted_at: Mapped[datetime | None]
    display_name: Mapped[str]
    extra: Mapped[str | None]
    file_id: Mapped[str] = mapped_column(ForeignKey("file.id"))
    folder_id: Mapped[str | None] = mapped_column(ForeignKey("folder.id"), nullable=True)
    lifecycle: Mapped[str]
    purge_after: Mapped[datetime | None]


class Folder(Base):
    __tablename__ = "folder"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    deleted_at: Mapped[datetime | None]
    name: Mapped[str]
    parent_id: Mapped[str | None] = mapped_column(
        ForeignKey("folder.id"), nullable=True
    )


class Journal(Base):
    __tablename__ = "journal"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    conversation_id: Mapped[str]
    created_at: Mapped[datetime]
    entry_ids: Mapped[Any] = mapped_column(JSON)
    invalidated_at: Mapped[datetime | None]
    invalidated_by_id: Mapped[str | None]
    invalidated_reason: Mapped[str | None]
    note: Mapped[str] = mapped_column(String, default="")
    source_kind: Mapped[str]
    summarized_journal_ids: Mapped[Any | None] = mapped_column(JSON)
    superseded_by_id: Mapped[str | None]
    tags: Mapped[Any] = mapped_column(JSON)


class Session(Base):
    __tablename__ = "session"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    deleted_at: Mapped[datetime | None]
    end_reason: Mapped[str | None]
    ended_at: Mapped[datetime | None]
    initiating_user_message: Mapped[str]
    started_at: Mapped[datetime]
    total_cache_read: Mapped[int] = mapped_column(Integer, default=0)
    total_cost_estimate: Mapped[Decimal] = mapped_column(Numeric(12, 6), default=0)
    total_duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    total_input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_llm_calls: Mapped[int] = mapped_column(Integer, default=0)
    total_output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tool_calls: Mapped[int] = mapped_column(Integer, default=0)
    turn_count: Mapped[int] = mapped_column(Integer, default=0)


class Tag(Base):
    __tablename__ = "tag"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    alias_of: Mapped[str | None]
    doc_count: Mapped[int] = mapped_column(Integer, default=0)
    facet: Mapped[str]
    last_reaffirmed_at: Mapped[datetime | None]
    last_used_at: Mapped[datetime | None]
    name: Mapped[str]
    reaffirm_count: Mapped[int] = mapped_column(Integer, default=0)


class TagAlias(Base):
    __tablename__ = "tag_alias"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    created_at: Mapped[datetime]
    from_name: Mapped[str]
    note: Mapped[str | None]
    to_tag_id: Mapped[str] = mapped_column(ForeignKey("tag.id"))


class Task(Base):
    __tablename__ = "task"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime]
    dedup_key: Mapped[str | None]
    finished_at: Mapped[datetime | None]
    kind: Mapped[str]
    last_error: Mapped[str | None]
    last_heartbeat_at: Mapped[datetime | None]
    lease_expires_at: Mapped[datetime | None]
    locked_by: Mapped[str | None]
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    payload: Mapped[Any] = mapped_column(JSON)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    scheduled_at: Mapped[datetime]
    started_at: Mapped[datetime | None]
    status: Mapped[str]


class TaskOutcome(Base):
    __tablename__ = "task_outcome"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    completed_at: Mapped[datetime]
    detail: Mapped[Any | None] = mapped_column(JSON)
    object_id: Mapped[str]
    object_kind: Mapped[str]
    outcome: Mapped[str]
    task_kind: Mapped[str]
    task_run_id: Mapped[str | None]


class View(Base):
    __tablename__ = "view"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    deleted_at: Mapped[datetime | None]
    description: Mapped[Any | None] = mapped_column(JSON)
    extra: Mapped[str | None]
    filter_spec: Mapped[Any] = mapped_column(JSON)
    name: Mapped[str]
    summary: Mapped[str | None]
    tags: Mapped[Any | None] = mapped_column(JSON)