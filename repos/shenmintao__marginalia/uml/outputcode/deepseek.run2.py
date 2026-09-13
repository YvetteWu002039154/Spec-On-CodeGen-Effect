# src/marginalia/db/models/base.py
import datetime
import uuid
from typing import Any

from sqlalchemy import DateTime, MetaData, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator


class Base(DeclarativeBase):
    metadata: MetaData = MetaData()
    type_annotation_map: dict[Any, Any] = {}


class IdMixin:
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )


class TimestampMixin:
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


class UtcDateTime(TypeDecorator):
    cache_ok: bool = True
    impl = DateTime

    def process_bind_param(self, value, dialect) -> Any:
        if value is not None and value.tzinfo is not None:
            value = value.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        return value

    def process_result_value(self, value, dialect) -> Any:
        if value is not None:
            value = value.replace(tzinfo=datetime.timezone.utc)
        return value


# src/marginalia/db/models/audit.py
import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, DateTime, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, IdMixin


class AuditEvent(IdMixin, Base):
    __tablename__ = "audit_event"

    conversation_id: Mapped[str | None] = mapped_column(String, nullable=True)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    occurred_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    payload: Mapped[Any] = mapped_column(JSON, nullable=False)
    session_id: Mapped[str | None] = mapped_column(String, nullable=True)
    task_id: Mapped[str | None] = mapped_column(String, nullable=True)


class Conversation(IdMixin, Base):
    __tablename__ = "conversation"

    agent_response: Mapped[str | None] = mapped_column(String, nullable=True)
    ended_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    llm_calls: Mapped[Any] = mapped_column(JSON, nullable=False)
    session_id: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    tool_calls: Mapped[Any] = mapped_column(JSON, nullable=False)
    total_cache_read: Mapped[int] = mapped_column(Integer, nullable=False)
    total_cost_estimate: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    total_duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    total_input_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    total_llm_calls: Mapped[int] = mapped_column(Integer, nullable=False)
    total_output_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    total_tool_calls: Mapped[int] = mapped_column(Integer, nullable=False)
    turn_index: Mapped[int] = mapped_column(Integer, nullable=False)
    user_message: Mapped[str] = mapped_column(String, nullable=False)


class Session(IdMixin, Base):
    __tablename__ = "session"

    deleted_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    end_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    ended_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    initiating_user_message: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    total_cache_read: Mapped[int] = mapped_column(Integer, nullable=False)
    total_cost_estimate: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    total_duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    total_input_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    total_llm_calls: Mapped[int] = mapped_column(Integer, nullable=False)
    total_output_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    total_tool_calls: Mapped[int] = mapped_column(Integer, nullable=False)
    turn_count: Mapped[int] = mapped_column(Integer, nullable=False)


# src/marginalia/db/models/ai_structural.py
import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, IdMixin


