from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, MetaData, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator


# ---------------------------------------------------------------------------
# src/marginalia/db/models/base.py
# ---------------------------------------------------------------------------

class UtcDateTime(TypeDecorator):
    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            if isinstance(value, datetime.datetime):
                if value.tzinfo is None:
                    value = value.replace(tzinfo=datetime.timezone.utc)
                return value.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            if isinstance(value, datetime.datetime):
                return value.replace(tzinfo=datetime.timezone.utc)
        return value


class Base(DeclarativeBase):
    metadata = MetaData()
    type_annotation_map: dict[Any, Any] = {
        datetime.datetime: UtcDateTime,
        Decimal: String,
    }


class IdMixin:
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: __import__('uuid').uuid4().hex)


class TimestampMixin:
    created_at: Mapped[datetime.datetime] = mapped_column(
        UtcDateTime, nullable=False, default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        UtcDateTime, nullable=False,
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc),
    )


# ---------------------------------------------------------------------------
# src/marginalia/db/models/audit.py
# ---------------------------------------------------------------------------

class AuditEvent(IdMixin, Base):
    __tablename__ = "audit_events"

    kind: Mapped[str] = mapped_column(String, nullable=False)
    occurred_at: Mapped[datetime.datetime] = mapped_column(UtcDateTime, nullable=False)
    payload: Mapped[Any] = mapped_column(__import__('sqlalchemy').JSON, nullable=False)
    conversation_id: Mapped[str | None] = mapped_column(String, nullable=True)
    session_id: Mapped[str | None] = mapped_column(String, nullable=True)
    task_id: Mapped[str | None] = mapped_column(String, nullable=True)


class Conversation(IdMixin, Base):
    __tablename__ = "conversations"

    session_id: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[datetime.datetime] = mapped_column(UtcDateTime, nullable=False)
    ended_at: Mapped[datetime.datetime | None] = mapped_column(UtcDateTime, nullable=True)
    user_message: Mapped[str] = mapped_column(String, nullable=False)
    agent_response: Mapped[str | None] = mapped_column(String, nullable=True)
    turn_index: Mapped[int] = mapped_column(__import__('sqlalchemy').Integer, nullable=False, default=0)
    total_llm_calls: Mapped[int] = mapped_column(__import__('sqlalchemy').Integer, nullable=False, default=0)
    total_tool_calls: Mapped[int] = mapped_column(__import__('sqlalchemy').Integer, nullable=False, default=0)
    total_input_tokens: Mapped[int] = mapped_column(__import__('sqlalchemy').Integer, nullable=False, default=0)
    total_output_tokens: Mapped[int] = mapped_column(__import__('sqlalchemy').Integer, nullable=False, default=0)
    total_cache_read: Mapped[int] = mapped_column(__import__('sqlalchemy').Integer, nullable=False, default=0)
    total_duration_ms: Mapped[int] = mapped_column(__import__('sqlalchemy').Integer, nullable=False, default=0)
    total_cost_estimate: Mapped[Decimal] = mapped_column(String, nullable=False, default="0")
    llm_calls: Mapped[Any] = mapped_column(__import__('sqlalchemy').JSON, nullable=False, default=list)
    tool_calls: Mapped[Any] = mapped_column(__import__('sqlalchemy').JSON, nullable=False, default=list)


class Session(IdMixin, Base):
    __tablename__ = "sessions"

    started_at: Mapped[datetime.datetime] = mapped_column(UtcDateTime, nullable=False)
    ended_at: Mapped[datetime.datetime | None] = mapped_column(UtcDateTime, nullable=True)
    deleted_at: Mapped[datetime.datetime | None] = mapped_column(UtcDateTime, nullable=True)
    initiating_user_message: Mapped[str] = mapped_column(String, nullable=False)
    end_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    turn_count: Mapped[int] = mapped_column(__import__('sqlalchemy').Integer, nullable=False, default=0)
    total_llm_calls: Mapped[int] = mapped_column(__import__('sqlalchemy').Integer, nullable=False, default=0)
    total_tool_calls: Mapped[int] = mapped_column(__import__('sqlalchemy').Integer, nullable=False, default=0)
    total_input_tokens: Mapped[int] = mapped_column(__import__('sqlalchemy').Integer, nullable=False, default=0)
    total_output_tokens: Mapped[int] = mapped_column(__import__('sqlalchemy').Integer, nullable=False, default=0)
    total_cache_read: Mapped[int] = mapped_column(__import__('sqlalchemy').Integer, nullable=False, default=0)
    total_duration_ms: Mapped[int] = mapped_column(__import__('sqlalchemy').Integer, nullable=False, default=0)
    total_cost_estimate: Mapped[Decimal] = mapped_column(String, nullable=False, default="0")


