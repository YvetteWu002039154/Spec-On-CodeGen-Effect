from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, MetaData, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator


# ─────────────────────────────────────────────
# src/marginalia/db/models/base.py
# ─────────────────────────────────────────────

class UtcDateTime(TypeDecorator):
    """Stores datetimes as UTC in the database."""

    impl = DateTime
    cache_ok: bool = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, datetime):
            if value.tzinfo is not None:
                value = value.astimezone(timezone.utc).replace(tzinfo=None)
            return value
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.replace(tzinfo=timezone.utc)
        return value


class Base(DeclarativeBase):
    metadata: MetaData = MetaData()
    type_annotation_map: dict[Any, Any] = {
        datetime: UtcDateTime,
        Decimal: String,
    }


class IdMixin:
    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


# ─────────────────────────────────────────────
# src/marginalia/db/models/audit.py
# ─────────────────────────────────────────────

from sqlalchemy import JSON, Numeric, Text
from sqlalchemy.orm import mapped_column, Mapped


class AuditEvent(IdMixin, Base):
    __tablename__ = "audit_events"

    kind: Mapped[str] = mapped_column(String, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    payload: Mapped[Any] = mapped_column(JSON, nullable=True)
    session_id: Mapped[str | None] = mapped_column(String, nullable=True)
    conversation_id: Mapped[str | None] = mapped_column(String, nullable=True)
    task_id: Mapped[str | None] = mapped_column(String, nullable=True)


class Session(IdMixin, Base):
    __tablename__ = "sessions"

    started_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    end_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    initiating_user_message: Mapped[str] = mapped_column(Text, nullable=False)
    turn_count: Mapped[int] = mapped_column(default=0, nullable=False)
    total_llm_calls: Mapped[int] = mapped_column(default=0, nullable=False)
    total_tool_calls: Mapped[int] = mapped_column(default=0, nullable=False)
    total_input_tokens: Mapped[int] = mapped_column(default=0, nullable=False)
    total_output_tokens: Mapped[int] = mapped_column(default=0, nullable=False)
    total_cache_read: Mapped[int] = mapped_column(default=0, nullable=False)
    total_duration_ms: Mapped[int] = mapped_column(default=0, nullable=False)
    total_cost_estimate: Mapped[Decimal] = mapped_column(
        Numeric(precision=18, scale=8), default=Decimal("0"), nullable=False
    )


class Conversation(IdMixin, Base):
    __tablename__ = "conversations"

    session_id: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    turn_index: Mapped[int] = mapped_column(default=0, nullable=False)
    user_message: Mapped[str] = mapped_column(Text, nullable=False)
    agent_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    llm_calls: Mapped[Any] = mapped_column(JSON, nullable=True)
    tool_calls: Mapped[Any] = mapped_column(JSON, nullable=True)
    total_llm_calls: Mapped[int] = mapped_column(default=0, nullable=False)
    total_tool_calls: Mapped[int] = mapped_column(default=0, nullable=False)
    total_input_tokens: Mapped[int] = mapped_column(default=0, nullable=False)
    total_output_tokens: Mapped[int] = mapped_column(default=0, nullable=False)
    total_cache_read: Mapped[int] = mapped_column(default=0, nullable=False)
    total_duration_ms: Mapped[int] = mapped_column(default=0, nullable=False)
    total_cost_estimate: Mapped[Decimal] = mapped_column(
        Numeric(precision=18, scale=8), default=Decimal("0"), nullable=False
    )


# ─────────────────────────────────────────────
# src/marginalia/db/models/ai_structural.py
# ─────────────────────────────────────────────


class Catalog(IdMixin, TimestampMixin, Base):
    __tablename__ = "catalogs"

    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    parent_id: Mapped[str | None] = mapped_column(String, nullable=True)
    is_system: Mapped[bool] = mapped_column(default=False, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)


class Tag(IdMixin, TimestampMixin, Base):
    __tablename__ = "tags"

    name: Mapped[str] = mapped_column(String, nullable=False)
    facet: Mapped[str] = mapped_column(String, nullable=False)
    alias_of: Mapped[str | None] = mapped_column(String, nullable=True)
    doc_count: Mapped[int] = mapped_column(default=0, nullable=False)
    reaffirm_count: Mapped[int] = mapped_column(default=0, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    last_reaffirmed_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)


class TagAlias(IdMixin, Base):
    __tablename__ = "tag_aliases"

    from_name: Mapped[str] = mapped_column(String, nullable=False)
    to_tag_id: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


class EntryTag(IdMixin, Base):
    __tablename__ = "entry_tags"

    entry_id: Mapped[str] = mapped_column(String, nullable=False)
    tag_id: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    reaffirm_count: Mapped[int] = mapped_column(default=0, nullable=False)
    last_reaffirmed_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)


