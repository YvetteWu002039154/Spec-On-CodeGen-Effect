from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, Iterable, List, Optional, Protocol, Sequence, Tuple, Union
from uuid import UUID, uuid4


class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"


class TaskEventType(str, Enum):
    TASK_CREATED = "task_created"
    TASK_UPDATED = "task_updated"
    TASK_DELETED = "task_deleted"
    TASK_STATUS_CHANGED = "task_status_changed"
    CHILD_CREATED = "child_created"
    DEPENDENCY_LINKED = "dependency_linked"


@dataclass(frozen=True)
class TaskEvent:
    event_type: TaskEventType
    tenant_id: str
    task_id: UUID
    timestamp: datetime
    payload: Dict[str, Any]


class EventHandler(Protocol):
    def __call__(self, event: TaskEvent) -> None: ...


class EventBus:
    def __init__(self) -> None:
        self._handlers: List[EventHandler] = []

    def subscribe(self, handler: EventHandler) -> None:
        if handler not in self._handlers:
            self._handlers.append(handler)

    def unsubscribe(self, handler: EventHandler) -> None:
        self._handlers = [h for h in self._handlers if h is not handler]

    def publish(self, event: TaskEvent) -> None:
        for handler in list(self._handlers):
            handler(event)


class TaskValidationError(ValueError):
    pass


class TaskNotFoundError(KeyError):
    pass


class DependencyError(ValueError):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


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
            raise TaskValidationError("tenant_id must be a non-empty string")
        if not title or not isinstance(title, str):
            raise TaskValidationError("title must be a non-empty string")
        if description is not None and not isinstance(description, str):
            raise TaskValidationError("description must be a string or None")

        self._tenant_id: str = tenant_id
        self._id: UUID = task_id or uuid4()
        self._title: str = title
        self._description: Optional[str] = description
        self._status: TaskStatus = TaskStatus(status)
        self._parent_id: Optional[UUID] = parent_id
        now = _utcnow()
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

    def set_title(self, title: str) -> None:
        if not title or not isinstance(title, str):
            raise TaskValidationError("title must be a non-empty string")
        self._title = title
        self._updated_at = _utcnow()

    def set_description(self, description: Optional[str]) -> None:
        if description is not None and not isinstance(description, str):
            raise TaskValidationError("description must be a string or None")
        self._description = description
        self._updated_at = _utcnow()

    def set_status(self, status: TaskStatus) -> None:
        self._status = TaskStatus(status)
        self._updated_at = _utcnow()

    def set_parent(self, parent_id: Optional[UUID]) -> None:
        self._parent_id = parent_id
        self._updated_at = _utcnow()

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

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Task":
        tenant_id = data["tenant_id"]
        task_id = UUID(data["id"]) if isinstance(data.get("id"), str) else data.get("id")
        parent_raw = data.get("parent_id")
        parent_id = UUID(parent_raw) if isinstance(parent_raw, str) and parent_raw else parent_raw
        created_at_raw = data.get("created_at")
        updated_at_raw = data.get("updated_at")
        created_at = (
            datetime.fromisoformat(created_at_raw) if isinstance(created_at_raw, str) else created_at_raw
        ) or _utcnow()
        updated_at = (
            datetime.fromisoformat(updated_at_raw) if isinstance(updated_at_raw, str) else updated_at_raw
        ) or created_at
        return Task(
            tenant_id=tenant_id,
            title=data["title"],
            description=data.get("description"),
            status=TaskStatus(data.get("status", TaskStatus.TODO.value)),
            task_id=task_id,
            parent_id=parent_id,
            created_at=created_at,
            updated_at=updated_at,
        )


class TaskRepository(Protocol):
    def list_tasks(self, tenant_id: str) -> List[Task]: ...
    def get_task(self, tenant_id: str, task_id: UUID) -> Task: ...
    def upsert_task(self, task: Task) -> None: ...
    def bulk_upsert(self, tasks: Sequence[Task]) -> None: ...
    def delete_task(self, tenant_id: str, task_id: UUID) -> None: ...
    def list_dependencies(self, tenant_id: str) -> List[Tuple[UUID, UUID]]: ...
    def add_dependency(self, tenant_id: str, task_id: UUID, depends_on_id: UUID) -> None: ...
    def remove_dependencies_for_task(self, tenant_id: str, task_id: UUID) -> None: ...
    def remove_dependency(self, tenant_id: str, task_id: UUID, depends_on_id: UUID) -> None: ...


