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
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime,
        default=lambda: datetime.now(timezone.utc),
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

from sqlalchemy import DateTime, MetaData, String
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
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
```

Now let me provide the complete, properly structured implementation:

```python
# Complete implementation as a single file for clarity

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import JSON, Boolean, DateTime, Integer, MetaData, Numeric, String, Text
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
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


# ---------------------------------------------------------------------------
# src/marginalia/db/models/audit.py
# ---------------------------------------------------------------------------

class AuditEvent(IdMixin, Base):
    __tablename__ = "audit_events"

    kind: Mapped[str] = mapped_column(String, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    payload: Mapped[Any] = mapped_column(JSON, nullable=False)
    conversation_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    session_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    task_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class Conversation(IdMixin, Base):
    __tablename__ = "conversations"

    session_id: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    ended_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    user_message: Mapped[str] = mapped_column(Text, nullable=False)
    agent_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    turn_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    llm_calls: Mapped[Any] = mapped_column(JSON, nullable=False, default=list)
    tool_calls: Mapped[Any] = mapped_column(JSON, nullable=False, default=list)
    total_llm_calls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tool_calls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_cache_read: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_cost_estimate: Mapped[Decimal] = mapped_column(
        Numeric(precision=20, scale=8), nullable=False, default=Decimal("0")
    )


class Session(IdMixin, Base):
    __tablename__ = "sessions"

    started_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    ended_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    initiating_user_message: Mapped[str] = mapped_column(Text, nullable=False)
    end_reason: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    turn_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_llm_calls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tool_calls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_cache_read: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_cost_estimate: Mapped[Decimal] = mapped_column(
        Numeric(precision=20, scale=8), nullable=False, default=Decimal("0")
    )


# ---------------------------------------------------------------------------
# src/marginalia/db/models/ai_structural.py
# ---------------------------------------------------------------------------

class Catalog(IdMixin, TimestampMixin, Base):
    __tablename__ = "catalogs"

    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extra: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    parent_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)


class Tag(IdMixin, TimestampMixin, Base):
    __tablename__ = "tags"

    name: Mapped[str] = mapped_column(String, nullable=False)
    facet: Mapped[str] = mapped_column(String, nullable=False)
    alias_of: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    doc_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reaffirm_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    last_reaffirmed_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)


class TagAlias(IdMixin, Base):
    __tablename__ = "tag_aliases"

    from_name: Mapped[str] = mapped_column(String, nullable=False)
    to_tag_id: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class EntryTag(IdMixin, Base):
    __tablename__ = "entry_tags"

    entry_id: Mapped[str] = mapped_column(String, nullable=False)
    tag_id: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    last_reaffirmed_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    reaffirm_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class View(IdMixin, TimestampMixin, Base):
    __tablename__ = "views"

    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extra: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    filter_spec: Mapped[Any] = mapped_column(JSON, nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)


# ---------------------------------------------------------------------------
# src/marginalia/db/models/ai_recall.py
# ---------------------------------------------------------------------------

class Journal(IdMixin, Base):
    __tablename__ = "journals"

    conversation_id: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    source_kind: Mapped[str] = mapped_column(String, nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False)
    entry_ids: Mapped[Any] = mapped_column(JSON, nullable=False, default=list)
    tags: Mapped[Any] = mapped_column(JSON, nullable=False, default=list)
    summarized_journal_ids: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    invalidated_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    invalidated_by_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    invalidated_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    superseded_by_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class EntryRelation(IdMixin, Base):
    __tablename__ = "entry_relations"

    entry_a_id: Mapped[str] = mapped_column(String, nullable=False)
    entry_b_id: Mapped[str] = mapped_column(String, nullable=False)
    source_kind: Mapped[str] = mapped_column(String, nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    last_observed_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    observation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    vetted: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    vetted_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    vetted_observation_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    vetted_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


# ---------------------------------------------------------------------------
# src/marginalia/db/models/user_visible.py
# ---------------------------------------------------------------------------

class File(IdMixin, TimestampMixin, Base):
    __tablename__ = "files"

    sha256: Mapped[str] = mapped_column(String, nullable=False)
    storage_key: Mapped[str] = mapped_column(String, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    original_ext: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    kind: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    ingest_status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    ingested_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    description: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extra: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)


class FileEntry(IdMixin, TimestampMixin, Base):
    __tablename__ = "file_entries"

    file_id: Mapped[str] = mapped_column(String, nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    folder_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    catalog_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    lifecycle: Mapped[str] = mapped_column(String, nullable=False, default="active")
    purge_after: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    extra: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)


class Folder(IdMixin, TimestampMixin, Base):
    __tablename__ = "folders"

    name: Mapped[str] = mapped_column(String, nullable=False)
    parent_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)


# ---------------------------------------------------------------------------
# src/marginalia/db/models/tasks.py
# ---------------------------------------------------------------------------

class Task(IdMixin, Base):
    __tablename__ = "tasks"

    kind: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    payload: Mapped[Any] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    scheduled_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_heartbeat_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    lease_expires_at: Mapped[Optional[datetime]] = mapped_column(UtcDateTime, nullable=True)
    locked_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    dedup_key: Mapped[Optional[str]] = mapped_column(String, nullable=True)


# ---------------------------------------------------------------------------
# src/marginalia/db/models/task_outcomes.py
# ---------------------------------------------------------------------------

class TaskOutcome(IdMixin, Base):
    __tablename__ = "task_outcomes"

    task_kind: Mapped[str] = mapped_column(String, nullable=False)
    task_run_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    object_kind: Mapped[str] = mapped_column(String, nullable=False)
    object_id: Mapped[str] = mapped_column(String, nullable=False)
    outcome: Mapped[str] = mapped_column(String, nullable=False)
    completed_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    detail: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)