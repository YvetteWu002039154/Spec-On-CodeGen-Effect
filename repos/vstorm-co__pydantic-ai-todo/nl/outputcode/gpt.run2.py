from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator


class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    DONE = "done"
    CANCELED = "canceled"


class TaskEventType(str, Enum):
    TASK_CREATED = "task_created"
    TASK_UPDATED = "task_updated"
    TASK_DELETED = "task_deleted"
    TASK_STATUS_CHANGED = "task_status_changed"
    DEPENDENCY_LINKED = "dependency_linked"
    CHILD_CREATED = "child_created"
    BULK_UPSERT = "bulk_upsert"


class TodoToolsetError(Exception):
    pass


class NotFoundError(TodoToolsetError):
    pass


class ValidationRuleError(TodoToolsetError):
    pass


class ConflictError(TodoToolsetError):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TaskCreate(BaseModel):
    title: str = Field(min_length=1)
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.TODO
    parent_id: Optional[UUID] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("title")
    @classmethod
    def _strip_title(cls, v: str) -> str:
        v2 = v.strip()
        if not v2:
            raise ValueError("title must not be empty")
        return v2


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1)
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    metadata: Optional[Dict[str, Any]] = None

    @field_validator("title")
    @classmethod
    def _strip_title(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v2 = v.strip()
        if not v2:
            raise ValueError("title must not be empty")
        return v2


class TaskBulkUpsertItem(BaseModel):
    id: Optional[UUID] = None
    title: str = Field(min_length=1)
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.TODO
    parent_id: Optional[UUID] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("title")
    @classmethod
    def _strip_title(cls, v: str) -> str:
        v2 = v.strip()
        if not v2:
            raise ValueError("title must not be empty")
        return v2


class Task(BaseModel):
    id: UUID
    tenant_id: str
    title: str
    description: Optional[str] = None
    status: TaskStatus
    parent_id: Optional[UUID] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def _validate_timestamps(self) -> "Task":
        if self.updated_at < self.created_at:
            raise ValueError("updated_at must be >= created_at")
        return self


class TaskNode(BaseModel):
    task: Task
    children: List["TaskNode"] = Field(default_factory=list)


TaskNode.model_rebuild()


class TaskDependency(BaseModel):
    tenant_id: str
    task_id: UUID
    depends_on_id: UUID
    created_at: datetime


class TaskEvent(BaseModel):
    id: UUID
    tenant_id: str
    type: TaskEventType
    task_id: Optional[UUID] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


EventCallback = Callable[[TaskEvent], None]


class EventBus:
    def __init__(self) -> None:
        self._subscribers: Dict[TaskEventType, List[EventCallback]] = {t: [] for t in TaskEventType}

    def subscribe(self, event_type: TaskEventType, callback: EventCallback) -> None:
        if callback not in self._subscribers[event_type]:
            self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: TaskEventType, callback: EventCallback) -> None:
        if callback in self._subscribers[event_type]:
            self._subscribers[event_type].remove(callback)

    def publish(self, event: TaskEvent) -> None:
        for cb in list(self._subscribers.get(event.type, [])):
            cb(event)


class TaskRepository:
    def add_task(self, task: Task) -> None:
        raise NotImplementedError

    def get_task(self, tenant_id: str, task_id: UUID) -> Task:
        raise NotImplementedError

    def list_tasks(self, tenant_id: str) -> List[Task]:
        raise NotImplementedError

    def update_task(self, tenant_id: str, task: Task) -> None:
        raise NotImplementedError

    def delete_task(self, tenant_id: str, task_id: UUID) -> None:
        raise NotImplementedError

    def bulk_upsert(self, tenant_id: str, tasks: Sequence[Task]) -> None:
        raise NotImplementedError

    def add_dependency(self, dep: TaskDependency) -> None:
        raise NotImplementedError

    def list_dependencies(self, tenant_id: str) -> List[TaskDependency]:
        raise NotImplementedError

    def delete_dependencies_for_task(self, tenant_id: str, task_id: UUID) -> None:
        raise NotImplementedError

    def delete_dependencies_involving_task(self, tenant_id: str, task_id: UUID) -> None:
        raise NotImplementedError


