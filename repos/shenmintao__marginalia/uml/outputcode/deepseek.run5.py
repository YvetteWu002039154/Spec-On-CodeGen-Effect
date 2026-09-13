import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional
from sqlalchemy import (
    MetaData,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    TypeDecorator,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class UtcDateTime(TypeDecorator):
    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            else:
                value = value.astimezone(timezone.utc)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            else:
                value = value.astimezone(timezone.utc)
        return value


class Base(DeclarativeBase):
    metadata: MetaData = MetaData()
    type_annotation_map: Dict[Any, Any] = {}


class IdMixin:
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


# ----------------------------------------------------------------------
# src.marginalia.db.models.audit
# ----------------------------------------------------------------------

class AuditEvent(Base, IdMixin):
    __tablename__ = "audit_events"

    conversation_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    kind: Mapped[str] = mapped_column(String)
    occurred_at: Mapped[datetime] = mapped_column(UtcDateTime)
    payload: Mapped[Any] = mapped_column(JSON)
    session_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    task_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)


class Conversation(Base, IdMixin):
    __tablename__ = "conversations"

    agent_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    llm_calls: Mapped[Any] = mapped_column(JSON)
    session_id: Mapped[str] = mapped_column(String(36))
    started_at: Mapped[datetime] = mapped_column(UtcDateTime)
    tool_calls: Mapped[Any] = mapped_column(JSON)
    total_cache_read: Mapped[int] = mapped_column(BigInteger, default=0)
    total_cost_estimate: Mapped[Decimal] = mapped_column(Numeric(18, 8), default=0)
    total_duration_ms: Mapped[int] = mapped_column(BigInteger, default=0)
    total_input_tokens: Mapped[int] = mapped_column(BigInteger, default=0)
    total_llm_calls: Mapped[int] = mapped_column(Integer, default=0)
    total_output_tokens: Mapped[int] = mapped_column(BigInteger, default=0)
    total_tool_calls: Mapped[int] = mapped_column(Integer, default=0)
    turn_index: Mapped[int] = mapped_column(Integer)
    user_message: Mapped[str] = mapped_column(Text)


class Session(Base, IdMixin):
    __tablename__ = "sessions"

    deleted_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    end_reason: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    initiating_user_message: Mapped[str] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(UtcDateTime)
    total_cache_read: Mapped[int] = mapped_column(BigInteger, default=0)
    total_cost_estimate: Mapped[Decimal] = mapped_column(Numeric(18, 8), default=0)
    total_duration_ms: Mapped[int] = mapped_column(BigInteger, default=0)
    total_input_tokens: Mapped[int] = mapped_column(BigInteger, default=0)
    total_llm_calls: Mapped[int] = mapped_column(Integer, default=0)
    total_output_tokens: Mapped[int] = mapped_column(BigInteger, default=0)
    total_tool_calls: Mapped[int] = mapped_column(Integer, default=0)
    turn_count: Mapped[int] = mapped_column(Integer)


# ----------------------------------------------------------------------
# src.marginalia.db.models.ai_structural
# ----------------------------------------------------------------------

class Catalog(Base, IdMixin):
    __tablename__ = "catalogs"

    deleted_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    description: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    extra: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    name: Mapped[str] = mapped_column(String)
    parent_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)


class EntryTag(Base, IdMixin):
    __tablename__ = "entry_tags"

    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime, default=lambda: datetime.now(timezone.utc)
    )
    entry_id: Mapped[str] = mapped_column(String(36))
    last_reaffirmed_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    reaffirm_count: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String)
    tag_id: Mapped[str] = mapped_column(String(36))


class Tag(Base, IdMixin):
    __tablename__ = "tags"

    alias_of: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    doc_count: Mapped[int] = mapped_column(Integer, default=0)
    facet: Mapped[str] = mapped_column(String)
    last_reaffirmed_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    name: Mapped[str] = mapped_column(String)
    reaffirm_count: Mapped[int] = mapped_column(Integer, default=0)


class TagAlias(Base, IdMixin):
    __tablename__ = "tag_aliases"

    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime, default=lambda: datetime.now(timezone.utc)
    )
    from_name: Mapped[str] = mapped_column(String)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    to_tag_id: Mapped[str] = mapped_column(String(36))


class View(Base, IdMixin):
    __tablename__ = "views"

    deleted_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    description: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    extra: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    filter_spec: Mapped[Any] = mapped_column(JSON)
    name: Mapped[str] = mapped_column(String)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)


# ----------------------------------------------------------------------
# src.marginalia.db.models.ai_recall
# ----------------------------------------------------------------------

class EntryRelation(Base, IdMixin):
    __tablename__ = "entry_relations"

    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime, default=lambda: datetime.now(timezone.utc)
    )
    entry_a_id: Mapped[str] = mapped_column(String(36))
    entry_b_id: Mapped[str] = mapped_column(String(36))
    last_observed_at: Mapped[datetime] = mapped_column(UtcDateTime)
    note: Mapped[str] = mapped_column(Text)
    observation_count: Mapped[int] = mapped_column(Integer, default=1)
    source_kind: Mapped[str] = mapped_column(String)
    vetted: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    vetted_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    vetted_observation_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    vetted_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class Journal(Base, IdMixin):
    __tablename__ = "journals"

    conversation_id: Mapped[str] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime, default=lambda: datetime.now(timezone.utc)
    )
    entry_ids: Mapped[Any] = mapped_column(JSON)
    invalidated_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    invalidated_by_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    invalidated_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    note: Mapped[str] = mapped_column(Text)
    source_kind: Mapped[str] = mapped_column(String)
    summarized_journal_ids: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    superseded_by_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    tags: Mapped[Any] = mapped_column(JSON)


# ----------------------------------------------------------------------
# src.marginalia.db.models.user_visible
# ----------------------------------------------------------------------

class File(Base, IdMixin):
    __tablename__ = "files"

    deleted_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    description: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    extra: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ingest_status: Mapped[str] = mapped_column(String)
    ingested_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    kind: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    original_ext: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    sha256: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    storage_key: Mapped[str] = mapped_column(String)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class FileEntry(Base, IdMixin):
    __tablename__ = "file_entries"

    catalog_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    display_name: Mapped[str] = mapped_column(String)
    extra: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_id: Mapped[str] = mapped_column(String(36))
    folder_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    lifecycle: Mapped[str] = mapped_column(String)
    purge_after: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)


class Folder(Base, IdMixin):
    __tablename__ = "folders"

    deleted_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    name: Mapped[str] = mapped_column(String)
    parent_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)


# ----------------------------------------------------------------------
# src.marginalia.db.models.tasks
# ----------------------------------------------------------------------

class Task(Base, IdMixin):
    __tablename__ = "tasks"

    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime, default=lambda: datetime.now(timezone.utc)
    )
    dedup_key: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    kind: Mapped[str] = mapped_column(String)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_heartbeat_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    lease_expires_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    locked_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    payload: Mapped[Any] = mapped_column(JSON)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    scheduled_at: Mapped[datetime] = mapped_column(UtcDateTime)
    started_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    status: Mapped[str] = mapped_column(String)


# ----------------------------------------------------------------------
# src.marginalia.db.models.task_outcomes
# ----------------------------------------------------------------------

class TaskOutcome(Base, IdMixin):
    __tablename__ = "task_outcomes"

    completed_at: Mapped[datetime] = mapped_column(UtcDateTime)
    detail: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    object_id: Mapped[str] = mapped_column(String(36))
    object_kind: Mapped[str] = mapped_column(String)
    outcome: Mapped[str] = mapped_column(String)
    task_kind: Mapped[str] = mapped_column(String)
    task_run_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)