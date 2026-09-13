from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    JSON,
    MetaData,
    Numeric,
    String,
    Text,
    TypeDecorator,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class UtcDateTime(TypeDecorator):
    """Custom type that stores all datetimes in UTC and returns them with UTC timezone."""

    cache_ok = True
    impl = DateTime(timezone=True)

    def process_bind_param(self, value: datetime | None, dialect: Any) -> datetime | None:
        if value is not None:
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            else:
                value = value.astimezone(timezone.utc)
        return value

    def process_result_value(self, value: datetime | None, dialect: Any) -> datetime | None:
        if value is not None:
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            else:
                value = value.astimezone(timezone.utc)
        return value


class Base(DeclarativeBase):
    metadata = MetaData()
    type_annotation_map: dict[Any, Any] = {}


def _new_uuid() -> str:
    return str(uuid.uuid4())


class IdMixin:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Audit models
# ---------------------------------------------------------------------------

class AuditEvent(IdMixin, Base):
    __tablename__ = "audit_event"

    conversation_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    kind: Mapped[str] = mapped_column(String)
    occurred_at: Mapped[datetime] = mapped_column(UtcDateTime)
    payload: Mapped[Any] = mapped_column(JSON)
    session_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    task_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class Conversation(IdMixin, Base):
    __tablename__ = "conversation"

    agent_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    llm_calls: Mapped[Any] = mapped_column(JSON)
    session_id: Mapped[str] = mapped_column(String(36))
    started_at: Mapped[datetime] = mapped_column(UtcDateTime)
    tool_calls: Mapped[Any] = mapped_column(JSON)
    total_cache_read: Mapped[int] = mapped_column(Integer)
    total_cost_estimate: Mapped[Decimal] = mapped_column(Numeric)
    total_duration_ms: Mapped[int] = mapped_column(Integer)
    total_input_tokens: Mapped[int] = mapped_column(Integer)
    total_llm_calls: Mapped[int] = mapped_column(Integer)
    total_output_tokens: Mapped[int] = mapped_column(Integer)
    total_tool_calls: Mapped[int] = mapped_column(Integer)
    turn_index: Mapped[int] = mapped_column(Integer)
    user_message: Mapped[str] = mapped_column(Text)


class Session(IdMixin, Base):
    __tablename__ = "session"

    deleted_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    end_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    initiating_user_message: Mapped[str] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(UtcDateTime)
    total_cache_read: Mapped[int] = mapped_column(Integer)
    total_cost_estimate: Mapped[Decimal] = mapped_column(Numeric)
    total_duration_ms: Mapped[int] = mapped_column(Integer)
    total_input_tokens: Mapped[int] = mapped_column(Integer)
    total_llm_calls: Mapped[int] = mapped_column(Integer)
    total_output_tokens: Mapped[int] = mapped_column(Integer)
    total_tool_calls: Mapped[int] = mapped_column(Integer)
    turn_count: Mapped[int] = mapped_column(Integer)


# ---------------------------------------------------------------------------
# AI structural models
# ---------------------------------------------------------------------------

class Catalog(IdMixin, Base):
    __tablename__ = "catalog"

    deleted_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    description: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    extra: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    name: Mapped[str] = mapped_column(String)
    parent_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[Any | None] = mapped_column(JSON, nullable=True)


class Tag(IdMixin, Base):
    __tablename__ = "tag"

    alias_of: Mapped[str | None] = mapped_column(String(36), nullable=True)
    doc_count: Mapped[int] = mapped_column(Integer, default=0)
    facet: Mapped[str] = mapped_column(String)
    last_reaffirmed_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    reaffirm_count: Mapped[int] = mapped_column(Integer, default=0)


class TagAlias(IdMixin, Base):
    __tablename__ = "tag_alias"

    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime, default=lambda: datetime.now(timezone.utc)
    )
    from_name: Mapped[str] = mapped_column(String)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    to_tag_id: Mapped[str] = mapped_column(String(36))