# ---------------------------------------------------------------------------
# src/marginalia/db/models/ai_structural.py
# ---------------------------------------------------------------------------

import sqlalchemy as sa


class Catalog(IdMixin, Base):
    __tablename__ = "catalogs"

    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Any | None] = mapped_column(sa.JSON, nullable=True)
    summary: Mapped[str | None] = mapped_column(String, nullable=True)
    extra: Mapped[str | None] = mapped_column(String, nullable=True)
    tags: Mapped[Any | None] = mapped_column(sa.JSON, nullable=True)
    parent_id: Mapped[str | None] = mapped_column(String, nullable=True)
    is_system: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime.datetime | None] = mapped_column(UtcDateTime, nullable=True)


class Tag(IdMixin, Base):
    __tablename__ = "tags"

    name: Mapped[str] = mapped_column(String, nullable=False)
    facet: Mapped[str] = mapped_column(String, nullable=False)
    alias_of: Mapped[str | None] = mapped_column(String, nullable=True)
    doc_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    reaffirm_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    last_used_at: Mapped[datetime.datetime | None] = mapped_column(UtcDateTime, nullable=True)
    last_reaffirmed_at: Mapped[datetime.datetime | None] = mapped_column(UtcDateTime, nullable=True)


class TagAlias(IdMixin, Base):
    __tablename__ = "tag_aliases"

    from_name: Mapped[str] = mapped_column(String, nullable=False)
    to_tag_id: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(UtcDateTime, nullable=False)
    note: Mapped[str | None] = mapped_column(String, nullable=True)


class EntryTag(IdMixin, Base):
    __tablename__ = "entry_tags"

    entry_id: Mapped[str] = mapped_column(String, nullable=False)
    tag_id: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(UtcDateTime, nullable=False)
    last_reaffirmed_at: Mapped[datetime.datetime | None] = mapped_column(UtcDateTime, nullable=True)
    reaffirm_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)


class View(IdMixin, Base):
    __tablename__ = "views"

    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Any | None] = mapped_column(sa.JSON, nullable=True)
    summary: Mapped[str | None] = mapped_column(String, nullable=True)
    extra: Mapped[str | None] = mapped_column(String, nullable=True)
    tags: Mapped[Any | None] = mapped_column(sa.JSON, nullable=True)
    filter_spec: Mapped[Any] = mapped_column(sa.JSON, nullable=False)
    deleted_at: Mapped[datetime.datetime | None] = mapped_column(UtcDateTime, nullable=True)


# ---------------------------------------------------------------------------
# src/marginalia/db/models/ai_recall.py
# ---------------------------------------------------------------------------

class Journal(IdMixin, Base):
    __tablename__ = "journals"

    conversation_id: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(UtcDateTime, nullable=False)
    source_kind: Mapped[str] = mapped_column(String, nullable=False)
    note: Mapped[str] = mapped_column(String, nullable=False)
    entry_ids: Mapped[Any] = mapped_column(sa.JSON, nullable=False, default=list)
    tags: Mapped[Any] = mapped_column(sa.JSON, nullable=False, default=list)
    summarized_journal_ids: Mapped[Any | None] = mapped_column(sa.JSON, nullable=True)
    superseded_by_id: Mapped[str | None] = mapped_column(String, nullable=True)
    invalidated_at: Mapped[datetime.datetime | None] = mapped_column(UtcDateTime, nullable=True)
    invalidated_by_id: Mapped[str | None] = mapped_column(String, nullable=True)
    invalidated_reason: Mapped[str | None] = mapped_column(String, nullable=True)


class EntryRelation(IdMixin, Base):
    __tablename__ = "entry_relations"

    entry_a_id: Mapped[str] = mapped_column(String, nullable=False)
    entry_b_id: Mapped[str] = mapped_column(String, nullable=False)
    source_kind: Mapped[str] = mapped_column(String, nullable=False)
    note: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(UtcDateTime, nullable=False)
    last_observed_at: Mapped[datetime.datetime] = mapped_column(UtcDateTime, nullable=False)
    observation_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=1)
    vetted: Mapped[bool | None] = mapped_column(sa.Boolean, nullable=True)
    vetted_at: Mapped[datetime.datetime | None] = mapped_column(UtcDateTime, nullable=True)
    vetted_observation_count: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    vetted_reason: Mapped[str | None] = mapped_column(String, nullable=True)


