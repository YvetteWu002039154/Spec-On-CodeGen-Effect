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


class TaskEventType(str, Enum):
    TASK_CREATED = "task_created"
    TASK_UPDATED = "task_updated"
    TASK_DELETED = "task_deleted"
    TASK_STATUS_UPDATED = "task_status_updated"
    TASK_CHILD_CREATED = "task_child_created"
    TASK_DEPENDENCY_LINKED = "task_dependency_linked"
    TASKS_BULK_UPSERTED = "tasks_bulk_upserted"


class TaskModel(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    tenant_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.TODO
    parent_id: Optional[UUID] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

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
    title: Optional[str] = Field(default=None, min_length=1)
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    parent_id: Optional[UUID] = None


class TaskBulkUpsertItem(BaseModel):
    id: Optional[UUID] = None
    tenant_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.TODO
    parent_id: Optional[UUID] = None


class TaskDependencyModel(BaseModel):
    tenant_id: str = Field(min_length=1)
    task_id: UUID
    depends_on_task_id: UUID
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("created_at")
    @classmethod
    def _ensure_tz_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None or v.tzinfo.utcoffset(v) is None:
            raise ValueError("datetime must be timezone-aware")
        return v

    @field_validator("depends_on_task_id")
    @classmethod
    def _no_self_dependency(cls, v: UUID, info: Any) -> UUID:
        task_id = info.data.get("task_id")
        if task_id is not None and v == task_id:
            raise ValueError("task cannot depend on itself")
        return v


class TaskNode(BaseModel):
    task: TaskModel
    children: List["TaskNode"] = Field(default_factory=list)


TaskNode.model_rebuild()


@dataclass(frozen=True)
class TaskEvent:
    type: TaskEventType
    tenant_id: str
    timestamp: datetime
    payload: Dict[str, Any]


class EventBus:
    def __init__(self) -> None:
        self._subscribers: Dict[TaskEventType, List[Callable[[TaskEvent], None]]] = {}

    def subscribe(self, event_type: TaskEventType, handler: Callable[[TaskEvent], None]) -> None:
        self._subscribers.setdefault(event_type, []).append(handler)

    def publish(self, event: TaskEvent) -> None:
        for handler in list(self._subscribers.get(event.type, [])):
            handler(event)


class TaskNotFoundError(KeyError):
    pass


class TaskValidationError(ValueError):
    pass


class DependencyError(ValueError):
    pass


class StorageError(RuntimeError):
    pass


class TaskRepository:
    def add_task(self, task: TaskModel) -> TaskModel:
        raise NotImplementedError

    def get_task(self, tenant_id: str, task_id: UUID) -> TaskModel:
        raise NotImplementedError

    def update_task(self, tenant_id: str, task_id: UUID, update: TaskUpdate) -> TaskModel:
        raise NotImplementedError

    def delete_task(self, tenant_id: str, task_id: UUID) -> None:
        raise NotImplementedError

    def list_tasks(self, tenant_id: str) -> List[TaskModel]:
        raise NotImplementedError

    def bulk_upsert_tasks(self, items: Sequence[TaskBulkUpsertItem]) -> List[TaskModel]:
        raise NotImplementedError

    def add_dependency(self, dep: TaskDependencyModel) -> None:
        raise NotImplementedError

    def list_dependencies(self, tenant_id: str) -> List[TaskDependencyModel]:
        raise NotImplementedError

    def list_dependencies_for_task(self, tenant_id: str, task_id: UUID) -> List[TaskDependencyModel]:
        raise NotImplementedError


class InMemoryTaskRepository(TaskRepository):
    def __init__(self) -> None:
        self._tasks: Dict[Tuple[str, UUID], TaskModel] = {}
        self._deps: Dict[Tuple[str, UUID, UUID], TaskDependencyModel] = {}

    def add_task(self, task: TaskModel) -> TaskModel:
        key = (task.tenant_id, task.id)
        if key in self._tasks:
            raise StorageError("task already exists")
        self._tasks[key] = task
        return task

    def get_task(self, tenant_id: str, task_id: UUID) -> TaskModel:
        key = (tenant_id, task_id)
        if key not in self._tasks:
            raise TaskNotFoundError(str(task_id))
        return self._tasks[key]

    def update_task(self, tenant_id: str, task_id: UUID, update: TaskUpdate) -> TaskModel:
        existing = self.get_task(tenant_id, task_id)
        data = existing.model_dump()
        upd = update.model_dump(exclude_unset=True)
        data.update(upd)
        data["updated_at"] = datetime.now(timezone.utc)
        updated = TaskModel(**data)
        self._tasks[(tenant_id, task_id)] = updated
        return updated

    def delete_task(self, tenant_id: str, task_id: UUID) -> None:
        key = (tenant_id, task_id)
        if key not in self._tasks:
            raise TaskNotFoundError(str(task_id))
        del self._tasks[key]
        to_delete = [k for k in self._deps.keys() if k[0] == tenant_id and (k[1] == task_id or k[2] == task_id)]
        for k in to_delete:
            del self._deps[k]

    def list_tasks(self, tenant_id: str) -> List[TaskModel]:
        return [t for (tid, _), t in self._tasks.items() if tid == tenant_id]

    def bulk_upsert_tasks(self, items: Sequence[TaskBulkUpsertItem]) -> List[TaskModel]:
        results: List[TaskModel] = []
        now = datetime.now(timezone.utc)
        for item in items:
            task_id = item.id or uuid4()
            key = (item.tenant_id, task_id)
            if key in self._tasks:
                existing = self._tasks[key]
                data = existing.model_dump()
                data.update(
                    {
                        "title": item.title,
                        "description": item.description,
                        "status": item.status,
                        "parent_id": item.parent_id,
                        "updated_at": now,
                    }
                )
                updated = TaskModel(**data)
                self._tasks[key] = updated
                results.append(updated)
            else:
                created = TaskModel(
                    id=task_id,
                    tenant_id=item.tenant_id,
                    title=item.title,
                    description=item.description,
                    status=item.status,
                    parent_id=item.parent_id,
                    created_at=now,
                    updated_at=now,
                )
                self._tasks[key] = created
                results.append(created)
        return results

    def add_dependency(self, dep: TaskDependencyModel) -> None:
        key = (dep.tenant_id, dep.task_id, dep.depends_on_task_id)
        if key in self._deps:
            return
        self._deps[key] = dep

    def list_dependencies(self, tenant_id: str) -> List[TaskDependencyModel]:
        return [d for (tid, _, _), d in self._deps.items() if tid == tenant_id]

    def list_dependencies_for_task(self, tenant_id: str, task_id: UUID) -> List[TaskDependencyModel]:
        return [d for (tid, t, _), d in self._deps.items() if tid == tenant_id and t == task_id]


class PostgresTaskRepository(TaskRepository):
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        raise NotImplementedError("PostgreSQL storage is not implemented in this runtime")

    def add_task(self, task: TaskModel) -> TaskModel:
        raise NotImplementedError

    def get_task(self, tenant_id: str, task_id: UUID) -> TaskModel:
        raise NotImplementedError

    def update_task(self, tenant_id: str, task_id: UUID, update: TaskUpdate) -> TaskModel:
        raise NotImplementedError

    def delete_task(self, tenant_id: str, task_id: UUID) -> None:
        raise NotImplementedError

    def list_tasks(self, tenant_id: str) -> List[TaskModel]:
        raise NotImplementedError

    def bulk_upsert_tasks(self, items: Sequence[TaskBulkUpsertItem]) -> List[TaskModel]:
        raise NotImplementedError

    def add_dependency(self, dep: TaskDependencyModel) -> None:
        raise NotImplementedError

    def list_dependencies(self, tenant_id: str) -> List[TaskDependencyModel]:
        raise NotImplementedError

    def list_dependencies_for_task(self, tenant_id: str, task_id: UUID) -> List[TaskDependencyModel]:
        raise NotImplementedError


class TodoToolset:
    def __init__(self, repository: TaskRepository, event_bus: Optional[EventBus] = None) -> None:
        self._repo = repository
        self._events = event_bus or EventBus()

    @property
    def events(self) -> EventBus:
        return self._events

    def add_task(self, task: Union[TaskCreate, Dict[str, Any]]) -> TaskModel:
        try:
            create = task if isinstance(task, TaskCreate) else TaskCreate(**task)
        except ValidationError as e:
            raise TaskValidationError(str(e)) from e

        now = datetime.now(timezone.utc)
        model = TaskModel(
            tenant_id=create.tenant_id,
            title=create.title,
            description=create.description,
            status=create.status,
            parent_id=create.parent_id,
            created_at=now,
            updated_at=now,
        )
        self._validate_parent_exists(model.tenant_id, model.parent_id)
        created = self._repo.add_task(model)
        self._publish(TaskEventType.TASK_CREATED, created.tenant_id, {"task": created.model_dump(mode="json")})
        return created

    def bulk_write_update_tasks(self, items: Sequence[Union[TaskBulkUpsertItem, Dict[str, Any]]]) -> List[TaskModel]:
        parsed: List[TaskBulkUpsertItem] = []
        try:
            for it in items:
                parsed.append(it if isinstance(it, TaskBulkUpsertItem) else TaskBulkUpsertItem(**it))
        except ValidationError as e:
            raise TaskValidationError(str(e)) from e

        for it in parsed:
            self._validate_parent_exists(it.tenant_id, it.parent_id)

        results = self._repo.bulk_upsert_tasks(parsed)
        self._publish(
            TaskEventType.TASKS_BULK_UPSERTED,
            results[0].tenant_id if results else (parsed[0].tenant_id if parsed else ""),
            {"tasks": [t.model_dump(mode="json") for t in results]},
        )
        return results

    def list_all_tasks(self, tenant_id: str, hierarchical: bool = False) -> Union[List[TaskModel], List[TaskNode]]:
        tasks = self._repo.list_tasks(tenant_id)
        if not hierarchical:
            return sorted(tasks, key=lambda t: (t.created_at, str(t.id)))
        return self._build_hierarchy(tasks)

    def update_task_status_by_id(self, tenant_id: str, task_id: UUID, status: TaskStatus) -> TaskModel:
        updated = self._repo.update_task(tenant_id, task_id, TaskUpdate(status=status))
        self._publish(
            TaskEventType.TASK_STATUS_UPDATED,
            tenant_id,
            {"task_id": str(task_id), "status": status.value, "task": updated.model_dump(mode="json")},
        )
        return updated

    def delete_task_by_id(self, tenant_id: str, task_id: UUID) -> None:
        self._repo.delete_task(tenant_id, task_id)
        self._publish(TaskEventType.TASK_DELETED, tenant_id, {"task_id": str(task_id)})

    def create_child_task(
        self, tenant_id: str, parent_id: UUID, child: Union[TaskCreate, Dict[str, Any]]
    ) -> TaskModel:
        self._repo.get_task(tenant_id, parent_id)
        try:
            create = child if isinstance(child, TaskCreate) else TaskCreate(**child)
        except ValidationError as e:
            raise TaskValidationError(str(e)) from e

        if create.tenant_id != tenant_id:
            raise TaskValidationError("tenant_id mismatch for child task")

        now = datetime.now(timezone.utc)
        model = TaskModel(
            tenant_id=tenant_id,
            title=create.title,
            description=create.description,
            status=create.status,
            parent_id=parent_id,
            created_at=now,
            updated_at=now,
        )
        created = self._repo.add_task(model)
        self._publish(
            TaskEventType.TASK_CHILD_CREATED,
            tenant_id,
            {"parent_id": str(parent_id), "task": created.model_dump(mode="json")},
        )
        return created

    def link_tasks_with_dependency(self, tenant_id: str, task_id: UUID, depends_on_task_id: UUID) -> None:
        self._repo.get_task(tenant_id, task_id)
        self._repo.get_task(tenant_id, depends_on_task_id)

        if task_id == depends_on_task_id:
            raise DependencyError("task cannot depend on itself")

        if self._creates_cycle(tenant_id, task_id, depends_on_task_id):
            raise DependencyError("dependency would create a cycle")

        dep = TaskDependencyModel(tenant_id=tenant_id, task_id=task_id, depends_on_task_id=depends_on_task_id)
        self._repo.add_dependency(dep)
        self._publish(
            TaskEventType.TASK_DEPENDENCY_LINKED,
            tenant_id,
            {"task_id": str(task_id), "depends_on_task_id": str(depends_on_task_id)},
        )

    def list_tasks_ready_to_work_on(self, tenant_id: str) -> List[TaskModel]:
        tasks = self._repo.list_tasks(tenant_id)
        deps = self._repo.list_dependencies(tenant_id)

        task_by_id: Dict[UUID, TaskModel] = {t.id: t for t in tasks}
        prereqs: Dict[UUID, List[UUID]] = {}
        for d in deps:
            prereqs.setdefault(d.task_id, []).append(d.depends_on_task_id)

        ready: List[TaskModel] = []
        for t in tasks:
            if t.status in (TaskStatus.DONE, TaskStatus.IN_PROGRESS):
                continue
            required = prereqs.get(t.id, [])
            if all(task_by_id.get(rid) is not None and task_by_id[rid].status == TaskStatus.DONE for rid in required):
                ready.append(t)

        return sorted(ready, key=lambda t: (t.created_at, str(t.id)))

    def _publish(self, event_type: TaskEventType, tenant_id: str, payload: Dict[str, Any]) -> None:
        event = TaskEvent(type=event_type, tenant_id=tenant_id, timestamp=datetime.now(timezone.utc), payload=payload)
        self._events.publish(event)

    def _validate_parent_exists(self, tenant_id: str, parent_id: Optional[UUID]) -> None:
        if parent_id is None:
            return
        self._repo.get_task(tenant_id, parent_id)

    def _build_hierarchy(self, tasks: Sequence[TaskModel]) -> List[TaskNode]:
        by_id: Dict[UUID, TaskModel] = {t.id: t for t in tasks}
        children_map: Dict[Optional[UUID], List[TaskModel]] = {}
        for t in tasks:
            pid = t.parent_id if t.parent_id in by_id else None
            children_map.setdefault(pid, []).append(t)

        def build(parent_id: Optional[UUID]) -> List[TaskNode]:
            nodes: List[TaskNode] = []
            for t in sorted(children_map.get(parent_id, []), key=lambda x: (x.created_at, str(x.id))):
                nodes.append(TaskNode(task=t, children=build(t.id)))
            return nodes

        return build(None)

    def _creates_cycle(self, tenant_id: str, task_id: UUID, depends_on_task_id: UUID) -> bool:
        deps = self._repo.list_dependencies(tenant_id)
        graph: Dict[UUID, List[UUID]] = {}
        for d in deps:
            graph.setdefault(d.task_id, []).append(d.depends_on_task_id)
        graph.setdefault(task_id, []).append(depends_on_task_id)

        visited: set[UUID] = set()
        stack: set[UUID] = set()

        def dfs(n: UUID) -> bool:
            if n in stack:
                return True
            if n in visited:
                return False
            visited.add(n)
            stack.add(n)
            for m in graph.get(n, []):
                if dfs(m):
                    return True
            stack.remove(n)
            return False

        return dfs(task_id)