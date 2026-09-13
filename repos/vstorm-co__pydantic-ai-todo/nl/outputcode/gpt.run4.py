from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ValidationError, field_validator


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
    TASK_CHILD_CREATED = "task_child_created"
    TASK_DEPENDENCY_LINKED = "task_dependency_linked"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Task(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    tenant_id: str
    title: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.TODO
    parent_id: Optional[UUID] = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    @field_validator("tenant_id")
    @classmethod
    def _validate_tenant_id(cls, v: str) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("tenant_id must be a non-empty string")
        return v.strip()

    @field_validator("title")
    @classmethod
    def _validate_title(cls, v: str) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("title must be a non-empty string")
        return v.strip()


class TaskCreate(BaseModel):
    tenant_id: str
    title: str
    description: Optional[str] = None
    parent_id: Optional[UUID] = None
    status: TaskStatus = TaskStatus.TODO

    @field_validator("tenant_id")
    @classmethod
    def _validate_tenant_id(cls, v: str) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("tenant_id must be a non-empty string")
        return v.strip()

    @field_validator("title")
    @classmethod
    def _validate_title(cls, v: str) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("title must be a non-empty string")
        return v.strip()


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None

    @field_validator("title")
    @classmethod
    def _validate_title(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not isinstance(v, str) or not v.strip():
            raise ValueError("title must be a non-empty string")
        return v.strip()


class TaskNode(BaseModel):
    task: Task
    children: List["TaskNode"] = Field(default_factory=list)


TaskNode.model_rebuild()


class TaskEvent(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    tenant_id: str
    type: TaskEventType
    task_id: Optional[UUID] = None
    timestamp: datetime = Field(default_factory=_utcnow)
    payload: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("tenant_id")
    @classmethod
    def _validate_tenant_id(cls, v: str) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("tenant_id must be a non-empty string")
        return v.strip()


class TaskNotFoundError(KeyError):
    pass


class TenantMismatchError(ValueError):
    pass


class InvalidOperationError(ValueError):
    pass


class StorageError(RuntimeError):
    pass


class EventBus:
    def __init__(self) -> None:
        self._subscribers: Dict[TaskEventType, List[Callable[[TaskEvent], None]]] = {}

    def subscribe(self, event_type: TaskEventType, handler: Callable[[TaskEvent], None]) -> None:
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    def publish(self, event: TaskEvent) -> None:
        handlers = self._subscribers.get(event.type, [])
        for h in list(handlers):
            h(event)


class TaskRepository:
    def add_task(self, task: Task) -> None:
        raise NotImplementedError

    def get_task(self, tenant_id: str, task_id: UUID) -> Task:
        raise NotImplementedError

    def update_task(self, tenant_id: str, task: Task) -> None:
        raise NotImplementedError

    def delete_task(self, tenant_id: str, task_id: UUID) -> None:
        raise NotImplementedError

    def list_tasks(self, tenant_id: str) -> List[Task]:
        raise NotImplementedError

    def bulk_upsert(self, tenant_id: str, tasks: Sequence[Task]) -> None:
        raise NotImplementedError

    def add_dependency(self, tenant_id: str, task_id: UUID, depends_on_id: UUID) -> None:
        raise NotImplementedError

    def list_dependencies(self, tenant_id: str, task_id: UUID) -> List[UUID]:
        raise NotImplementedError

    def list_dependents(self, tenant_id: str, task_id: UUID) -> List[UUID]:
        raise NotImplementedError

    def delete_dependencies_for_task(self, tenant_id: str, task_id: UUID) -> None:
        raise NotImplementedError

    def delete_dependencies_involving_task(self, tenant_id: str, task_id: UUID) -> None:
        raise NotImplementedError


class InMemoryTaskRepository(TaskRepository):
    def __init__(self) -> None:
        self._tasks: Dict[str, Dict[UUID, Task]] = {}
        self._deps: Dict[str, Dict[UUID, set[UUID]]] = {}
        self._dependents: Dict[str, Dict[UUID, set[UUID]]] = {}

    def _ensure_tenant(self, tenant_id: str) -> None:
        if tenant_id not in self._tasks:
            self._tasks[tenant_id] = {}
            self._deps[tenant_id] = {}
            self._dependents[tenant_id] = {}

    def add_task(self, task: Task) -> None:
        self._ensure_tenant(task.tenant_id)
        self._tasks[task.tenant_id][task.id] = task
        self._deps[task.tenant_id].setdefault(task.id, set())
        self._dependents[task.tenant_id].setdefault(task.id, set())

    def get_task(self, tenant_id: str, task_id: UUID) -> Task:
        self._ensure_tenant(tenant_id)
        try:
            return self._tasks[tenant_id][task_id]
        except KeyError as e:
            raise TaskNotFoundError(str(task_id)) from e

    def update_task(self, tenant_id: str, task: Task) -> None:
        self._ensure_tenant(tenant_id)
        if task.id not in self._tasks[tenant_id]:
            raise TaskNotFoundError(str(task.id))
        if task.tenant_id != tenant_id:
            raise TenantMismatchError("tenant_id mismatch")
        self._tasks[tenant_id][task.id] = task

    def delete_task(self, tenant_id: str, task_id: UUID) -> None:
        self._ensure_tenant(tenant_id)
        if task_id not in self._tasks[tenant_id]:
            raise TaskNotFoundError(str(task_id))
        del self._tasks[tenant_id][task_id]
        self._deps[tenant_id].pop(task_id, None)
        self._dependents[tenant_id].pop(task_id, None)

    def list_tasks(self, tenant_id: str) -> List[Task]:
        self._ensure_tenant(tenant_id)
        return list(self._tasks[tenant_id].values())

    def bulk_upsert(self, tenant_id: str, tasks: Sequence[Task]) -> None:
        self._ensure_tenant(tenant_id)
        for t in tasks:
            if t.tenant_id != tenant_id:
                raise TenantMismatchError("tenant_id mismatch in bulk_upsert")
            self._tasks[tenant_id][t.id] = t
            self._deps[tenant_id].setdefault(t.id, set())
            self._dependents[tenant_id].setdefault(t.id, set())

    def add_dependency(self, tenant_id: str, task_id: UUID, depends_on_id: UUID) -> None:
        self._ensure_tenant(tenant_id)
        self._deps[tenant_id].setdefault(task_id, set()).add(depends_on_id)
        self._dependents[tenant_id].setdefault(depends_on_id, set()).add(task_id)

    def list_dependencies(self, tenant_id: str, task_id: UUID) -> List[UUID]:
        self._ensure_tenant(tenant_id)
        return list(self._deps[tenant_id].get(task_id, set()))

    def list_dependents(self, tenant_id: str, task_id: UUID) -> List[UUID]:
        self._ensure_tenant(tenant_id)
        return list(self._dependents[tenant_id].get(task_id, set()))

    def delete_dependencies_for_task(self, tenant_id: str, task_id: UUID) -> None:
        self._ensure_tenant(tenant_id)
        deps = self._deps[tenant_id].pop(task_id, set())
        for dep in deps:
            self._dependents[tenant_id].get(dep, set()).discard(task_id)

    def delete_dependencies_involving_task(self, tenant_id: str, task_id: UUID) -> None:
        self._ensure_tenant(tenant_id)
        self.delete_dependencies_for_task(tenant_id, task_id)
        dependents = self._dependents[tenant_id].pop(task_id, set())
        for dependent in dependents:
            self._deps[tenant_id].get(dependent, set()).discard(task_id)


class PostgresTaskRepository(TaskRepository):
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        raise StorageError("PostgresTaskRepository requires a PostgreSQL driver; provide a concrete implementation.")

    def add_task(self, task: Task) -> None:
        raise NotImplementedError

    def get_task(self, tenant_id: str, task_id: UUID) -> Task:
        raise NotImplementedError

    def update_task(self, tenant_id: str, task: Task) -> None:
        raise NotImplementedError

    def delete_task(self, tenant_id: str, task_id: UUID) -> None:
        raise NotImplementedError

    def list_tasks(self, tenant_id: str) -> List[Task]:
        raise NotImplementedError

    def bulk_upsert(self, tenant_id: str, tasks: Sequence[Task]) -> None:
        raise NotImplementedError

    def add_dependency(self, tenant_id: str, task_id: UUID, depends_on_id: UUID) -> None:
        raise NotImplementedError

    def list_dependencies(self, tenant_id: str, task_id: UUID) -> List[UUID]:
        raise NotImplementedError

    def list_dependents(self, tenant_id: str, task_id: UUID) -> List[UUID]:
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
    def events(self) -> EventBus:
        return self._events

    def add_task(self, task: Union[TaskCreate, Dict[str, Any]]) -> Task:
        if isinstance(task, dict):
            task_in = TaskCreate.model_validate(task)
        else:
            task_in = task

        if task_in.parent_id is not None:
            parent = self._repo.get_task(task_in.tenant_id, task_in.parent_id)
            if parent.tenant_id != task_in.tenant_id:
                raise TenantMismatchError("parent tenant mismatch")

        new_task = Task(
            tenant_id=task_in.tenant_id,
            title=task_in.title,
            description=task_in.description,
            status=task_in.status,
            parent_id=task_in.parent_id,
        )
        self._repo.add_task(new_task)
        self._events.publish(
            TaskEvent(
                tenant_id=new_task.tenant_id,
                type=TaskEventType.TASK_CREATED,
                task_id=new_task.id,
                payload={"task": new_task.model_dump(mode="json")},
            )
        )
        return new_task

    def bulk_write_update_tasks(self, tenant_id: str, tasks: Sequence[Union[Task, Dict[str, Any]]]) -> List[Task]:
        normalized: List[Task] = []
        for t in tasks:
            if isinstance(t, Task):
                task_obj = t
            else:
                task_obj = Task.model_validate(t)
            if task_obj.tenant_id != tenant_id:
                raise TenantMismatchError("tenant_id mismatch in bulk write/update")
            normalized.append(task_obj)

        existing_ids = {t.id for t in self._repo.list_tasks(tenant_id)}
        now = _utcnow()
        upserted: List[Task] = []
        for t in normalized:
            if t.parent_id is not None:
                parent = self._repo.get_task(tenant_id, t.parent_id)
                if parent.tenant_id != tenant_id:
                    raise TenantMismatchError("parent tenant mismatch")
            if t.id in existing_ids:
                t = t.model_copy(update={"updated_at": now})
            else:
                t = t.model_copy(update={"created_at": now, "updated_at": now})
            upserted.append(t)

        self._repo.bulk_upsert(tenant_id, upserted)
        self._events.publish(
            TaskEvent(
                tenant_id=tenant_id,
                type=TaskEventType.TASK_UPDATED,
                task_id=None,
                payload={"tasks": [t.model_dump(mode="json") for t in upserted]},
            )
        )
        return upserted

    def list_all_tasks(self, tenant_id: str, hierarchical: bool = False) -> Union[List[Task], List[TaskNode]]:
        tasks = self._repo.list_tasks(tenant_id)
        if not hierarchical:
            return sorted(tasks, key=lambda x: (x.created_at, str(x.id)))

        by_id: Dict[UUID, Task] = {t.id: t for t in tasks}
        children_map: Dict[Optional[UUID], List[Task]] = {}
        for t in tasks:
            children_map.setdefault(t.parent_id, []).append(t)

        for k in list(children_map.keys()):
            children_map[k].sort(key=lambda x: (x.created_at, str(x.id)))

        def build(parent_id: Optional[UUID]) -> List[TaskNode]:
            nodes: List[TaskNode] = []
            for child in children_map.get(parent_id, []):
                nodes.append(TaskNode(task=child, children=build(child.id)))
            return nodes

        roots: List[TaskNode] = []
        for t in children_map.get(None, []):
            roots.append(TaskNode(task=t, children=build(t.id)))
        return roots

    def update_task_status_by_id(self, tenant_id: str, task_id: UUID, status: TaskStatus) -> Task:
        task = self._repo.get_task(tenant_id, task_id)
        if task.tenant_id != tenant_id:
            raise TenantMismatchError("tenant_id mismatch")
        updated = task.model_copy(update={"status": status, "updated_at": _utcnow()})
        self._repo.update_task(tenant_id, updated)
        self._events.publish(
            TaskEvent(
                tenant_id=tenant_id,
                type=TaskEventType.TASK_STATUS_CHANGED,
                task_id=task_id,
                payload={"from": task.status.value, "to": status.value},
            )
        )
        return updated

    def delete_task_by_id(self, tenant_id: str, task_id: UUID) -> None:
        task = self._repo.get_task(tenant_id, task_id)
        if task.tenant_id != tenant_id:
            raise TenantMismatchError("tenant_id mismatch")

        tasks = self._repo.list_tasks(tenant_id)
        children_map: Dict[UUID, List[UUID]] = {}
        for t in tasks:
            if t.parent_id is not None:
                children_map.setdefault(t.parent_id, []).append(t.id)

        to_delete: List[UUID] = []
        stack: List[UUID] = [task_id]
        while stack:
            cur = stack.pop()
            to_delete.append(cur)
            for ch in children_map.get(cur, []):
                stack.append(ch)

        for tid in to_delete:
            self._repo.delete_dependencies_involving_task(tenant_id, tid)

        for tid in reversed(to_delete):
            self._repo.delete_task(tenant_id, tid)
            self._events.publish(
                TaskEvent(
                    tenant_id=tenant_id,
                    type=TaskEventType.TASK_DELETED,
                    task_id=tid,
                    payload={},
                )
            )

    def create_child_task(self, tenant_id: str, parent_id: UUID, title: str, description: Optional[str] = None) -> Task:
        parent = self._repo.get_task(tenant_id, parent_id)
        if parent.tenant_id != tenant_id:
            raise TenantMismatchError("tenant_id mismatch")
        child = self.add_task(
            TaskCreate(
                tenant_id=tenant_id,
                title=title,
                description=description,
                parent_id=parent_id,
                status=TaskStatus.TODO,
            )
        )
        self._events.publish(
            TaskEvent(
                tenant_id=tenant_id,
                type=TaskEventType.TASK_CHILD_CREATED,
                task_id=child.id,
                payload={"parent_id": str(parent_id)},
            )
        )
        return child

    def link_tasks_with_dependency(self, tenant_id: str, task_id: UUID, depends_on_id: UUID) -> None:
        if task_id == depends_on_id:
            raise InvalidOperationError("task cannot depend on itself")

        task = self._repo.get_task(tenant_id, task_id)
        dep = self._repo.get_task(tenant_id, depends_on_id)
        if task.tenant_id != tenant_id or dep.tenant_id != tenant_id:
            raise TenantMismatchError("tenant_id mismatch")

        if self._creates_cycle(tenant_id, task_id, depends_on_id):
            raise InvalidOperationError("dependency would create a cycle")

        self._repo.add_dependency(tenant_id, task_id, depends_on_id)
        self._events.publish(
            TaskEvent(
                tenant_id=tenant_id,
                type=TaskEventType.TASK_DEPENDENCY_LINKED,
                task_id=task_id,
                payload={"depends_on_id": str(depends_on_id)},
            )
        )

    def list_tasks_ready_to_work_on(self, tenant_id: str) -> List[Task]:
        tasks = self._repo.list_tasks(tenant_id)
        by_id: Dict[UUID, Task] = {t.id: t for t in tasks}

        ready: List[Task] = []
        for t in tasks:
            if t.status in (TaskStatus.DONE, TaskStatus.CANCELED):
                continue
            deps = self._repo.list_dependencies(tenant_id, t.id)
            all_done = True
            for dep_id in deps:
                dep_task = by_id.get(dep_id)
                if dep_task is None:
                    all_done = False
                    break
                if dep_task.status != TaskStatus.DONE:
                    all_done = False
                    break
            if all_done:
                ready.append(t)

        ready.sort(key=lambda x: (x.created_at, str(x.id)))
        return ready

    def _creates_cycle(self, tenant_id: str, task_id: UUID, depends_on_id: UUID) -> bool:
        target = task_id
        stack: List[UUID] = [depends_on_id]
        visited: set[UUID] = set()
        while stack:
            cur = stack.pop()
            if cur == target:
                return True
            if cur in visited:
                continue
            visited.add(cur)
            for nxt in self._repo.list_dependencies(tenant_id, cur):
                stack.append(nxt)
        return False


__all__ = [
    "TaskStatus",
    "TaskEventType",
    "Task",
    "TaskCreate",
    "TaskUpdate",
    "TaskNode",
    "TaskEvent",
    "TaskNotFoundError",
    "TenantMismatchError",
    "InvalidOperationError",
    "StorageError",
    "EventBus",
    "TaskRepository",
    "InMemoryTaskRepository",
    "PostgresTaskRepository",
    "TodoToolset",
]