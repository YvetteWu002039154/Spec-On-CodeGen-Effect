from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple, Union
from uuid import UUID, uuid4


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
    DEPENDENCY_LINKED = "dependency_linked"
    CHILD_CREATED = "child_created"


@dataclass(frozen=True)
class TaskEvent:
    event_id: UUID
    tenant_id: str
    event_type: TaskEventType
    task_id: UUID
    timestamp: datetime
    payload: Dict[str, Any]


class EventBus:
    def __init__(self) -> None:
        self._subscribers: Dict[TaskEventType, List[Callable[[TaskEvent], None]]] = {}

    def subscribe(self, event_type: TaskEventType, callback: Callable[[TaskEvent], None]) -> None:
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    def publish(self, event: TaskEvent) -> None:
        for cb in self._subscribers.get(event.event_type, []):
            cb(event)


class Task:
    def __init__(
        self,
        tenant_id: str,
        title: str,
        description: Optional[str] = None,
        status: TaskStatus = TaskStatus.TODO,
        task_id: Optional[UUID] = None,
        parent_id: Optional[UUID] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        if not tenant_id or not isinstance(tenant_id, str):
            raise ValueError("tenant_id must be a non-empty string")
        if not title or not isinstance(title, str):
            raise ValueError("title must be a non-empty string")
        if description is not None and not isinstance(description, str):
            raise ValueError("description must be a string or None")
        if not isinstance(status, TaskStatus):
            raise ValueError("status must be a TaskStatus")

        now = datetime.now(timezone.utc)
        self._tenant_id: str = tenant_id
        self._id: UUID = task_id or uuid4()
        self._title: str = title
        self._description: Optional[str] = description
        self._status: TaskStatus = status
        self._parent_id: Optional[UUID] = parent_id
        self._created_at: datetime = created_at or now
        self._updated_at: datetime = updated_at or now

    @property
    def tenant_id(self) -> str:
        return self._tenant_id

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def title(self) -> str:
        return self._title

    @property
    def description(self) -> Optional[str]:
        return self._description

    @property
    def status(self) -> TaskStatus:
        return self._status

    @property
    def parent_id(self) -> Optional[UUID]:
        return self._parent_id

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    def update(
        self,
        *,
        title: Optional[str] = None,
        description: Optional[Optional[str]] = None,
        status: Optional[TaskStatus] = None,
        parent_id: Optional[Optional[UUID]] = None,
    ) -> None:
        changed = False

        if title is not None:
            if not title or not isinstance(title, str):
                raise ValueError("title must be a non-empty string")
            if title != self._title:
                self._title = title
                changed = True

        if description is not None:
            if description is not None and not isinstance(description, str):
                raise ValueError("description must be a string or None")
            if description != self._description:
                self._description = description
                changed = True

        if status is not None:
            if not isinstance(status, TaskStatus):
                raise ValueError("status must be a TaskStatus")
            if status != self._status:
                self._status = status
                changed = True

        if parent_id is not None:
            if parent_id is not None and not isinstance(parent_id, UUID):
                raise ValueError("parent_id must be a UUID or None")
            if parent_id != self._parent_id:
                self._parent_id = parent_id
                changed = True

        if changed:
            self._updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tenant_id": self._tenant_id,
            "id": str(self._id),
            "title": self._title,
            "description": self._description,
            "status": self._status.value,
            "parent_id": str(self._parent_id) if self._parent_id else None,
            "created_at": self._created_at.isoformat(),
            "updated_at": self._updated_at.isoformat(),
        }


class TaskRepository:
    def add(self, task: Task) -> None:
        raise NotImplementedError

    def get(self, tenant_id: str, task_id: UUID) -> Task:
        raise NotImplementedError

    def list(self, tenant_id: str) -> List[Task]:
        raise NotImplementedError

    def update(self, task: Task) -> None:
        raise NotImplementedError

    def delete(self, tenant_id: str, task_id: UUID) -> None:
        raise NotImplementedError

    def bulk_upsert(self, tasks: Sequence[Task]) -> None:
        raise NotImplementedError

    def list_children(self, tenant_id: str, parent_id: UUID) -> List[Task]:
        raise NotImplementedError


