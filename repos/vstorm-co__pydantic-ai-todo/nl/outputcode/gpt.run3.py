from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple, Union
from uuid import UUID, uuid4


class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    DONE = "done"
    CANCELED = "canceled"


class TodoEventType(str, Enum):
    TASK_CREATED = "task_created"
    TASK_UPDATED = "task_updated"
    TASK_DELETED = "task_deleted"
    DEPENDENCY_LINKED = "dependency_linked"
    CHILD_CREATED = "child_created"


@dataclass(frozen=True)
class TodoEvent:
    event_type: TodoEventType
    tenant_id: str
    task_id: Optional[UUID]
    timestamp: datetime
    payload: Dict[str, Any]


class TodoError(Exception):
    pass


class NotFoundError(TodoError):
    pass


class ValidationError(TodoError):
    pass


class ConflictError(TodoError):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_tenant_id(tenant_id: str) -> str:
    if not isinstance(tenant_id, str) or not tenant_id.strip():
        raise ValidationError("tenant_id must be a non-empty string")
    return tenant_id.strip()


def _validate_title(title: str) -> str:
    if not isinstance(title, str) or not title.strip():
        raise ValidationError("title must be a non-empty string")
    return title.strip()


def _validate_status(status: Union[str, TaskStatus]) -> TaskStatus:
    if isinstance(status, TaskStatus):
        return status
    if isinstance(status, str):
        try:
            return TaskStatus(status)
        except ValueError as e:
            raise ValidationError(f"invalid status: {status}") from e
    raise ValidationError("status must be a TaskStatus or str")


class Task:
    __slots__ = (
        "_id",
        "_tenant_id",
        "_title",
        "_description",
        "_status",
        "_parent_id",
        "_created_at",
        "_updated_at",
    )

    def __init__(
        self,
        tenant_id: str,
        title: str,
        description: Optional[str] = None,
        status: Union[str, TaskStatus] = TaskStatus.TODO,
        parent_id: Optional[UUID] = None,
        task_id: Optional[UUID] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        self._tenant_id = _normalize_tenant_id(tenant_id)
        self._id = task_id or uuid4()
        self._title = _validate_title(title)
        self._description = (description or "").strip() or None
        self._status = _validate_status(status)
        self._parent_id = parent_id
        now = _utcnow()
        self._created_at = created_at or now
        self._updated_at = updated_at or self._created_at

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def tenant_id(self) -> str:
        return self._tenant_id

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

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self._id),
            "tenant_id": self._tenant_id,
            "title": self._title,
            "description": self._description,
            "status": self._status.value,
            "parent_id": str(self._parent_id) if self._parent_id else None,
            "created_at": self._created_at.isoformat(),
            "updated_at": self._updated_at.isoformat(),
        }

    def _touch(self) -> None:
        self._updated_at = _utcnow()

    def update(
        self,
        *,
        title: Optional[str] = None,
        description: Optional[Optional[str]] = None,
        status: Optional[Union[str, TaskStatus]] = None,
        parent_id: Optional[Optional[UUID]] = None,
    ) -> None:
        changed = False
        if title is not None:
            new_title = _validate_title(title)
            if new_title != self._title:
                self._title = new_title
                changed = True
        if description is not None:
            new_desc = (description or "").strip() or None
            if new_desc != self._description:
                self._description = new_desc
                changed = True
        if status is not None:
            new_status = _validate_status(status)
            if new_status != self._status:
                self._status = new_status
                changed = True
        if parent_id is not None:
            if parent_id != self._parent_id:
                self._parent_id = parent_id
                changed = True
        if changed:
            self._touch()


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

    def bulk_upsert(self, tenant_id: str, tasks: Sequence[Task]) -> None:
        raise NotImplementedError


class DependencyRepository:
    def add_dependency(self, tenant_id: str, task_id: UUID, depends_on_id: UUID) -> None:
        raise NotImplementedError

    def remove_task(self, tenant_id: str, task_id: UUID) -> None:
        raise NotImplementedError

    def list_dependencies(self, tenant_id: str, task_id: UUID) -> Set[UUID]:
        raise NotImplementedError

    def list_dependents(self, tenant_id: str, task_id: UUID) -> Set[UUID]:
        raise NotImplementedError

    def all_edges(self, tenant_id: str) -> Set[Tuple[UUID, UUID]]:
        raise NotImplementedError


