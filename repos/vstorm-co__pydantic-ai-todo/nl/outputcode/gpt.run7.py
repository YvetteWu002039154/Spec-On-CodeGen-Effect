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


class TaskValidationError(ValueError):
    pass


class TaskNotFoundError(KeyError):
    pass


class DependencyError(ValueError):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_tenant_id(tenant_id: str) -> str:
    if not isinstance(tenant_id, str) or not tenant_id.strip():
        raise TaskValidationError("tenant_id must be a non-empty string")
    return tenant_id.strip()


def _ensure_title(title: str) -> str:
    if not isinstance(title, str) or not title.strip():
        raise TaskValidationError("title must be a non-empty string")
    return title.strip()


def _ensure_status(status: Union[TaskStatus, str]) -> TaskStatus:
    if isinstance(status, TaskStatus):
        return status
    if isinstance(status, str):
        try:
            return TaskStatus(status)
        except Exception as e:
            raise TaskValidationError(f"invalid status: {status}") from e
    raise TaskValidationError("status must be a TaskStatus or str")


def _ensure_uuid(value: Union[UUID, str], field_name: str) -> UUID:
    if isinstance(value, UUID):
        return value
    if isinstance(value, str):
        try:
            return UUID(value)
        except Exception as e:
            raise TaskValidationError(f"{field_name} must be a valid UUID string") from e
    raise TaskValidationError(f"{field_name} must be a UUID or UUID string")


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
        "_dependency_ids",
    )

    def __init__(
        self,
        tenant_id: str,
        title: str,
        description: Optional[str] = None,
        status: Union[TaskStatus, str] = TaskStatus.TODO,
        task_id: Optional[UUID] = None,
        parent_id: Optional[UUID] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        dependency_ids: Optional[Iterable[UUID]] = None,
    ) -> None:
        self._id = task_id or uuid4()
        self._tenant_id = _ensure_tenant_id(tenant_id)
        self._title = _ensure_title(title)
        self._description = (description or "").strip()
        self._status = _ensure_status(status)
        self._parent_id = parent_id
        now = _utcnow()
        self._created_at = created_at or now
        self._updated_at = updated_at or now
        self._dependency_ids = set(dependency_ids or [])

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
    def description(self) -> str:
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

    @property
    def dependency_ids(self) -> Tuple[UUID, ...]:
        return tuple(sorted(self._dependency_ids, key=lambda x: x.hex))

    def set_title(self, title: str) -> None:
        self._title = _ensure_title(title)
        self._touch()

    def set_description(self, description: Optional[str]) -> None:
        self._description = (description or "").strip()
        self._touch()

    def set_status(self, status: Union[TaskStatus, str]) -> None:
        self._status = _ensure_status(status)
        self._touch()

    def set_parent(self, parent_id: Optional[UUID]) -> None:
        self._parent_id = parent_id
        self._touch()

    def add_dependency(self, dependency_id: UUID) -> None:
        self._dependency_ids.add(dependency_id)
        self._touch()

    def remove_dependency(self, dependency_id: UUID) -> None:
        if dependency_id in self._dependency_ids:
            self._dependency_ids.remove(dependency_id)
            self._touch()

    def _touch(self) -> None:
        self._updated_at = _utcnow()

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
            "dependency_ids": [str(d) for d in self.dependency_ids],
        }


class EventBus:
    def __init__(self) -> None:
        self._subscribers: Dict[TaskEventType, List[Callable[[TaskEvent], None]]] = {}

    def subscribe(self, event_type: TaskEventType, callback: Callable[[TaskEvent], None]) -> None:
        if not callable(callback):
            raise TaskValidationError("callback must be callable")
        self._subscribers.setdefault(event_type, []).append(callback)

    def publish(self, event: TaskEvent) -> None:
        for cb in list(self._subscribers.get(event.event_type, [])):
            cb(event)


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


