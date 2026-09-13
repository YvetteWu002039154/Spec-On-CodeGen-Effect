from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, DateTime, Dialect, MetaData, Numeric, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator


# ---------- base ----------

class UtcDateTime(TypeDecorator[datetime]):
    """Stores and retrieves naïve datetime values in UTC."""
    impl = DateTime(timezone=False)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is not None:
            if value.tzinfo is None:
                # Assume local is UTC; no conversion needed
                return value
            # Convert to UTC and strip timezone info
            return value.astimezone(timezone.utc).replace(tzinfo=None)
        return value

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is not None:
            # The stored value has no timezone; treat as UTC
            return value.replace(tzinfo=timezone.utc)
        return value


class Base(DeclarativeBase):
    metadata = MetaData()
    type_annotation_map: dict[Any, Any] = {
        datetime: UtcDateTime,
    }


class IdMixin:
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: uuid.uuid4().hex
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime, default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime, default=func.now(), onupdate=func.now()
    )


# ---------- audit ----------

class AuditEvent(Base, IdMixin, TimestampMixin):
    __tablename__ = "audit_event"

    conversation_id: Mapped[str | None] = mapped_column(String, nullable=True)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(UtcDateTime, default=func.now())
    payload: Mapped[Any] = mapped_column(JSON, nullable=False)
    session_id: Mapped[str | None] = mapped_column(String, nullable=True)
    task_id: Mapped[str | None] = mapped_column(String, nullable=True)


class Conversation(Base, IdMixin, TimestampMixin):
    __tablename__ = "conversation"

    agent_response: Mapped[str | None] = mapped_column(String, nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    llm_calls: Mapped[Any] = mapped_column(JSON, nullable=False)
    session_id: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[datetime] = mapped_column(UtcDateTime, default=func.now())
    tool_calls: Mapped[Any] = mapped_column(JSON, nullable=False)
    total_cache_read: Mapped[int] = mapped_column(nullable=False)
    total_cost_estimate: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    total_duration_ms: Mapped[int] = mapped_column(nullable=False)
    total_input_tokens: Mapped[int] = mapped_column(nullable=False)
    total_llm_calls: Mapped[int] = mapped_column(nullable=False)
    total_output_tokens: Mapped[int] = mapped_column(nullable=False)
    total_tool_calls: Mapped[int] = mapped_column(nullable=False)
    turn_index: Mapped[int] = mapped_column(nullable=False)
    user_message: Mapped[str] = mapped_column(String, nullable=False)


class Session(Base, IdMixin, TimestampMixin):
    __tablename__ = "session"

    deleted_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    end_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    initiating_user_message: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[datetime] = mapped_column(UtcDateTime, default=func.now())
    total_cache_read: Mapped[int] = mapped_column(nullable=False)
    total_cost_estimate: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    total_duration_ms: Mapped[int] = mapped_column(nullable=False)
    total_input_tokens: Mapped[int] = mapped_column(nullable=False)
    total_llm_calls: Mapped[int] = mapped_column(nullable=False)
    total_output_tokens: Mapped[int] = mapped_column(nullable=False)
    total_tool_calls: Mapped[int] = mapped_column(nullable=False)
    turn_count: Mapped[int] = mapped_column(nullable=False)


# ---------- ai_structural ----------

class Catalog(Base, IdMixin, TimestampMixin):
    __tablename__ = "catalog"

    deleted_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    description: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    extra: Mapped[str | None] = mapped_column(String, nullable=True)
    is_system: Mapped[bool] = mapped_column(nullable=False, default=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    parent_id: Mapped[str | None] = mapped_column(String, nullable=True)
    summary: Mapped[str | None] = mapped_column(String, nullable=True)
    tags: Mapped[Any | None] = mapped_column(JSON, nullable=True)


class Tag(Base, IdMixin, TimestampMixin):
    __tablename__ = "tag"

    alias_of: Mapped[str | None] = mapped_column(String, nullable=True)
    doc_count: Mapped[int] = mapped_column(nullable=False, default=0)
    facet: Mapped[str] = mapped_column(String, nullable=False)
    last_reaffirmed_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    reaffirm_count: Mapped[int] = mapped_column(nullable=False, default=0)


class TagAlias(Base, IdMixin, TimestampMixin):
    __tablename__ = "tag_alias"

    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=func.now())
    from_name: Mapped[str] = mapped_column(String, nullable=False)
    note: Mapped[str | None] = mapped_column(String, nullable=True)
    to_tag_id: Mapped[str] = mapped_column(String, nullable=False)


class EntryTag(Base, IdMixin, TimestampMixin):
    __tablename__ = "entry_tag"

    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=func.now())
    entry_id: Mapped[str] = mapped_column(String, nullable=False)
    last_reaffirmed_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    reaffirm_count: Mapped[int] = mapped_column(nullable=False, default=0)
    source: Mapped[str] = mapped_column(String, nullable=False)
    tag_id: Mapped[str] = mapped_column(String, nullable=False)