class InMemoryTaskRepository:
    def __init__(self) -> None:
        self._tasks: Dict[str, Dict[UUID, Task]] = {}
        self._deps: Dict[str, Dict[UUID, set[UUID]]] = {}

    def list_tasks(self, tenant_id: str) -> List[Task]:
        return list(self._tasks.get(tenant_id, {}).values())

    def get_task(self, tenant_id: str, task_id: UUID) -> Task:
        try:
            return self._tasks[tenant_id][task_id]
        except KeyError as e:
            raise TaskNotFoundError(f"Task not found: {task_id}") from e

    def upsert_task(self, task: Task) -> None:
        self._tasks.setdefault(task.tenant_id, {})[task.id] = task
        self._deps.setdefault(task.tenant_id, {}).setdefault(task.id, set())

    def bulk_upsert(self, tasks: Sequence[Task]) -> None:
        for t in tasks:
            self.upsert_task(t)

    def delete_task(self, tenant_id: str, task_id: UUID) -> None:
        if tenant_id not in self._tasks or task_id not in self._tasks[tenant_id]:
            raise TaskNotFoundError(f"Task not found: {task_id}")
        del self._tasks[tenant_id][task_id]
        if tenant_id in self._deps:
            self._deps[tenant_id].pop(task_id, None)
            for tid, deps in list(self._deps[tenant_id].items()):
                if task_id in deps:
                    deps.discard(task_id)

    def list_dependencies(self, tenant_id: str) -> List[Tuple[UUID, UUID]]:
        out: List[Tuple[UUID, UUID]] = []
        for task_id, deps in self._deps.get(tenant_id, {}).items():
            for dep in deps:
                out.append((task_id, dep))
        return out

    def add_dependency(self, tenant_id: str, task_id: UUID, depends_on_id: UUID) -> None:
        self._deps.setdefault(tenant_id, {}).setdefault(task_id, set()).add(depends_on_id)

    def remove_dependencies_for_task(self, tenant_id: str, task_id: UUID) -> None:
        if tenant_id in self._deps:
            self._deps[tenant_id].pop(task_id, None)

    def remove_dependency(self, tenant_id: str, task_id: UUID, depends_on_id: UUID) -> None:
        if tenant_id in self._deps and task_id in self._deps[tenant_id]:
            self._deps[tenant_id][task_id].discard(depends_on_id)


class PostgresTaskRepository:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        raise NotImplementedError("PostgreSQL storage is not available in this runtime")

    def list_tasks(self, tenant_id: str) -> List[Task]:
        raise NotImplementedError

    def get_task(self, tenant_id: str, task_id: UUID) -> Task:
        raise NotImplementedError

    def upsert_task(self, task: Task) -> None:
        raise NotImplementedError

    def bulk_upsert(self, tasks: Sequence[Task]) -> None:
        raise NotImplementedError

    def delete_task(self, tenant_id: str, task_id: UUID) -> None:
        raise NotImplementedError

    def list_dependencies(self, tenant_id: str) -> List[Tuple[UUID, UUID]]:
        raise NotImplementedError

    def add_dependency(self, tenant_id: str, task_id: UUID, depends_on_id: UUID) -> None:
        raise NotImplementedError

    def remove_dependencies_for_task(self, tenant_id: str, task_id: UUID) -> None:
        raise NotImplementedError

    def remove_dependency(self, tenant_id: str, task_id: UUID, depends_on_id: UUID) -> None:
        raise NotImplementedError


@dataclass(frozen=True)
class TaskNode:
    task: Task
    children: List["TaskNode"]