class Catalog(IdMixin, Base):
    __tablename__ = "catalog"

    deleted_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    description: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    extra: Mapped[str | None] = mapped_column(String, nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    parent_id: Mapped[str | None] = mapped_column(String, nullable=True)
    summary: Mapped[str | None] = mapped_column(String, nullable=True)
    tags: Mapped[Any | None] = mapped_column(JSON, nullable=True)


class EntryTag(IdMixin, Base):
    __tablename__ = "entry_tag"

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    entry_id: Mapped[str] = mapped_column(String, nullable=False)
    last_reaffirmed_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    reaffirm_count: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    tag_id: Mapped[str] = mapped_column(String, nullable=False)


class Tag(IdMixin, Base):
    __tablename__ = "tag"

    alias_of: Mapped[str | None] = mapped_column(String, nullable=True)
    doc_count: Mapped[int] = mapped_column(Integer, nullable=False)
    facet: Mapped[str] = mapped_column(String, nullable=False)
    last_reaffirmed_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    last_used_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    reaffirm_count: Mapped[int] = mapped_column(Integer, nullable=False)


class TagAlias(IdMixin, Base):
    __tablename__ = "tag_alias"

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    from_name: Mapped[str] = mapped_column(String, nullable=False)
    note: Mapped[str | None] = mapped_column(String, nullable=True)
    to_tag_id: Mapped[str] = mapped_column(String, nullable=False)


class View(IdMixin, Base):
    __tablename__ = "view"

    deleted_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    description: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    extra: Mapped[str | None] = mapped_column(String, nullable=True)
    filter_spec: Mapped[Any] = mapped_column(JSON, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    summary: Mapped[str | None] = mapped_column(String, nullable=True)
    tags: Mapped[Any | None] = mapped_column(JSON, nullable=True)


# src/marginalia/db/models/ai_recall.py
import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, IdMixin


class EntryRelation(IdMixin, Base):
    __tablename__ = "entry_relation"

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    entry_a_id: Mapped[str] = mapped_column(String, nullable=False)
    entry_b_id: Mapped[str] = mapped_column(String, nullable=False)
    last_observed_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    note: Mapped[str] = mapped_column(String, nullable=False)
    observation_count: Mapped[int] = mapped_column(Integer, nullable=False)
    source_kind: Mapped[str] = mapped_column(String, nullable=False)
    vetted: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    vetted_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    vetted_observation_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    vetted_reason: Mapped[str | None] = mapped_column(String, nullable=True)


class Journal(IdMixin, Base):
    __tablename__ = "journal"

    conversation_id: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    entry_ids: Mapped[Any] = mapped_column(JSON, nullable=False)
    invalidated_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    invalidated_by_id: Mapped[str | None] = mapped_column(String, nullable=True)
    invalidated_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    note: Mapped[str] = mapped_column(String, nullable=False)
    source_kind: Mapped[str] = mapped_column(String, nullable=False)
    summarized_journal_ids: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    superseded_by_id: Mapped[str | None] = mapped_column(String, nullable=True)
    tags: Mapped[Any] = mapped_column(JSON, nullable=False)


# src/marginalia/db/models/user_visible.py
import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, IdMixin


class File(IdMixin, Base):
    __tablename__ = "file"

    deleted_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    description: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    extra: Mapped[str | None] = mapped_column(String, nullable=True)
    ingest_status: Mapped[str] = mapped_column(String, nullable=False)
    ingested_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    kind: Mapped[str | None] = mapped_column(String, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String, nullable=True)
    original_ext: Mapped[str | None] = mapped_column(String, nullable=True)
    sha256: Mapped[str] = mapped_column(String, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_key: Mapped[str] = mapped_column(String, nullable=False)
    summary: Mapped[str | None] = mapped_column(String, nullable=True)


class FileEntry(IdMixin, Base):
    __tablename__ = "file_entry"

    catalog_id: Mapped[str | None] = mapped_column(String, nullable=True)
    deleted_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    extra: Mapped[str | None] = mapped_column(String, nullable=True)
    file_id: Mapped[str] = mapped_column(String, nullable=False)
    folder_id: Mapped[str | None] = mapped_column(String, nullable=True)
    lifecycle: Mapped[str] = mapped_column(String, nullable=False)
    purge_after: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)


class Folder(IdMixin, Base):
    __tablename__ = "folder"

    deleted_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    parent_id: Mapped[str | None] = mapped_column(String, nullable=True)


# src/marginalia/db/models/tasks.py
import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, IdMixin


class Task(IdMixin, Base):
    __tablename__ = "task"

    attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    dedup_key: Mapped[str | None] = mapped_column(String, nullable=True)
    finished_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    last_error: Mapped[str | None] = mapped_column(String, nullable=True)
    last_heartbeat_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    lease_expires_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    locked_by: Mapped[str | None] = mapped_column(String, nullable=True)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[Any] = mapped_column(JSON, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False)
    scheduled_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    started_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False)


# src/marginalia/db/models/task_outcomes.py
import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, IdMixin


class TaskOutcome(IdMixin, Base):
    __tablename__ = "task_outcome"

    completed_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    detail: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    object_id: Mapped[str] = mapped_column(String, nullable=False)
    object_kind: Mapped[str] = mapped_column(String, nullable=False)
    outcome: Mapped[str] = mapped_column(String, nullable=False)
    task_kind: Mapped[str] = mapped_column(String, nullable=False)
    task_run_id: Mapped[str | None] = mapped_column(String, nullable=True)