class InMemoryTaskRepository(TaskRepository):
    def __init__(self) -> None:
        self._tasks: Dict[str, Dict[UUID, Task]] = {}

    def add(self, task: Task) -> None:
        tenant_id = _normalize_tenant_id(task.tenant_id)
        bucket = self._tasks.setdefault(tenant_id, {})
        if task.id in bucket:
            raise ConflictError("task already exists")
        bucket[task.id] = task

    def get(self, tenant_id: str, task_id: UUID) -> Task:
        tenant_id = _normalize_tenant_id(tenant_id)
        try:
            return self._tasks[tenant_id][task_id]
        except KeyError as e:
            raise NotFoundError("task not found") from e

    def list(self, tenant_id: str) -> List[Task]:
        tenant_id = _normalize_tenant_id(tenant_id)
        return list(self._tasks.get(tenant_id, {}).values())

    def update(self, task: Task) -> None:
        tenant_id = _normalize_tenant_id(task.tenant_id)
        bucket = self._tasks.setdefault(tenant_id, {})
        if task.id not in bucket:
            raise NotFoundError("task not found")
        bucket[task.id] = task

    def delete(self, tenant_id: str, task_id: UUID) -> None:
        tenant_id = _normalize_tenant_id(tenant_id)
        bucket = self._tasks.get(tenant_id, {})
        if task_id not in bucket:
            raise NotFoundError("task not found")
        del bucket[task_id]

    def bulk_upsert(self, tenant_id: str, tasks: Sequence[Task]) -> None:
        tenant_id = _normalize_tenant_id(tenant_id)
        bucket = self._tasks.setdefault(tenant_id, {})
        for t in tasks:
            if t.tenant_id != tenant_id:
                raise ValidationError("all tasks must match tenant_id")
            bucket[t.id] = t


class InMemoryDependencyRepository(DependencyRepository):
    def __init__(self) -> None:
        self._deps: Dict[str, Dict[UUID, Set[UUID]]] = {}
        self._rev: Dict[str, Dict[UUID, Set[UUID]]] = {}

    def add_dependency(self, tenant_id: str, task_id: UUID, depends_on_id: UUID) -> None:
        tenant_id = _normalize_tenant_id(tenant_id)
        deps_bucket = self._deps.setdefault(tenant_id, {})
        rev_bucket = self._rev.setdefault(tenant_id, {})
        deps_bucket.setdefault(task_id, set()).add(depends_on_id)
        rev_bucket.setdefault(depends_on_id, set()).add(task_id)

    def remove_task(self, tenant_id: str, task_id: UUID) -> None:
        tenant_id = _normalize_tenant_id(tenant_id)
        deps_bucket = self._deps.get(tenant_id, {})
        rev_bucket = self._rev.get(tenant_id, {})

        for dep in list(deps_bucket.get(task_id, set())):
            rev_bucket.get(dep, set()).discard(task_id)
            if dep in rev_bucket and not rev_bucket[dep]:
                del rev_bucket[dep]
        if task_id in deps_bucket:
            del deps_bucket[task_id]

        for dependent in list(rev_bucket.get(task_id, set())):
            deps_bucket.get(dependent, set()).discard(task_id)
            if dependent in deps_bucket and not deps_bucket[dependent]:
                del deps_bucket[dependent]
        if task_id in rev_bucket:
            del rev_bucket[task_id]

    def list_dependencies(self, tenant_id: str, task_id: UUID) -> Set[UUID]:
        tenant_id = _normalize_tenant_id(tenant_id)
        return set(self._deps.get(tenant_id, {}).get(task_id, set()))

    def list_dependents(self, tenant_id: str, task_id: UUID) -> Set[UUID]:
        tenant_id = _normalize_tenant_id(tenant_id)
        return set(self._rev.get(tenant_id, {}).get(task_id, set()))

    def all_edges(self, tenant_id: str) -> Set[Tuple[UUID, UUID]]:
        tenant_id = _normalize_tenant_id(tenant_id)
        edges: Set[Tuple[UUID, UUID]] = set()
        for task_id, deps in self._deps.get(tenant_id, {}).items():
            for dep in deps:
                edges.add((task_id, dep))
        return edges


class EventBus:
    def __init__(self) -> None:
        self._subscribers: Dict[TodoEventType, List[Callable[[TodoEvent], None]]] = {}

    def subscribe(self, event_type: TodoEventType, callback: Callable[[TodoEvent], None]) -> None:
        if not callable(callback):
            raise ValidationError("callback must be callable")
        self._subscribers.setdefault(event_type, []).append(callback)

    def publish(self, event: TodoEvent) -> None:
        for cb in list(self._subscribers.get(event.event_type, [])):
            cb(event)


