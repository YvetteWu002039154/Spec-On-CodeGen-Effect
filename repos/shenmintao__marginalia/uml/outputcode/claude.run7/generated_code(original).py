from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, MetaData, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator


class UtcDateTime(TypeDecorator):
    cache_ok: bool = True
    impl = DateTime

    def process_bind_param(self, value, dialect):
        if value is not None:
            if isinstance(value, datetime):
                if value.tzinfo is None:
                    value = value.replace(tzinfo=timezone.utc)
                return value.astimezone(timezone.utc).replace(tzinfo=None)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            if isinstance(value, datetime):
                return value.replace(tzinfo=timezone.utc)
        return value


class Base(DeclarativeBase):
    metadata = MetaData()
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
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
    )
```

```python
# src/marginalia/db/models/base.py
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, MetaData, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator


class UtcDateTime(TypeDecorator):
    cache_ok: bool = True
    impl = DateTime

    def process_bind_param(self, value, dialect):
        if value is not None:
            if isinstance(value, datetime):
                if value.tzinfo is None:
                    value = value.replace(tzinfo=timezone.utc)
                return value.astimezone(timezone.utc).replace(tzinfo=None)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            if isinstance(value, datetime):
                return value.replace(tzinfo=timezone.utc)
        return value


class Base(DeclarativeBase):
    metadata = MetaData()
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
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
    )
```

Now let me provide the complete, single-file implementation:

```python
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Integer,
    MetaData,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator


# ---------------------------------------------------------------------------
# src/marginalia/db/models/base.py
# ---------------------------------------------------------------------------

class UtcDateTime(TypeDecorator):
    """A DateTime type that stores UTC and returns timezone-aware datetimes."""

    cache_ok: bool = True
    impl = DateTime

    def process_bind_param(self, value, dialect):
        if value is not None:
            if isinstance(value, datetime):
                if value.tzinfo is None:
                    value = value.replace(tzinfo=timezone.utc)
                return value.astimezone(timezone.utc).replace(tzinfo=None)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            if isinstance(value, datetime):
                return value.replace(tzinfo=timezone.utc)
        return value


class Base(DeclarativeBase):
    metadata = MetaData()
    type_annotation_map: dict[Any, Any] = {
        datetime: UtcDateTime,
        Decimal: Numeric(precision=20, scale=8),
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
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


# ---------------------------------------------------------------------------
# src/marginalia/db/models/audit.py
# ---------------------------------------------------------------------------

class AuditEvent(IdMixin, Base):
    __tablename__ = "audit_events"

    conversation_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    payload: Mapped[Any] = mapped_column(JSON, nullable=True)
    session_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    task_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class Conversation(IdMixin, Base):
    __tablename__ = "conversations"

    agent_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    llm_calls: Mapped[Any] = mapped_column(JSON, nullable=True)
    session_id: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    tool_calls: Mapped[Any] = mapped_column(JSON, nullable=True)
    total_cache_read: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_cost_estimate: Mapped[Decimal] = mapped_column(
        Numeric(precision=20, scale=8), nullable=False, default=Decimal("0")
    )
    total_duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_llm_calls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tool_calls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    turn_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    user_message: Mapped[str] = mapped_column(Text, nullable=False)


class Session(IdMixin, Base):
    __tablename__ = "sessions"

    deleted_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    end_reason: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    initiating_user_message: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    total_cache_read: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_cost_estimate: Mapped[Decimal] = mapped_column(
        Numeric(precision=20, scale=8), nullable=False, default=Decimal("0")
    )
    total_duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_llm_calls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tool_calls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    turn_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


# ---------------------------------------------------------------------------
# src/marginalia/db/models/ai_structural.py
# ---------------------------------------------------------------------------

class Catalog(IdMixin, Base):
    __tablename__ = "catalogs"

    deleted_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    description: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    extra: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    parent_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)


class EntryTag(IdMixin, Base):
    __tablename__ = "entry_tags"

    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    entry_id: Mapped[str] = mapped_column(String, nullable=False)
    last_reaffirmed_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    reaffirm_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source: Mapped[str] = mapped_column(String, nullable=False)
    tag_id: Mapped[str] = mapped_column(String, nullable=False)


class Tag(IdMixin, Base):
    __tablename__ = "tags"

    alias_of: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    doc_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    facet: Mapped[str] = mapped_column(String, nullable=False)
    last_reaffirmed_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    reaffirm_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class TagAlias(IdMixin, Base):
    __tablename__ = "tag_aliases"

    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    from_name: Mapped[str] = mapped_column(String, nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    to_tag_id: Mapped[str] = mapped_column(String, nullable=False)


class View(IdMixin, Base):
    __tablename__ = "views"

    deleted_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    description: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    extra: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    filter_spec: Mapped[Any] = mapped_column(JSON, nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)


# ---------------------------------------------------------------------------
# src/marginalia/db/models/ai_recall.py
# ---------------------------------------------------------------------------

class EntryRelation(IdMixin, Base):
    __tablename__ = "entry_relations"

    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    entry_a_id: Mapped[str] = mapped_column(String, nullable=False)
    entry_b_id: Mapped[str] = mapped_column(String, nullable=False)
    last_observed_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False)
    observation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source_kind: Mapped[str] = mapped_column(String, nullable=False)
    vetted: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    vetted_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    vetted_observation_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    vetted_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class Journal(IdMixin, Base):
    __tablename__ = "journals"

    conversation_id: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    entry_ids: Mapped[Any] = mapped_column(JSON, nullable=True)
    invalidated_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    invalidated_by_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    invalidated_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    note: Mapped[str] = mapped_column(Text, nullable=False)
    source_kind: Mapped[str] = mapped_column(String, nullable=False)
    summarized_journal_ids: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    superseded_by_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    tags: Mapped[Any] = mapped_column(JSON, nullable=True)


# ---------------------------------------------------------------------------
# src/marginalia/db/models/user_visible.py
# ---------------------------------------------------------------------------

class File(IdMixin, Base):
    __tablename__ = "files"

    deleted_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    description: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    extra: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ingest_status: Mapped[str] = mapped_column(String, nullable=False)
    ingested_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    kind: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    original_ext: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    sha256: Mapped[str] = mapped_column(String, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_key: Mapped[str] = mapped_column(String, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class FileEntry(IdMixin, Base):
    __tablename__ = "file_entries"

    catalog_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    extra: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_id: Mapped[str] = mapped_column(String, nullable=False)
    folder_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    lifecycle: Mapped[str] = mapped_column(String, nullable=False)
    purge_after: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)


class Folder(IdMixin, Base):
    __tablename__ = "folders"

    deleted_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    parent_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)


# ---------------------------------------------------------------------------
# src/marginalia/db/models/tasks.py
# ---------------------------------------------------------------------------

class Task(IdMixin, Base):
    __tablename__ = "tasks"

    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    dedup_key: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_heartbeat_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    lease_expires_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    locked_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    payload: Mapped[Any] = mapped_column(JSON, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    scheduled_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False)


# ---------------------------------------------------------------------------
# src/marginalia/db/models/task_outcomes.py
# ---------------------------------------------------------------------------

class TaskOutcome(IdMixin, Base):
    __tablename__ = "task_outcomes"

    completed_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    detail: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    object_id: Mapped[str] = mapped_column(String, nullable=False)
    object_kind: Mapped[str] = mapped_column(String, nullable=False)
    outcome: Mapped[str] = mapped_column(String, nullable=False)
    task_kind: Mapped[str] = mapped_column(String, nullable=False)
    task_run_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)