class InMemoryTaskRepository(TaskRepository):
    def __init__(self) -> None:
        self._tasks: Dict[str, Dict[UUID, Task]] = {}

    def add(self, task: Task) -> None:
        tenant = self._tasks.setdefault(task.tenant_id, {})
        if task.id in tenant:
            raise TaskValidationError("task with this id already exists")
        tenant[task.id] = task

    def get(self, tenant_id: str, task_id: UUID) -> Task:
        tenant_id = _ensure_tenant_id(tenant_id)
        try:
            return self._tasks[tenant_id][task_id]
        except KeyError as e:
            raise TaskNotFoundError(f"task not found: {task_id}") from e

    def list(self, tenant_id: str) -> List[Task]:
        tenant_id = _ensure_tenant_id(tenant_id)
        return list(self._tasks.get(tenant_id, {}).values())

    def update(self, task: Task) -> None:
        tenant = self._tasks.setdefault(task.tenant_id, {})
        if task.id not in tenant:
            raise TaskNotFoundError(f"task not found: {task.id}")
        tenant[task.id] = task

    def delete(self, tenant_id: str, task_id: UUID) -> None:
        tenant_id = _ensure_tenant_id(tenant_id)
        tenant = self._tasks.get(tenant_id, {})
        if task_id not in tenant:
            raise TaskNotFoundError(f"task not found: {task_id}")
        del tenant[task_id]

    def bulk_upsert(self, tasks: Sequence[Task]) -> None:
        for task in tasks:
            tenant = self._tasks.setdefault(task.tenant_id, {})
            tenant[task.id] = task


