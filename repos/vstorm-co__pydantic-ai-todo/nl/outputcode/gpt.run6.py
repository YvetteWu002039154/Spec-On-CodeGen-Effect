from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ValidationError, field_validator
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    delete,
    func,
    select,
    update,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker


class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    DONE = "done"
    CANCELED = "canceled"


TERMINAL_STATUSES = {TaskStatus.DONE, TaskStatus.CANCELED}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class TaskORM(Base):
    __tablename__ = "tasks"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    status: Mapped[TaskStatus] = mapped_column(SAEnum(TaskStatus, name="task_status"), nullable=False, default=TaskStatus.TODO)

    parent_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, index=True)

    metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    parent: Mapped[Optional["TaskORM"]] = relationship("TaskORM", remote_side="TaskORM.id", back_populates="children")
    children: Mapped[List["TaskORM"]] = relationship("TaskORM", back_populates="parent", cascade="all", passive_deletes=True)

    dependencies_out: Mapped[List["TaskDependencyORM"]] = relationship(
        "TaskDependencyORM",
        foreign_keys="TaskDependencyORM.task_id",
        back_populates="task",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    dependencies_in: Mapped[List["TaskDependencyORM"]] = relationship(
        "TaskDependencyORM",
        foreign_keys="TaskDependencyORM.depends_on_task_id",
        back_populates="depends_on_task",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        Index("ix_tasks_tenant_parent", "tenant_id", "parent_id"),
        Index("ix_tasks_tenant_status", "tenant_id", "status"),
    )


class TaskDependencyORM(Base):
    __tablename__ = "task_dependencies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)

    task_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    depends_on_task_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    task: Mapped[TaskORM] = relationship("TaskORM", foreign_keys=[task_id], back_populates="dependencies_out")
    depends_on_task: Mapped[TaskORM] = relationship("TaskORM", foreign_keys=[depends_on_task_id], back_populates="dependencies_in")

    __table_args__ = (
        UniqueConstraint("tenant_id", "task_id", "depends_on_task_id", name="uq_task_dependency"),
        Index("ix_task_deps_tenant_task", "tenant_id", "task_id"),
        Index("ix_task_deps_tenant_depends", "tenant_id", "depends_on_task_id"),
    )


class TaskEventType(str, Enum):
    TASK_CREATED = "task.created"
    TASK_UPDATED = "task.updated"
    TASK_DELETED = "task.deleted"
    TASK_STATUS_UPDATED = "task.status_updated"
    TASK_CHILD_CREATED = "task.child_created"
    TASK_DEPENDENCY_LINKED = "task.dependency_linked"


class TaskEvent(BaseModel):
    type: TaskEventType
    tenant_id: str
    task_id: Optional[UUID] = None
    timestamp: datetime = Field(default_factory=utcnow)
    payload: Dict[str, Any] = Field(default_factory=dict)


EventCallback = Callable[[TaskEvent], None]


class EventBus:
    def __init__(self) -> None:
        self._subscribers: Dict[TaskEventType, List[EventCallback]] = {}

    def subscribe(self, event_type: TaskEventType, callback: EventCallback) -> None:
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    def publish(self, event: TaskEvent) -> None:
        for cb in self._subscribers.get(event.type, []):
            cb(event)


class TaskCreate(BaseModel):
    tenant_id: str
    title: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.TODO
    parent_id: Optional[UUID] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("tenant_id")
    @classmethod
    def _tenant_nonempty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("tenant_id must be non-empty")
        return v

    @field_validator("title")
    @classmethod
    def _title_nonempty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("title must be non-empty")
        return v


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    parent_id: Optional[UUID] = None
    metadata: Optional[Dict[str, Any]] = None

    @field_validator("title")
    @classmethod
    def _title_nonempty(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("title must be non-empty")
        return v


class TaskRead(BaseModel):
    id: UUID
    tenant_id: str
    title: str
    description: Optional[str]
    status: TaskStatus
    parent_id: Optional[UUID]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class TaskNode(TaskRead):
    children: List["TaskNode"] = Field(default_factory=list)


TaskNode.model_rebuild()


class TaskNotFoundError(Exception):
    pass


class TaskValidationError(Exception):
    pass


class DependencyError(Exception):
    pass


class StorageError(Exception):
    pass


class TodoToolset:
    def __init__(self, engine: Engine, event_bus: Optional[EventBus] = None) -> None:
        self._engine = engine
        self._Session = sessionmaker(bind=self._engine, expire_on_commit=False, future=True)
        self._events = event_bus or EventBus()

    @property
    def events(self) -> EventBus:
        return self._events

    def create_schema(self) -> None:
        Base.metadata.create_all(self._engine)

    def drop_schema(self) -> None:
        Base.metadata.drop_all(self._engine)

    def add_task(self, task: TaskCreate) -> TaskRead:
        try:
            task = TaskCreate.model_validate(task)
        except ValidationError as e:
            raise TaskValidationError(str(e)) from e

        with self._Session() as session:
            if task.parent_id is not None:
                parent = session.execute(
                    select(TaskORM.id).where(TaskORM.tenant_id == task.tenant_id, TaskORM.id == task.parent_id)
                ).scalar_one_or_none()
                if parent is None:
                    raise TaskValidationError("parent task not found for tenant")

            orm = TaskORM(
                tenant_id=task.tenant_id,
                title=task.title,
                description=task.description,
                status=task.status,
                parent_id=task.parent_id,
                metadata=task.metadata or {},
            )
            session.add(orm)
            session.commit()

            read = self._to_read(orm)
            self._events.publish(
                TaskEvent(
                    type=TaskEventType.TASK_CREATED,
                    tenant_id=read.tenant_id,
                    task_id=read.id,
                    payload={"task": read.model_dump(mode="json")},
                )
            )
            return read

    def bulk_write_tasks(self, tasks: Sequence[TaskCreate]) -> List[TaskRead]:
        validated: List[TaskCreate] = []
        for t in tasks:
            try:
                validated.append(TaskCreate.model_validate(t))
            except ValidationError as e:
                raise TaskValidationError(str(e)) from e

        if not validated:
            return []

        tenant_ids = {t.tenant_id for t in validated}
        if len(tenant_ids) != 1:
            raise TaskValidationError("bulk_write_tasks requires all tasks to share the same tenant_id")
        tenant_id = next(iter(tenant_ids))

        with self._Session() as session:
            parent_ids = {t.parent_id for t in validated if t.parent_id is not None}
            if parent_ids:
                existing = set(
                    session.execute(
                        select(TaskORM.id).where(TaskORM.tenant_id == tenant_id, TaskORM.id.in_(parent_ids))
                    ).scalars()
                )
                missing = parent_ids - existing
                if missing:
                    raise TaskValidationError("one or more parent tasks not found for tenant")

            orms = [
                TaskORM(
                    tenant_id=t.tenant_id,
                    title=t.title,
                    description=t.description,
                    status=t.status,
                    parent_id=t.parent_id,
                    metadata=t.metadata or {},
                )
                for t in validated
            ]
            session.add_all(orms)
            session.commit()

            reads = [self._to_read(o) for o in orms]
            for r in reads:
                self._events.publish(
                    TaskEvent(
                        type=TaskEventType.TASK_CREATED,
                        tenant_id=r.tenant_id,
                        task_id=r.id,
                        payload={"task": r.model_dump(mode="json")},
                    )
                )
            return reads

    def list_all_tasks(self, tenant_id: str, hierarchical: bool = False) -> List[Union[TaskRead, TaskNode]]:
        tenant_id = tenant_id.strip()
        if not tenant_id:
            raise TaskValidationError("tenant_id must be non-empty")

        with self._Session() as session:
            tasks = session.execute(select(TaskORM).where(TaskORM.tenant_id == tenant_id).order_by(TaskORM.created_at.asc())).scalars().all()

        if not hierarchical:
            return [self._to_read(t) for t in tasks]

        nodes: Dict[UUID, TaskNode] = {}
        for t in tasks:
            nodes[t.id] = TaskNode(**self._to_read(t).model_dump())

        roots: List[TaskNode] = []
        for t in tasks:
            node = nodes[t.id]
            if t.parent_id is None:
                roots.append(node)
            else:
                parent = nodes.get(t.parent_id)
                if parent is None:
                    roots.append(node)
                else:
                    parent.children.append(node)

        return roots

    def update_task(self, tenant_id: str, task_id: UUID, patch: TaskUpdate) -> TaskRead:
        tenant_id = tenant_id.strip()
        if not tenant_id:
            raise TaskValidationError("tenant_id must be non-empty")

        try:
            patch = TaskUpdate.model_validate(patch)
        except ValidationError as e:
            raise TaskValidationError(str(e)) from e

        with self._Session() as session:
            orm = session.execute(
                select(TaskORM).where(TaskORM.tenant_id == tenant_id, TaskORM.id == task_id)
            ).scalar_one_or_none()
            if orm is None:
                raise TaskNotFoundError("task not found")

            if patch.parent_id is not None:
                if patch.parent_id == orm.id:
                    raise TaskValidationError("task cannot be its own parent")
                parent = session.execute(
                    select(TaskORM).where(TaskORM.tenant_id == tenant_id, TaskORM.id == patch.parent_id)
                ).scalar_one_or_none()
                if parent is None:
                    raise TaskValidationError("parent task not found for tenant")
                if self._would_create_cycle(session, tenant_id, orm.id, patch.parent_id):
                    raise TaskValidationError("parent assignment would create a cycle")

            if patch.title is not None:
                orm.title = patch.title
            if patch.description is not None:
                orm.description = patch.description
            if patch.status is not None:
                orm.status = patch.status
            if patch.parent_id is not None or patch.parent_id is None:
                if patch.parent_id is not None:
                    orm.parent_id = patch.parent_id
            if patch.metadata is not None:
                orm.metadata = patch.metadata

            session.commit()
            read = self._to_read(orm)
            self._events.publish(
                TaskEvent(
                    type=TaskEventType.TASK_UPDATED,
                    tenant_id=tenant_id,
                    task_id=task_id,
                    payload={"task": read.model_dump(mode="json")},
                )
            )
            return read

    def update_task_status_by_id(self, tenant_id: str, task_id: UUID, status: TaskStatus) -> TaskRead:
        tenant_id = tenant_id.strip()
        if not tenant_id:
            raise TaskValidationError("tenant_id must be non-empty")

        if not isinstance(status, TaskStatus):
            try:
                status = TaskStatus(str(status))
            except Exception as e:
                raise TaskValidationError("invalid status") from e

        with self._Session() as session:
            orm = session.execute(
                select(TaskORM).where(TaskORM.tenant_id == tenant_id, TaskORM.id == task_id)
            ).scalar_one_or_none()
            if orm is None:
                raise TaskNotFoundError("task not found")

            orm.status = status
            session.commit()

            read = self._to_read(orm)
            self._events.publish(
                TaskEvent(
                    type=TaskEventType.TASK_STATUS_UPDATED,
                    tenant_id=tenant_id,
                    task_id=task_id,
                    payload={"task": read.model_dump(mode="json"), "status": status.value},
                )
            )
            return read

    def delete_task_by_id(self, tenant_id: str, task_id: UUID) -> None:
        tenant_id = tenant_id.strip()
        if not tenant_id:
            raise TaskValidationError("tenant_id must be non-empty")

        with self._Session() as session:
            orm = session.execute(
                select(TaskORM).where(TaskORM.tenant_id == tenant_id, TaskORM.id == task_id)
            ).scalar_one_or_none()
            if orm is None:
                raise TaskNotFoundError("task not found")

            session.delete(orm)
            session.commit()

            self._events.publish(
                TaskEvent(
                    type=TaskEventType.TASK_DELETED,
                    tenant_id=tenant_id,
                    task_id=task_id,
                    payload={},
                )
            )

    def create_child_task(self, tenant_id: str, parent_id: UUID, child: TaskCreate) -> TaskRead:
        tenant_id = tenant_id.strip()
        if not tenant_id:
            raise TaskValidationError("tenant_id must be non-empty")

        try:
            child = TaskCreate.model_validate(child)
        except ValidationError as e:
            raise TaskValidationError(str(e)) from e

        if child.tenant_id != tenant_id:
            raise TaskValidationError("child task tenant_id must match tenant_id")

        with self._Session() as session:
            parent = session.execute(
                select(TaskORM).where(TaskORM.tenant_id == tenant_id, TaskORM.id == parent_id)
            ).scalar_one_or_none()
            if parent is None:
                raise TaskValidationError("parent task not found for tenant")

            orm = TaskORM(
                tenant_id=tenant_id,
                title=child.title,
                description=child.description,
                status=child.status,
                parent_id=parent_id,
                metadata=child.metadata or {},
            )
            session.add(orm)
            session.commit()

            read = self._to_read(orm)
            self._events.publish(
                TaskEvent(
                    type=TaskEventType.TASK_CHILD_CREATED,
                    tenant_id=tenant_id,
                    task_id=read.id,
                    payload={"parent_id": str(parent_id), "task": read.model_dump(mode="json")},
                )
            )
            return read

    def link_tasks_with_dependency(self, tenant_id: str, task_id: UUID, depends_on_task_id: UUID) -> None:
        tenant_id = tenant_id.strip()
        if not tenant_id:
            raise TaskValidationError("tenant_id must be non-empty")
        if task_id == depends_on_task_id:
            raise DependencyError("task cannot depend on itself")

        with self._Session() as session:
            t1 = session.execute(
                select(TaskORM.id).where(TaskORM.tenant_id == tenant_id, TaskORM.id == task_id)
            ).scalar_one_or_none()
            t2 = session.execute(
                select(TaskORM.id).where(TaskORM.tenant_id == tenant_id, TaskORM.id == depends_on_task_id)
            ).scalar_one_or_none()
            if t1 is None or t2 is None:
                raise TaskNotFoundError("task or dependency task not found")

            if self._dependency_would_create_cycle(session, tenant_id, task_id, depends_on_task_id):
                raise DependencyError("dependency would create a cycle")

            dep = TaskDependencyORM(tenant_id=tenant_id, task_id=task_id, depends_on_task_id=depends_on_task_id)
            session.add(dep)
            try:
                session.commit()
            except IntegrityError as e:
                session.rollback()
                raise DependencyError("dependency already exists") from e

            self._events.publish(
                TaskEvent(
                    type=TaskEventType.TASK_DEPENDENCY_LINKED,
                    tenant_id=tenant_id,
                    task_id=task_id,
                    payload={"depends_on_task_id": str(depends_on_task_id)},
                )
            )

    def list_tasks_ready_to_work_on(self, tenant_id: str) -> List[TaskRead]:
        tenant_id = tenant_id.strip()
        if not tenant_id:
            raise TaskValidationError("tenant_id must be non-empty")

        with self._Session() as session:
            candidates = session.execute(
                select(TaskORM).where(
                    TaskORM.tenant_id == tenant_id,
                    TaskORM.status.in_([TaskStatus.TODO, TaskStatus.IN_PROGRESS]),
                )
            ).scalars().all()

            if not candidates:
                return []

            ids = [t.id for t in candidates]
            deps = session.execute(
                select(TaskDependencyORM.task_id, TaskDependencyORM.depends_on_task_id).where(
                    TaskDependencyORM.tenant_id == tenant_id,
                    TaskDependencyORM.task_id.in_(ids),
                )
            ).all()

            dep_map: Dict[UUID, List[UUID]] = {}
            for task_id, depends_id in deps:
                dep_map.setdefault(task_id, []).append(depends_id)

            dep_ids = {d for ds in dep_map.values() for d in ds}
            dep_status: Dict[UUID, TaskStatus] = {}
            if dep_ids:
                rows = session.execute(
                    select(TaskORM.id, TaskORM.status).where(TaskORM.tenant_id == tenant_id, TaskORM.id.in_(dep_ids))
                ).all()
                dep_status = {rid: st for rid, st in rows}

            ready: List[TaskORM] = []
            for t in candidates:
                deps_for_t = dep_map.get(t.id, [])
                if all(dep_status.get(d) in TERMINAL_STATUSES for d in deps_for_t):
                    ready.append(t)

            ready.sort(key=lambda x: x.created_at)
            return [self._to_read(t) for t in ready]

    def _to_read(self, orm: TaskORM) -> TaskRead:
        return TaskRead(
            id=orm.id,
            tenant_id=orm.tenant_id,
            title=orm.title,
            description=orm.description,
            status=orm.status,
            parent_id=orm.parent_id,
            metadata=orm.metadata or {},
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    def _would_create_cycle(self, session: Session, tenant_id: str, task_id: UUID, new_parent_id: UUID) -> bool:
        current = new_parent_id
        visited: set[UUID] = set()
        while current is not None:
            if current == task_id:
                return True
            if current in visited:
                return True
            visited.add(current)
            current = session.execute(
                select(TaskORM.parent_id).where(TaskORM.tenant_id == tenant_id, TaskORM.id == current)
            ).scalar_one_or_none()
        return False

    def _dependency_would_create_cycle(self, session: Session, tenant_id: str, task_id: UUID, depends_on_task_id: UUID) -> bool:
        stack = [depends_on_task_id]
        visited: set[UUID] = set()
        while stack:
            cur = stack.pop()
            if cur == task_id:
                return True
            if cur in visited:
                continue
            visited.add(cur)
            nexts = session.execute(
                select(TaskDependencyORM.depends_on_task_id).where(
                    TaskDependencyORM.tenant_id == tenant_id,
                    TaskDependencyORM.task_id == cur,
                )
            ).scalars().all()
            stack.extend(nexts)
        return False


def create_postgres_engine(
    dsn: str,
    *,
    echo: bool = False,
    pool_pre_ping: bool = True,
) -> Engine:
    return create_engine(dsn, echo=echo, future=True, pool_pre_ping=pool_pre_ping)