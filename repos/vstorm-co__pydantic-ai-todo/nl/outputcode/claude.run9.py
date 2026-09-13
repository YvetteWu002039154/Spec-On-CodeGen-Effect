from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    import asyncpg
    HAS_ASYNCPG = True
except ImportError:
    HAS_ASYNCPG = False

try:
    from pydantic_ai import Agent
    from pydantic_ai.tools import Tool
    HAS_PYDANTIC_AI = True
except ImportError:
    HAS_PYDANTIC_AI = False

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────

class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EventType(str, Enum):
    TASK_CREATED = "task_created"
    TASK_UPDATED = "task_updated"
    TASK_DELETED = "task_deleted"
    TASK_COMPLETED = "task_completed"
    TASK_STATUS_CHANGED = "task_status_changed"
    DEPENDENCY_ADDED = "dependency_added"
    CHILD_TASK_CREATED = "child_task_created"


# ─────────────────────────────────────────────
# Pydantic Models
# ─────────────────────────────────────────────

class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    parent_id: Optional[str] = None
    tenant_id: str = "default"
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    due_date: Optional[datetime] = None
    assigned_to: Optional[str] = None

    class Config:
        use_enum_values = True


class TaskWithChildren(Task):
    children: List["TaskWithChildren"] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)


class TaskDependency(BaseModel):
    task_id: str
    depends_on_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TaskEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType
    task_id: str
    tenant_id: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class BulkTaskInput(BaseModel):
    tasks: List[Task]


class CreateTaskInput(BaseModel):
    title: str
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    parent_id: Optional[str] = None
    tenant_id: str = "default"
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    due_date: Optional[datetime] = None
    assigned_to: Optional[str] = None


class UpdateTaskStatusInput(BaseModel):
    task_id: str
    status: TaskStatus
    tenant_id: str = "default"


class DeleteTaskInput(BaseModel):
    task_id: str
    tenant_id: str = "default"


class CreateChildTaskInput(BaseModel):
    parent_id: str
    title: str
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    tenant_id: str = "default"
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class LinkDependencyInput(BaseModel):
    task_id: str
    depends_on_id: str
    tenant_id: str = "default"


class ListTasksInput(BaseModel):
    tenant_id: str = "default"
    hierarchical: bool = False
    status_filter: Optional[TaskStatus] = None
    priority_filter: Optional[TaskPriority] = None
    assigned_to: Optional[str] = None
    tags: Optional[List[str]] = None


# ─────────────────────────────────────────────
# Storage Backends
# ─────────────────────────────────────────────

