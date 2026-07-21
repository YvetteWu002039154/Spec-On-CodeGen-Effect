from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, Iterable, List, Optional, Protocol, Sequence, Tuple, Union
from uuid import UUID, uuid4


class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    DONE = "done"
    CANCELED = "canceled"


class TodoToolsetError(Exception):
    pass


class ValidationError(TodoToolsetError):
    pass


class NotFoundError(TodoToolsetError):
    pass


class ConflictError(TodoToolsetError):
    pass


class StorageError(TodoToolsetError):
    pass


class EventType(str, Enum):
    TASK_CREATED = "task.created"
    TASK_UPDATED = "task.updated"
    TASK_DELETED = "task.deleted"
    TASK_DEPENDENCY_LINKED = "task.dependency_linked"
    TASK_CHILD_CREATED = "task.child_created"


@dataclass(frozen=True)
class Event:
    event_id: UUID
    event_type: EventType
    tenant_id: str
    occurred_at: datetime
    payload: Dict[str, Any]


class EventHandler(Protocol):
    def __call__(self, event: Event) -> None: ...


class EventBus:
    def __init__(self) -> None:
        self._handlers: Dict[EventType, List[EventHandler]] = {}

    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: EventType, handler: EventHandler) -> None:
        handlers = self._handlers.get(event_type)
        if not handlers:
            return
        self._handlers[event_type] = [h for h in handlers if h is not handler]

    def publish(self, event: Event) -> None:
        for handler in list(self._handlers.get(event.event_type, [])):
            handler(event)


@dataclass
class Task:
    id: UUID
    tenant_id: str
    title: str
    description: Optional[str]
    status: TaskStatus
    parent_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "tenant_id": self.tenant_id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "parent_id": str(self.parent_id) if self.parent_id else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass(frozen=True)
class TaskDependency:
    tenant_id: str
    task_id: UUID
    depends_on_task_id: UUID


@dataclass
class TaskNode:
    task: Task
    children: List["TaskNode"]

    def to_dict(self) -> Dict[str, Any]:
        d = self.task.to_dict()
        d["children"] = [c.to_dict() for c in self.children]
        return d


class TaskStorage(Protocol):
    def list_tasks(self, tenant_id: str) -> List[Task]: ...
    def get_task(self, tenant_id: str, task_id: UUID) -> Task: ...
    def upsert_tasks(self, tenant_id: str, tasks: Sequence[Task]) -> None: ...
    def add_task(self, tenant_id: str, task: Task) -> None: ...
    def update_task(self, tenant_id: str, task: Task) -> None: ...
    def delete_task(self, tenant_id: str, task_id: UUID) -> None: ...
    def list_dependencies(self, tenant_id: str) -> List[TaskDependency]: ...
    def add_dependency(self, tenant_id: str, dep: TaskDependency) -> None: ...
    def delete_dependencies_for_task(self, tenant_id: str, task_id: UUID) -> None: ...
    def delete_dependencies_referencing_task(self, tenant_id: str, task_id: UUID) -> None: ...


class InMemoryTaskStorage:
    def __init__(self) -> None:
        self._tasks: Dict[str, Dict[UUID, Task]] = {}
        self._deps: Dict[str, List[TaskDependency]] = {}

    def _tenant_tasks(self, tenant_id: str) -> Dict[UUID, Task]:
        return self._tasks.setdefault(tenant_id, {})

    def _tenant_deps(self, tenant_id: str) -> List[TaskDependency]:
        return self._deps.setdefault(tenant_id, [])

    def list_tasks(self, tenant_id: str) -> List[Task]:
        return list(self._tenant_tasks(tenant_id).values())

    def get_task(self, tenant_id: str, task_id: UUID) -> Task:
        t = self._tenant_tasks(tenant_id).get(task_id)
        if t is None:
            raise NotFoundError(f"Task not found: {task_id}")
        return t

    def upsert_tasks(self, tenant_id: str, tasks: Sequence[Task]) -> None:
        store = self._tenant_tasks(tenant_id)
        for t in tasks:
            store[t.id] = t

    def add_task(self, tenant_id: str, task: Task) -> None:
        store = self._tenant_tasks(tenant_id)
        if task.id in store:
            raise ConflictError(f"Task already exists: {task.id}")
        store[task.id] = task

    def update_task(self, tenant_id: str, task: Task) -> None:
        store = self._tenant_tasks(tenant_id)
        if task.id not in store:
            raise NotFoundError(f"Task not found: {task.id}")
        store[task.id] = task

    def delete_task(self, tenant_id: str, task_id: UUID) -> None:
        store = self._tenant_tasks(tenant_id)
        if task_id not in store:
            raise NotFoundError(f"Task not found: {task_id}")
        del store[task_id]

    def list_dependencies(self, tenant_id: str) -> List[TaskDependency]:
        return list(self._tenant_deps(tenant_id))

    def add_dependency(self, tenant_id: str, dep: TaskDependency) -> None:
        deps = self._tenant_deps(tenant_id)
        if any(d.task_id == dep.task_id and d.depends_on_task_id == dep.depends_on_task_id for d in deps):
            raise ConflictError("Dependency already exists")
        deps.append(dep)

    def delete_dependencies_for_task(self, tenant_id: str, task_id: UUID) -> None:
        deps = self._tenant_deps(tenant_id)
        self._deps[tenant_id] = [d for d in deps if d.task_id != task_id]

    def delete_dependencies_referencing_task(self, tenant_id: str, task_id: UUID) -> None:
        deps = self._tenant_deps(tenant_id)
        self._deps[tenant_id] = [d for d in deps if d.depends_on_task_id != task_id]


