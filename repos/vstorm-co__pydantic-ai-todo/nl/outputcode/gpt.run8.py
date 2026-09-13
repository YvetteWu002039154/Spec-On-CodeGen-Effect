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
    TASK_CREATED = "task.created"
    TASK_UPDATED = "task.updated"
    TASK_DELETED = "task.deleted"
    TASK_STATUS_CHANGED = "task.status_changed"
    TASK_DEPENDENCY_LINKED = "task.dependency_linked"
    TASK_CHILD_CREATED = "task.child_created"
    TASK_BULK_UPSERTED = "task.bulk_upserted"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Task(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    tenant_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.TODO
    parent_id: Optional[UUID] = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    @field_validator("created_at", "updated_at")
    @classmethod
    def _ensure_tz_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None or v.tzinfo.utcoffset(v) is None:
            raise ValueError("datetime must be timezone-aware")
        return v


class TaskCreate(BaseModel):
    tenant_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.TODO
    parent_id: Optional[UUID] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    parent_id: Optional[UUID] = None


class TaskUpsert(BaseModel):
    tenant_id: str = Field(min_length=1)
    id: Optional[UUID] = None
    title: str = Field(min_length=1)
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.TODO
    parent_id: Optional[UUID] = None


class TaskEvent(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    tenant_id: str = Field(min_length=1)
    type: TaskEventType
    task_id: Optional[UUID] = None
    timestamp: datetime = Field(default_factory=_utcnow)
    payload: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("timestamp")
    @classmethod
    def _ensure_tz_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None or v.tzinfo.utcoffset(v) is None:
            raise ValueError("datetime must be timezone-aware")
        return v


class TaskNotFoundError(KeyError):
    pass


class TaskValidationError(ValueError):
    pass


class DependencyError(ValueError):
    pass


class EventHandlerError(RuntimeError):
    pass


class TaskRepository:
    def add_task(self, task: Task) -> Task:
        raise NotImplementedError

    def get_task(self, tenant_id: str, task_id: UUID) -> Task:
        raise NotImplementedError

    def update_task(self, tenant_id: str, task_id: UUID, update: TaskUpdate) -> Task:
        raise NotImplementedError

    def delete_task(self, tenant_id: str, task_id: UUID) -> None:
        raise NotImplementedError

    def list_tasks(self, tenant_id: str) -> List[Task]:
        raise NotImplementedError

    def bulk_upsert(self, tasks: Sequence[TaskUpsert]) -> List[Task]:
        raise NotImplementedError

    def create_child_task(self, tenant_id: str, parent_id: UUID, child: TaskCreate) -> Task:
        raise NotImplementedError

    def link_dependency(self, tenant_id: str, task_id: UUID, depends_on_id: UUID) -> None:
        raise NotImplementedError

    def list_dependencies(self, tenant_id: str, task_id: UUID) -> List[UUID]:
        raise NotImplementedError

    def list_dependents(self, tenant_id: str, task_id: UUID) -> List[UUID]:
        raise NotImplementedError


class InMemoryTaskRepository(TaskRepository):
    def __init__(self) -> None:
        self._tasks: Dict[Tuple[str, UUID], Task] = {}
        self._deps: Dict[Tuple[str, UUID], set[UUID]] = {}
        self._dependents: Dict[Tuple[str, UUID], set[UUID]] = {}

    def add_task(self, task: Task) -> Task:
        key = (task.tenant_id, task.id)
        if key in self._tasks:
            raise TaskValidationError("task with id already exists")
        self._tasks[key] = task
        self._deps.setdefault(key, set())
        self._dependents.setdefault(key, set())
        return task

    def get_task(self, tenant_id: str, task_id: UUID) -> Task:
        key = (tenant_id, task_id)
        task = self._tasks.get(key)
        if task is None:
            raise TaskNotFoundError(str(task_id))
        return task

    def update_task(self, tenant_id: str, task_id: UUID, update: TaskUpdate) -> Task:
        key = (tenant_id, task_id)
        task = self._tasks.get(key)
        if task is None:
            raise TaskNotFoundError(str(task_id))

        data = task.model_dump()
        upd = update.model_dump(exclude_unset=True)
        if "parent_id" in upd:
            data["parent_id"] = upd["parent_id"]
        if "title" in upd:
            data["title"] = upd["title"]
        if "description" in upd:
            data["description"] = upd["description"]
        if "status" in upd:
            data["status"] = upd["status"]
        data["updated_at"] = _utcnow()
        new_task = Task(**data)
        self._tasks[key] = new_task
        return new_task

    def delete_task(self, tenant_id: str, task_id: UUID) -> None:
        key = (tenant_id, task_id)
        if key not in self._tasks:
            raise TaskNotFoundError(str(task_id))

        for dep in list(self._deps.get(key, set())):
            dep_key = (tenant_id, dep)
            self._dependents.get(dep_key, set()).discard(task_id)
        for depd in list(self._dependents.get(key, set())):
            depd_key = (tenant_id, depd)
            self._deps.get(depd_key, set()).discard(task_id)

        self._deps.pop(key, None)
        self._dependents.pop(key, None)
        self._tasks.pop(key, None)

    def list_tasks(self, tenant_id: str) -> List[Task]:
        return [t for (tid, _), t in self._tasks.items() if tid == tenant_id]

    def bulk_upsert(self, tasks: Sequence[TaskUpsert]) -> List[Task]:
        results: List[Task] = []
        for up in tasks:
            task_id = up.id or uuid4()
            key = (up.tenant_id, task_id)
            existing = self._tasks.get(key)
            if existing is None:
                task = Task(
                    id=task_id,
                    tenant_id=up.tenant_id,
                    title=up.title,
                    description=up.description,
                    status=up.status,
                    parent_id=up.parent_id,
                    created_at=_utcnow(),
                    updated_at=_utcnow(),
                )
                self._tasks[key] = task
                self._deps.setdefault(key, set())
                self._dependents.setdefault(key, set())
                results.append(task)
            else:
                data = existing.model_dump()
                data["title"] = up.title
                data["description"] = up.description
                data["status"] = up.status
                data["parent_id"] = up.parent_id
                data["updated_at"] = _utcnow()
                task = Task(**data)
                self._tasks[key] = task
                self._deps.setdefault(key, set())
                self._dependents.setdefault(key, set())
                results.append(task)
        return results

    def create_child_task(self, tenant_id: str, parent_id: UUID, child: TaskCreate) -> Task:
        _ = self.get_task(tenant_id, parent_id)
        task = Task(
            tenant_id=tenant_id,
            title=child.title,
            description=child.description,
            status=child.status,
            parent_id=parent_id,
        )
        return self.add_task(task)

    def link_dependency(self, tenant_id: str, task_id: UUID, depends_on_id: UUID) -> None:
        task_key = (tenant_id, task_id)
        dep_key = (tenant_id, depends_on_id)
        if task_id == depends_on_id:
            raise DependencyError("task cannot depend on itself")
        if task_key not in self._tasks:
            raise TaskNotFoundError(str(task_id))
        if dep_key not in self._tasks:
            raise TaskNotFoundError(str(depends_on_id))

        self._deps.setdefault(task_key, set())
        self._dependents.setdefault(dep_key, set())
        self._deps[task_key].add(depends_on_id)
        self._dependents[dep_key].add(task_id)

    def list_dependencies(self, tenant_id: str, task_id: UUID) -> List[UUID]:
        key = (tenant_id, task_id)
        if key not in self._tasks:
            raise TaskNotFoundError(str(task_id))
        return sorted(self._deps.get(key, set()), key=lambda x: str(x))

    def list_dependents(self, tenant_id: str, task_id: UUID) -> List[UUID]:
        key = (tenant_id, task_id)
        if key not in self._tasks:
            raise TaskNotFoundError(str(task_id))
        return sorted(self._dependents.get(key, set()), key=lambda x: str(x))


class EventBus:
    def __init__(self) -> None:
        self._handlers: Dict[TaskEventType, List[Callable[[TaskEvent], None]]] = {}

    def subscribe(self, event_type: TaskEventType, handler: Callable[[TaskEvent], None]) -> None:
        self._handlers.setdefault(event_type, []).append(handler)

    def publish(self, event: TaskEvent) -> None:
        handlers = list(self._handlers.get(event.type, []))
        for h in handlers:
            try:
                h(event)
            except Exception as e:
                raise EventHandlerError(str(e)) from e


class TaskNode(BaseModel):
    task: Task
    children: List["TaskNode"] = Field(default_factory=list)


TaskNode.model_rebuild()


class TodoToolset:
    def __init__(self, repository: TaskRepository, event_bus: Optional[EventBus] = None) -> None:
        self._repo = repository
        self._events = event_bus or EventBus()

    @property
    def events(self) -> EventBus:
        return self._events

    def add_task(self, task: TaskCreate) -> Task:
        try:
            t = Task(
                tenant_id=task.tenant_id,
                title=task.title,
                description=task.description,
                status=task.status,
                parent_id=task.parent_id,
            )
        except ValidationError as e:
            raise TaskValidationError(str(e)) from e

        self._validate_parent(t.tenant_id, t.parent_id, t.id)
        created = self._repo.add_task(t)
        self._events.publish(
            TaskEvent(
                tenant_id=created.tenant_id,
                type=TaskEventType.TASK_CREATED,
                task_id=created.id,
                payload={"task": created.model_dump(mode="json")},
            )
        )
        return created

    def bulk_write_update_tasks(self, tasks: Sequence[TaskUpsert]) -> List[Task]:
        if not tasks:
            return []
        for up in tasks:
            self._validate_parent(up.tenant_id, up.parent_id, up.id)
        results = self._repo.bulk_upsert(tasks)
        if results:
            tenant_id = results[0].tenant_id
            self._events.publish(
                TaskEvent(
                    tenant_id=tenant_id,
                    type=TaskEventType.TASK_BULK_UPSERTED,
                    payload={"tasks": [t.model_dump(mode="json") for t in results]},
                )
            )
        return results

    def list_all_tasks(self, tenant_id: str, hierarchical: bool = False) -> Union[List[Task], List[TaskNode]]:
        tasks = self._repo.list_tasks(tenant_id)
        tasks_sorted = sorted(tasks, key=lambda t: (t.created_at, str(t.id)))
        if not hierarchical:
            return tasks_sorted
        return self._build_tree(tasks_sorted)

    def update_task_status_by_id(self, tenant_id: str, task_id: UUID, status: TaskStatus) -> Task:
        existing = self._repo.get_task(tenant_id, task_id)
        updated = self._repo.update_task(tenant_id, task_id, TaskUpdate(status=status))
        self._events.publish(
            TaskEvent(
                tenant_id=tenant_id,
                type=TaskEventType.TASK_STATUS_CHANGED,
                task_id=task_id,
                payload={
                    "from": existing.status,
                    "to": updated.status,
                    "task": updated.model_dump(mode="json"),
                },
            )
        )
        return updated

    def delete_task_by_id(self, tenant_id: str, task_id: UUID) -> None:
        _ = self._repo.get_task(tenant_id, task_id)
        self._repo.delete_task(tenant_id, task_id)
        self._events.publish(
            TaskEvent(
                tenant_id=tenant_id,
                type=TaskEventType.TASK_DELETED,
                task_id=task_id,
                payload={"task_id": str(task_id)},
            )
        )

    def create_child_task(self, tenant_id: str, parent_id: UUID, child: TaskCreate) -> Task:
        if child.tenant_id != tenant_id:
            raise TaskValidationError("child.tenant_id must match tenant_id")
        created = self._repo.create_child_task(tenant_id, parent_id, child)
        self._events.publish(
            TaskEvent(
                tenant_id=tenant_id,
                type=TaskEventType.TASK_CHILD_CREATED,
                task_id=created.id,
                payload={"parent_id": str(parent_id), "task": created.model_dump(mode="json")},
            )
        )
        return created

    def link_tasks_with_dependency(self, tenant_id: str, task_id: UUID, depends_on_id: UUID) -> None:
        self._repo.link_dependency(tenant_id, task_id, depends_on_id)
        if self._creates_cycle(tenant_id, task_id):
            self._repo.link_dependency(tenant_id, task_id, depends_on_id)
            self._unlink_dependency_in_memory_if_possible(tenant_id, task_id, depends_on_id)
            raise DependencyError("dependency would create a cycle")
        self._events.publish(
            TaskEvent(
                tenant_id=tenant_id,
                type=TaskEventType.TASK_DEPENDENCY_LINKED,
                task_id=task_id,
                payload={"task_id": str(task_id), "depends_on_id": str(depends_on_id)},
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
            if all((by_id.get(d) is not None and by_id[d].status == TaskStatus.DONE) for d in deps):
                ready.append(t)
        return sorted(ready, key=lambda t: (t.created_at, str(t.id)))

    def _build_tree(self, tasks: Sequence[Task]) -> List[TaskNode]:
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

        def sort_children(n: TaskNode) -> None:
            n.children.sort(key=lambda c: (c.task.created_at, str(c.task.id)))
            for ch in n.children:
                sort_children(ch)

        roots.sort(key=lambda n: (n.task.created_at, str(n.task.id)))
        for r in roots:
            sort_children(r)
        return roots

    def _validate_parent(self, tenant_id: str, parent_id: Optional[UUID], self_id: Optional[UUID]) -> None:
        if parent_id is None:
            return
        if self_id is not None and parent_id == self_id:
            raise TaskValidationError("task cannot be its own parent")
        parent = self._repo.get_task(tenant_id, parent_id)
        if parent.tenant_id != tenant_id:
            raise TaskValidationError("parent must be in same tenant")

    def _creates_cycle(self, tenant_id: str, start_task_id: UUID) -> bool:
        visited: set[UUID] = set()
        stack: List[UUID] = [start_task_id]
        while stack:
            cur = stack.pop()
            if cur in visited:
                continue
            visited.add(cur)
            deps = self._repo.list_dependencies(tenant_id, cur)
            for d in deps:
                if d == start_task_id and cur != start_task_id:
                    return True
                if d == start_task_id and cur == start_task_id:
                    return True
                if d in visited:
                    continue
                stack.append(d)
        return False

    def _unlink_dependency_in_memory_if_possible(self, tenant_id: str, task_id: UUID, depends_on_id: UUID) -> None:
        repo = self._repo
        if isinstance(repo, InMemoryTaskRepository):
            task_key = (tenant_id, task_id)
            dep_key = (tenant_id, depends_on_id)
            repo._deps.get(task_key, set()).discard(depends_on_id)
            repo._dependents.get(dep_key, set()).discard(task_id)


__all__ = [
    "TaskStatus",
    "TaskEventType",
    "Task",
    "TaskCreate",
    "TaskUpdate",
    "TaskUpsert",
    "TaskEvent",
    "TaskRepository",
    "InMemoryTaskRepository",
    "EventBus",
    "TaskNode",
    "TodoToolset",
    "TaskNotFoundError",
    "TaskValidationError",
    "DependencyError",
    "EventHandlerError",
]