class InMemoryTaskRepository(TaskRepository):
    def __init__(self) -> None:
        self._tasks: Dict[Tuple[str, UUID], Task] = {}
        self._deps: Dict[Tuple[str, UUID, UUID], TaskDependency] = {}

    def add_task(self, task: Task) -> None:
        key = (task.tenant_id, task.id)
        if key in self._tasks:
            raise ConflictError("task already exists")
        self._tasks[key] = task

    def get_task(self, tenant_id: str, task_id: UUID) -> Task:
        key = (tenant_id, task_id)
        if key not in self._tasks:
            raise NotFoundError("task not found")
        return self._tasks[key]

    def list_tasks(self, tenant_id: str) -> List[Task]:
        return [t for (tid, _), t in self._tasks.items() if tid == tenant_id]

    def update_task(self, tenant_id: str, task: Task) -> None:
        key = (tenant_id, task.id)
        if key not in self._tasks:
            raise NotFoundError("task not found")
        self._tasks[key] = task

    def delete_task(self, tenant_id: str, task_id: UUID) -> None:
        key = (tenant_id, task_id)
        if key not in self._tasks:
            raise NotFoundError("task not found")
        del self._tasks[key]

    def bulk_upsert(self, tenant_id: str, tasks: Sequence[Task]) -> None:
        for t in tasks:
            key = (tenant_id, t.id)
            self._tasks[key] = t

    def add_dependency(self, dep: TaskDependency) -> None:
        key = (dep.tenant_id, dep.task_id, dep.depends_on_id)
        self._deps[key] = dep

    def list_dependencies(self, tenant_id: str) -> List[TaskDependency]:
        return [d for (tid, _, _), d in self._deps.items() if tid == tenant_id]

    def delete_dependencies_for_task(self, tenant_id: str, task_id: UUID) -> None:
        to_del = [k for k in self._deps.keys() if k[0] == tenant_id and k[1] == task_id]
        for k in to_del:
            del self._deps[k]

    def delete_dependencies_involving_task(self, tenant_id: str, task_id: UUID) -> None:
        to_del = [k for k in self._deps.keys() if k[0] == tenant_id and (k[1] == task_id or k[2] == task_id)]
        for k in to_del:
            del self._deps[k]


class PostgresTaskRepository(TaskRepository):
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        raise NotImplementedError("PostgreSQL repository is not implemented in this package")

    def add_task(self, task: Task) -> None:
        raise NotImplementedError

    def get_task(self, tenant_id: str, task_id: UUID) -> Task:
        raise NotImplementedError

    def list_tasks(self, tenant_id: str) -> List[Task]:
        raise NotImplementedError

    def update_task(self, tenant_id: str, task: Task) -> None:
        raise NotImplementedError

    def delete_task(self, tenant_id: str, task_id: UUID) -> None:
        raise NotImplementedError

    def bulk_upsert(self, tenant_id: str, tasks: Sequence[Task]) -> None:
        raise NotImplementedError

    def add_dependency(self, dep: TaskDependency) -> None:
        raise NotImplementedError

    def list_dependencies(self, tenant_id: str) -> List[TaskDependency]:
        raise NotImplementedError

    def delete_dependencies_for_task(self, tenant_id: str, task_id: UUID) -> None:
        raise NotImplementedError

    def delete_dependencies_involving_task(self, tenant_id: str, task_id: UUID) -> None:
        raise NotImplementedError