class PostgresTaskStorage:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        raise StorageError("PostgresTaskStorage requires a PostgreSQL driver; provide a concrete implementation.")

    def list_tasks(self, tenant_id: str) -> List[Task]:
        raise StorageError("Not implemented")

    def get_task(self, tenant_id: str, task_id: UUID) -> Task:
        raise StorageError("Not implemented")

    def upsert_tasks(self, tenant_id: str, tasks: Sequence[Task]) -> None:
        raise StorageError("Not implemented")

    def add_task(self, tenant_id: str, task: Task) -> None:
        raise StorageError("Not implemented")

    def update_task(self, tenant_id: str, task: Task) -> None:
        raise StorageError("Not implemented")

    def delete_task(self, tenant_id: str, task_id: UUID) -> None:
        raise StorageError("Not implemented")

    def list_dependencies(self, tenant_id: str) -> List[TaskDependency]:
        raise StorageError("Not implemented")

    def add_dependency(self, tenant_id: str, dep: TaskDependency) -> None:
        raise StorageError("Not implemented")

    def delete_dependencies_for_task(self, tenant_id: str, task_id: UUID) -> None:
        raise StorageError("Not implemented")

    def delete_dependencies_referencing_task(self, tenant_id: str, task_id: UUID) -> None:
        raise StorageError("Not implemented")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class TodoToolset:
    def __init__(self, storage: TaskStorage, event_bus: Optional[EventBus] = None) -> None:
        self._storage = storage
        self._events = event_bus or EventBus()

    @property
    def events(self) -> EventBus:
        return self._events

    def list_all_tasks(self, tenant_id: str, hierarchical: bool = True) -> Union[List[Task], List[TaskNode]]:
        tasks = self._storage.list_tasks(tenant_id)
        if not hierarchical:
            return sorted(tasks, key=lambda t: (t.created_at, str(t.id)))

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

    def bulk_write_tasks(
        self,
        tenant_id: str,
        tasks: Sequence[Dict[str, Any]],
    ) -> List[Task]:
        if not tenant_id or not isinstance(tenant_id, str):
            raise ValidationError("tenant_id must be a non-empty string")
        if tasks is None:
            raise ValidationError("tasks must not be None")

        existing = {t.id: t for t in self._storage.list_tasks(tenant_id)}
        now = _now_utc()
        result: List[Task] = []

        parsed: List[Task] = []
        for item in tasks:
            if not isinstance(item, dict):
                raise ValidationError("Each task must be a dict")
            task_id = item.get("id")
            if task_id is None:
                tid = uuid4()
            else:
                tid = UUID(str(task_id))

            title = item.get("title")
            if not title or not isinstance(title, str):
                raise ValidationError("Task title must be a non-empty string")

            description = item.get("description")
            if description is not None and not isinstance(description, str):
                raise ValidationError("Task description must be a string or None")

            status_raw = item.get("status")
            if status_raw is None:
                status = existing.get(tid).status if tid in existing else TaskStatus.TODO
            else:
                status = TaskStatus(str(status_raw))

            parent_raw = item.get("parent_id")
            parent_id = UUID(str(parent_raw)) if parent_raw is not None else None

            if tid in existing:
                created_at = existing[tid].created_at
            else:
                created_at = now

            parsed.append(
                Task(
                    id=tid,
                    tenant_id=tenant_id,
                    title=title,
                    description=description,
                    status=status,
                    parent_id=parent_id,
                    created_at=created_at,
                    updated_at=now,
                )
            )

        self._validate_parent_links(tenant_id, parsed)
        self._storage.upsert_tasks(tenant_id, parsed)

        for t in parsed:
            if t.id in existing:
                self._publish(EventType.TASK_UPDATED, tenant_id, {"task": t.to_dict()})
            else:
                self._publish(EventType.TASK_CREATED, tenant_id, {"task": t.to_dict()})
            result.append(t)

        return result

    def add_task(
        self,
        tenant_id: str,
        title: str,
        description: Optional[str] = None,
        parent_id: Optional[UUID] = None,
    ) -> Task:
        if not tenant_id or not isinstance(tenant_id, str):
            raise ValidationError("tenant_id must be a non-empty string")
        if not title or not isinstance(title, str):
            raise ValidationError("title must be a non-empty string")
        if description is not None and not isinstance(description, str):
            raise ValidationError("description must be a string or None")

        if parent_id is not None:
            self._storage.get_task(tenant_id, parent_id)

        now = _now_utc()
        task = Task(
            id=uuid4(),
            tenant_id=tenant_id,
            title=title,
            description=description,
            status=TaskStatus.TODO,
            parent_id=parent_id,
            created_at=now,
            updated_at=now,
        )
        self._storage.add_task(tenant_id, task)
        self._publish(EventType.TASK_CREATED, tenant_id, {"task": task.to_dict()})
        return task

    def update_task_status_by_id(self, tenant_id: str, task_id: UUID, status: TaskStatus) -> Task:
        if not tenant_id or not isinstance(tenant_id, str):
            raise ValidationError("tenant_id must be a non-empty string")
        if not isinstance(task_id, UUID):
            raise ValidationError("task_id must be a UUID")
        if not isinstance(status, TaskStatus):
            status = TaskStatus(str(status))

        task = self._storage.get_task(tenant_id, task_id)
        now = _now_utc()
        updated = Task(
            id=task.id,
            tenant_id=task.tenant_id,
            title=task.title,
            description=task.description,
            status=status,
            parent_id=task.parent_id,
            created_at=task.created_at,
            updated_at=now,
        )
        self._storage.update_task(tenant_id, updated)
        self._publish(EventType.TASK_UPDATED, tenant_id, {"task": updated.to_dict()})
        return updated

    def delete_task_by_id(self, tenant_id: str, task_id: UUID) -> None:
        if not tenant_id or not isinstance(tenant_id, str):
            raise ValidationError("tenant_id must be a non-empty string")
        if not isinstance(task_id, UUID):
            raise ValidationError("task_id must be a UUID")

        tasks = self._storage.list_tasks(tenant_id)
        children_map: Dict[UUID, List[UUID]] = {}
        for t in tasks:
            if t.parent_id is not None:
                children_map.setdefault(t.parent_id, []).append(t.id)

        to_delete: List[UUID] = []
        stack: List[UUID] = [task_id]
        existing_ids = {t.id for t in tasks}
        if task_id not in existing_ids:
            raise NotFoundError(f"Task not found: {task_id}")

        while stack:
            cur = stack.pop()
            to_delete.append(cur)
            for child in children_map.get(cur, []):
                stack.append(child)

        for tid in to_delete:
            self._storage.delete_dependencies_for_task(tenant_id, tid)
            self._storage.delete_dependencies_referencing_task(tenant_id, tid)

        for tid in reversed(to_delete):
            self._storage.delete_task(tenant_id, tid)
            self._publish(EventType.TASK_DELETED, tenant_id, {"task_id": str(tid)})

    def create_child_task(
        self,
        tenant_id: str,
        parent_id: UUID,
        title: str,
        description: Optional[str] = None,
    ) -> Task:
        if not isinstance(parent_id, UUID):
            raise ValidationError("parent_id must be a UUID")
        parent = self._storage.get_task(tenant_id, parent_id)
        child = self.add_task(tenant_id=tenant_id, title=title, description=description, parent_id=parent.id)
        self._publish(
            EventType.TASK_CHILD_CREATED,
            tenant_id,
            {"parent_id": str(parent.id), "child_task": child.to_dict()},
        )
        return child

    def link_tasks_with_dependency(self, tenant_id: str, task_id: UUID, depends_on_task_id: UUID) -> TaskDependency:
        if not tenant_id or not isinstance(tenant_id, str):
            raise ValidationError("tenant_id must be a non-empty string")
        if not isinstance(task_id, UUID) or not isinstance(depends_on_task_id, UUID):
            raise ValidationError("task_id and depends_on_task_id must be UUIDs")
        if task_id == depends_on_task_id:
            raise ValidationError("A task cannot depend on itself")

        self._storage.get_task(tenant_id, task_id)
        self._storage.get_task(tenant_id, depends_on_task_id)

        deps = self._storage.list_dependencies(tenant_id)
        graph: Dict[UUID, List[UUID]] = {}
        for d in deps:
            graph.setdefault(d.task_id, []).append(d.depends_on_task_id)
        graph.setdefault(task_id, []).append(depends_on_task_id)

        if self._has_cycle(graph):
            raise ConflictError("Dependency would create a cycle")

        dep = TaskDependency(tenant_id=tenant_id, task_id=task_id, depends_on_task_id=depends_on_task_id)
        self._storage.add_dependency(tenant_id, dep)
        self._publish(
            EventType.TASK_DEPENDENCY_LINKED,
            tenant_id,
            {"task_id": str(task_id), "depends_on_task_id": str(depends_on_task_id)},
        )
        return dep

    def list_tasks_ready_to_work_on(self, tenant_id: str) -> List[Task]:
        if not tenant_id or not isinstance(tenant_id, str):
            raise ValidationError("tenant_id must be a non-empty string")

        tasks = self._storage.list_tasks(tenant_id)
        deps = self._storage.list_dependencies(tenant_id)

        task_by_id: Dict[UUID, Task] = {t.id: t for t in tasks}
        deps_by_task: Dict[UUID, List[UUID]] = {}
        for d in deps:
            deps_by_task.setdefault(d.task_id, []).append(d.depends_on_task_id)

        ready: List[Task] = []
        for t in tasks:
            if t.status not in (TaskStatus.TODO, TaskStatus.IN_PROGRESS):
                continue
            blocked = False
            for dep_id in deps_by_task.get(t.id, []):
                dep_task = task_by_id.get(dep_id)
                if dep_task is None:
                    continue
                if dep_task.status != TaskStatus.DONE:
                    blocked = True
                    break
            if not blocked:
                ready.append(t)

        ready.sort(key=lambda t: (t.created_at, str(t.id)))
        return ready

    def _publish(self, event_type: EventType, tenant_id: str, payload: Dict[str, Any]) -> None:
        event = Event(
            event_id=uuid4(),
            event_type=event_type,
            tenant_id=tenant_id,
            occurred_at=_now_utc(),
            payload=payload,
        )
        self._events.publish(event)

    def _validate_parent_links(self, tenant_id: str, tasks: Sequence[Task]) -> None:
        incoming_by_id: Dict[UUID, Task] = {t.id: t for t in tasks}
        existing = {t.id: t for t in self._storage.list_tasks(tenant_id)}
        all_ids = set(existing.keys()) | set(incoming_by_id.keys())

        for t in tasks:
            if t.parent_id is not None and t.parent_id not in all_ids:
                raise ValidationError(f"parent_id does not exist: {t.parent_id}")

        parent_map: Dict[UUID, Optional[UUID]] = {}
        for tid, t in existing.items():
            parent_map[tid] = t.parent_id
        for tid, t in incoming_by_id.items():
            parent_map[tid] = t.parent_id

        for tid in incoming_by_id.keys():
            seen: set[UUID] = set()
            cur: Optional[UUID] = tid
            while cur is not None:
                if cur in seen:
                    raise ConflictError("Parent relationship would create a cycle")
                seen.add(cur)
                cur = parent_map.get(cur)

    def _has_cycle(self, graph: Dict[UUID, List[UUID]]) -> bool:
        visited: set[UUID] = set()
        in_stack: set[UUID] = set()

        def dfs(node: UUID) -> bool:
            if node in in_stack:
                return True
            if node in visited:
                return False
            visited.add(node)
            in_stack.add(node)
            for nxt in graph.get(node, []):
                if dfs(nxt):
                    return True
            in_stack.remove(node)
            return False

        for n in list(graph.keys()):
            if dfs(n):
                return True
        return False


__all__ = [
    "TaskStatus",
    "TodoToolsetError",
    "ValidationError",
    "NotFoundError",
    "ConflictError",
    "StorageError",
    "EventType",
    "Event",
    "EventBus",
    "Task",
    "TaskDependency",
    "TaskNode",
    "TaskStorage",
    "InMemoryTaskStorage",
    "PostgresTaskStorage",
    "TodoToolset",
]