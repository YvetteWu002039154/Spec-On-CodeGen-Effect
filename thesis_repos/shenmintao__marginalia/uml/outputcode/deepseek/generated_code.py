import datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import DateTime, MetaData, Text, TypeDecorator
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column
from sqlalchemy.sql import functions


class UtcDateTime(TypeDecorator):
    """Custom type that ensures datetimes are stored and retrieved as UTC."""
    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: Optional[datetime.datetime], dialect: Any) -> Optional[datetime.datetime]:
        if value is not None and value.tzinfo is None:
            raise ValueError("Datetime must be timezone-aware")
        return value

    def process_result_value(self, value: Optional[datetime.datetime], dialect: Any) -> Optional[datetime.datetime]:
        if value is not None:
            return value.replace(tzinfo=datetime.timezone.utc)
        return value


class Base(DeclarativeBase):
    metadata = MetaData()
    type_annotation_map = {
        # Use default mappings; we'll rely on explicit column types if needed.
    }


class IdMixin:
    """Provides a universally unique primary key for all entities."""
    @declared_attr
    def id(cls) -> Mapped[str]:
        return mapped_column(primary_key=True, default=lambda: None)  # UUIDs generated at application level
    # Alternatively, we could use a callable, but spec shows just attribute.
    # We'll define id as a normal column with primary_key=True and String type.
    # Since Mapped[str] is declared, SQLAlchemy will use String by default.
    # To be explicit: mapped_column(String, primary_key=True, default=uuid4)
    # But we'll keep minimal.


class TimestampMixin:
    """Adds standard created_at and updated_at columns."""
    created_at: Mapped[datetime.datetime] = mapped_column(
        UtcDateTime, default=functions.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        UtcDateTime, default=functions.now(), onupdate=functions.now()
    )


# -----------------------------------------------------------------
# Audit models
# -----------------------------------------------------------------
from sqlalchemy import Column, String, Integer, Boolean, Numeric, JSON, ForeignKey

class AuditEvent(Base, IdMixin):
    __tablename__ = "audit_events"

    conversation_id: Mapped[Optional[str]]
    kind: Mapped[str]
    occurred_at: Mapped[datetime.datetime] = mapped_column(UtcDateTime)
    payload: Mapped[Any] = mapped_column(JSON)
    session_id: Mapped[Optional[str]]
    task_id: Mapped[Optional[str]]


class Conversation(Base, IdMixin):
    __tablename__ = "conversations"

    agent_response: Mapped[Optional[str]]
    ended_at: Mapped[Optional[datetime.datetime]] = mapped_column(UtcDateTime)
    llm_calls: Mapped[Any] = mapped_column(JSON)
    session_id: Mapped[str]
    started_at: Mapped[datetime.datetime] = mapped_column(UtcDateTime)
    tool_calls: Mapped[Any] = mapped_column(JSON)
    total_cache_read: Mapped[int]
    total_cost_estimate: Mapped[Decimal]
    total_duration_ms: Mapped[int]
    total_input_tokens: Mapped[int]
    total_llm_calls: Mapped[int]
    total_output_tokens: Mapped[int]
    total_tool_calls: Mapped[int]
    turn_index: Mapped[int]
    user_message: Mapped[str]


class Session(Base, IdMixin):
    __tablename__ = "sessions"

    deleted_at: Mapped[Optional[datetime.datetime]] = mapped_column(UtcDateTime)
    end_reason: Mapped[Optional[str]]
    ended_at: Mapped[Optional[datetime.datetime]] = mapped_column(UtcDateTime)
    initiating_user_message: Mapped[str]
    started_at: Mapped[datetime.datetime] = mapped_column(UtcDateTime)
    total_cache_read: Mapped[int]
    total_cost_estimate: Mapped[Decimal]
    total_duration_ms: Mapped[int]
    total_input_tokens: Mapped[int]
    total_llm_calls: Mapped[int]
    total_output_tokens: Mapped[int]
    total_tool_calls: Mapped[int]
    turn_count: Mapped[int]


# -----------------------------------------------------------------
# AI Structural models
# -----------------------------------------------------------------
class Catalog(Base, IdMixin):
    __tablename__ = "catalogs"

    deleted_at: Mapped[Optional[datetime.datetime]] = mapped_column(UtcDateTime)
    description: Mapped[Any | None] = mapped_column(JSON)
    extra: Mapped[Optional[str]]
    is_system: Mapped[bool]
    name: Mapped[str]
    parent_id: Mapped[Optional[str]]
    summary: Mapped[Optional[str]]
    tags: Mapped[Any | None] = mapped_column(JSON)


class EntryTag(Base, IdMixin):
    __tablename__ = "entry_tags"

    created_at: Mapped[datetime.datetime] = mapped_column(UtcDateTime)
    entry_id: Mapped[str]
    last_reaffirmed_at: Mapped[Optional[datetime.datetime]] = mapped_column(UtcDateTime)
    reaffirm_count: Mapped[int]
    source: Mapped[str]
    tag_id: Mapped[str]


class Tag(Base, IdMixin):
    __tablename__ = "tags"

    alias_of: Mapped[Optional[str]]
    doc_count: Mapped[int]
    facet: Mapped[str]
    last_reaffirmed_at: Mapped[Optional[datetime.datetime]] = mapped_column(UtcDateTime)
    last_used_at: Mapped[Optional[datetime.datetime]] = mapped_column(UtcDateTime)
    name: Mapped[str]
    reaffirm_count: Mapped[int]