class DependencyRepository:
    def link(self, tenant_id: str, task_id: UUID, depends_on_id: UUID) -> None:
        raise NotImplementedError

    def unlink_all_for_task(self, tenant_id: str, task_id: UUID) -> None:
        raise NotImplementedError

    def list_dependencies(self, tenant_id: str, task_id: UUID) -> List[UUID]:
        raise NotImplementedError

    def list_dependents(self, tenant_id: str, task_id: UUID) -> List[UUID]:
        raise NotImplementedError


class InMemoryTaskRepository(TaskRepository):
    def __init__(self) -> None:
        self._tasks: Dict[Tuple[str, UUID], Task] = {}

    def add(self, task: Task) -> None:
        key = (task.tenant_id, task.id)
        if key in self._tasks:
            raise ValueError("task already exists")
        self._tasks[key] = task

    def get(self, tenant_id: str, task_id: UUID) -> Task:
        key = (tenant_id, task_id)
        if key not in self._tasks:
            raise KeyError("task not found")
        return self._tasks[key]

    def list(self, tenant_id: str) -> List[Task]:
        return [t for (tid, _), t in self._tasks.items() if tid == tenant_id]

    def update(self, task: Task) -> None:
        key = (task.tenant_id, task.id)
        if key not in self._tasks:
            raise KeyError("task not found")
        self._tasks[key] = task

    def delete(self, tenant_id: str, task_id: UUID) -> None:
        key = (tenant_id, task_id)
        if key not in self._tasks:
            raise KeyError("task not found")
        del self._tasks[key]

    def bulk_upsert(self, tasks: Sequence[Task]) -> None:
        for task in tasks:
            key = (task.tenant_id, task.id)
            self._tasks[key] = task

    def list_children(self, tenant_id: str, parent_id: UUID) -> List[Task]:
        return [t for (tid, _), t in self._tasks.items() if tid == tenant_id and t.parent_id == parent_id]


class InMemoryDependencyRepository(DependencyRepository):
    def __init__(self) -> None:
        self._deps: Dict[Tuple[str, UUID], set[UUID]] = {}
        self._reverse: Dict[Tuple[str, UUID], set[UUID]] = {}

    def link(self, tenant_id: str, task_id: UUID, depends_on_id: UUID) -> None:
        if task_id == depends_on_id:
            raise ValueError("task cannot depend on itself")
        key = (tenant_id, task_id)
        self._deps.setdefault(key, set()).add(depends_on_id)
        rkey = (tenant_id, depends_on_id)
        self._reverse.setdefault(rkey, set()).add(task_id)

    def unlink_all_for_task(self, tenant_id: str, task_id: UUID) -> None:
        key = (tenant_id, task_id)
        deps = self._deps.pop(key, set())
        for dep in deps:
            rkey = (tenant_id, dep)
            if rkey in self._reverse:
                self._reverse[rkey].discard(task_id)
                if not self._reverse[rkey]:
                    del self._reverse[rkey]

        rkey = (tenant_id, task_id)
        dependents = self._reverse.pop(rkey, set())
        for dep_task in dependents:
            dkey = (tenant_id, dep_task)
            if dkey in self._deps:
                self._deps[dkey].discard(task_id)
                if not self._deps[dkey]:
                    del self._deps[dkey]

    def list_dependencies(self, tenant_id: str, task_id: UUID) -> List[UUID]:
        return list(self._deps.get((tenant_id, task_id), set()))

    def list_dependents(self, tenant_id: str, task_id: UUID) -> List[UUID]:
        return list(self._reverse.get((tenant_id, task_id), set()))