class InMemoryStorage:
    """In-memory storage backend for development/testing."""

    def __init__(self) -> None:
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._dependencies: List[Dict[str, Any]] = []

    async def initialize(self) -> None:
        pass

    async def close(self) -> None:
        pass

    async def save_task(self, task: Task) -> Task:
        self._tasks[task.id] = task.dict()
        return task

    async def get_task(self, task_id: str, tenant_id: str) -> Optional[Task]:
        data = self._tasks.get(task_id)
        if data and data.get("tenant_id") == tenant_id:
            return Task(**data)
        return None

    async def list_tasks(
        self,
        tenant_id: str,
        status_filter: Optional[str] = None,
        priority_filter: Optional[str] = None,
        assigned_to: Optional[str] = None,
        tags: Optional[List[str]] = None,
        parent_id: Optional[str] = "__root__",
    ) -> List[Task]:
        results = []
        for data in self._tasks.values():
            if data.get("tenant_id") != tenant_id:
                continue
            if status_filter and data.get("status") != status_filter:
                continue
            if priority_filter and data.get("priority") != priority_filter:
                continue
            if assigned_to and data.get("assigned_to") != assigned_to:
                continue
            if tags:
                task_tags = data.get("tags", [])
                if not all(t in task_tags for t in tags):
                    continue
            if parent_id == "__root__":
                pass
            elif parent_id is None:
                if data.get("parent_id") is not None:
                    continue
            else:
                if data.get("parent_id") != parent_id:
                    continue
            results.append(Task(**data))
        return results

    async def delete_task(self, task_id: str, tenant_id: str) -> bool:
        data = self._tasks.get(task_id)
        if data and data.get("tenant_id") == tenant_id:
            del self._tasks[task_id]
            return True
        return False

    async def add_dependency(self, task_id: str, depends_on_id: str) -> TaskDependency:
        dep = TaskDependency(task_id=task_id, depends_on_id=depends_on_id)
        self._dependencies.append(dep.dict())
        return dep

    async def get_dependencies(self, task_id: str) -> List[str]:
        return [
            d["depends_on_id"]
            for d in self._dependencies
            if d["task_id"] == task_id
        ]

    async def get_dependents(self, task_id: str) -> List[str]:
        return [
            d["task_id"]
            for d in self._dependencies
            if d["depends_on_id"] == task_id
        ]

    async def dependency_exists(self, task_id: str, depends_on_id: str) -> bool:
        return any(
            d["task_id"] == task_id and d["depends_on_id"] == depends_on_id
            for d in self._dependencies
        )

    async def get_ready_tasks(self, tenant_id: str) -> List[Task]:
        all_tasks = await self.list_tasks(tenant_id)
        ready = []
        for task in all_tasks:
            if task.status not in (TaskStatus.PENDING, TaskStatus.IN_PROGRESS):
                continue
            deps = await self.get_dependencies(task.id)
            if not deps:
                ready.append(task)
                continue
            all_completed = True
            for dep_id in deps:
                dep_task = await self.get_task(dep_id, tenant_id)
                if dep_task is None or dep_task.status != TaskStatus.COMPLETED:
                    all_completed = False
                    break
            if all_completed:
                ready.append(task)
        return ready

    async def bulk_save_tasks(self, tasks: List[Task]) -> List[Task]:
        saved = []
        for task in tasks:
            saved.append(await self.save_task(task))
        return saved