class TagAlias(Base, IdMixin):
    __tablename__ = "tag_aliases"

    created_at: Mapped[datetime.datetime] = mapped_column(UtcDateTime)
    from_name: Mapped[str]
    note: Mapped[Optional[str]]
    to_tag_id: Mapped[str]


class View(Base, IdMixin):
    __tablename__ = "views"

    deleted_at: Mapped[Optional[datetime.datetime]] = mapped_column(UtcDateTime)
    description: Mapped[Any | None] = mapped_column(JSON)
    extra: Mapped[Optional[str]]
    filter_spec: Mapped[Any] = mapped_column(JSON)
    name: Mapped[str]
    summary: Mapped[Optional[str]]
    tags: Mapped[Any | None] = mapped_column(JSON)


# -----------------------------------------------------------------
# AI Recall models
# -----------------------------------------------------------------
class EntryRelation(Base, IdMixin):
    __tablename__ = "entry_relations"

    created_at: Mapped[datetime.datetime] = mapped_column(UtcDateTime)
    entry_a_id: Mapped[str]
    entry_b_id: Mapped[str]
    last_observed_at: Mapped[datetime.datetime] = mapped_column(UtcDateTime)
    note: Mapped[str]
    observation_count: Mapped[int]
    source_kind: Mapped[str]
    vetted: Mapped[Optional[bool]]
    vetted_at: Mapped[Optional[datetime.datetime]] = mapped_column(UtcDateTime)
    vetted_observation_count: Mapped[Optional[int]]
    vetted_reason: Mapped[Optional[str]]


class Journal(Base, IdMixin):
    __tablename__ = "journals"

    conversation_id: Mapped[str]
    created_at: Mapped[datetime.datetime] = mapped_column(UtcDateTime)
    entry_ids: Mapped[Any] = mapped_column(JSON)
    invalidated_at: Mapped[Optional[datetime.datetime]] = mapped_column(UtcDateTime)
    invalidated_by_id: Mapped[Optional[str]]
    invalidated_reason: Mapped[Optional[str]]
    note: Mapped[str]
    source_kind: Mapped[str]
    summarized_journal_ids: Mapped[Any | None] = mapped_column(JSON)
    superseded_by_id: Mapped[Optional[str]]
    tags: Mapped[Any] = mapped_column(JSON)


# -----------------------------------------------------------------
# User Visible models
# -----------------------------------------------------------------
class File(Base, IdMixin):
    __tablename__ = "files"

    deleted_at: Mapped[Optional[datetime.datetime]] = mapped_column(UtcDateTime)
    description: Mapped[Any | None] = mapped_column(JSON)
    extra: Mapped[Optional[str]]
    ingest_status: Mapped[str]
    ingested_at: Mapped[Optional[datetime.datetime]] = mapped_column(UtcDateTime)
    kind: Mapped[Optional[str]]
    mime_type: Mapped[Optional[str]]
    original_ext: Mapped[Optional[str]]
    sha256: Mapped[str]
    size_bytes: Mapped[int]
    storage_key: Mapped[str]
    summary: Mapped[Optional[str]]


class FileEntry(Base, IdMixin):
    __tablename__ = "file_entries"

    catalog_id: Mapped[Optional[str]]
    deleted_at: Mapped[Optional[datetime.datetime]] = mapped_column(UtcDateTime)
    display_name: Mapped[str]
    extra: Mapped[Optional[str]]
    file_id: Mapped[str]
    folder_id: Mapped[Optional[str]]
    lifecycle: Mapped[str]
    purge_after: Mapped[Optional[datetime.datetime]] = mapped_column(UtcDateTime)


class Folder(Base, IdMixin):
    __tablename__ = "folders"

    deleted_at: Mapped[Optional[datetime.datetime]] = mapped_column(UtcDateTime)
    name: Mapped[str]
    parent_id: Mapped[Optional[str]]


# -----------------------------------------------------------------
# Task models
# -----------------------------------------------------------------
class Task(Base, IdMixin):
    __tablename__ = "tasks"

    attempts: Mapped[int]
    created_at: Mapped[datetime.datetime] = mapped_column(UtcDateTime)
    dedup_key: Mapped[Optional[str]]
    finished_at: Mapped[Optional[datetime.datetime]] = mapped_column(UtcDateTime)
    kind: Mapped[str]
    last_error: Mapped[Optional[str]]
    last_heartbeat_at: Mapped[Optional[datetime.datetime]] = mapped_column(UtcDateTime)
    lease_expires_at: Mapped[Optional[datetime.datetime]] = mapped_column(UtcDateTime)
    locked_by: Mapped[Optional[str]]
    max_attempts: Mapped[int]
    payload: Mapped[Any] = mapped_column(JSON)
    priority: Mapped[int]
    scheduled_at: Mapped[datetime.datetime] = mapped_column(UtcDateTime)
    started_at: Mapped[Optional[datetime.datetime]] = mapped_column(UtcDateTime)
    status: Mapped[str]


class TaskOutcome(Base, IdMixin):
    __tablename__ = "task_outcomes"

    completed_at: Mapped[datetime.datetime] = mapped_column(UtcDateTime)
    detail: Mapped[Any | None] = mapped_column(JSON)
    object_id: Mapped[str]
    object_kind: Mapped[str]
    outcome: Mapped[str]
    task_kind: Mapped[str]
    task_run_id: Mapped[Optional[str]]