class PostgresTaskRepository(TaskRepository):
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        raise NotImplementedError("PostgreSQL storage is not implemented in this standalone module")

    def add(self, task: Task) -> None:
        raise NotImplementedError

    def get(self, tenant_id: str, task_id: UUID) -> Task:
        raise NotImplementedError

    def list(self, tenant_id: str) -> List[Task]:
        raise NotImplementedError

    def update(self, task: Task) -> None:
        raise NotImplementedError

    def delete(self, tenant_id: str, task_id: UUID) -> None:
        raise NotImplementedError

    def bulk_upsert(self, tasks: Sequence[Task]) -> None:
        raise NotImplementedError

    def list_children(self, tenant_id: str, parent_id: UUID) -> List[Task]:
        raise NotImplementedError


class PostgresDependencyRepository(DependencyRepository):
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        raise NotImplementedError("PostgreSQL storage is not implemented in this standalone module")

    def link(self, tenant_id: str, task_id: UUID, depends_on_id: UUID) -> None:
        raise NotImplementedError

    def unlink_all_for_task(self, tenant_id: str, task_id: UUID) -> None:
        raise NotImplementedError

    def list_dependencies(self, tenant_id: str, task_id: UUID) -> List[UUID]:
        raise NotImplementedError

    def list_dependents(self, tenant_id: str, task_id: UUID) -> List[UUID]:
        raise NotImplementedError


@dataclass(frozen=True)
class TaskNode:
    task: Task
    children: List["TaskNode"]


