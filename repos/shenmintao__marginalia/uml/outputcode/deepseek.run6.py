import datetime
import uuid
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import (
    DateTime,
    MetaData,
    Numeric,
    String,
    Text,
    Boolean,
    Integer,
    JSON,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, declared_attr
from sqlalchemy.types import TypeDecorator


class UtcDateTime(TypeDecorator):
    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            if value.tzinfo is None:
                value = value.replace(tzinfo=datetime.timezone.utc)
            return value.astimezone(datetime.timezone.utc)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = value.replace(tzinfo=datetime.timezone.utc)
        return value


class Base(DeclarativeBase):
    metadata = MetaData()
    type_annotation_map = {
        datetime.datetime: UtcDateTime,
        Decimal: Numeric(19, 4),
    }


class IdMixin:
    id: Mapped[str] = mapped_column(
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        unique=True,
    )


class TimestampMixin:
    created_at: Mapped[datetime.datetime] = mapped_column(
        default=func.now(),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        default=func.now(),
        onupdate=func.now(),
        server_default=func.now(),
    )


class AuditEvent(Base, IdMixin):
    __tablename__ = "audit_events"
    conversation_id: Mapped[Optional[str]]
    kind: Mapped[str]
    occurred_at: Mapped[datetime.datetime] = mapped_column(
        default=func.now(),
        server_default=func.now(),
    )
    payload: Mapped[Any] = mapped_column(JSON)
    session_id: Mapped[Optional[str]]
    task_id: Mapped[Optional[str]]


class Conversation(Base, IdMixin):
    __tablename__ = "conversations"
    agent_response: Mapped[Optional[str]] = mapped_column(Text)
    ended_at: Mapped[Optional[datetime.datetime]]
    llm_calls: Mapped[Any] = mapped_column(JSON)
    session_id: Mapped[str]
    started_at: Mapped[datetime.datetime] = mapped_column(
        default=func.now(),
        server_default=func.now(),
    )
    tool_calls: Mapped[Any] = mapped_column(JSON)
    total_cache_read: Mapped[int] = mapped_column(default=0)
    total_cost_estimate: Mapped[Decimal]
    total_duration_ms: Mapped[int] = mapped_column(default=0)
    total_input_tokens: Mapped[int] = mapped_column(default=0)
    total_llm_calls: Mapped[int] = mapped_column(default=0)
    total_output_tokens: Mapped[int] = mapped_column(default=0)
    total_tool_calls: Mapped[int] = mapped_column(default=0)
    turn_index: Mapped[int] = mapped_column(default=0)
    user_message: Mapped[str] = mapped_column(Text)


class Session(Base, IdMixin):
    __tablename__ = "sessions"
    deleted_at: Mapped[Optional[datetime.datetime]]
    end_reason: Mapped[Optional[str]]
    ended_at: Mapped[Optional[datetime.datetime]]
    initiating_user_message: Mapped[str] = mapped_column(Text)
    started_at: Mapped[datetime.datetime] = mapped_column(
        default=func.now(),
        server_default=func.now(),
    )
    total_cache_read: Mapped[int] = mapped_column(default=0)
    total_cost_estimate: Mapped[Decimal]
    total_duration_ms: Mapped[int] = mapped_column(default=0)
    total_input_tokens: Mapped[int] = mapped_column(default=0)
    total_llm_calls: Mapped[int] = mapped_column(default=0)
    total_output_tokens: Mapped[int] = mapped_column(default=0)
    total_tool_calls: Mapped[int] = mapped_column(default=0)
    turn_count: Mapped[int] = mapped_column(default=0)


class Catalog(Base, IdMixin):
    __tablename__ = "catalogs"
    deleted_at: Mapped[Optional[datetime.datetime]]
    description: Mapped[Optional[Any]] = mapped_column(JSON)
    extra: Mapped[Optional[str]] = mapped_column(Text)
    is_system: Mapped[bool] = mapped_column(default=False)
    name: Mapped[str]
    parent_id: Mapped[Optional[str]]
    summary: Mapped[Optional[str]] = mapped_column(Text)
    tags: Mapped[Optional[Any]] = mapped_column(JSON)


class EntryRelation(Base, IdMixin):
    __tablename__ = "entry_relations"
    created_at: Mapped[datetime.datetime] = mapped_column(
        default=func.now(),
        server_default=func.now(),
    )
    entry_a_id: Mapped[str]
    entry_b_id: Mapped[str]
    last_observed_at: Mapped[datetime.datetime]
    note: Mapped[str] = mapped_column(Text)
    observation_count: Mapped[int] = mapped_column(default=0)
    source_kind: Mapped[str]
    vetted: Mapped[Optional[bool]]
    vetted_at: Mapped[Optional[datetime.datetime]]
    vetted_observation_count: Mapped[Optional[int]]
    vetted_reason: Mapped[Optional[str]] = mapped_column(Text)


class EntryTag(Base, IdMixin):
    __tablename__ = "entry_tags"
    created_at: Mapped[datetime.datetime] = mapped_column(
        default=func.now(),
        server_default=func.now(),
    )
    entry_id: Mapped[str]
    last_reaffirmed_at: Mapped[Optional[datetime.datetime]]
    reaffirm_count: Mapped[int] = mapped_column(default=0)
    source: Mapped[str]
    tag_id: Mapped[str]


class File(Base, IdMixin):
    __tablename__ = "files"
    deleted_at: Mapped[Optional[datetime.datetime]]
    description: Mapped[Optional[Any]] = mapped_column(JSON)
    extra: Mapped[Optional[str]] = mapped_column(Text)
    ingest_status: Mapped[str] = mapped_column(default="pending")
    ingested_at: Mapped[Optional[datetime.datetime]]
    kind: Mapped[Optional[str]]
    mime_type: Mapped[Optional[str]]
    original_ext: Mapped[Optional[str]]
    sha256: Mapped[str]
    size_bytes: Mapped[int] = mapped_column(default=0)
    storage_key: Mapped[str]
    summary: Mapped[Optional[str]] = mapped_column(Text)


class FileEntry(Base, IdMixin):
    __tablename__ = "file_entries"
    catalog_id: Mapped[Optional[str]]
    deleted_at: Mapped[Optional[datetime.datetime]]
    display_name: Mapped[str]
    extra: Mapped[Optional[str]] = mapped_column(Text)
    file_id: Mapped[str]
    folder_id: Mapped[Optional[str]]
    lifecycle: Mapped[str] = mapped_column(default="active")
    purge_after: Mapped[Optional[datetime.datetime]]


class Folder(Base, IdMixin):
    __tablename__ = "folders"
    deleted_at: Mapped[Optional[datetime.datetime]]
    name: Mapped[str]
    parent_id: Mapped[Optional[str]]


class Journal(Base, IdMixin):
    __tablename__ = "journals"
    conversation_id: Mapped[str]
    created_at: Mapped[datetime.datetime] = mapped_column(
        default=func.now(),
        server_default=func.now(),
    )
    entry_ids: Mapped[Any] = mapped_column(JSON)
    invalidated_at: Mapped[Optional[datetime.datetime]]
    invalidated_by_id: Mapped[Optional[str]]
    invalidated_reason: Mapped[Optional[str]] = mapped_column(Text)
    note: Mapped[str] = mapped_column(Text)
    source_kind: Mapped[str]
    summarized_journal_ids: Mapped[Optional[Any]] = mapped_column(JSON)
    superseded_by_id: Mapped[Optional[str]]
    tags: Mapped[Any] = mapped_column(JSON)


class Tag(Base, IdMixin):
    __tablename__ = "tags"
    alias_of: Mapped[Optional[str]]
    doc_count: Mapped[int] = mapped_column(default=0)
    facet: Mapped[str]
    last_reaffirmed_at: Mapped[Optional[datetime.datetime]]
    last_used_at: Mapped[Optional[datetime.datetime]]
    name: Mapped[str] = mapped_column(unique=True)
    reaffirm_count: Mapped[int] = mapped_column(default=0)


class TagAlias(Base, IdMixin):
    __tablename__ = "tag_aliases"
    created_at: Mapped[datetime.datetime] = mapped_column(
        default=func.now(),
        server_default=func.now(),
    )
    from_name: Mapped[str]
    note: Mapped[Optional[str]] = mapped_column(Text)
    to_tag_id: Mapped[str]


class Task(Base, IdMixin):
    __tablename__ = "tasks"
    attempts: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime.datetime] = mapped_column(
        default=func.now(),
        server_default=func.now(),
    )
    dedup_key: Mapped[Optional[str]]
    finished_at: Mapped[Optional[datetime.datetime]]
    kind: Mapped[str]
    last_error: Mapped[Optional[str]] = mapped_column(Text)
    last_heartbeat_at: Mapped[Optional[datetime.datetime]]
    lease_expires_at: Mapped[Optional[datetime.datetime]]
    locked_by: Mapped[Optional[str]]
    max_attempts: Mapped[int] = mapped_column(default=3)
    payload: Mapped[Any] = mapped_column(JSON)
    priority: Mapped[int] = mapped_column(default=0)
    scheduled_at: Mapped[datetime.datetime]
    started_at: Mapped[Optional[datetime.datetime]]
    status: Mapped[str] = mapped_column(default="pending")


class TaskOutcome(Base, IdMixin):
    __tablename__ = "task_outcomes"
    completed_at: Mapped[datetime.datetime]
    detail: Mapped[Optional[Any]] = mapped_column(JSON)
    object_id: Mapped[str]
    object_kind: Mapped[str]
    outcome: Mapped[str]
    task_kind: Mapped[str]
    task_run_id: Mapped[Optional[str]]


class View(Base, IdMixin):
    __tablename__ = "views"
    deleted_at: Mapped[Optional[datetime.datetime]]
    description: Mapped[Optional[Any]] = mapped_column(JSON)
    extra: Mapped[Optional[str]] = mapped_column(Text)
    filter_spec: Mapped[Any] = mapped_column(JSON)
    name: Mapped[str]
    summary: Mapped[Optional[str]] = mapped_column(Text)
    tags: Mapped[Optional[Any]] = mapped_column(JSON)