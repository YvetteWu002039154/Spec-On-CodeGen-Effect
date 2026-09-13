from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator, DateTime, JSON, Numeric


class UtcDateTime(TypeDecorator):
    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc).replace(tzinfo=None)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return value.replace(tzinfo=timezone.utc)
        return value


class Base(DeclarativeBase):
    metadata = MetaData()
    type_annotation_map = {
        Any: JSON,
    }


class IdMixin:
    id: Mapped[str] = mapped_column(sa.String(36), primary_key=True, default=lambda: str(uuid4()))


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AuditEvent(Base, IdMixin, TimestampMixin):
    __tablename__ = "audit_events"

    conversation_id: Mapped[Optional[str]] = mapped_column(sa.String(36), nullable=True)
    kind: Mapped[str] = mapped_column(sa.String(255))
    occurred_at: Mapped[datetime] = mapped_column(UtcDateTime)
    payload: Mapped[Any] = mapped_column(JSON)
    session_id: Mapped[Optional[str]] = mapped_column(sa.String(36), nullable=True)
    task_id: Mapped[Optional[str]] = mapped_column(sa.String(36), nullable=True)


class Catalog(Base, IdMixin, TimestampMixin):
    __tablename__ = "catalogs"

    deleted_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    description: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    extra: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)
    is_system: Mapped[bool] = mapped_column(sa.Boolean, default=False)
    name: Mapped[str] = mapped_column(sa.String(255))
    parent_id: Mapped[Optional[str]] = mapped_column(sa.String(36), nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)
    tags: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)


class Conversation(Base, IdMixin, TimestampMixin):
    __tablename__ = "conversations"

    agent_response: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    llm_calls: Mapped[Any] = mapped_column(JSON)
    session_id: Mapped[str] = mapped_column(sa.String(36))
    started_at: Mapped[datetime] = mapped_column(UtcDateTime)
    tool_calls: Mapped[Any] = mapped_column(JSON)
    total_cache_read: Mapped[int] = mapped_column(sa.BigInteger, default=0)
    total_cost_estimate: Mapped[Decimal] = mapped_column(Numeric, default=Decimal("0.0"))
    total_duration_ms: Mapped[int] = mapped_column(sa.BigInteger, default=0)
    total_input_tokens: Mapped[int] = mapped_column(sa.BigInteger, default=0)
    total_llm_calls: Mapped[int] = mapped_column(sa.BigInteger, default=0)
    total_output_tokens: Mapped[int] = mapped_column(sa.BigInteger, default=0)
    total_tool_calls: Mapped[int] = mapped_column(sa.BigInteger, default=0)
    turn_index: Mapped[int] = mapped_column(sa.Integer, default=0)
    user_message: Mapped[str] = mapped_column(sa.Text)


class EntryRelation(Base, IdMixin):
    __tablename__ = "entry_relations"

    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=datetime.utcnow)
    entry_a_id: Mapped[str] = mapped_column(sa.String(36))
    entry_b_id: Mapped[str] = mapped_column(sa.String(36))
    last_observed_at: Mapped[datetime] = mapped_column(UtcDateTime, default=datetime.utcnow)
    note: Mapped[str] = mapped_column(sa.Text, default="")
    observation_count: Mapped[int] = mapped_column(sa.Integer, default=0)
    source_kind: Mapped[str] = mapped_column(sa.String(255))
    vetted: Mapped[Optional[bool]] = mapped_column(sa.Boolean, nullable=True)
    vetted_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    vetted_observation_count: Mapped[Optional[int]] = mapped_column(sa.Integer, nullable=True)
    vetted_reason: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)


class EntryTag(Base, IdMixin):
    __tablename__ = "entry_tags"

    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=datetime.utcnow)
    entry_id: Mapped[str] = mapped_column(sa.String(36))
    last_reaffirmed_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    reaffirm_count: Mapped[int] = mapped_column(sa.Integer, default=0)
    source: Mapped[str] = mapped_column(sa.String(255))
    tag_id: Mapped[str] = mapped_column(sa.String(36))


class File(Base, IdMixin, TimestampMixin):
    __tablename__ = "files"

    deleted_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    description: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    extra: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)
    ingest_status: Mapped[str] = mapped_column(sa.String(255))
    ingested_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    kind: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)
    original_ext: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)
    sha256: Mapped[str] = mapped_column(sa.String(64), unique=True)
    size_bytes: Mapped[int] = mapped_column(sa.BigInteger, default=0)
    storage_key: Mapped[str] = mapped_column(sa.String(255))
    summary: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)