class View(Base, IdMixin, TimestampMixin):
    __tablename__ = "view"

    deleted_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    description: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    extra: Mapped[str | None] = mapped_column(String, nullable=True)
    filter_spec: Mapped[Any] = mapped_column(JSON, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    summary: Mapped[str | None] = mapped_column(String, nullable=True)
    tags: Mapped[Any | None] = mapped_column(JSON, nullable=True)


# ---------- ai_recall ----------

class EntryRelation(Base, IdMixin, TimestampMixin):
    __tablename__ = "entry_relation"

    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=func.now())
    entry_a_id: Mapped[str] = mapped_column(String, nullable=False)
    entry_b_id: Mapped[str] = mapped_column(String, nullable=False)
    last_observed_at: Mapped[datetime] = mapped_column(UtcDateTime, default=func.now())
    note: Mapped[str] = mapped_column(String, nullable=False)
    observation_count: Mapped[int] = mapped_column(nullable=False, default=1)
    source_kind: Mapped[str] = mapped_column(String, nullable=False)
    vetted: Mapped[bool | None] = mapped_column(nullable=True)
    vetted_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    vetted_observation_count: Mapped[int | None] = mapped_column(nullable=True)
    vetted_reason: Mapped[str | None] = mapped_column(String, nullable=True)


class Journal(Base, IdMixin, TimestampMixin):
    __tablename__ = "journal"

    conversation_id: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=func.now())
    entry_ids: Mapped[Any] = mapped_column(JSON, nullable=False)
    invalidated_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    invalidated_by_id: Mapped[str | None] = mapped_column(String, nullable=True)
    invalidated_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    note: Mapped[str] = mapped_column(String, nullable=False)
    source_kind: Mapped[str] = mapped_column(String, nullable=False)
    summarized_journal_ids: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    superseded_by_id: Mapped[str | None] = mapped_column(String, nullable=True)
    tags: Mapped[Any] = mapped_column(JSON, nullable=False)


# ---------- user_visible ----------

class File(Base, IdMixin, TimestampMixin):
    __tablename__ = "file"

    deleted_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    description: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    extra: Mapped[str | None] = mapped_column(String, nullable=True)
    ingest_status: Mapped[str] = mapped_column(String, nullable=False)
    ingested_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    kind: Mapped[str | None] = mapped_column(String, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String, nullable=True)
    original_ext: Mapped[str | None] = mapped_column(String, nullable=True)
    sha256: Mapped[str] = mapped_column(String, nullable=False)
    size_bytes: Mapped[int] = mapped_column(nullable=False)
    storage_key: Mapped[str] = mapped_column(String, nullable=False)
    summary: Mapped[str | None] = mapped_column(String, nullable=True)


class FileEntry(Base, IdMixin, TimestampMixin):
    __tablename__ = "file_entry"

    catalog_id: Mapped[str | None] = mapped_column(String, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    extra: Mapped[str | None] = mapped_column(String, nullable=True)
    file_id: Mapped[str] = mapped_column(String, nullable=False)
    folder_id: Mapped[str | None] = mapped_column(String, nullable=True)
    lifecycle: Mapped[str] = mapped_column(String, nullable=False)
    purge_after: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)


class Folder(Base, IdMixin, TimestampMixin):
    __tablename__ = "folder"

    deleted_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    parent_id: Mapped[str | None] = mapped_column(String, nullable=True)


# ---------- tasks ----------

class Task(Base, IdMixin, TimestampMixin):
    __tablename__ = "task"

    attempts: Mapped[int] = mapped_column(nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=func.now())
    dedup_key: Mapped[str | None] = mapped_column(String, nullable=True, unique=True)
    finished_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    last_error: Mapped[str | None] = mapped_column(String, nullable=True)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    locked_by: Mapped[str | None] = mapped_column(String, nullable=True)
    max_attempts: Mapped[int] = mapped_column(nullable=False)
    payload: Mapped[Any] = mapped_column(JSON, nullable=False)
    priority: Mapped[int] = mapped_column(nullable=False, default=0)
    scheduled_at: Mapped[datetime] = mapped_column(UtcDateTime, default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")


# ---------- task_outcomes ----------

class TaskOutcome(Base, IdMixin, TimestampMixin):
    __tablename__ = "task_outcome"

    completed_at: Mapped[datetime] = mapped_column(UtcDateTime, default=func.now())
    detail: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    object_id: Mapped[str] = mapped_column(String, nullable=False)
    object_kind: Mapped[str] = mapped_column(String, nullable=False)
    outcome: Mapped[str] = mapped_column(String, nullable=False)
    task_kind: Mapped[str] = mapped_column(String, nullable=False)
    task_run_id: Mapped[str | None] = mapped_column(String, nullable=True)