class TodoToolset:
    def __init__(
        self,
        task_repository: Optional[TaskRepository] = None,
        dependency_repository: Optional[DependencyRepository] = None,
        event_bus: Optional[EventBus] = None,
    ) -> None:
        self._tasks = task_repository or InMemoryTaskRepository()
        self._deps = dependency_repository or InMemoryDependencyRepository()
        self._events = event_bus or EventBus()

    @property
    def event_bus(self) -> EventBus:
        return self._events

    def add_task(
        self,
        tenant_id: str,
        title: str,
        description: Optional[str] = None,
        status: Union[str, TaskStatus] = TaskStatus.TODO,
        parent_id: Optional[UUID] = None,
    ) -> Task:
        tenant_id = _normalize_tenant_id(tenant_id)
        if parent_id is not None:
            parent = self._tasks.get(tenant_id, parent_id)
            if parent.status in (TaskStatus.DONE, TaskStatus.CANCELED):
                raise ConflictError("cannot add child to a completed/canceled parent task")

        task = Task(
            tenant_id=tenant_id,
            title=title,
            description=description,
            status=status,
            parent_id=parent_id,
        )
        self._tasks.add(task)
        self._events.publish(
            TodoEvent(
                event_type=TodoEventType.TASK_CREATED,
                tenant_id=tenant_id,
                task_id=task.id,
                timestamp=_utcnow(),
                payload={"task": task.to_dict()},
            )
        )
        return task

    def bulk_write_update_tasks(self, tenant_id: str, tasks: Sequence[Union[Task, Dict[str, Any]]]) -> List[Task]:
        tenant_id = _normalize_tenant_id(tenant_id)
        built: List[Task] = []
        for item in tasks:
            if isinstance(item, Task):
                if item.tenant_id != tenant_id:
                    raise ValidationError("all tasks must match tenant_id")
                built.append(item)
                continue
            if not isinstance(item, dict):
                raise ValidationError("tasks must be Task or dict")
            t_tenant = item.get("tenant_id", tenant_id)
            if t_tenant != tenant_id:
                raise ValidationError("all tasks must match tenant_id")
            task_id_val = item.get("id")
            task_id = UUID(str(task_id_val)) if task_id_val is not None else None
            parent_id_val = item.get("parent_id")
            parent_id = UUID(str(parent_id_val)) if parent_id_val is not None else None
            status = item.get("status", TaskStatus.TODO)
            title = item.get("title")
            if title is None:
                raise ValidationError("title is required")
            description = item.get("description")
            built.append(
                Task(
                    tenant_id=tenant_id,
                    title=title,
                    description=description,
                    status=status,
                    parent_id=parent_id,
                    task_id=task_id,
                )
            )

        for t in built:
            if t.parent_id is not None:
                self._tasks.get(tenant_id, t.parent_id)

        self._tasks.bulk_upsert(tenant_id, built)
        for t in built:
            self._events.publish(
                TodoEvent(
                    event_type=TodoEventType.TASK_UPDATED,
                    tenant_id=tenant_id,
                    task_id=t.id,
                    timestamp=_utcnow(),
                    payload={"task": t.to_dict(), "bulk": True},
                )
            )
        return built

    def update_task_status_by_id(self, tenant_id: str, task_id: UUID, status: Union[str, TaskStatus]) -> Task:
        tenant_id = _normalize_tenant_id(tenant_id)
        task = self._tasks.get(tenant_id, task_id)
        new_status = _validate_status(status)

        if new_status == TaskStatus.DONE:
            children = self._children_of(tenant_id, task_id)
            for c in children:
                if c.status not in (TaskStatus.DONE, TaskStatus.CANCELED):
                    raise ConflictError("cannot mark task done while it has incomplete children")
            deps = self._deps.list_dependencies(tenant_id, task_id)
            for dep_id in deps:
                dep_task = self._tasks.get(tenant_id, dep_id)
                if dep_task.status not in (TaskStatus.DONE, TaskStatus.CANCELED):
                    raise ConflictError("cannot mark task done while dependencies are incomplete")

        task.update(status=new_status)
        self._tasks.update(task)
        self._events.publish(
            TodoEvent(
                event_type=TodoEventType.TASK_UPDATED,
                tenant_id=tenant_id,
                task_id=task.id,
                timestamp=_utcnow(),
                payload={"task": task.to_dict(), "fields": ["status"]},
            )
        )
        return task

    def delete_task_by_id(self, tenant_id: str, task_id: UUID) -> None:
        tenant_id = _normalize_tenant_id(tenant_id)
        self._tasks.get(tenant_id, task_id)

        children = self._children_of(tenant_id, task_id)
        for c in children:
            self.delete_task_by_id(tenant_id, c.id)

        self._deps.remove_task(tenant_id, task_id)
        self._tasks.delete(tenant_id, task_id)
        self._events.publish(
            TodoEvent(
                event_type=TodoEventType.TASK_DELETED,
                tenant_id=tenant_id,
                task_id=task_id,
                timestamp=_utcnow(),
                payload={"task_id": str(task_id)},
            )
        )

    def create_child_task(
        self,
        tenant_id: str,
        parent_id: UUID,
        title: str,
        description: Optional[str] = None,
        status: Union[str, TaskStatus] = TaskStatus.TODO,
    ) -> Task:
        tenant_id = _normalize_tenant_id(tenant_id)
        self._tasks.get(tenant_id, parent_id)
        child = self.add_task(
            tenant_id=tenant_id,
            title=title,
            description=description,
            status=status,
            parent_id=parent_id,
        )
        self._events.publish(
            TodoEvent(
                event_type=TodoEventType.CHILD_CREATED,
                tenant_id=tenant_id,
                task_id=child.id,
                timestamp=_utcnow(),
                payload={"parent_id": str(parent_id), "child": child.to_dict()},
            )
        )
        return child

    def link_tasks_with_dependency(self, tenant_id: str, task_id: UUID, depends_on_id: UUID) -> None:
        tenant_id = _normalize_tenant_id(tenant_id)
        if task_id == depends_on_id:
            raise ValidationError("task cannot depend on itself")
        self._tasks.get(tenant_id, task_id)
        self._tasks.get(tenant_id, depends_on_id)

        if self._creates_cycle(tenant_id, task_id, depends_on_id):
            raise ConflictError("dependency would create a cycle")

        self._deps.add_dependency(tenant_id, task_id, depends_on_id)
        self._events.publish(
            TodoEvent(
                event_type=TodoEventType.DEPENDENCY_LINKED,
                tenant_id=tenant_id,
                task_id=task_id,
                timestamp=_utcnow(),
                payload={"task_id": str(task_id), "depends_on_id": str(depends_on_id)},
            )
        )

    def list_all_tasks(self, tenant_id: str, hierarchical: bool = False) -> Union[List[Task], List[Dict[str, Any]]]:
        tenant_id = _normalize_tenant_id(tenant_id)
        tasks = self._tasks.list(tenant_id)
        tasks.sort(key=lambda t: (t.created_at, str(t.id)))
        if not hierarchical:
            return tasks
        return self._hierarchical_view(tenant_id, tasks)

    def list_tasks_ready_to_work_on(self, tenant_id: str) -> List[Task]:
        tenant_id = _normalize_tenant_id(tenant_id)
        tasks = self._tasks.list(tenant_id)
        by_id: Dict[UUID, Task] = {t.id: t for t in tasks}

        ready: List[Task] = []
        for t in tasks:
            if t.status not in (TaskStatus.TODO, TaskStatus.IN_PROGRESS):
                continue
            if t.parent_id is not None:
                parent = by_id.get(t.parent_id)
                if parent is None:
                    continue
                if parent.status in (TaskStatus.DONE, TaskStatus.CANCELED):
                    continue
            deps = self._deps.list_dependencies(tenant_id, t.id)
            blocked = False
            for dep_id in deps:
                dep_task = by_id.get(dep_id)
                if dep_task is None:
                    blocked = True
                    break
                if dep_task.status not in (TaskStatus.DONE, TaskStatus.CANCELED):
                    blocked = True
                    break
            if blocked:
                continue
            ready.append(t)

        ready.sort(key=lambda t: (t.created_at, str(t.id)))
        return ready

    def _children_of(self, tenant_id: str, parent_id: UUID) -> List[Task]:
        tasks = self._tasks.list(tenant_id)
        children = [t for t in tasks if t.parent_id == parent_id]
        children.sort(key=lambda t: (t.created_at, str(t.id)))
        return children

    def _hierarchical_view(self, tenant_id: str, tasks: Sequence[Task]) -> List[Dict[str, Any]]:
        by_parent: Dict[Optional[UUID], List[Task]] = {}
        for t in tasks:
            by_parent.setdefault(t.parent_id, []).append(t)
        for k in list(by_parent.keys()):
            by_parent[k].sort(key=lambda t: (t.created_at, str(t.id)))

        def build(parent_id: Optional[UUID]) -> List[Dict[str, Any]]:
            out: List[Dict[str, Any]] = []
            for t in by_parent.get(parent_id, []):
                node = t.to_dict()
                node["children"] = build(t.id)
                out.append(node)
            return out

        return build(None)

    def _creates_cycle(self, tenant_id: str, task_id: UUID, depends_on_id: UUID) -> bool:
        visited: Set[UUID] = set()
        stack: List[UUID] = [depends_on_id]
        while stack:
            cur = stack.pop()
            if cur == task_id:
                return True
            if cur in visited:
                continue
            visited.add(cur)
            for nxt in self._deps.list_dependencies(tenant_id, cur):
                stack.append(nxt)
        return False


class PostgreSQLTaskRepository(TaskRepository):
    def __init__(self, dsn: str) -> None:
        raise NotImplementedError("PostgreSQL storage is not implemented in this standalone module")


class PostgreSQLDependencyRepository(DependencyRepository):
    def __init__(self, dsn: str) -> None:
        raise NotImplementedError("PostgreSQL storage is not implemented in this standalone module")