class TodoToolset:
    def __init__(
        self,
        task_repo: TaskRepository,
        dependency_repo: DependencyRepository,
        event_bus: Optional[EventBus] = None,
    ) -> None:
        self._tasks = task_repo
        self._deps = dependency_repo
        self._events = event_bus or EventBus()

    @property
    def event_bus(self) -> EventBus:
        return self._events

    def add_task(
        self,
        tenant_id: str,
        title: str,
        description: Optional[str] = None,
        status: TaskStatus = TaskStatus.TODO,
        parent_id: Optional[UUID] = None,
    ) -> Task:
        if parent_id is not None:
            parent = self._tasks.get(tenant_id, parent_id)
            if parent.tenant_id != tenant_id:
                raise ValueError("parent task must belong to same tenant")

        task = Task(tenant_id=tenant_id, title=title, description=description, status=status, parent_id=parent_id)
        self._tasks.add(task)
        self._publish(TaskEventType.TASK_CREATED, tenant_id, task.id, {"task": task.to_dict()})
        return task

    def bulk_write_update_tasks(self, tasks: Sequence[Task]) -> None:
        if not tasks:
            return
        tenant_ids = {t.tenant_id for t in tasks}
        if len(tenant_ids) != 1:
            raise ValueError("bulk operations must be within a single tenant")
        tenant_id = next(iter(tenant_ids))

        ids = {t.id for t in tasks}
        for t in tasks:
            if t.parent_id is not None:
                if t.parent_id in ids:
                    continue
                self._tasks.get(tenant_id, t.parent_id)

        self._tasks.bulk_upsert(tasks)
        for t in tasks:
            self._publish(TaskEventType.TASK_UPDATED, tenant_id, t.id, {"task": t.to_dict()})

    def update_task_status_by_id(self, tenant_id: str, task_id: UUID, status: TaskStatus) -> Task:
        task = self._tasks.get(tenant_id, task_id)
        task.update(status=status)
        self._tasks.update(task)
        self._publish(TaskEventType.TASK_UPDATED, tenant_id, task.id, {"task": task.to_dict()})
        return task

    def delete_task_by_id(self, tenant_id: str, task_id: UUID) -> None:
        self._tasks.get(tenant_id, task_id)
        self._deps.unlink_all_for_task(tenant_id, task_id)
        self._tasks.delete(tenant_id, task_id)
        self._publish(TaskEventType.TASK_DELETED, tenant_id, task_id, {"task_id": str(task_id)})

    def create_child_task(
        self,
        tenant_id: str,
        parent_id: UUID,
        title: str,
        description: Optional[str] = None,
        status: TaskStatus = TaskStatus.TODO,
    ) -> Task:
        parent = self._tasks.get(tenant_id, parent_id)
        child = self.add_task(tenant_id=tenant_id, title=title, description=description, status=status, parent_id=parent.id)
        self._publish(
            TaskEventType.CHILD_CREATED,
            tenant_id,
            child.id,
            {"parent_id": str(parent.id), "child": child.to_dict()},
        )
        return child

    def link_tasks_with_dependency(self, tenant_id: str, task_id: UUID, depends_on_id: UUID) -> None:
        self._tasks.get(tenant_id, task_id)
        self._tasks.get(tenant_id, depends_on_id)
        if self._creates_cycle(tenant_id, task_id, depends_on_id):
            raise ValueError("link would create a dependency cycle")
        self._deps.link(tenant_id, task_id, depends_on_id)
        self._publish(
            TaskEventType.DEPENDENCY_LINKED,
            tenant_id,
            task_id,
            {"task_id": str(task_id), "depends_on_id": str(depends_on_id)},
        )

    def list_all_tasks(self, tenant_id: str) -> List[Task]:
        return sorted(self._tasks.list(tenant_id), key=lambda t: (t.created_at, str(t.id)))

    def list_all_tasks_hierarchical(self, tenant_id: str) -> List[TaskNode]:
        tasks = self._tasks.list(tenant_id)
        by_parent: Dict[Optional[UUID], List[Task]] = {}
        for t in tasks:
            by_parent.setdefault(t.parent_id, []).append(t)
        for k in list(by_parent.keys()):
            by_parent[k].sort(key=lambda t: (t.created_at, str(t.id)))

        def build(parent_id: Optional[UUID]) -> List[TaskNode]:
            nodes: List[TaskNode] = []
            for t in by_parent.get(parent_id, []):
                nodes.append(TaskNode(task=t, children=build(t.id)))
            return nodes

        return build(None)

    def list_tasks_ready_to_work_on(self, tenant_id: str) -> List[Task]:
        tasks = self._tasks.list(tenant_id)
        task_by_id: Dict[UUID, Task] = {t.id: t for t in tasks}

        ready: List[Task] = []
        for t in tasks:
            if t.status in (TaskStatus.DONE, TaskStatus.CANCELED):
                continue
            deps = self._deps.list_dependencies(tenant_id, t.id)
            all_done = True
            for dep_id in deps:
                dep_task = task_by_id.get(dep_id)
                if dep_task is None:
                    all_done = False
                    break
                if dep_task.status != TaskStatus.DONE:
                    all_done = False
                    break
            if all_done:
                ready.append(t)

        return sorted(ready, key=lambda t: (t.created_at, str(t.id)))

    def _publish(self, event_type: TaskEventType, tenant_id: str, task_id: UUID, payload: Dict[str, Any]) -> None:
        event = TaskEvent(
            event_id=uuid4(),
            tenant_id=tenant_id,
            event_type=event_type,
            task_id=task_id,
            timestamp=datetime.now(timezone.utc),
            payload=payload,
        )
        self._events.publish(event)

    def _creates_cycle(self, tenant_id: str, task_id: UUID, depends_on_id: UUID) -> bool:
        target = task_id
        stack = [depends_on_id]
        visited: set[UUID] = set()
        while stack:
            current = stack.pop()
            if current == target:
                return True
            if current in visited:
                continue
            visited.add(current)
            for nxt in self._deps.list_dependencies(tenant_id, current):
                stack.append(nxt)
        return False


__all__ = [
    "TaskStatus",
    "TaskEventType",
    "TaskEvent",
    "EventBus",
    "Task",
    "TaskNode",
    "TaskRepository",
    "DependencyRepository",
    "InMemoryTaskRepository",
    "InMemoryDependencyRepository",
    "PostgresTaskRepository",
    "PostgresDependencyRepository",
    "TodoToolset",
]