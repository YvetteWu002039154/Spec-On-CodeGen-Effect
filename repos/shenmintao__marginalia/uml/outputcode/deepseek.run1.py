# marginalia/__init__.py

# marginalia/db/__init__.py

# marginalia/db/models/__init__.py

# marginalia/db/models/base.py
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, MetaData, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator


class UtcDateTime(TypeDecorator):
    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Any) -> datetime | None:
        if value is not None:
            if value.tzinfo is None:
                value = value.replace(tzinfo=__import__('datetime').timezone.utc)
            return value.astimezone(__import__('datetime').timezone.utc).replace(tzinfo=None)
        return value

    def process_result_value(self, value: datetime | None, dialect: Any) -> datetime | None:
        if value is not None:
            return value.replace(tzinfo=__import__('datetime').timezone.utc)
        return value


class Base(DeclarativeBase):
    metadata = MetaData()
    type_annotation_map = {
        Any: __import__('sqlalchemy').JSON,
    }


class IdMixin:
    id: Mapped[str] = mapped_column(String, primary_key=True, default=__import__('uuid').uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=__import__('datetime').datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime, default=__import__('datetime').datetime.utcnow, onupdate=__import__('datetime').datetime.utcnow)


# marginalia/db/models/ai_structural.py
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, IdMixin, TimestampMixin


class Catalog(Base, IdMixin, TimestampMixin):
    __tablename__ = "catalog"

    deleted_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    description: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    extra: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    name: Mapped[str] = mapped_column(String(255))
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("catalog.id"), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[Any | None] = mapped_column(JSON, nullable=True)


class Tag(Base, IdMixin, TimestampMixin):
    __tablename__ = "tag"

    alias_of: Mapped[str | None] = mapped_column(ForeignKey("tag.id"), nullable=True)
    doc_count: Mapped[int] = mapped_column(default=0)
    facet: Mapped[str] = mapped_column(String(100))
    last_reaffirmed_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    reaffirm_count: Mapped[int] = mapped_column(default=0)


class TagAlias(Base, IdMixin):
    __tablename__ = "tag_alias"

    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=datetime.utcnow)
    from_name: Mapped[str] = mapped_column(String(255))
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    to_tag_id: Mapped[str] = mapped_column(ForeignKey("tag.id"))


class EntryTag(Base, IdMixin):
    __tablename__ = "entry_tag"

    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=datetime.utcnow)
    entry_id: Mapped[str] = mapped_column(String, index=True)
    last_reaffirmed_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    reaffirm_count: Mapped[int] = mapped_column(default=0)
    source: Mapped[str] = mapped_column(String(50))
    tag_id: Mapped[str] = mapped_column(ForeignKey("tag.id"))


class View(Base, IdMixin, TimestampMixin):
    __tablename__ = "view"

    deleted_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    description: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    extra: Mapped[str | None] = mapped_column(Text, nullable=True)
    filter_spec: Mapped[Any] = mapped_column(JSON)
    name: Mapped[str] = mapped_column(String(255))
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[Any | None] = mapped_column(JSON, nullable=True)


# marginalia/db/models/ai_recall.py
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, IdMixin, TimestampMixin, UtcDateTime


class EntryRelation(Base, IdMixin):
    __tablename__ = "entry_relation"

    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=datetime.utcnow)
    entry_a_id: Mapped[str] = mapped_column(String, nullable=False)
    entry_b_id: Mapped[str] = mapped_column(String, nullable=False)
    last_observed_at: Mapped[datetime] = mapped_column(UtcDateTime, default=datetime.utcnow)
    note: Mapped[str] = mapped_column(Text, default="")
    observation_count: Mapped[int] = mapped_column(default=0)
    source_kind: Mapped[str] = mapped_column(String(50))
    vetted: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    vetted_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    vetted_observation_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    vetted_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class Journal(Base, IdMixin):
    __tablename__ = "journal"

    conversation_id: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=datetime.utcnow)
    entry_ids: Mapped[Any] = mapped_column(JSON)
    invalidated_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    invalidated_by_id: Mapped[str | None] = mapped_column(String, nullable=True)
    invalidated_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    note: Mapped[str] = mapped_column(Text, default="")
    source_kind: Mapped[str] = mapped_column(String(50))
    summarized_journal_ids: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    superseded_by_id: Mapped[str | None] = mapped_column(ForeignKey("journal.id"), nullable=True)
    tags: Mapped[Any] = mapped_column(JSON)


# marginalia/db/models/audit.py
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, Integer, Numeric, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, IdMixin, UtcDateTime