class View(IdMixin, TimestampMixin, Base):
    __tablename__ = "views"

    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    filter_spec: Mapped[Any] = mapped_column(JSON, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)


# ─────────────────────────────────────────────
# src/marginalia/db/models/ai_recall.py
# ─────────────────────────────────────────────


class Journal(IdMixin, Base):
    __tablename__ = "journals"

    conversation_id: Mapped[str] = mapped_column(String, nullable=False)
    source_kind: Mapped[str] = mapped_column(String, nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[Any] = mapped_column(JSON, nullable=True)
    entry_ids: Mapped[Any] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    invalidated_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    invalidated_by_id: Mapped[str | None] = mapped_column(String, nullable=True)
    invalidated_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    superseded_by_id: Mapped[str | None] = mapped_column(String, nullable=True)
    summarized_journal_ids: Mapped[Any | None] = mapped_column(JSON, nullable=True)


class EntryRelation(IdMixin, Base):
    __tablename__ = "entry_relations"

    entry_a_id: Mapped[str] = mapped_column(String, nullable=False)
    entry_b_id: Mapped[str] = mapped_column(String, nullable=False)
    source_kind: Mapped[str] = mapped_column(String, nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False)
    observation_count: Mapped[int] = mapped_column(default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    last_observed_at: Mapped[datetime] = mapped_column(
        UtcDateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    vetted: Mapped[bool | None] = mapped_column(nullable=True)
    vetted_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    vetted_observation_count: Mapped[int | None] = mapped_column(nullable=True)
    vetted_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


# ─────────────────────────────────────────────
# src/marginalia/db/models/user_visible.py
# ─────────────────────────────────────────────


class Folder(IdMixin, TimestampMixin, Base):
    __tablename__ = "folders"

    name: Mapped[str] = mapped_column(String, nullable=False)
    parent_id: Mapped[str | None] = mapped_column(String, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)


class File(IdMixin, TimestampMixin, Base):
    __tablename__ = "files"

    sha256: Mapped[str] = mapped_column(String, nullable=False)
    storage_key: Mapped[str] = mapped_column(String, nullable=False)
    size_bytes: Mapped[int] = mapped_column(nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String, nullable=True)
    original_ext: Mapped[str | None] = mapped_column(String, nullable=True)
    kind: Mapped[str | None] = mapped_column(String, nullable=True)
    ingest_status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    ingested_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    description: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra: Mapped[str | None] = mapped_column(Text, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)


class FileEntry(IdMixin, TimestampMixin, Base):
    __tablename__ = "file_entries"

    file_id: Mapped[str] = mapped_column(String, nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    folder_id: Mapped[str | None] = mapped_column(String, nullable=True)
    catalog_id: Mapped[str | None] = mapped_column(String, nullable=True)
    lifecycle: Mapped[str] = mapped_column(String, nullable=False, default="active")
    purge_after: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    extra: Mapped[str | None] = mapped_column(Text, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)


# ─────────────────────────────────────────────
# src/marginalia/db/models/tasks.py
# ─────────────────────────────────────────────


class Task(IdMixin, Base):
    __tablename__ = "tasks"

    kind: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    priority: Mapped[int] = mapped_column(default=0, nullable=False)
    payload: Mapped[Any] = mapped_column(JSON, nullable=True)
    dedup_key: Mapped[str | None] = mapped_column(String, nullable=True)
    attempts: Mapped[int] = mapped_column(default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(default=3, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    scheduled_at: Mapped[datetime] = mapped_column(
        UtcDateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    locked_by: Mapped[str | None] = mapped_column(String, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)


# ─────────────────────────────────────────────
# src/marginalia/db/models/task_outcomes.py
# ─────────────────────────────────────────────


class TaskOutcome(IdMixin, Base):
    __tablename__ = "task_outcomes"

    task_kind: Mapped[str] = mapped_column(String, nullable=False)
    task_run_id: Mapped[str | None] = mapped_column(String, nullable=True)
    object_kind: Mapped[str] = mapped_column(String, nullable=False)
    object_id: Mapped[str] = mapped_column(String, nullable=False)
    outcome: Mapped[str] = mapped_column(String, nullable=False)
    completed_at: Mapped[datetime] = mapped_column(
        UtcDateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    detail: Mapped[Any | None] = mapped_column(JSON, nullable=True)