class PostgreSQLStorage:
    """PostgreSQL storage backend for production multi-tenant use."""

    def __init__(self, dsn: str) -> None:
        if not HAS_ASYNCPG:
            raise ImportError("asyncpg is required for PostgreSQL storage. Install it with: pip install asyncpg")
        self._dsn = dsn
        self._pool: Optional[Any] = None

    async def initialize(self) -> None:
        self._pool = await asyncpg.create_pool(self._dsn)
        await self._create_tables()

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()

    async def _create_tables(self) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    priority TEXT NOT NULL DEFAULT 'medium',
                    parent_id TEXT,
                    tenant_id TEXT NOT NULL DEFAULT 'default',
                    tags JSONB NOT NULL DEFAULT '[]',
                    metadata JSONB NOT NULL DEFAULT '{}',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    due_date TIMESTAMPTZ,
                    assigned_to TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_tasks_tenant_id ON tasks(tenant_id);
                CREATE INDEX IF NOT EXISTS idx_tasks_parent_id ON tasks(parent_id);
                CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);

                CREATE TABLE IF NOT EXISTS task_dependencies (
                    task_id TEXT NOT NULL,
                    depends_on_id TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    PRIMARY KEY (task_id, depends_on_id)
                );

                CREATE TABLE IF NOT EXISTS task_events (
                    id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    payload JSONB NOT NULL DEFAULT '{}',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS idx_task_events_task_id ON task_events(task_id);
                CREATE INDEX IF NOT EXISTS idx_task_events_tenant_id ON task_events(tenant_id);
            """)

    def _row_to_task(self, row: Any) -> Task:
        data = dict(row)
        if isinstance(data.get("tags"), str):
            data["tags"] = json.loads(data["tags"])
        if isinstance(data.get("metadata"), str):
            data["metadata"] = json.loads(data["metadata"])
        return Task(**data)

    async def save_task(self, task: Task) -> Task:
        async with self._pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO tasks (id, title, description, status, priority, parent_id,
                    tenant_id, tags, metadata, created_at, updated_at, due_date, assigned_to)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9::jsonb, $10, $11, $12, $13)
                ON CONFLICT (id) DO UPDATE SET
                    title = EXCLUDED.title,
                    description = EXCLUDED.description,
                    status = EXCLUDED.status,
                    priority = EXCLUDED.priority,
                    parent_id = EXCLUDED.parent_id,
                    tags = EXCLUDED.tags,
                    metadata = EXCLUDED.metadata,
                    updated_at = NOW(),
                    due_date = EXCLUDED.due_date,
                    assigned_to = EXCLUDED.assigned_to
            """,
                task.id, task.title, task.description, task.status,
                task.priority, task.parent_id, task.tenant_id,
                json.dumps(task.tags), json.dumps(task.metadata),
                task.created_at, task.updated_at, task.due_date, task.assigned_to
            )
        return task

    async def get_task(self, task_id: str, tenant_id: str) -> Optional[Task]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM tasks WHERE id = $1 AND tenant_id = $2",
                task_id, tenant_id
            )
            if row:
                return self._row_to_task(row)
        return None

    async def list_tasks(
        self,
        tenant_id: str,
        status_filter: Optional[str] = None,
        priority_filter: Optional[str] = None,
        assigned_to: Optional[str] = None,
        tags: Optional[List[str]] = None,
        parent_id: Optional[str] = "__root__",
    ) -> List[Task]:
        conditions = ["tenant_id = $1"]
        params: List[Any] = [tenant_id]
        idx = 2

        if status_filter:
            conditions.append(f"status = ${idx}")
            params.append(status_filter)
            idx += 1
        if priority_filter:
            conditions.append(f"priority = ${idx}")
            params.append(priority_filter)
            idx += 1
        if assigned_to:
            conditions.append(f"assigned_to = ${idx}")
            params.append(assigned_to)
            idx += 1
        if tags:
            conditions.append(f"tags @> ${idx}::jsonb")
            params.append(json.dumps(tags))
            idx += 1
        if parent_id == "__root__":
            pass
        elif parent_id is None:
            conditions.append("parent_id IS NULL")
        else:
            conditions.append(f"parent_id = ${idx}")
            params.append(parent_id)
            idx += 1

        query = f"SELECT * FROM tasks WHERE {' AND '.join(conditions)} ORDER BY created_at ASC"
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [self._row_to_task(r) for r in rows]

    async def delete_task(self, task_id: str, tenant_id: str) -> bool:
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM tasks WHERE id = $1 AND tenant_id = $2",
                task_id, tenant_id
            )
            return result == "DELETE 1"

    async def add_dependency(self, task_id: str, depends_on_id: str) -> TaskDependency:
        dep = TaskDependency(task_id=task_id, depends_on_id=depends_on_id)
        async with self._pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO task_dependencies (task_id, depends_on_id, created_at) VALUES ($1, $2, $3) ON CONFLICT DO NOTHING",
                task_id, depends_on_id, dep.created_at
            )
        return dep

    async def get_dependencies(self, task_id: str) -> List[str]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT depends_on_id FROM task_dependencies WHERE task_id = $1",
                task_id
            )
            return [r["depends_on_id"] for r in rows]

    async def get_dependents(self, task_id: str) -> List[str]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT task_id FROM task_dependencies WHERE depends_on_id = $1",
                task_id
            )
            return [r["task_id"] for r in rows]

    async def dependency_exists(self, task_id: str, depends_on_id: str) -> bool:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT 1 FROM task_dependencies WHERE task_id = $1 AND depends_on_id = $2",
                task_id, depends_on_id
            )
            return row is not None

    async def get_ready_tasks(self, tenant_id: str) -> List[Task]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT t.* FROM tasks t
                WHERE t.tenant_id = $1
                  AND t.status IN ('pending', 'in_progress')
                  AND NOT EXISTS (
                    SELECT 1 FROM task_dependencies td
                    JOIN tasks dep ON dep.id = td.depends_on_id
                    WHERE td.task_id = t.id
                      AND dep.status != 'completed'
                  )
                ORDER BY t.created_at ASC
            """, tenant_id)
            return [self._row_to_task(r) for r in rows]

    async def bulk_save_tasks(self, tasks: List[Task]) -> List[Task]:
        saved = []
        for task in tasks:
            saved.append(await self.save_task(task))
        return saved

    async def save_event(self, event: TaskEvent) -> TaskEvent:
        async with self._pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO task_events (id, event_type, task_id, tenant_id, payload, created_at)
                VALUES ($1, $2, $3, $4, $5::jsonb, $6)
            """,
                event.id, event.event_type, event.task_id,
                event.tenant_id, json.dumps(event.payload), event.created_at
            )
        return event


