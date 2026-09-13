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
# Enums & Models
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
    completed_at: Optional[datetime] = None
    due_date: Optional[datetime] = None
    assignee: Optional[str] = None

    class Config:
        use_enum_values = True


class TaskDependency(BaseModel):
    task_id: str
    depends_on_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TaskEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str
    task_id: str
    tenant_id: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class BulkTaskInput(BaseModel):
    tasks: List[Task]


class TaskFilter(BaseModel):
    tenant_id: str = "default"
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    parent_id: Optional[str] = None
    assignee: Optional[str] = None
    tags: Optional[List[str]] = None


# ─────────────────────────────────────────────
# Storage Backends
# ─────────────────────────────────────────────

class InMemoryStorage:
    """In-memory storage backend for development/testing."""

    def __init__(self) -> None:
        self._tasks: Dict[str, Task] = {}
        self._dependencies: List[TaskDependency] = []

    async def initialize(self) -> None:
        pass

    async def close(self) -> None:
        pass

    async def save_task(self, task: Task) -> Task:
        task.updated_at = datetime.utcnow()
        self._tasks[task.id] = task
        return task

    async def get_task(self, task_id: str, tenant_id: str = "default") -> Optional[Task]:
        task = self._tasks.get(task_id)
        if task and task.tenant_id == tenant_id:
            return task
        return None

    async def list_tasks(self, filters: TaskFilter) -> List[Task]:
        results = []
        for task in self._tasks.values():
            if task.tenant_id != filters.tenant_id:
                continue
            if filters.status and task.status != filters.status:
                continue
            if filters.priority and task.priority != filters.priority:
                continue
            if filters.parent_id is not None and task.parent_id != filters.parent_id:
                continue
            if filters.assignee and task.assignee != filters.assignee:
                continue
            if filters.tags:
                if not all(tag in task.tags for tag in filters.tags):
                    continue
            results.append(task)
        return results

    async def delete_task(self, task_id: str, tenant_id: str = "default") -> bool:
        task = self._tasks.get(task_id)
        if task and task.tenant_id == tenant_id:
            del self._tasks[task_id]
            self._dependencies = [
                d for d in self._dependencies
                if d.task_id != task_id and d.depends_on_id != task_id
            ]
            return True
        return False

    async def add_dependency(self, dependency: TaskDependency) -> TaskDependency:
        existing = [
            d for d in self._dependencies
            if d.task_id == dependency.task_id and d.depends_on_id == dependency.depends_on_id
        ]
        if not existing:
            self._dependencies.append(dependency)
        return dependency

    async def get_dependencies(self, task_id: str) -> List[str]:
        return [d.depends_on_id for d in self._dependencies if d.task_id == task_id]

    async def get_dependents(self, task_id: str) -> List[str]:
        return [d.task_id for d in self._dependencies if d.depends_on_id == task_id]

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
        self._pool: Optional[asyncpg.Pool] = None

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
                    parent_id TEXT REFERENCES tasks(id) ON DELETE SET NULL,
                    tenant_id TEXT NOT NULL DEFAULT 'default',
                    tags JSONB NOT NULL DEFAULT '[]',
                    metadata JSONB NOT NULL DEFAULT '{}',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    completed_at TIMESTAMPTZ,
                    due_date TIMESTAMPTZ,
                    assignee TEXT
                );
                
                CREATE TABLE IF NOT EXISTS task_dependencies (
                    task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                    depends_on_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    PRIMARY KEY (task_id, depends_on_id)
                );
                
                CREATE INDEX IF NOT EXISTS idx_tasks_tenant_id ON tasks(tenant_id);
                CREATE INDEX IF NOT EXISTS idx_tasks_parent_id ON tasks(parent_id);
                CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
            """)

    def _row_to_task(self, row: asyncpg.Record) -> Task:
        data = dict(row)
        data['tags'] = json.loads(data['tags']) if isinstance(data['tags'], str) else data['tags']
        data['metadata'] = json.loads(data['metadata']) if isinstance(data['metadata'], str) else data['metadata']
        return Task(**data)

    async def save_task(self, task: Task) -> Task:
        task.updated_at = datetime.utcnow()
        async with self._pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO tasks (id, title, description, status, priority, parent_id, tenant_id,
                                   tags, metadata, created_at, updated_at, completed_at, due_date, assignee)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9::jsonb, $10, $11, $12, $13, $14)
                ON CONFLICT (id) DO UPDATE SET
                    title = EXCLUDED.title,
                    description = EXCLUDED.description,
                    status = EXCLUDED.status,
                    priority = EXCLUDED.priority,
                    parent_id = EXCLUDED.parent_id,
                    tags = EXCLUDED.tags,
                    metadata = EXCLUDED.metadata,
                    updated_at = EXCLUDED.updated_at,
                    completed_at = EXCLUDED.completed_at,
                    due_date = EXCLUDED.due_date,
                    assignee = EXCLUDED.assignee
            """,
                task.id, task.title, task.description, task.status, task.priority,
                task.parent_id, task.tenant_id, json.dumps(task.tags),
                json.dumps(task.metadata), task.created_at, task.updated_at,
                task.completed_at, task.due_date, task.assignee
            )
        return task

    async def get_task(self, task_id: str, tenant_id: str = "default") -> Optional[Task]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM tasks WHERE id = $1 AND tenant_id = $2",
                task_id, tenant_id
            )
            return self._row_to_task(row) if row else None

    async def list_tasks(self, filters: TaskFilter) -> List[Task]:
        conditions = ["tenant_id = $1"]
        params: List[Any] = [filters.tenant_id]
        idx = 2

        if filters.status:
            conditions.append(f"status = ${idx}")
            params.append(filters.status)
            idx += 1
        if filters.priority:
            conditions.append(f"priority = ${idx}")
            params.append(filters.priority)
            idx += 1
        if filters.parent_id is not None:
            conditions.append(f"parent_id = ${idx}")
            params.append(filters.parent_id)
            idx += 1
        if filters.assignee:
            conditions.append(f"assignee = ${idx}")
            params.append(filters.assignee)
            idx += 1

        where_clause = " AND ".join(conditions)
        query = f"SELECT * FROM tasks WHERE {where_clause} ORDER BY created_at DESC"

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            tasks = [self._row_to_task(row) for row in rows]

        if filters.tags:
            tasks = [t for t in tasks if all(tag in t.tags for tag in filters.tags)]

        return tasks

    async def delete_task(self, task_id: str, tenant_id: str = "default") -> bool:
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM tasks WHERE id = $1 AND tenant_id = $2",
                task_id, tenant_id
            )
            return result == "DELETE 1"

    async def add_dependency(self, dependency: TaskDependency) -> TaskDependency:
        async with self._pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO task_dependencies (task_id, depends_on_id, created_at)
                VALUES ($1, $2, $3)
                ON CONFLICT DO NOTHING
            """, dependency.task_id, dependency.depends_on_id, dependency.created_at)
        return dependency

    async def get_dependencies(self, task_id: str) -> List[str]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT depends_on_id FROM task_dependencies WHERE task_id = $1",
                task_id
            )
            return [row['depends_on_id'] for row in rows]

    async def get_dependents(self, task_id: str) -> List[str]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT task_id FROM task_dependencies WHERE depends_on_id = $1",
                task_id
            )
            return [row['task_id'] for row in rows]

    async def bulk_save_tasks(self, tasks: List[Task]) -> List[Task]:
        saved = []
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                for task in tasks:
                    task.updated_at = datetime.utcnow()
                    await conn.execute("""
                        INSERT INTO tasks (id, title, description, status, priority, parent_id, tenant_id,
                                           tags, metadata, created_at, updated_at, completed_at, due_date, assignee)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9::jsonb, $10, $11, $12, $13, $14)
                        ON CONFLICT (id) DO UPDATE SET
                            title = EXCLUDED.title,
                            description = EXCLUDED.description,
                            status = EXCLUDED.status,
                            priority = EXCLUDED.priority,
                            parent_id = EXCLUDED.parent_id,
                            tags = EXCLUDED.tags,
                            metadata = EXCLUDED.metadata,
                            updated_at = EXCLUDED.updated_at,
                            completed_at = EXCLUDED.completed_at,
                            due_date = EXCLUDED.due_date,
                            assignee = EXCLUDED.assignee
                    """,
                        task.id, task.title, task.description, task.status, task.priority,
                        task.parent_id, task.tenant_id, json.dumps(task.tags),
                        json.dumps(task.metadata), task.created_at, task.updated_at,
                        task.completed_at, task.due_date, task.assignee
                    )
                    saved.append(task)
        return saved


# ─────────────────────────────────────────────
# Event System
# ─────────────────────────────────────────────

class EventBus:
    """Simple event bus for webhooks and callbacks."""

    def __init__(self) -> None:
        self._handlers: Dict[str, List[Callable]] = {}
        self._history: List[TaskEvent] = []

    def subscribe(self, event_type: str, handler: Callable) -> None:
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: Callable) -> None:
        if event_type in self._handlers:
            self._handlers[event_type] = [
                h for h in self._handlers[event_type] if h != handler
            ]

    async def emit(self, event: TaskEvent) -> None:
        self._history.append(event)
        handlers = self._handlers.get(event.event_type, []) + self._handlers.get("*", [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                print(f"Event handler error for {event.event_type}: {e}")

    def get_history(self, event_type: Optional[str] = None, limit: int = 100) -> List[TaskEvent]:
        history = self._history
        if event_type:
            history = [e for e in history if e.event_type == event_type]
        return history[-limit:]


# ─────────────────────────────────────────────
# Core Todo Toolset
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
        default_tenant_id: str = "default",
    ) -> None:
        self._storage = storage or InMemoryStorage()
        self._event_bus = event_bus or EventBus()
        self._default_tenant_id = default_tenant_id

    async def initialize(self) -> None:
        await self._storage.initialize()

    async def close(self) -> None:
        await self._storage.close()

    async def __aenter__(self) -> "TodoToolset":
        await self.initialize()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    # ── Event helpers ──────────────────────────────────────────────────────

    async def _emit(self, event_type: str, task: Task, extra: Optional[Dict] = None) -> None:
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

    def on_event(self, event_type: str, handler: Callable) -> None:
        self._event_bus.subscribe(event_type, handler)

    def off_event(self, event_type: str, handler: Callable) -> None:
        self._event_bus.unsubscribe(event_type, handler)

    # ── Core CRUD ──────────────────────────────────────────────────────────

    async def add_task(
        self,
        title: str,
        description: Optional[str] = None,
        priority: TaskPriority = TaskPriority.MEDIUM,
        tenant_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        due_date: Optional[datetime] = None,
        assignee: Optional[str] = None,
    ) -> Task:
        """Add a single new task."""
        task = Task(
            title=title,
            description=description,
            priority=priority,
            tenant_id=tenant_id or self._default_tenant_id,
            tags=tags or [],
            metadata=metadata or {},
            due_date=due_date,
            assignee=assignee,
        )
        saved = await self._storage.save_task(task)
        await self._emit("task.created", saved)
        return saved

    async def get_task(self, task_id: str, tenant_id: Optional[str] = None) -> Optional[Task]:
        """Get a task by ID."""
        return await self._storage.get_task(
            task_id, tenant_id or self._default_tenant_id
        )

    async def list_tasks(
        self,
        tenant_id: Optional[str] = None,
        status: Optional[TaskStatus] = None,
        priority: Optional[TaskPriority] = None,
        parent_id: Optional[str] = None,
        assignee: Optional[str] = None,
        tags: Optional[List[str]] = None,
        hierarchical: bool = False,
    ) -> List[Task]:
        """
        List all tasks with optional filters.
        If hierarchical=True, returns only root tasks (parent_id=None);
        subtasks are accessible via get_subtasks().
        """
        filters = TaskFilter(
            tenant_id=tenant_id or self._default_tenant_id,
            status=status,
            priority=priority,
            parent_id=parent_id,
            assignee=assignee,
            tags=tags,
        )
        tasks = await self._storage.list_tasks(filters)
        if hierarchical:
            tasks = [t for t in tasks if t.parent_id is None]
        return tasks

    async def list_tasks_hierarchical(
        self,
        tenant_id: Optional[str] = None,
        status: Optional[TaskStatus] = None,
    ) -> List[Dict[str, Any]]:
        """
        List tasks in a hierarchical view with nested subtasks.
        Returns a list of root task dicts, each with a 'subtasks' key.
        """
        tid = tenant_id or self._default_tenant_id
        filters = TaskFilter(tenant_id=tid, status=status)
        all_tasks = await self._storage.list_tasks(filters)

        task_map: Dict[str, Dict[str, Any]] = {}
        for task in all_tasks:
            d = task.dict()
            d['subtasks'] = []
            task_map[task.id] = d

        roots: List[Dict[str, Any]] = []
        for task in all_tasks:
            if task.parent_id and task.parent_id in task_map:
                task_map[task.parent_id]['subtasks'].append(task_map[task.id])
            elif task.parent_id is None:
                roots.append(task_map[task.id])

        return roots

    async def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        tenant_id: Optional[str] = None,
    ) -> Optional[Task]:
        """Update the status of a task by ID."""
        tid = tenant_id or self._default_tenant_id
        task = await self._storage.get_task(task_id, tid)
        if not task:
            return None

        old_status = task.status
        task.status = status
        task.updated_at = datetime.utcnow()

        if status == TaskStatus.COMPLETED:
            task.completed_at = datetime.utcnow()
        elif old_status == TaskStatus.COMPLETED and status != TaskStatus.COMPLETED:
            task.completed_at = None

        saved = await self._storage.save_task(task)
        await self._emit("task.status_changed", saved, {"old_status": old_status})
        return saved

    async def update_task(
        self,
        task_id: str,
        tenant_id: Optional[str] = None,
        **kwargs: Any,
    ) -> Optional[Task]:
        """Update arbitrary fields of a task."""
        tid = tenant_id or self._default_tenant_id
        task = await self._storage.get_task(task_id, tid)
        if not task:
            return None

        allowed_fields = {
            'title', 'description', 'status', 'priority', 'tags',
            'metadata', 'due_date', 'assignee', 'completed_at'
        }
        for key, value in kwargs.items():
            if key in allowed_fields:
                setattr(task, key, value)

        task.updated_at = datetime.utcnow()
        saved = await self._storage.save_task(task)
        await self._emit("task.updated", saved)
        return saved

    async def delete_task(
        self,
        task_id: str,
        tenant_id: Optional[str] = None,
    ) -> bool:
        """Delete a task by ID."""
        tid = tenant_id or self._default_tenant_id
        task = await self._storage.get_task(task_id, tid)
        if not task:
            return False

        deleted = await self._storage.delete_task(task_id, tid)
        if deleted:
            await self._emit("task.deleted", task)
        return deleted

    async def bulk_write_tasks(
        self,
        tasks: List[Task],
    ) -> List[Task]:
        """Bulk write/update tasks."""
        saved = await self._storage.bulk_save_tasks(tasks)
        for task in saved:
            await self._emit("task.bulk_written", task)
        return saved

    async def bulk_update_tasks(
        self,
        updates: List[Dict[str, Any]],
        tenant_id: Optional[str] = None,
    ) -> List[Task]:
        """
        Bulk update tasks. Each dict must have 'id' plus fields to update.
        """
        tid = tenant_id or self._default_tenant_id
        updated_tasks = []
        for update in updates:
            task_id = update.pop('id', None)
            if not task_id:
                continue
            task = await self.update_task(task_id, tenant_id=tid, **update)
            if task:
                updated_tasks.append(task)
        return updated_tasks

    # ── Subtasks ───────────────────────────────────────────────────────────

    async def create_child_task(
        self,
        parent_id: str,
        title: str,
        description: Optional[str] = None,
        priority: Optional[TaskPriority] = None,
        tenant_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        due_date: Optional[datetime] = None,
        assignee: Optional[str] = None,
    ) -> Optional[Task]:
        """Create a child (sub) task under a parent task."""
        tid = tenant_id or self._default_tenant_id
        parent = await self._storage.get_task(parent_id, tid)
        if not parent:
            return None

        child = Task(
            title=title,
            description=description,
            priority=priority or parent.priority,
            parent_id=parent_id,
            tenant_id=tid,
            tags=tags or [],
            metadata=metadata or {},
            due_date=due_date,
            assignee=assignee,
        )
        saved = await self._storage.save_task(child)
        await self._emit("task.child_created", saved, {"parent_id": parent_id})
        return saved

    async def get_subtasks(
        self,
        parent_id: str,
        tenant_id: Optional[str] = None,
        recursive: bool = False,
    ) -> List[Task]:
        """Get all direct subtasks of a parent task."""
        tid = tenant_id or self._default_tenant_id
        filters = TaskFilter(tenant_id=tid, parent_id=parent_id)
        subtasks = await self._storage.list_tasks(filters)

        if recursive:
            all_subtasks = list(subtasks)
            for subtask in subtasks:
                children = await self.get_subtasks(subtask.id, tid, recursive=True)
                all_subtasks.extend(children)
            return all_subtasks

        return subtasks

    # ── Dependencies ───────────────────────────────────────────────────────

    async def link_dependency(
        self,
        task_id: str,
        depends_on_id: str,
        tenant_id: Optional[str] = None,
    ) -> Optional[TaskDependency]:
        """
        Link tasks with a dependency: task_id depends on depends_on_id.
        The task_id task cannot start until depends_on_id is completed.
        """
        tid = tenant_id or self._default_tenant_id

        task = await self._storage.get_task(task_id, tid)
        depends_on = await self._storage.get_task(depends_on_id, tid)

        if not task or not depends_on:
            return None

        if task_id == depends_on_id:
            raise ValueError("A task cannot depend on itself.")

        # Check for circular dependency
        if await self._would_create_cycle(task_id, depends_on_id):
            raise ValueError(
                f"Adding dependency from {task_id} to {depends_on_id} would create a cycle."
            )

        dependency = TaskDependency(task_id=task_id, depends_on_id=depends_on_id)
        saved = await self._storage.add_dependency(dependency)

        # Update task status to blocked if dependency is not completed
        if depends_on.status != TaskStatus.COMPLETED:
            await self.update_task_status(task_id, TaskStatus.BLOCKED, tid)

        event = TaskEvent(
            event_type="task.dependency_linked",
            task_id=task_id,
            tenant_id=tid,
            payload={"task_id": task_id, "depends_on_id": depends_on_id},
        )
        await self._event_bus.emit(event)
        return saved

    async def _would_create_cycle(self, task_id: str, depends_on_id: str) -> bool:
        """Check if adding task_id -> depends_on_id would create a cycle."""
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

    async def get_dependencies(self, task_id: str) -> List[Task]:
        """Get all tasks that the given task depends on."""
        dep_ids = await self._storage.get_dependencies(task_id)
        tasks = []
        for dep_id in dep_ids:
            task = await self._storage.get_task(dep_id)
            if task:
                tasks.append(task)
        return tasks

    async def get_dependents(self, task_id: str) -> List[Task]:
        """Get all tasks that depend on the given task."""
        dep_ids = await self._storage.get_dependents(task_id)
        tasks = []
        for dep_id in dep_ids:
            task = await self._storage.get_task(dep_id)
            if task:
                tasks.append(task)
        return tasks

    async def unblock_dependents(self, completed_task_id: str, tenant_id: Optional[str] = None) -> List[Task]:
        """
        After a task is completed, check if any dependent tasks can now be unblocked.
        A task is unblocked when ALL its dependencies are completed.
        """
        tid = tenant_id or self._default_tenant_id
        dependent_ids = await self._storage.get_dependents(completed_task_id)
        unblocked = []

        for dep_id in dependent_ids:
            task = await self._storage.get_task(dep_id, tid)
            if not task or task.status != TaskStatus.BLOCKED:
                continue

            dep_task_ids = await self._storage.get_dependencies(dep_id)
            all_completed = True
            for dt_id in dep_task_ids:
                dt = await self._storage.get_task(dt_id)
                if not dt or dt.status != TaskStatus.COMPLETED:
                    all_completed = False
                    break

            if all_completed:
                updated = await self.update_task_status(dep_id, TaskStatus.PENDING, tid)
                if updated:
                    unblocked.append(updated)

        return unblocked

    # ── Ready Tasks ────────────────────────────────────────────────────────

    async def list_ready_tasks(
        self,
        tenant_id: Optional[str] = None,
    ) -> List[Task]:
        """
        List tasks that are ready to work on.
        A task is ready if:
        - Its status is PENDING or IN_PROGRESS
        - It has no incomplete dependencies
        - It has no parent, or its parent is IN_PROGRESS or COMPLETED
        """
        tid = tenant_id or self._default_tenant_id
        filters = TaskFilter(tenant_id=tid)
        all_tasks = await self._storage.list_tasks(filters)

        ready = []
        for task in all_tasks:
            if task.status not in (TaskStatus.PENDING, TaskStatus.IN_PROGRESS):
                continue

            # Check dependencies
            dep_ids = await self._storage.get_dependencies(task.id)
            has_incomplete_dep = False
            for dep_id in dep_ids:
                dep_task = await self._storage.get_task(dep_id)
                if dep_task and dep_task.status != TaskStatus.COMPLETED:
                    has_incomplete_dep = True
                    break

            if has_incomplete_dep:
                continue

            # Check parent
            if task.parent_id:
                parent = await self._storage.get_task(task.parent_id, tid)
                if parent and parent.status in (TaskStatus.PENDING, TaskStatus.BLOCKED, TaskStatus.CANCELLED):
                    continue

            ready.append(task)

        return ready

    # ── Statistics ─────────────────────────────────────────────────────────

    async def get_stats(self, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """Get task statistics for a tenant."""
        tid = tenant_id or self._default_tenant_id
        filters = TaskFilter(tenant_id=tid)
        all_tasks = await self._storage.list_tasks(filters)

        stats: Dict[str, Any] = {
            "total": len(all_tasks),
            "by_status": {},
            "by_priority": {},
            "root_tasks": 0,
            "subtasks": 0,
        }

        for status in TaskStatus:
            stats["by_status"][status.value] = 0
        for priority in TaskPriority:
            stats["by_priority"][priority.value] = 0

        for task in all_tasks:
            stats["by_status"][task.status] = stats["by_status"].get(task.status, 0) + 1
            stats["by_priority"][task.priority] = stats["by_priority"].get(task.priority, 0) + 1
            if task.parent_id is None:
                stats["root_tasks"] += 1
            else:
                stats["subtasks"] += 1

        return stats

    # ── Event History ──────────────────────────────────────────────────────

    def get_event_history(
        self,
        event_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[TaskEvent]:
        """Get event history."""
        return self._event_bus.get_history(event_type, limit)


# ─────────────────────────────────────────────
# Pydantic AI Tool Wrappers
# ─────────────────────────────────────────────

class TodoTools:
    """
    Pydantic AI compatible tool wrappers for the TodoToolset.
    Each method is designed to be registered as an agent tool.
    """

    def __init__(self, toolset: TodoToolset) -> None:
        self._toolset = toolset

    async def list_all_tasks(
        self,
        tenant_id: str = "default",
        status: Optional[str] = None,
        priority: Optional[str] = None,
        hierarchical: bool = False,
    ) -> Dict[str, Any]:
        """List all tasks, optionally in hierarchical view."""
        status_enum = TaskStatus(status) if status else None
        priority_enum = TaskPriority(priority) if priority else None

        if hierarchical:
            tasks = await self._toolset.list_tasks_hierarchical(
                tenant_id=tenant_id,
                status=status_enum,
            )
            return {"tasks": tasks, "count": len(tasks), "hierarchical": True}
        else:
            tasks = await self._toolset.list_tasks(
                tenant_id=tenant_id,
                status=status_enum,
                priority=priority_enum,
            )
            return {
                "tasks": [t.dict() for t in tasks],
                "count": len(tasks),
                "hierarchical": False,
            }

    async def add_task(
        self,
        title: str,
        description: Optional[str] = None,
        priority: str = "medium",
        tenant_id: str = "default",
        tags: Optional[List[str]] = None,
        assignee: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Add a single new task."""
        task = await self._toolset.add_task(
            title=title,
            description=description,
            priority=TaskPriority(priority),
            tenant_id=tenant_id,
            tags=tags,
            assignee=assignee,
        )
        return {"success": True, "task": task.dict()}

    async def update_task_status(
        self,
        task_id: str,
        status: str,
        tenant_id: str = "default",
    ) -> Dict[str, Any]:
        """Update the status of a task by ID."""
        task = await self._toolset.update_task_status(
            task_id=task_id,
            status=TaskStatus(status),
            tenant_id=tenant_id,
        )
        if not task:
            return {"success": False, "error": f"Task {task_id} not found."}

        unblocked = []
        if task.status == TaskStatus.COMPLETED:
            unblocked_tasks = await self._toolset.unblock_dependents(task_id, tenant_id)
            unblocked = [t.dict() for t in unblocked_tasks]

        return {"success": True, "task": task.dict(), "unblocked_tasks": unblocked}

    async def delete_task(
        self,
        task_id: str,
        tenant_id: str = "default",
    ) -> Dict[str, Any]:
        """Delete a task by ID."""
        deleted = await self._toolset.delete_task(task_id, tenant_id)
        return {"success": deleted, "task_id": task_id}

    async def create_child_task(
        self,
        parent_id: str,
        title: str,
        description: Optional[str] = None,
        priority: Optional[str] = None,
        tenant_id: str = "default",
        assignee: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a child (sub) task under a parent task."""
        priority_enum = TaskPriority(priority) if priority else None
        task = await self._toolset.create_child_task(
            parent_id=parent_id,
            title=title,
            description=description,
            priority=priority_enum,
            tenant_id=tenant_id,
            assignee=assignee,
        )
        if not task:
            return {"success": False, "error": f"Parent task {parent_id} not found."}
        return {"success": True, "task": task.dict()}

    async def link_dependency(
        self,
        task_id: str,
        depends_on_id: str,
        tenant_id: str = "default",
    ) -> Dict[str, Any]:
        """Link tasks with a dependency relationship."""
        try:
            dep = await self._toolset.link_dependency(task_id, depends_on_id, tenant_id)
            if not dep:
                return {"success": False, "error": "One or both tasks not found."}
            return {"success": True, "dependency": dep.dict()}
        except ValueError as e:
            return {"success": False, "error": str(e)}

    async def list_ready_tasks(
        self,
        tenant_id: str = "default",
    ) -> Dict[str, Any]:
        """List tasks that are ready to work on (no incomplete dependencies)."""
        tasks = await self._toolset.list_ready_tasks(tenant_id=tenant_id)
        return {"tasks": [t.dict() for t in tasks], "count": len(tasks)}

    async def bulk_write_tasks(
        self,
        tasks_data: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Bulk write/update tasks."""
        tasks = [Task(**data) for data in tasks_data]
        saved = await self._toolset.bulk_write_tasks(tasks)
        return {"success": True, "tasks": [t.dict() for t in saved], "count": len(saved)}

    async def get_task_stats(
        self,
        tenant_id: str = "default",
    ) -> Dict[str, Any]:
        """Get task statistics."""
        return await self._toolset.get_stats(tenant_id)


# ─────────────────────────────────────────────
# Factory / Builder
# ─────────────────────────────────────────────

class TodoToolsetBuilder:
    """Builder for creating a TodoToolset with various configurations."""

    def __init__(self) -> None:
        self._storage = None
        self._event_bus = None
        self._default_tenant_id = "default"
        self._event_handlers: List[Tuple[str, Callable]] = []

    def with_in_memory_storage(self) -> "TodoToolsetBuilder":
        self._storage = InMemoryStorage()
        return self

    def with_postgresql_storage(self, dsn: str) -> "TodoToolsetBuilder":
        self._storage = PostgreSQLStorage(dsn)
        return self

    def with_custom_storage(self, storage: Any) -> "TodoToolsetBuilder":
        self._storage = storage
        return self

    def with_event_bus(self, event_bus: EventBus) -> "TodoToolsetBuilder":
        self._event_bus = event_bus
        return self

    def with_default_tenant(self, tenant_id: str) -> "TodoToolsetBuilder":
        self._default_tenant_id = tenant_id
        return self

    def on_event(self, event_type: str, handler: Callable) -> "TodoToolsetBuilder":
        self._event_handlers.append((event_type, handler))
        return self

    def build(self) -> TodoToolset:
        storage = self._storage or InMemoryStorage()
        event_bus = self._event_bus or EventBus()
        toolset = TodoToolset(
            storage=storage,
            event_bus=event_bus,
            default_tenant_id=self._default_tenant_id,
        )
        for event_type, handler in self._event_handlers:
            toolset.on_event(event_type, handler)
        return toolset


# ─────────────────────────────────────────────
# Convenience factory functions
# ─────────────────────────────────────────────

def create_todo_toolset(
    storage_type: str = "memory",
    dsn: Optional[str] = None,
    default_tenant_id: str = "default",
) -> TodoToolset:
    """
    Convenience factory to create a TodoToolset.

    Args:
        storage_type: "memory" or "postgresql"
        dsn: PostgreSQL DSN (required if storage_type="postgresql")
        default_tenant_id: Default tenant ID for operations
    """
    builder = TodoToolsetBuilder().with_default_tenant(default_tenant_id)

    if storage_type == "postgresql":
        if not dsn:
            raise ValueError("dsn is required for PostgreSQL storage")
        builder.with_postgresql_storage(dsn)
    else:
        builder.with_in_memory_storage()

    return builder.build()


def create_todo_tools(toolset: TodoToolset) -> TodoTools:
    """Create a TodoTools instance from a TodoToolset."""
    return TodoTools(toolset)


# ─────────────────────────────────────────────
# Main / Demo
# ─────────────────────────────────────────────

async def _demo() -> None:
    """Demonstrate the TodoToolset capabilities."""
    print("=== Todo Toolset Demo ===\n")

    toolset = create_todo_toolset()
    tools = create_todo_tools(toolset)

    # Register event handler
    async def on_task_event(event: TaskEvent) -> None:
        print(f"  [EVENT] {event.event_type}: task_id={event.task_id}")

    toolset.on_event("*", on_task_event)

    async with toolset:
        print("1. Adding tasks...")
        result = await tools.add_task(
            "Build API",
            description="Build the REST API",
            priority="high",
        )
        api_task_id = result["task"]["id"]
        print(f"   Created: {result['task']['title']} ({api_task_id})")

        result = await tools.add_task(
            "Write tests",
            description="Write unit and integration tests",
            priority="medium",
        )
        test_task_id = result["task"]["id"]
        print(f"   Created: {result['task']['title']} ({test_task_id})")

        result = await tools.add_task(
            "Deploy to production",
            description="Deploy the application",
            priority="critical",
        )
        deploy_task_id = result["task"]["id"]
        print(f"   Created: {result['task']['title']} ({deploy_task_id})")

        print("\n2. Creating subtasks...")
        result = await tools.create_child_task(
            parent_id=api_task_id,
            title="Design endpoints",
            description="Design the API endpoints",
        )
        print(f"   Subtask: {result['task']['title']}")

        result = await tools.create_child_task(
            parent_id=api_task_id,
            title="Implement endpoints",
            description="Implement the API endpoints",
        )
        print(f"   Subtask: {result['task']['title']}")

        print("\n3. Linking dependencies...")
        result = await tools.link_dependency(test_task_id, api_task_id)
        print(f"   'Write tests' depends on 'Build API': {result['success']}")

        result = await tools.link_dependency(deploy_task_id, test_task_id)
        print(f"   'Deploy' depends on 'Write tests': {result['success']}")

        print("\n4. Listing ready tasks...")
        result = await tools.list_ready_tasks()
        print(f"   Ready tasks: {[t['title'] for t in result['tasks']]}")

        print("\n5. Completing 'Build API'...")
        result = await tools.update_task_status(api_task_id, "completed")
        print(f"   Status: {result['task']['status']}")
        print(f"   Unblocked: {[t['title'] for t in result['unblocked_tasks']]}")

        print("\n6. Listing ready tasks after completion...")
        result = await tools.list_ready_tasks()
        print(f"   Ready tasks: {[t['title'] for t in result['tasks']]}")

        print("\n7. Hierarchical task view...")
        result = await tools.list_all_tasks(hierarchical=True)
        for task in result["tasks"]:
            print(f"   - {task['title']} [{task['status']}]")
            for sub in task.get("subtasks", []):
                print(f"     - {sub['title']} [{sub['status']}]")

        print("\n8. Task statistics...")
        stats = await tools.get_task_stats()
        print(f"   Total: {stats['total']}")
        print(f"   By status: {stats['by_status']}")

        print("\n9. Bulk write tasks...")
        bulk_result = await tools.bulk_write_tasks([
            {"title": "Task A", "priority": "low", "tenant_id": "default"},
            {"title": "Task B", "priority": "high", "tenant_id": "default"},
        ])
        print(f"   Bulk written: {bulk_result['count']} tasks")

        print("\n10. Deleting a task...")
        result = await tools.delete_task(deploy_task_id)
        print(f"    Deleted: {result['success']}")

    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    asyncio.run(_demo())