class PostgresTaskRepository(TaskRepository):
    def __init__(self, dsn: str) -> None:
        if not isinstance(dsn, str) or not dsn.strip():
            raise TaskValidationError("dsn must be a non-empty string")
        self._dsn = dsn.strip()
        raise NotImplementedError("PostgresTaskRepository requires a PostgreSQL driver; not implemented in this runtime.")

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
        status: Union[TaskStatus, str] = TaskStatus.TODO,
        parent_id: Optional[Union[UUID, str]] = None,
        task_id: Optional[Union[UUID, str]] = None,
    ) -> Task:
        tenant_id = _ensure_tenant_id(tenant_id)
        pid = _ensure_uuid(parent_id, "parent_id") if parent_id is not None else None
        tid = _ensure_uuid(task_id, "task_id") if task_id is not None else None

        if pid is not None:
            parent = self._repo.get(tenant_id, pid)
            if parent.parent_id == tid and tid is not None:
                raise DependencyError("invalid parent relationship")

        task = Task(
            tenant_id=tenant_id,
            title=title,
            description=description,
            status=status,
            task_id=tid,
            parent_id=pid,
        )
        self._repo.add(task)
        self._publish(TaskEventType.TASK_CREATED, task, {"task": task.to_dict()})
        return task

    def bulk_write_update_tasks(self, tasks: Sequence[Dict[str, Any]]) -> List[Task]:
        created_or_updated: List[Task] = []
        task_objs: List[Task] = []

        for item in tasks:
            if not isinstance(item, dict):
                raise TaskValidationError("each task must be a dict")
            tenant_id = _ensure_tenant_id(item.get("tenant_id", ""))
            title = item.get("title")
            if title is None:
                raise TaskValidationError("title is required")
            title = _ensure_title(title)
            description = item.get("description")
            status = _ensure_status(item.get("status", TaskStatus.TODO))
            task_id = item.get("id") or item.get("task_id")
            tid = _ensure_uuid(task_id, "id") if task_id is not None else uuid4()
            parent_id = item.get("parent_id")
            pid = _ensure_uuid(parent_id, "parent_id") if parent_id is not None else None
            dependency_ids_raw = item.get("dependency_ids") or []
            if not isinstance(dependency_ids_raw, list):
                raise TaskValidationError("dependency_ids must be a list")
            dep_ids: List[UUID] = [_ensure_uuid(d, "dependency_id") for d in dependency_ids_raw]

            if pid is not None:
                self._repo.get(tenant_id, pid)

            task = Task(
                tenant_id=tenant_id,
                title=title,
                description=description,
                status=status,
                task_id=tid,
                parent_id=pid,
                dependency_ids=dep_ids,
            )
            task_objs.append(task)

        for task in task_objs:
            self._validate_dependencies(task.tenant_id, task.id, list(task.dependency_ids))
            self._validate_no_parent_cycle(task.tenant_id, task.id, task.parent_id, staged={t.id: t for t in task_objs if t.tenant_id == task.tenant_id})

        self._repo.bulk_upsert(task_objs)
        for task in task_objs:
            created_or_updated.append(task)
            self._publish(TaskEventType.TASK_UPDATED, task, {"task": task.to_dict()})
        return created_or_updated

    def list_all_tasks(self, tenant_id: str, hierarchical: bool = False) -> Union[List[Dict[str, Any]], List[Task]]:
        tenant_id = _ensure_tenant_id(tenant_id)
        tasks = self._repo.list(tenant_id)
        if not hierarchical:
            return tasks

        by_id: Dict[UUID, Task] = {t.id: t for t in tasks}
        children: Dict[Optional[UUID], List[UUID]] = {}
        for t in tasks:
            children.setdefault(t.parent_id, []).append(t.id)
        for k in list(children.keys()):
            children[k].sort(key=lambda x: by_id[x].created_at)

        def build(node_id: UUID) -> Dict[str, Any]:
            t = by_id[node_id]
            return {
                **t.to_dict(),
                "children": [build(cid) for cid in children.get(node_id, [])],
            }

        roots = [tid for tid in children.get(None, []) if tid in by_id]
        return [build(rid) for rid in roots]

    def update_task_status_by_id(
        self,
        tenant_id: str,
        task_id: Union[UUID, str],
        status: Union[TaskStatus, str],
    ) -> Task:
        tenant_id = _ensure_tenant_id(tenant_id)
        tid = _ensure_uuid(task_id, "task_id")
        task = self._repo.get(tenant_id, tid)
        task.set_status(status)
        self._repo.update(task)
        self._publish(TaskEventType.TASK_UPDATED, task, {"task": task.to_dict(), "updated_fields": ["status"]})
        return task

    def delete_task_by_id(self, tenant_id: str, task_id: Union[UUID, str]) -> None:
        tenant_id = _ensure_tenant_id(tenant_id)
        tid = _ensure_uuid(task_id, "task_id")

        tasks = self._repo.list(tenant_id)
        by_id: Dict[UUID, Task] = {t.id: t for t in tasks}
        if tid not in by_id:
            raise TaskNotFoundError(f"task not found: {tid}")

        to_delete: List[UUID] = []
        stack = [tid]
        while stack:
            cur = stack.pop()
            to_delete.append(cur)
            for t in tasks:
                if t.parent_id == cur:
                    stack.append(t.id)

        for t in tasks:
            if t.id in to_delete:
                continue
            for dep in t.dependency_ids:
                if dep in to_delete:
                    t.remove_dependency(dep)
                    self._repo.update(t)
                    self._publish(TaskEventType.TASK_UPDATED, t, {"task": t.to_dict(), "updated_fields": ["dependency_ids"]})

        for did in to_delete:
            task = by_id[did]
            self._repo.delete(tenant_id, did)
            self._publish(TaskEventType.TASK_DELETED, task, {"task_id": str(did)})

    def create_child_task(
        self,
        tenant_id: str,
        parent_task_id: Union[UUID, str],
        title: str,
        description: Optional[str] = None,
        status: Union[TaskStatus, str] = TaskStatus.TODO,
        task_id: Optional[Union[UUID, str]] = None,
    ) -> Task:
        tenant_id = _ensure_tenant_id(tenant_id)
        pid = _ensure_uuid(parent_task_id, "parent_task_id")
        self._repo.get(tenant_id, pid)

        child = self.add_task(
            tenant_id=tenant_id,
            title=title,
            description=description,
            status=status,
            parent_id=pid,
            task_id=task_id,
        )
        self._publish(TaskEventType.CHILD_CREATED, child, {"child_task": child.to_dict(), "parent_id": str(pid)})
        return child

    def link_tasks_with_dependency(
        self,
        tenant_id: str,
        task_id: Union[UUID, str],
        depends_on_task_id: Union[UUID, str],
    ) -> Task:
        tenant_id = _ensure_tenant_id(tenant_id)
        tid = _ensure_uuid(task_id, "task_id")
        depid = _ensure_uuid(depends_on_task_id, "depends_on_task_id")
        if tid == depid:
            raise DependencyError("task cannot depend on itself")

        task = self._repo.get(tenant_id, tid)
        self._repo.get(tenant_id, depid)

        new_deps = set(task.dependency_ids)
        new_deps.add(depid)
        self._validate_dependencies(tenant_id, tid, list(new_deps))

        task.add_dependency(depid)
        self._repo.update(task)
        self._publish(
            TaskEventType.DEPENDENCY_LINKED,
            task,
            {"task_id": str(tid), "depends_on_task_id": str(depid), "task": task.to_dict()},
        )
        return task

    def list_tasks_ready_to_work_on(self, tenant_id: str) -> List[Task]:
        tenant_id = _ensure_tenant_id(tenant_id)
        tasks = self._repo.list(tenant_id)
        by_id: Dict[UUID, Task] = {t.id: t for t in tasks}

        def is_done(t: Task) -> bool:
            return t.status == TaskStatus.DONE

        ready: List[Task] = []
        for t in tasks:
            if t.status in (TaskStatus.DONE, TaskStatus.CANCELED):
                continue
            deps_ok = True
            for dep_id in t.dependency_ids:
                dep = by_id.get(dep_id)
                if dep is None or not is_done(dep):
                    deps_ok = False
                    break
            if deps_ok:
                ready.append(t)

        ready.sort(key=lambda x: (x.created_at, x.id.hex))
        return ready

    def _publish(self, event_type: TaskEventType, task: Task, payload: Dict[str, Any]) -> None:
        event = TaskEvent(
            event_id=uuid4(),
            tenant_id=task.tenant_id,
            event_type=event_type,
            task_id=task.id,
            timestamp=_utcnow(),
            payload=payload,
        )
        self._events.publish(event)

    def _validate_dependencies(self, tenant_id: str, task_id: UUID, dependency_ids: List[UUID]) -> None:
        for dep_id in dependency_ids:
            if dep_id == task_id:
                raise DependencyError("task cannot depend on itself")
            self._repo.get(tenant_id, dep_id)

        graph: Dict[UUID, List[UUID]] = {}
        tasks = self._repo.list(tenant_id)
        for t in tasks:
            graph[t.id] = list(t.dependency_ids)
        graph[task_id] = list(dependency_ids)

        visited: set[UUID] = set()
        stack: set[UUID] = set()

        def dfs(n: UUID) -> None:
            if n in stack:
                raise DependencyError("dependency cycle detected")
            if n in visited:
                return
            visited.add(n)
            stack.add(n)
            for m in graph.get(n, []):
                dfs(m)
            stack.remove(n)

        dfs(task_id)

    def _validate_no_parent_cycle(
        self,
        tenant_id: str,
        task_id: UUID,
        parent_id: Optional[UUID],
        staged: Optional[Dict[UUID, Task]] = None,
    ) -> None:
        if parent_id is None:
            return
        if parent_id == task_id:
            raise DependencyError("task cannot be its own parent")

        staged = staged or {}
        seen: set[UUID] = set()
        cur = parent_id
        while cur is not None:
            if cur == task_id:
                raise DependencyError("parent cycle detected")
            if cur in seen:
                raise DependencyError("parent cycle detected")
            seen.add(cur)
            t = staged.get(cur)
            if t is None:
                t = self._repo.get(tenant_id, cur)
            cur = t.parent_id