class EntryTag(Base):
    __tablename__ = "entry_tag"

    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime, default=lambda: datetime.now(timezone.utc)
    )
    entry_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    last_reaffirmed_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    reaffirm_count: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String)
    tag_id: Mapped[str] = mapped_column(String(36), primary_key=True)


class View(IdMixin, Base):
    __tablename__ = "view"

    deleted_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    description: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    extra: Mapped[str | None] = mapped_column(Text, nullable=True)
    filter_spec: Mapped[Any] = mapped_column(JSON)
    name: Mapped[str] = mapped_column(String)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[Any | None] = mapped_column(JSON, nullable=True)


# ---------------------------------------------------------------------------
# AI recall models
# ---------------------------------------------------------------------------

class Journal(IdMixin, Base):
    __tablename__ = "journal"

    conversation_id: Mapped[str] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime, default=lambda: datetime.now(timezone.utc)
    )
    entry_ids: Mapped[Any] = mapped_column(JSON)
    invalidated_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    invalidated_by_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    invalidated_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    note: Mapped[str] = mapped_column(Text)
    source_kind: Mapped[str] = mapped_column(String)
    summarized_journal_ids: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    superseded_by_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    tags: Mapped[Any] = mapped_column(JSON)


class EntryRelation(Base):
    __tablename__ = "entry_relation"

    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime, default=lambda: datetime.now(timezone.utc)
    )
    entry_a_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    entry_b_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    last_observed_at: Mapped[datetime] = mapped_column(UtcDateTime)
    note: Mapped[str] = mapped_column(Text)
    observation_count: Mapped[int] = mapped_column(Integer, default=0)
    source_kind: Mapped[str] = mapped_column(String)
    vetted: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    vetted_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    vetted_observation_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    vetted_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


# ---------------------------------------------------------------------------
# User visible models
# ---------------------------------------------------------------------------

class File(IdMixin, Base):
    __tablename__ = "file"

    deleted_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    description: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    extra: Mapped[str | None] = mapped_column(Text, nullable=True)
    ingest_status: Mapped[str] = mapped_column(String)
    ingested_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    kind: Mapped[str | None] = mapped_column(String, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String, nullable=True)
    original_ext: Mapped[str | None] = mapped_column(String, nullable=True)
    sha256: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(Integer)
    storage_key: Mapped[str] = mapped_column(String)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)


class FileEntry(IdMixin, Base):
    __tablename__ = "file_entry"

    catalog_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    display_name: Mapped[str] = mapped_column(String)
    extra: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_id: Mapped[str] = mapped_column(String(36))
    folder_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    lifecycle: Mapped[str] = mapped_column(String)
    purge_after: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)


class Folder(IdMixin, Base):
    __tablename__ = "folder"

    deleted_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    name: Mapped[str] = mapped_column(String)
    parent_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


# ---------------------------------------------------------------------------
# Task models
# ---------------------------------------------------------------------------

class Task(IdMixin, Base):
    __tablename__ = "task"

    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime, default=lambda: datetime.now(timezone.utc)
    )
    dedup_key: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    kind: Mapped[str] = mapped_column(String)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    locked_by: Mapped[str | None] = mapped_column(String, nullable=True)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    payload: Mapped[Any] = mapped_column(JSON)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    scheduled_at: Mapped[datetime] = mapped_column(UtcDateTime)
    started_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    status: Mapped[str] = mapped_column(String)


class TaskOutcome(IdMixin, Base):
    __tablename__ = "task_outcome"

    completed_at: Mapped[datetime] = mapped_column(UtcDateTime)
    detail: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    object_id: Mapped[str] = mapped_column(String(36))
    object_kind: Mapped[str] = mapped_column(String)
    outcome: Mapped[str] = mapped_column(String)
    task_kind: Mapped[str] = mapped_column(String)
    task_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)