# ─────────────────────────────────────────────
# Event System
# ─────────────────────────────────────────────

class EventBus:
    """Simple event bus for webhooks and callbacks."""

    def __init__(self) -> None:
        self._listeners: Dict[str, List[Callable]] = {}

    def on(self, event_type: EventType, callback: Callable) -> None:
        key = event_type.value if isinstance(event_type, EventType) else event_type
        if key not in self._listeners:
            self._listeners[key] = []
        self._listeners[key].append(callback)

    def off(self, event_type: EventType, callback: Callable) -> None:
        key = event_type.value if isinstance(event_type, EventType) else event_type
        if key in self._listeners:
            self._listeners[key] = [cb for cb in self._listeners[key] if cb != callback]

    async def emit(self, event: TaskEvent) -> None:
        key = event.event_type.value if isinstance(event.event_type, EventType) else event.event_type
        listeners = self._listeners.get(key, [])
        for listener in listeners:
            try:
                if asyncio.iscoroutinefunction(listener):
                    await listener(event)
                else:
                    listener(event)
            except Exception:
                pass


# ─────────────────────────────────────────────
# Core TodoToolset
# ─────────────────────────────────────────────

class TodoToolset:
    """
    Task Planning and Tracking toolset for Pydantic AI agents.
    Supports hierarchical tasks, dependencies, multi-tenancy, and events.
    """

    def __init__(
        self,
        storage: Optional[Any] = None,
        event_bus: Optional[EventBus] = None,
    ) -> None:
        self._storage = storage or InMemoryStorage()
        self._event_bus = event_bus or EventBus()
        self._initialized = False

    async def initialize(self) -> None:
        if not self._initialized:
            await self._storage.initialize()
            self._initialized = True

    async def close(self) -> None:
        await self._storage.close()

    def on_event(self, event_type: EventType, callback: Callable) -> None:
        self._event_bus.on(event_type, callback)

    async def _emit(self, event_type: EventType, task: Task, extra: Optional[Dict] = None) -> None:
        payload = task.dict()
        if extra:
            payload.update(extra)
        event = TaskEvent(
            event_type=event_type,
            task_id=task.id,
            tenant_id=task.tenant_id,
            payload=payload,
        )
        await self._event_bus.emit(event)
        if hasattr(self._storage, "save_event"):
            try:
                await self._storage.save_event(event)
            except Exception:
                pass

    # ── List Tasks ──────────────────────────────

    async def list_tasks(
        self,
        tenant_id: str = "default",
        hierarchical: bool = False,
        status_filter: Optional[TaskStatus] = None,
        priority_filter: Optional[TaskPriority] = None,
        assigned_to: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> List[Any]:
        await self.initialize()
        sf = status_filter.value if isinstance(status_filter, TaskStatus) else status_filter
        pf = priority_filter.value if isinstance(priority_filter, TaskPriority) else priority_filter

        tasks = await self._storage.list_tasks(
            tenant_id=tenant_id,
            status_filter=sf,
            priority_filter=pf,
            assigned_to=assigned_to,
            tags=tags,
        )

        if not hierarchical:
            return tasks

        return await self._build_hierarchy(tasks, tenant_id)

    async def _build_hierarchy(
        self, tasks: List[Task], tenant_id: str
    ) -> List[TaskWithChildren]:
        task_map: Dict[str, TaskWithChildren] = {}
        for task in tasks:
            deps = await self._storage.get_dependencies(task.id)
            twc = TaskWithChildren(**task.dict(), dependencies=deps)
            task_map[task.id] = twc

        roots: List[TaskWithChildren] = []
        for twc in task_map.values():
            if twc.parent_id is None:
                roots.append(twc)
            elif twc.parent_id in task_map:
                task_map[twc.parent_id].children.append(twc)
            else:
                roots.append(twc)

        return roots

    # ── Bulk Write/Update Tasks ──────────────────

    async def bulk_write_tasks(
        self,
        tasks: List[Task],
    ) -> List[Task]:
        await self.initialize()
        saved = await self._storage.bulk_save_tasks(tasks)
        for task in saved:
            await self._emit(EventType.TASK_CREATED, task)
        return saved

    async def bulk_update_tasks(
        self,
        tasks: List[Task],
    ) -> List[Task]:
        await self.initialize()
        updated = []
        for task in tasks:
            task.updated_at = datetime.utcnow()
            saved = await self._storage.save_task(task)
            updated.append(saved)
            await self._emit(EventType.TASK_UPDATED, saved)
        return updated

    # ── Add Single Task ──────────────────────────

    async def add_task(
        self,
        title: str,
        description: Optional[str] = None,
        priority: TaskPriority = TaskPriority.MEDIUM,
        parent_id: Optional[str] = None,
        tenant_id: str = "default",
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        due_date: Optional[datetime] = None,
        assigned_to: Optional[str] = None,
    ) -> Task:
        await self.initialize()
        task = Task(
            title=title,
            description=description,
            priority=priority,
            parent_id=parent_id,
            tenant_id=tenant_id,
            tags=tags or [],
            metadata=metadata or {},
            due_date=due_date,
            assigned_to=assigned_to,
        )
        saved = await self._storage.save_task(task)
        await self._emit(EventType.TASK_CREATED, saved)
        return saved

    # ── Update Task Status ───────────────────────

    async def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        tenant_id: str = "default",
    ) -> Task:
        await self.initialize()
        task = await self._storage.get_task(task_id, tenant_id)
        if task is None:
            raise ValueError(f"Task {task_id} not found for tenant {tenant_id}")

        old_status = task.status
        task.status = status.value if isinstance(status, TaskStatus) else status
        task.updated_at = datetime.utcnow()
        saved = await self._storage.save_task(task)

        await self._emit(
            EventType.TASK_STATUS_CHANGED,
            saved,
            {"old_status": old_status, "new_status": task.status},
        )
        if task.status == TaskStatus.COMPLETED:
            await self._emit(EventType.TASK_COMPLETED, saved)

        return saved

    # ── Delete Task ──────────────────────────────

    async def delete_task(
        self,
        task_id: str,
        tenant_id: str = "default",
    ) -> bool:
        await self.initialize()
        task = await self._storage.get_task(task_id, tenant_id)
        if task is None:
            raise ValueError(f"Task {task_id} not found for tenant {tenant_id}")

        deleted = await self._storage.delete_task(task_id, tenant_id)
        if deleted:
            await self._emit(EventType.TASK_DELETED, task)
        return deleted

    # ── Create Child Task ────────────────────────

    async def create_child_task(
        self,
        parent_id: str,
        title: str,
        description: Optional[str] = None,
        priority: TaskPriority = TaskPriority.MEDIUM,
        tenant_id: str = "default",
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Task:
        await self.initialize()
        parent = await self._storage.get_task(parent_id, tenant_id)
        if parent is None:
            raise ValueError(f"Parent task {parent_id} not found for tenant {tenant_id}")

        child = Task(
            title=title,
            description=description,
            priority=priority,
            parent_id=parent_id,
            tenant_id=tenant_id,
            tags=tags or [],
            metadata=metadata or {},
        )
        saved = await self._storage.save_task(child)
        await self._emit(EventType.CHILD_TASK_CREATED, saved, {"parent_id": parent_id})
        return saved

    # ── Link Dependency ──────────────────────────

    async def link_dependency(
        self,
        task_id: str,
        depends_on_id: str,
        tenant_id: str = "default",
    ) -> TaskDependency:
        await self.initialize()
        task = await self._storage.get_task(task_id, tenant_id)
        if task is None:
            raise ValueError(f"Task {task_id} not found for tenant {tenant_id}")

        dep_task = await self._storage.get_task(depends_on_id, tenant_id)
        if dep_task is None:
            raise ValueError(f"Dependency task {depends_on_id} not found for tenant {tenant_id}")

        if task_id == depends_on_id:
            raise ValueError("A task cannot depend on itself")

        if await self._storage.dependency_exists(task_id, depends_on_id):
            raise ValueError(f"Dependency already exists: {task_id} -> {depends_on_id}")

        if await self._would_create_cycle(task_id, depends_on_id):
            raise ValueError(f"Adding dependency would create a cycle: {task_id} -> {depends_on_id}")

        dep = await self._storage.add_dependency(task_id, depends_on_id)
        await self._emit(
            EventType.DEPENDENCY_ADDED,
            task,
            {"depends_on_id": depends_on_id},
        )
        return dep

    async def _would_create_cycle(self, task_id: str, depends_on_id: str) -> bool:
        visited = set()
        queue = [depends_on_id]
        while queue:
            current = queue.pop(0)
            if current == task_id:
                return True
            if current in visited:
                continue
            visited.add(current)
            deps = await self._storage.get_dependencies(current)
            queue.extend(deps)
        return False

    # ── List Ready Tasks ─────────────────────────

    async def list_ready_tasks(
        self,
        tenant_id: str = "default",
    ) -> List[Task]:
        await self.initialize()
        return await self._storage.get_ready_tasks(tenant_id)

    # ── Get Single Task ──────────────────────────

    async def get_task(self, task_id: str, tenant_id: str = "default") -> Optional[Task]:
        await self.initialize()
        return await self._storage.get_task(task_id, tenant_id)

    # ── Get Task Dependencies ────────────────────

    async def get_task_dependencies(
        self, task_id: str, tenant_id: str = "default"
    ) -> List[Task]:
        await self.initialize()
        dep_ids = await self._storage.get_dependencies(task_id)
        tasks = []
        for dep_id in dep_ids:
            t = await self._storage.get_task(dep_id, tenant_id)
            if t:
                tasks.append(t)
        return tasks

    # ── Get Task Dependents ──────────────────────

    async def get_task_dependents(
        self, task_id: str, tenant_id: str = "default"
    ) -> List[Task]:
        await self.initialize()
        dep_ids = await self._storage.get_dependents(task_id)
        tasks = []
        for dep_id in dep_ids:
            t = await self._storage.get_task(dep_id, tenant_id)
            if t:
                tasks.append(t)
        return tasks


# ─────────────────────────────────────────────
# Pydantic AI Tool Wrappers
# ─────────────────────────────────────────────

class TodoTools:
    """
    Wraps TodoToolset methods as callable tools compatible with Pydantic AI agents.
    """

    def __init__(self, toolset: TodoToolset) -> None:
        self._toolset = toolset

    def get_tools(self) -> List[Callable]:
        return [
            self.list_tasks,
            self.bulk_write_tasks,
            self.bulk_update_tasks,
            self.add_task,
            self.update_task_status,
            self.delete_task,
            self.create_child_task,
            self.link_dependency,
            self.list_ready_tasks,
            self.get_task,
            self.get_task_dependencies,
            self.get_task_dependents,
        ]

    async def list_tasks(
        self,
        tenant_id: str = "default",
        hierarchical: bool = False,
        status_filter: Optional[str] = None,
        priority_filter: Optional[str] = None,
        assigned_to: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """List all tasks. Supports hierarchical view with subtasks."""
        sf = TaskStatus(status_filter) if status_filter else None
        pf = TaskPriority(priority_filter) if priority_filter else None
        tasks = await self._toolset.list_tasks(
            tenant_id=tenant_id,
            hierarchical=hierarchical,
            status_filter=sf,
            priority_filter=pf,
            assigned_to=assigned_to,
            tags=tags,
        )
        return [t.dict() for t in tasks]

    async def bulk_write_tasks(
        self,
        tasks: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Bulk create tasks."""
        task_objs = [Task(**t) for t in tasks]
        saved = await self._toolset.bulk_write_tasks(task_objs)
        return [t.dict() for t in saved]

    async def bulk_update_tasks(
        self,
        tasks: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Bulk update tasks."""
        task_objs = [Task(**t) for t in tasks]
        updated = await self._toolset.bulk_update_tasks(task_objs)
        return [t.dict() for t in updated]

    async def add_task(
        self,
        title: str,
        description: Optional[str] = None,
        priority: str = "medium",
        parent_id: Optional[str] = None,
        tenant_id: str = "default",
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        due_date: Optional[str] = None,
        assigned_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Add a single task."""
        due = datetime.fromisoformat(due_date) if due_date else None
        task = await self._toolset.add_task(
            title=title,
            description=description,
            priority=TaskPriority(priority),
            parent_id=parent_id,
            tenant_id=tenant_id,
            tags=tags,
            metadata=metadata,
            due_date=due,
            assigned_to=assigned_to,
        )
        return task.dict()

    async def update_task_status(
        self,
        task_id: str,
        status: str,
        tenant_id: str = "default",
    ) -> Dict[str, Any]:
        """Update task status by ID."""
        task = await self._toolset.update_task_status(
            task_id=task_id,
            status=TaskStatus(status),
            tenant_id=tenant_id,
        )
        return task.dict()

    async def delete_task(
        self,
        task_id: str,
        tenant_id: str = "default",
    ) -> Dict[str, Any]:
        """Delete task by ID."""
        deleted = await self._toolset.delete_task(task_id=task_id, tenant_id=tenant_id)
        return {"deleted": deleted, "task_id": task_id}

    async def create_child_task(
        self,
        parent_id: str,
        title: str,
        description: Optional[str] = None,
        priority: str = "medium",
        tenant_id: str = "default",
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a child task under a parent task."""
        task = await self._toolset.create_child_task(
            parent_id=parent_id,
            title=title,
            description=description,
            priority=TaskPriority(priority),
            tenant_id=tenant_id,
            tags=tags,
            metadata=metadata,
        )
        return task.dict()

    async def link_dependency(
        self,
        task_id: str,
        depends_on_id: str,
        tenant_id: str = "default",
    ) -> Dict[str, Any]:
        """Link tasks with a dependency (task_id depends on depends_on_id)."""
        dep = await self._toolset.link_dependency(
            task_id=task_id,
            depends_on_id=depends_on_id,
            tenant_id=tenant_id,
        )
        return dep.dict()

    async def list_ready_tasks(
        self,
        tenant_id: str = "default",
    ) -> List[Dict[str, Any]]:
        """List tasks that are ready to work on (no incomplete dependencies)."""
        tasks = await self._toolset.list_ready_tasks(tenant_id=tenant_id)
        return [t.dict() for t in tasks]

    async def get_task(
        self,
        task_id: str,
        tenant_id: str = "default",
    ) -> Optional[Dict[str, Any]]:
        """Get a single task by ID."""
        task = await self._toolset.get_task(task_id=task_id, tenant_id=tenant_id)
        return task.dict() if task else None

    async def get_task_dependencies(
        self,
        task_id: str,
        tenant_id: str = "default",
    ) -> List[Dict[str, Any]]:
        """Get all tasks that a given task depends on."""
        tasks = await self._toolset.get_task_dependencies(task_id=task_id, tenant_id=tenant_id)
        return [t.dict() for t in tasks]

    async def get_task_dependents(
        self,
        task_id: str,
        tenant_id: str = "default",
    ) -> List[Dict[str, Any]]:
        """Get all tasks that depend on a given task."""
        tasks = await self._toolset.get_task_dependents(task_id=task_id, tenant_id=tenant_id)
        return [t.dict() for t in tasks]


# ─────────────────────────────────────────────
# Factory / Builder
# ─────────────────────────────────────────────

def create_todo_toolset(
    storage_type: str = "memory",
    postgres_dsn: Optional[str] = None,
    event_bus: Optional[EventBus] = None,
) -> Tuple[TodoToolset, TodoTools]:
    """
    Factory function to create a TodoToolset and its tool wrappers.

    Args:
        storage_type: "memory" or "postgres"
        postgres_dsn: PostgreSQL DSN string (required if storage_type="postgres")
        event_bus: Optional custom EventBus instance

    Returns:
        Tuple of (TodoToolset, TodoTools)
    """
    if storage_type == "postgres":
        if not postgres_dsn:
            raise ValueError("postgres_dsn is required for PostgreSQL storage")
        storage = PostgreSQLStorage(dsn=postgres_dsn)
    else:
        storage = InMemoryStorage()

    bus = event_bus or EventBus()
    toolset = TodoToolset(storage=storage, event_bus=bus)
    tools = TodoTools(toolset=toolset)
    return toolset, tools


# ─────────────────────────────────────────────
# Convenience: register tools with a Pydantic AI agent
# ─────────────────────────────────────────────

def register_todo_tools_with_agent(agent: Any, tools: TodoTools) -> None:
    """
    Register all todo tools with a Pydantic AI agent.
    Requires pydantic_ai to be installed.
    """
    if not HAS_PYDANTIC_AI:
        raise ImportError("pydantic_ai is required. Install it with: pip install pydantic-ai")
    for tool_fn in tools.get_tools():
        agent.tool(tool_fn)


# ─────────────────────────────────────────────
# CLI / Demo
# ─────────────────────────────────────────────

async def _demo() -> None:
    toolset, tools = create_todo_toolset(storage_type="memory")

    def on_task_created(event: TaskEvent) -> None:
        print(f"[EVENT] Task created: {event.payload.get('title')} (id={event.task_id})")

    def on_task_completed(event: TaskEvent) -> None:
        print(f"[EVENT] Task completed: {event.payload.get('title')} (id={event.task_id})")

    toolset.on_event(EventType.TASK_CREATED, on_task_created)
    toolset.on_event(EventType.TASK_COMPLETED, on_task_completed)

    print("=== Adding tasks ===")
    t1 = await tools.add_task("Design database schema", priority="high", tenant_id="acme")
    t2 = await tools.add_task("Implement API endpoints", priority="high", tenant_id="acme")
    t3 = await tools.add_task("Write tests", priority="medium", tenant_id="acme")
    t4 = await tools.add_task("Deploy to production", priority="critical", tenant_id="acme")

    print("\n=== Creating child tasks ===")
    c1 = await tools.create_child_task(
        parent_id=t2["id"],
        title="Implement GET /tasks",
        tenant_id="acme",
    )
    c2 = await tools.create_child_task(
        parent_id=t2["id"],
        title="Implement POST /tasks",
        tenant_id="acme",
    )

    print("\n=== Linking dependencies ===")
    await tools.link_dependency(t2["id"], t1["id"], tenant_id="acme")
    await tools.link_dependency(t3["id"], t2["id"], tenant_id="acme")
    await tools.link_dependency(t4["id"], t3["id"], tenant_id="acme")

    print("\n=== Ready tasks (before completing t1) ===")
    ready = await tools.list_ready_tasks(tenant_id="acme")
    for t in ready:
        print(f"  - {t['title']} [{t['status']}]")

    print("\n=== Completing t1 ===")
    await tools.update_task_status(t1["id"], "completed", tenant_id="acme")

    print("\n=== Ready tasks (after completing t1) ===")
    ready = await tools.list_ready_tasks(tenant_id="acme")
    for t in ready:
        print(f"  - {t['title']} [{t['status']}]")

    print("\n=== Hierarchical task list ===")
    hierarchy = await tools.list_tasks(tenant_id="acme", hierarchical=True)
    for t in hierarchy:
        print(f"  [{t['status']}] {t['title']}")
        for child in t.get("children", []):
            print(f"    └─ [{child['status']}] {child['title']}")

    print("\n=== All tasks (flat) ===")
    all_tasks = await tools.list_tasks(tenant_id="acme")
    for t in all_tasks:
        print(f"  {t['id'][:8]}... [{t['priority']}] {t['title']} -> {t['status']}")

    print("\n=== Deleting a task ===")
    result = await tools.delete_task(c1["id"], tenant_id="acme")
    print(f"  Deleted: {result}")

    print("\n=== Bulk write tasks ===")
    bulk = await tools.bulk_write_tasks([
        {"title": "Bulk task 1", "tenant_id": "acme", "priority": "low"},
        {"title": "Bulk task 2", "tenant_id": "acme", "priority": "medium"},
    ])
    for t in bulk:
        print(f"  Created: {t['title']}")

    await toolset.close()
    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(_demo())