class TodoToolset:
    def __init__(self, repository: TaskRepository, event_bus: Optional[EventBus] = None) -> None:
        self._repo = repository
        self._events = event_bus or EventBus()

    @property
    def events(self) -> EventBus:
        return self._events

    def add_task(
        self,
        tenant_id: str,
        title: str,
        description: Optional[str] = None,
        status: TaskStatus = TaskStatus.TODO,
    ) -> Task:
        task = Task(tenant_id=tenant_id, title=title, description=description, status=status)
        self._repo.upsert_task(task)
        self._events.publish(
            TaskEvent(
                event_type=TaskEventType.TASK_CREATED,
                tenant_id=tenant_id,
                task_id=task.id,
                timestamp=_utcnow(),
                payload={"task": task.to_dict()},
            )
        )
        return task

    def bulk_write_update_tasks(self, tasks: Sequence[Union[Task, Dict[str, Any]]]) -> List[Task]:
        normalized: List[Task] = []
        for item in tasks:
            if isinstance(item, Task):
                normalized.append(item)
            elif isinstance(item, dict):
                normalized.append(Task.from_dict(item))
            else:
                raise TaskValidationError("bulk_write_update_tasks expects Task or dict items")
        if not normalized:
            return []
        tenant_ids = {t.tenant_id for t in normalized}
        if len(tenant_ids) != 1:
            raise TaskValidationError("All tasks in bulk operation must share the same tenant_id")
        self._repo.bulk_upsert(normalized)
        tenant_id = normalized[0].tenant_id
        self._events.publish(
            TaskEvent(
                event_type=TaskEventType.TASK_UPDATED,
                tenant_id=tenant_id,
                task_id=normalized[0].id,
                timestamp=_utcnow(),
                payload={"count": len(normalized), "tasks": [t.to_dict() for t in normalized]},
            )
        )
        return normalized

    def list_all_tasks(self, tenant_id: str, hierarchical: bool = False) -> Union[List[Task], List[TaskNode]]:
        tasks = self._repo.list_tasks(tenant_id)
        if not hierarchical:
            return sorted(tasks, key=lambda t: (t.created_at, str(t.id)))

        by_parent: Dict[Optional[UUID], List[Task]] = {}
        by_id: Dict[UUID, Task] = {}
        for t in tasks:
            by_id[t.id] = t
            by_parent.setdefault(t.parent_id, []).append(t)

        for k in list(by_parent.keys()):
            by_parent[k].sort(key=lambda t: (t.created_at, str(t.id)))

        def build(parent_id: Optional[UUID]) -> List[TaskNode]:
            nodes: List[TaskNode] = []
            for t in by_parent.get(parent_id, []):
                nodes.append(TaskNode(task=t, children=build(t.id)))
            return nodes

        return build(None)

    def update_task_status_by_id(self, tenant_id: str, task_id: Union[UUID, str], status: TaskStatus) -> Task:
        tid = UUID(task_id) if isinstance(task_id, str) else task_id
        task = self._repo.get_task(tenant_id, tid)
        old = task.status
        task.set_status(status)
        self._repo.upsert_task(task)
        self._events.publish(
            TaskEvent(
                event_type=TaskEventType.TASK_STATUS_CHANGED,
                tenant_id=tenant_id,
                task_id=task.id,
                timestamp=_utcnow(),
                payload={"from": old.value, "to": task.status.value, "task": task.to_dict()},
            )
        )
        return task

    def delete_task_by_id(self, tenant_id: str, task_id: Union[UUID, str]) -> None:
        tid = UUID(task_id) if isinstance(task_id, str) else task_id
        self._repo.get_task(tenant_id, tid)
        self._repo.delete_task(tenant_id, tid)
        self._events.publish(
            TaskEvent(
                event_type=TaskEventType.TASK_DELETED,
                tenant_id=tenant_id,
                task_id=tid,
                timestamp=_utcnow(),
                payload={},
            )
        )

    def create_child_task(
        self,
        tenant_id: str,
        parent_task_id: Union[UUID, str],
        title: str,
        description: Optional[str] = None,
        status: TaskStatus = TaskStatus.TODO,
    ) -> Task:
        pid = UUID(parent_task_id) if isinstance(parent_task_id, str) else parent_task_id
        parent = self._repo.get_task(tenant_id, pid)
        child = Task(tenant_id=tenant_id, title=title, description=description, status=status, parent_id=parent.id)
        self._repo.upsert_task(child)
        self._events.publish(
            TaskEvent(
                event_type=TaskEventType.CHILD_CREATED,
                tenant_id=tenant_id,
                task_id=child.id,
                timestamp=_utcnow(),
                payload={"parent_id": str(parent.id), "child": child.to_dict()},
            )
        )
        return child

    def link_tasks_with_dependency(
        self,
        tenant_id: str,
        task_id: Union[UUID, str],
        depends_on_id: Union[UUID, str],
    ) -> None:
        tid = UUID(task_id) if isinstance(task_id, str) else task_id
        did = UUID(depends_on_id) if isinstance(depends_on_id, str) else depends_on_id
        if tid == did:
            raise DependencyError("A task cannot depend on itself")
        self._repo.get_task(tenant_id, tid)
        self._repo.get_task(tenant_id, did)

        self._repo.add_dependency(tenant_id, tid, did)
        if self._has_cycle(tenant_id):
            self._repo.remove_dependency(tenant_id, tid, did)
            raise DependencyError("Dependency would create a cycle")

        self._events.publish(
            TaskEvent(
                event_type=TaskEventType.DEPENDENCY_LINKED,
                tenant_id=tenant_id,
                task_id=tid,
                timestamp=_utcnow(),
                payload={"task_id": str(tid), "depends_on_id": str(did)},
            )
        )

    def list_tasks_ready_to_work_on(self, tenant_id: str) -> List[Task]:
        tasks = {t.id: t for t in self._repo.list_tasks(tenant_id)}
        deps_map: Dict[UUID, set[UUID]] = {}
        for task_id, dep_id in self._repo.list_dependencies(tenant_id):
            deps_map.setdefault(task_id, set()).add(dep_id)

        ready: List[Task] = []
        for t in tasks.values():
            if t.status in (TaskStatus.DONE,):
                continue
            deps = deps_map.get(t.id, set())
            blocked = False
            for dep_id in deps:
                dep_task = tasks.get(dep_id)
                if dep_task is None:
                    blocked = True
                    break
                if dep_task.status != TaskStatus.DONE:
                    blocked = True
                    break
            if not blocked:
                ready.append(t)

        ready.sort(key=lambda x: (x.created_at, str(x.id)))
        return ready

    def _has_cycle(self, tenant_id: str) -> bool:
        edges: Dict[UUID, set[UUID]] = {}
        for task_id, dep_id in self._repo.list_dependencies(tenant_id):
            edges.setdefault(task_id, set()).add(dep_id)

        visited: set[UUID] = set()
        stack: set[UUID] = set()

        def dfs(node: UUID) -> bool:
            if node in stack:
                return True
            if node in visited:
                return False
            visited.add(node)
            stack.add(node)
            for nxt in edges.get(node, set()):
                if dfs(nxt):
                    return True
            stack.remove(node)
            return False

        nodes = set(edges.keys())
        for deps in edges.values():
            nodes.update(deps)

        for n in nodes:
            if dfs(n):
                return True
        return False