class TodoToolset:
    def __init__(self, repository: TaskRepository, event_bus: Optional[EventBus] = None) -> None:
        self._repo = repository
        self._events = event_bus or EventBus()

    @property
    def event_bus(self) -> EventBus:
        return self._events

    def add_task(self, tenant_id: str, data: Union[TaskCreate, Dict[str, Any]]) -> Task:
        if isinstance(data, dict):
            data = TaskCreate.model_validate(data)
        now = _utcnow()
        task = Task(
            id=uuid4(),
            tenant_id=tenant_id,
            title=data.title,
            description=data.description,
            status=data.status,
            parent_id=data.parent_id,
            metadata=dict(data.metadata),
            created_at=now,
            updated_at=now,
        )
        if task.parent_id is not None:
            self._repo.get_task(tenant_id, task.parent_id)
        self._repo.add_task(task)
        self._events.publish(
            TaskEvent(
                id=uuid4(),
                tenant_id=tenant_id,
                type=TaskEventType.TASK_CREATED,
                task_id=task.id,
                payload={"task": task.model_dump(mode="json")},
                created_at=_utcnow(),
            )
        )
        return task

    def bulk_write_update_tasks(
        self, tenant_id: str, items: Union[Sequence[TaskBulkUpsertItem], Sequence[Dict[str, Any]]]
    ) -> List[Task]:
        parsed: List[TaskBulkUpsertItem] = []
        for it in items:
            if isinstance(it, dict):
                parsed.append(TaskBulkUpsertItem.model_validate(it))
            else:
                parsed.append(it)

        existing = {t.id: t for t in self._repo.list_tasks(tenant_id)}
        now = _utcnow()
        result: List[Task] = []

        for it in parsed:
            if it.parent_id is not None:
                if it.parent_id == it.id and it.id is not None:
                    raise ValidationRuleError("task cannot be its own parent")
                self._repo.get_task(tenant_id, it.parent_id)

            if it.id is None:
                tid = uuid4()
                task = Task(
                    id=tid,
                    tenant_id=tenant_id,
                    title=it.title,
                    description=it.description,
                    status=it.status,
                    parent_id=it.parent_id,
                    metadata=dict(it.metadata),
                    created_at=now,
                    updated_at=now,
                )
            else:
                prev = existing.get(it.id)
                if prev is None:
                    task = Task(
                        id=it.id,
                        tenant_id=tenant_id,
                        title=it.title,
                        description=it.description,
                        status=it.status,
                        parent_id=it.parent_id,
                        metadata=dict(it.metadata),
                        created_at=now,
                        updated_at=now,
                    )
                else:
                    task = Task(
                        id=prev.id,
                        tenant_id=tenant_id,
                        title=it.title,
                        description=it.description,
                        status=it.status,
                        parent_id=it.parent_id,
                        metadata=dict(it.metadata),
                        created_at=prev.created_at,
                        updated_at=now,
                    )
            result.append(task)

        self._validate_no_parent_cycles(tenant_id, result, existing)
        self._repo.bulk_upsert(tenant_id, result)

        self._events.publish(
            TaskEvent(
                id=uuid4(),
                tenant_id=tenant_id,
                type=TaskEventType.BULK_UPSERT,
                task_id=None,
                payload={"tasks": [t.model_dump(mode="json") for t in result]},
                created_at=_utcnow(),
            )
        )
        return result

    def update_task_status_by_id(self, tenant_id: str, task_id: UUID, status: TaskStatus) -> Task:
        task = self._repo.get_task(tenant_id, task_id)
        updated = task.model_copy(update={"status": status, "updated_at": _utcnow()})
        self._repo.update_task(tenant_id, updated)
        self._events.publish(
            TaskEvent(
                id=uuid4(),
                tenant_id=tenant_id,
                type=TaskEventType.TASK_STATUS_CHANGED,
                task_id=task_id,
                payload={"from": task.status, "to": status, "task": updated.model_dump(mode="json")},
                created_at=_utcnow(),
            )
        )
        return updated

    def update_task_by_id(self, tenant_id: str, task_id: UUID, data: Union[TaskUpdate, Dict[str, Any]]) -> Task:
        if isinstance(data, dict):
            data = TaskUpdate.model_validate(data)
        task = self._repo.get_task(tenant_id, task_id)

        new_parent_id = task.parent_id
        if data.metadata is not None:
            new_metadata = dict(data.metadata)
        else:
            new_metadata = task.metadata

        new_title = data.title if data.title is not None else task.title
        new_description = data.description if data.description is not None else task.description
        new_status = data.status if data.status is not None else task.status

        updated = task.model_copy(
            update={
                "title": new_title,
                "description": new_description,
                "status": new_status,
                "parent_id": new_parent_id,
                "metadata": new_metadata,
                "updated_at": _utcnow(),
            }
        )
        self._repo.update_task(tenant_id, updated)
        self._events.publish(
            TaskEvent(
                id=uuid4(),
                tenant_id=tenant_id,
                type=TaskEventType.TASK_UPDATED,
                task_id=task_id,
                payload={"task": updated.model_dump(mode="json")},
                created_at=_utcnow(),
            )
        )
        return updated

    def delete_task_by_id(self, tenant_id: str, task_id: UUID) -> None:
        tasks = self._repo.list_tasks(tenant_id)
        children = [t for t in tasks if t.parent_id == task_id]
        if children:
            raise ConflictError("cannot delete a task that has child tasks")
        self._repo.delete_dependencies_involving_task(tenant_id, task_id)
        self._repo.delete_task(tenant_id, task_id)
        self._events.publish(
            TaskEvent(
                id=uuid4(),
                tenant_id=tenant_id,
                type=TaskEventType.TASK_DELETED,
                task_id=task_id,
                payload={},
                created_at=_utcnow(),
            )
        )

    def create_child_task(
        self, tenant_id: str, parent_id: UUID, data: Union[TaskCreate, Dict[str, Any]]
    ) -> Task:
        self._repo.get_task(tenant_id, parent_id)
        if isinstance(data, dict):
            data = TaskCreate.model_validate(data)
        child_data = data.model_copy(update={"parent_id": parent_id})
        child = self.add_task(tenant_id, child_data)
        self._events.publish(
            TaskEvent(
                id=uuid4(),
                tenant_id=tenant_id,
                type=TaskEventType.CHILD_CREATED,
                task_id=child.id,
                payload={"parent_id": str(parent_id), "child": child.model_dump(mode="json")},
                created_at=_utcnow(),
            )
        )
        return child

    def link_tasks_with_dependency(self, tenant_id: str, task_id: UUID, depends_on_id: UUID) -> TaskDependency:
        if task_id == depends_on_id:
            raise ValidationRuleError("task cannot depend on itself")
        self._repo.get_task(tenant_id, task_id)
        self._repo.get_task(tenant_id, depends_on_id)

        deps = self._repo.list_dependencies(tenant_id)
        graph: Dict[UUID, List[UUID]] = {}
        for d in deps:
            graph.setdefault(d.task_id, []).append(d.depends_on_id)
        graph.setdefault(task_id, []).append(depends_on_id)

        if self._has_dependency_cycle(graph):
            raise ConflictError("dependency would create a cycle")

        dep = TaskDependency(tenant_id=tenant_id, task_id=task_id, depends_on_id=depends_on_id, created_at=_utcnow())
        self._repo.add_dependency(dep)
        self._events.publish(
            TaskEvent(
                id=uuid4(),
                tenant_id=tenant_id,
                type=TaskEventType.DEPENDENCY_LINKED,
                task_id=task_id,
                payload={"task_id": str(task_id), "depends_on_id": str(depends_on_id)},
                created_at=_utcnow(),
            )
        )
        return dep

    def list_all_tasks(self, tenant_id: str, hierarchical: bool = False) -> Union[List[Task], List[TaskNode]]:
        tasks = self._repo.list_tasks(tenant_id)
        if not hierarchical:
            return sorted(tasks, key=lambda t: (t.created_at, str(t.id)))
        return self._build_hierarchy(tasks)

    def list_tasks_ready_to_work_on(self, tenant_id: str) -> List[Task]:
        tasks = self._repo.list_tasks(tenant_id)
        deps = self._repo.list_dependencies(tenant_id)

        by_id: Dict[UUID, Task] = {t.id: t for t in tasks}
        dep_map: Dict[UUID, List[UUID]] = {}
        for d in deps:
            dep_map.setdefault(d.task_id, []).append(d.depends_on_id)

        ready: List[Task] = []
        for t in tasks:
            if t.status in (TaskStatus.DONE, TaskStatus.CANCELED):
                continue
            blockers = dep_map.get(t.id, [])
            ok = True
            for b in blockers:
                bt = by_id.get(b)
                if bt is None:
                    ok = False
                    break
                if bt.status != TaskStatus.DONE:
                    ok = False
                    break
            if ok:
                ready.append(t)

        return sorted(ready, key=lambda x: (x.created_at, str(x.id)))

    def _build_hierarchy(self, tasks: Sequence[Task]) -> List[TaskNode]:
        nodes: Dict[UUID, TaskNode] = {t.id: TaskNode(task=t, children=[]) for t in tasks}
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

        def sort_node(n: TaskNode) -> None:
            n.children.sort(key=lambda c: (c.task.created_at, str(c.task.id)))
            for ch in n.children:
                sort_node(ch)

        roots.sort(key=lambda r: (r.task.created_at, str(r.task.id)))
        for r in roots:
            sort_node(r)
        return roots

    def _validate_no_parent_cycles(
        self, tenant_id: str, upserts: Sequence[Task], existing: Dict[UUID, Task]
    ) -> None:
        parent_map: Dict[UUID, Optional[UUID]] = {}
        for tid, t in existing.items():
            parent_map[tid] = t.parent_id
        for t in upserts:
            parent_map[t.id] = t.parent_id

        def visit(start: UUID) -> None:
            seen: set[UUID] = set()
            cur: Optional[UUID] = start
            while cur is not None:
                if cur in seen:
                    raise ConflictError("parent relationship would create a cycle")
                seen.add(cur)
                cur = parent_map.get(cur)

        for t in upserts:
            if t.parent_id is not None and t.parent_id == t.id:
                raise ValidationRuleError("task cannot be its own parent")
            visit(t.id)

    def _has_dependency_cycle(self, graph: Dict[UUID, List[UUID]]) -> bool:
        visiting: set[UUID] = set()
        visited: set[UUID] = set()

        def dfs(n: UUID) -> bool:
            if n in visited:
                return False
            if n in visiting:
                return True
            visiting.add(n)
            for m in graph.get(n, []):
                if dfs(m):
                    return True
            visiting.remove(n)
            visited.add(n)
            return False

        for node in list(graph.keys()):
            if dfs(node):
                return True
        return False


__all__ = [
    "TaskStatus",
    "TaskEventType",
    "TaskCreate",
    "TaskUpdate",
    "TaskBulkUpsertItem",
    "Task",
    "TaskNode",
    "TaskDependency",
    "TaskEvent",
    "EventBus",
    "TaskRepository",
    "InMemoryTaskRepository",
    "PostgresTaskRepository",
    "TodoToolset",
    "TodoToolsetError",
    "NotFoundError",
    "ValidationRuleError",
    "ConflictError",
]