class Session(Base, IdMixin):
    __tablename__ = "session"

    deleted_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    end_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    initiating_user_message: Mapped[str] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(UtcDateTime, default=datetime.utcnow)
    total_cache_read: Mapped[int] = mapped_column(default=0)
    total_cost_estimate: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal('0'))
    total_duration_ms: Mapped[int] = mapped_column(default=0)
    total_input_tokens: Mapped[int] = mapped_column(default=0)
    total_llm_calls: Mapped[int] = mapped_column(default=0)
    total_output_tokens: Mapped[int] = mapped_column(default=0)
    total_tool_calls: Mapped[int] = mapped_column(default=0)
    turn_count: Mapped[int] = mapped_column(default=0)


class Conversation(Base, IdMixin):
    __tablename__ = "conversation"

    agent_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    llm_calls: Mapped[Any] = mapped_column(JSON)
    session_id: Mapped[str] = mapped_column(ForeignKey("session.id"))
    started_at: Mapped[datetime] = mapped_column(UtcDateTime, default=datetime.utcnow)
    tool_calls: Mapped[Any] = mapped_column(JSON)
    total_cache_read: Mapped[int] = mapped_column(default=0)
    total_cost_estimate: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal('0'))
    total_duration_ms: Mapped[int] = mapped_column(default=0)
    total_input_tokens: Mapped[int] = mapped_column(default=0)
    total_llm_calls: Mapped[int] = mapped_column(default=0)
    total_output_tokens: Mapped[int] = mapped_column(default=0)
    total_tool_calls: Mapped[int] = mapped_column(default=0)
    turn_index: Mapped[int] = mapped_column()
    user_message: Mapped[str] = mapped_column(Text)


class AuditEvent(Base, IdMixin):
    __tablename__ = "audit_event"

    conversation_id: Mapped[str | None] = mapped_column(ForeignKey("conversation.id"), nullable=True)
    kind: Mapped[str] = mapped_column(String(50))
    occurred_at: Mapped[datetime] = mapped_column(UtcDateTime, default=datetime.utcnow)
    payload: Mapped[Any] = mapped_column(JSON)
    session_id: Mapped[str | None] = mapped_column(ForeignKey("session.id"), nullable=True)
    task_id: Mapped[str | None] = mapped_column(String, nullable=True)


# marginalia/db/models/tasks.py
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, IdMixin, UtcDateTime


class Task(Base, IdMixin):
    __tablename__ = "task"

    attempts: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=datetime.utcnow)
    dedup_key: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    finished_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    kind: Mapped[str] = mapped_column(String(100))
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    locked_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    max_attempts: Mapped[int] = mapped_column(default=3)
    payload: Mapped[Any] = mapped_column(JSON)
    priority: Mapped[int] = mapped_column(default=0)
    scheduled_at: Mapped[datetime] = mapped_column(UtcDateTime, default=datetime.utcnow)
    started_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")


# marginalia/db/models/task_outcomes.py
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, IdMixin, UtcDateTime


class TaskOutcome(Base, IdMixin):
    __tablename__ = "task_outcome"

    completed_at: Mapped[datetime] = mapped_column(UtcDateTime, default=datetime.utcnow)
    detail: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    object_id: Mapped[str] = mapped_column(String)
    object_kind: Mapped[str] = mapped_column(String(100))
    outcome: Mapped[str] = mapped_column(String(50))
    task_kind: Mapped[str] = mapped_column(String(100))
    task_run_id: Mapped[str | None] = mapped_column(String, nullable=True)


# marginalia/db/models/user_visible.py
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text, JSON, BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, IdMixin, TimestampMixin, UtcDateTime


class Folder(Base, IdMixin, TimestampMixin):
    __tablename__ = "folder"

    deleted_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    name: Mapped[str] = mapped_column(String(255))
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("folder.id"), nullable=True)


class File(Base, IdMixin, TimestampMixin):
    __tablename__ = "file"

    deleted_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    description: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    extra: Mapped[str | None] = mapped_column(Text, nullable=True)
    ingest_status: Mapped[str] = mapped_column(String(50), default="pending")
    ingested_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    kind: Mapped[str | None] = mapped_column(String(50), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    original_ext: Mapped[str | None] = mapped_column(String(10), nullable=True)
    sha256: Mapped[str] = mapped_column(String(64), unique=True)
    size_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    storage_key: Mapped[str] = mapped_column(String(500))
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)


class FileEntry(Base, IdMixin, TimestampMixin):
    __tablename__ = "file_entry"

    catalog_id: Mapped[str | None] = mapped_column(ForeignKey("catalog.id"), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    display_name: Mapped[str] = mapped_column(String(255))
    extra: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_id: Mapped[str] = mapped_column(ForeignKey("file.id"))
    folder_id: Mapped[str | None] = mapped_column(ForeignKey("folder.id"), nullable=True)
    lifecycle: Mapped[str] = mapped_column(String(50), default="active")
    purge_after: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)