# ---------------------------------------------------------------------------
# src/marginalia/db/models/user_visible.py
# ---------------------------------------------------------------------------

class File(IdMixin, Base):
    __tablename__ = "files"

    sha256: Mapped[str] = mapped_column(String, nullable=False)
    storage_key: Mapped[str] = mapped_column(String, nullable=False)
    size_bytes: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String, nullable=True)
    original_ext: Mapped[str | None] = mapped_column(String, nullable=True)
    kind: Mapped[str | None] = mapped_column(String, nullable=True)
    ingest_status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    ingested_at: Mapped[datetime.datetime | None] = mapped_column(UtcDateTime, nullable=True)
    description: Mapped[Any | None] = mapped_column(sa.JSON, nullable=True)
    summary: Mapped[str | None] = mapped_column(String, nullable=True)
    extra: Mapped[str | None] = mapped_column(String, nullable=True)
    deleted_at: Mapped[datetime.datetime | None] = mapped_column(UtcDateTime, nullable=True)


class Folder(IdMixin, Base):
    __tablename__ = "folders"

    name: Mapped[str] = mapped_column(String, nullable=False)
    parent_id: Mapped[str | None] = mapped_column(String, nullable=True)
    deleted_at: Mapped[datetime.datetime | None] = mapped_column(UtcDateTime, nullable=True)


class FileEntry(IdMixin, Base):
    __tablename__ = "file_entries"

    file_id: Mapped[str] = mapped_column(String, nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    folder_id: Mapped[str | None] = mapped_column(String, nullable=True)
    catalog_id: Mapped[str | None] = mapped_column(String, nullable=True)
    lifecycle: Mapped[str] = mapped_column(String, nullable=False, default="active")
    purge_after: Mapped[datetime.datetime | None] = mapped_column(UtcDateTime, nullable=True)
    extra: Mapped[str | None] = mapped_column(String, nullable=True)
    deleted_at: Mapped[datetime.datetime | None] = mapped_column(UtcDateTime, nullable=True)


# ---------------------------------------------------------------------------
# src/marginalia/db/models/tasks.py
# ---------------------------------------------------------------------------

class Task(IdMixin, Base):
    __tablename__ = "tasks"

    kind: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    priority: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    payload: Mapped[Any] = mapped_column(sa.JSON, nullable=False)
    attempts: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=3)
    created_at: Mapped[datetime.datetime] = mapped_column(UtcDateTime, nullable=False)
    scheduled_at: Mapped[datetime.datetime] = mapped_column(UtcDateTime, nullable=False)
    started_at: Mapped[datetime.datetime | None] = mapped_column(UtcDateTime, nullable=True)
    finished_at: Mapped[datetime.datetime | None] = mapped_column(UtcDateTime, nullable=True)
    last_heartbeat_at: Mapped[datetime.datetime | None] = mapped_column(UtcDateTime, nullable=True)
    lease_expires_at: Mapped[datetime.datetime | None] = mapped_column(UtcDateTime, nullable=True)
    locked_by: Mapped[str | None] = mapped_column(String, nullable=True)
    last_error: Mapped[str | None] = mapped_column(String, nullable=True)
    dedup_key: Mapped[str | None] = mapped_column(String, nullable=True)


# ---------------------------------------------------------------------------
# src/marginalia/db/models/task_outcomes.py
# ---------------------------------------------------------------------------

class TaskOutcome(IdMixin, Base):
    __tablename__ = "task_outcomes"

    task_kind: Mapped[str] = mapped_column(String, nullable=False)
    task_run_id: Mapped[str | None] = mapped_column(String, nullable=True)
    object_kind: Mapped[str] = mapped_column(String, nullable=False)
    object_id: Mapped[str] = mapped_column(String, nullable=False)
    outcome: Mapped[str] = mapped_column(String, nullable=False)
    completed_at: Mapped[datetime.datetime] = mapped_column(UtcDateTime, nullable=False)
    detail: Mapped[Any | None] = mapped_column(sa.JSON, nullable=True)