class FileEntry(Base, IdMixin, TimestampMixin):
    __tablename__ = "file_entries"

    catalog_id: Mapped[Optional[str]] = mapped_column(sa.String(36), nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    display_name: Mapped[str] = mapped_column(sa.String(255))
    extra: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)
    file_id: Mapped[str] = mapped_column(sa.String(36))
    folder_id: Mapped[Optional[str]] = mapped_column(sa.String(36), nullable=True)
    lifecycle: Mapped[str] = mapped_column(sa.String(255))
    purge_after: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)


class Folder(Base, IdMixin, TimestampMixin):
    __tablename__ = "folders"

    deleted_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    name: Mapped[str] = mapped_column(sa.String(255))
    parent_id: Mapped[Optional[str]] = mapped_column(sa.String(36), nullable=True)


class Journal(Base, IdMixin):
    __tablename__ = "journals"

    conversation_id: Mapped[str] = mapped_column(sa.String(36))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=datetime.utcnow)
    entry_ids: Mapped[Any] = mapped_column(JSON)
    invalidated_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    invalidated_by_id: Mapped[Optional[str]] = mapped_column(sa.String(36), nullable=True)
    invalidated_reason: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    note: Mapped[str] = mapped_column(sa.Text, default="")
    source_kind: Mapped[str] = mapped_column(sa.String(255))
    summarized_journal_ids: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    superseded_by_id: Mapped[Optional[str]] = mapped_column(sa.String(36), nullable=True)
    tags: Mapped[Any] = mapped_column(JSON)


class Session(Base, IdMixin, TimestampMixin):
    __tablename__ = "sessions"

    deleted_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    end_reason: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    initiating_user_message: Mapped[str] = mapped_column(sa.Text)
    started_at: Mapped[datetime] = mapped_column(UtcDateTime)
    total_cache_read: Mapped[int] = mapped_column(sa.BigInteger, default=0)
    total_cost_estimate: Mapped[Decimal] = mapped_column(Numeric, default=Decimal("0.0"))
    total_duration_ms: Mapped[int] = mapped_column(sa.BigInteger, default=0)
    total_input_tokens: Mapped[int] = mapped_column(sa.BigInteger, default=0)
    total_llm_calls: Mapped[int] = mapped_column(sa.BigInteger, default=0)
    total_output_tokens: Mapped[int] = mapped_column(sa.BigInteger, default=0)
    total_tool_calls: Mapped[int] = mapped_column(sa.BigInteger, default=0)
    turn_count: Mapped[int] = mapped_column(sa.Integer, default=0)


class Tag(Base, IdMixin, TimestampMixin):
    __tablename__ = "tags"

    alias_of: Mapped[Optional[str]] = mapped_column(sa.String(36), nullable=True)
    doc_count: Mapped[int] = mapped_column(sa.Integer, default=0)
    facet: Mapped[str] = mapped_column(sa.String(255))
    last_reaffirmed_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    name: Mapped[str] = mapped_column(sa.String(255), unique=True)
    reaffirm_count: Mapped[int] = mapped_column(sa.Integer, default=0)


class TagAlias(Base, IdMixin):
    __tablename__ = "tag_aliases"

    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=datetime.utcnow)
    from_name: Mapped[str] = mapped_column(sa.String(255))
    note: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    to_tag_id: Mapped[str] = mapped_column(sa.String(36))


class Task(Base, IdMixin):
    __tablename__ = "tasks"

    attempts: Mapped[int] = mapped_column(sa.Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=datetime.utcnow)
    dedup_key: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    kind: Mapped[str] = mapped_column(sa.String(255))
    last_error: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    last_heartbeat_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    lease_expires_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    locked_by: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)
    max_attempts: Mapped[int] = mapped_column(sa.Integer, default=1)
    payload: Mapped[Any] = mapped_column(JSON)
    priority: Mapped[int] = mapped_column(sa.Integer, default=0)
    scheduled_at: Mapped[datetime] = mapped_column(UtcDateTime, default=datetime.utcnow)
    started_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    status: Mapped[str] = mapped_column(sa.String(255))


class TaskOutcome(Base, IdMixin):
    __tablename__ = "task_outcomes"

    completed_at: Mapped[datetime] = mapped_column(UtcDateTime)
    detail: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    object_id: Mapped[str] = mapped_column(sa.String(36))
    object_kind: Mapped[str] = mapped_column(sa.String(255))
    outcome: Mapped[str] = mapped_column(sa.String(255))
    task_kind: Mapped[str] = mapped_column(sa.String(255))
    task_run_id: Mapped[Optional[str]] = mapped_column(sa.String(36), nullable=True)


class View(Base, IdMixin, TimestampMixin):
    __tablename__ = "views"

    deleted_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    description: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    extra: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)
    filter_spec: Mapped[Any] = mapped_column(JSON)
    name: Mapped[str] = mapped_column(sa.String(255))
    summary: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)
    tags: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)