class TodoToolsetForPydanticAI:
    def __init__(self, toolset: TodoToolset, tenant_id: str) -> None:
        if not tenant_id or not isinstance(tenant_id, str):
            raise TaskValidationError("tenant_id must be a non-empty string")
        self._toolset = toolset
        self._tenant_id = tenant_id

    @property
    def tenant_id(self) -> str:
        return self._tenant_id

    @property
    def events(self) -> EventBus:
        return self._toolset.events

    def list_all_tasks(self, hierarchical: bool = False) -> Union[List[Task], List[TaskNode]]:
        return self._toolset.list_all_tasks(self._tenant_id, hierarchical=hierarchical)

    def bulk_write_update_tasks(self, tasks: Sequence[Union[Task, Dict[str, Any]]]) -> List[Task]:
        normalized: List[Union[Task, Dict[str, Any]]] = []
        for item in tasks:
            if isinstance(item, Task):
                if item.tenant_id != self._tenant_id:
                    raise TaskValidationError("Task tenant_id does not match tool tenant_id")
                normalized.append(item)
            elif isinstance(item, dict):
                if item.get("tenant_id") != self._tenant_id:
                    raise TaskValidationError("Task dict tenant_id does not match tool tenant_id")
                normalized.append(item)
            else:
                raise TaskValidationError("bulk_write_update_tasks expects Task or dict items")
        return self._toolset.bulk_write_update_tasks(normalized)

    def add_task(
        self,
        title: str,
        description: Optional[str] = None,
        status: TaskStatus = TaskStatus.TODO,
    ) -> Task:
        return self._toolset.add_task(self._tenant_id, title=title, description=description, status=status)

    def update_task_status_by_id(self, task_id: Union[UUID, str], status: TaskStatus) -> Task:
        return self._toolset.update_task_status_by_id(self._tenant_id, task_id=task_id, status=status)

    def delete_task_by_id(self, task_id: Union[UUID, str]) -> None:
        self._toolset.delete_task_by_id(self._tenant_id, task_id=task_id)

    def create_child_task(
        self,
        parent_task_id: Union[UUID, str],
        title: str,
        description: Optional[str] = None,
        status: TaskStatus = TaskStatus.TODO,
    ) -> Task:
        return self._toolset.create_child_task(
            self._tenant_id,
            parent_task_id=parent_task_id,
            title=title,
            description=description,
            status=status,
        )

    def link_tasks_with_dependency(self, task_id: Union[UUID, str], depends_on_id: Union[UUID, str]) -> None:
        self._toolset.link_tasks_with_dependency(self._tenant_id, task_id=task_id, depends_on_id=depends_on_id)

    def list_tasks_ready_to_work_on(self) -> List[Task]:
        return self._toolset.list_tasks_ready_to_work_on(self._tenant_id)