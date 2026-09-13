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
    from pydantic import BaseModel, Field
    from pydantic_ai import Agent, RunContext
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


class CreateTaskInput(BaseModel):
    title: str
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    parent_id: Optional[str] = None
    tenant_id: str = "default"
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    due_date: Optional[datetime] = None
    assignee: Optional[str] = None


class UpdateTaskInput(BaseModel):
    id: str
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    due_date: Optional[datetime] = None
    assignee: Optional[str] = None


class BulkWriteInput(BaseModel):
    tasks: List[CreateTaskInput]
    tenant_id: str = "default"


class HierarchicalTask(BaseModel):
    task: Task
    children: List["HierarchicalTask"] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)

    class Config:
        arbitrary_types_allowed = True


HierarchicalTask.model_rebuild()


# ─────────────────────────────────────────────
# Storage Backends
# ─────────────────────────────────────────────

class InMemoryStorage:
    """In-memory storage backend for development/testing."""

    def __init__(self):
        self._tasks: Dict[str, Task] = {}
        self._dependencies: List[TaskDependency] = []

    async def initialize(self):
        pass

    async def close(self):
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

    async def list_tasks(self, tenant_id: str = "default", parent_id: Optional[str] = None,
                         status: Optional[TaskStatus] = None) -> List[Task]:
        results = []
        for task in self._tasks.values():
            if task.tenant_id != tenant_id:
                continue
            if parent_id is not None and task.parent_id != parent_id:
                continue
            if status is not None and task.status != status.value:
                continue
            results.append(task)
        return sorted(results, key=lambda t: t.created_at)

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

    async def add_dependency(self, task_id: str, depends_on_id: str) -> TaskDependency:
        for dep in self._dependencies:
            if dep.task_id == task_id and dep.depends_on_id == depends_on_id:
                return dep
        dep = TaskDependency(task_id=task_id, depends_on_id=depends_on_id)
        self._dependencies.append(dep)
        return dep

    async def get_dependencies(self, task_id: str) -> List[str]:
        return [d.depends_on_id for d in self._dependencies if d.task_id == task_id]

    async def get_dependents(self, task_id: str) -> List[str]:
        return [d.task_id for d in self._dependencies if d.depends_on_id == task_id]

    async def get_ready_tasks(self, tenant_id: str = "default") -> List[Task]:
        all_tasks = await self.list_tasks(tenant_id=tenant_id)
        pending_tasks = [t for t in all_tasks if t.status in (TaskStatus.PENDING, TaskStatus.PENDING.value)]

        ready = []
        for task in pending_tasks:
            deps = await self.get_dependencies(task.id)
            if not deps:
                ready.append(task)
                continue
            all_completed = True
            for dep_id in deps:
                dep_task = await self.get_task(dep_id, tenant_id)
                if dep_task is None or dep_task.status not in (TaskStatus.COMPLETED, TaskStatus.COMPLETED.value):
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

    CREATE_TASKS_TABLE = """
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
        due_date TIMESTAMPTZ,
        assignee TEXT
    );
    """

    CREATE_DEPENDENCIES_TABLE = """
    CREATE TABLE IF NOT EXISTS task_dependencies (
        task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
        depends_on_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        PRIMARY KEY (task_id, depends_on_id)
    );
    """

    CREATE_EVENTS_TABLE = """
    CREATE TABLE IF NOT EXISTS task_events (
        id TEXT PRIMARY KEY,
        event_type TEXT NOT NULL,
        task_id TEXT NOT NULL,
        tenant_id TEXT NOT NULL,
        payload JSONB NOT NULL DEFAULT '{}',
        timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """

    def __init__(self, dsn: str):
        if not HAS_ASYNCPG:
            raise ImportError("asyncpg is required for PostgreSQL storage. Install it with: pip install asyncpg")
        self.dsn = dsn
        self._pool: Optional[asyncpg.Pool] = None

    async def initialize(self):
        self._pool = await asyncpg.create_pool(self.dsn)
        async with self._pool.acquire() as conn:
            await conn.execute(self.CREATE_TASKS_TABLE)
            await conn.execute(self.CREATE_DEPENDENCIES_TABLE)
            await conn.execute(self.CREATE_EVENTS_TABLE)

    async def close(self):
        if self._pool:
            await self._pool.close()

    def _row_to_task(self, row) -> Task:
        return Task(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            status=row["status"],
            priority=row["priority"],
            parent_id=row["parent_id"],
            tenant_id=row["tenant_id"],
            tags=json.loads(row["tags"]) if isinstance(row["tags"], str) else row["tags"],
            metadata=json.loads(row["metadata"]) if isinstance(row["metadata"], str) else row["metadata"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            due_date=row["due_date"],
            assignee=row["assignee"],
        )

    async def save_task(self, task: Task) -> Task:
        task.updated_at = datetime.utcnow()
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO tasks (id, title, description, status, priority, parent_id, tenant_id,
                                   tags, metadata, created_at, updated_at, due_date, assignee)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9::jsonb, $10, $11, $12, $13)
                ON CONFLICT (id) DO UPDATE SET
                    title = EXCLUDED.title,
                    description = EXCLUDED.description,
                    status = EXCLUDED.status,
                    priority = EXCLUDED.priority,
                    parent_id = EXCLUDED.parent_id,
                    tags = EXCLUDED.tags,
                    metadata = EXCLUDED.metadata,
                    updated_at = EXCLUDED.updated_at,
                    due_date = EXCLUDED.due_date,
                    assignee = EXCLUDED.assignee
                """,
                task.id, task.title, task.description, task.status, task.priority,
                task.parent_id, task.tenant_id,
                json.dumps(task.tags), json.dumps(task.metadata),
                task.created_at, task.updated_at, task.due_date, task.assignee
            )
        return task

    async def get_task(self, task_id: str, tenant_id: str = "default") -> Optional[Task]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM tasks WHERE id = $1 AND tenant_id = $2",
                task_id, tenant_id
            )
        if row:
            return self._row_to_task(row)
        return None

    async def list_tasks(self, tenant_id: str = "default", parent_id: Optional[str] = None,
                         status: Optional[TaskStatus] = None) -> List[Task]:
        query = "SELECT * FROM tasks WHERE tenant_id = $1"
        params: List[Any] = [tenant_id]

        if parent_id is not None:
            params.append(parent_id)
            query += f" AND parent_id = ${len(params)}"
        if status is not None:
            params.append(status.value if isinstance(status, TaskStatus) else status)
            query += f" AND status = ${len(params)}"

        query += " ORDER BY created_at ASC"

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
        return [self._row_to_task(r) for r in rows]

    async def delete_task(self, task_id: str, tenant_id: str = "default") -> bool:
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM tasks WHERE id = $1 AND tenant_id = $2",
                task_id, tenant_id
            )
        return result.split()[-1] != "0"

    async def add_dependency(self, task_id: str, depends_on_id: str) -> TaskDependency:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO task_dependencies (task_id, depends_on_id)
                VALUES ($1, $2)
                ON CONFLICT DO NOTHING
                """,
                task_id, depends_on_id
            )
        return TaskDependency(task_id=task_id, depends_on_id=depends_on_id)

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

    async def get_ready_tasks(self, tenant_id: str = "default") -> List[Task]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT t.* FROM tasks t
                WHERE t.tenant_id = $1
                  AND t.status = 'pending'
                  AND NOT EXISTS (
                      SELECT 1 FROM task_dependencies td
                      JOIN tasks dep ON dep.id = td.depends_on_id
                      WHERE td.task_id = t.id
                        AND dep.status != 'completed'
                  )
                ORDER BY t.created_at ASC
                """,
                tenant_id
            )
        return [self._row_to_task(r) for r in rows]

    async def bulk_save_tasks(self, tasks: List[Task]) -> List[Task]:
        saved = []
        for task in tasks:
            saved.append(await self.save_task(task))
        return saved

    async def save_event(self, event: TaskEvent):
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO task_events (id, event_type, task_id, tenant_id, payload, timestamp)
                VALUES ($1, $2, $3, $4, $5::jsonb, $6)
                """,
                event.id, event.event_type, event.task_id, event.tenant_id,
                json.dumps(event.payload), event.timestamp
            )


# ─────────────────────────────────────────────
# Event System
# ─────────────────────────────────────────────

class EventBus:
    """Simple event bus for task lifecycle events."""

    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}
        self._global_handlers: List[Callable] = []

    def on(self, event_type: str, handler: Callable):
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def on_any(self, handler: Callable):
        self._global_handlers.append(handler)

    async def emit(self, event: TaskEvent):
        handlers = self._handlers.get(event.event_type, []) + self._global_handlers
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception:
                pass


# ─────────────────────────────────────────────
# Core TodoToolset
# ─────────────────────────────────────────────

class TodoToolset:
    """
    Task Planning and Tracking toolset for Pydantic AI agents.
    Provides hierarchical task management with subtasks, dependencies,
    multi-tenant storage, and an event system.
    """

    def __init__(
        self,
        storage=None,
        event_bus: Optional[EventBus] = None,
        default_tenant_id: str = "default",
    ):
        self.storage = storage or InMemoryStorage()
        self.event_bus = event_bus or EventBus()
        self.default_tenant_id = default_tenant_id

    async def initialize(self):
        await self.storage.initialize()

    async def close(self):
        await self.storage.close()

    async def _emit(self, event_type: str, task: Task, extra: Dict[str, Any] = None):
        event = TaskEvent(
            event_type=event_type,
            task_id=task.id,
            tenant_id=task.tenant_id,
            payload={"task": task.model_dump(mode="json"), **(extra or {})},
        )
        await self.event_bus.emit(event)
        if hasattr(self.storage, "save_event"):
            try:
                await self.storage.save_event(event)
            except Exception:
                pass

    # ── Core CRUD ──────────────────────────────

    async def add_task(self, input_data: CreateTaskInput) -> Task:
        """Add a single task."""
        task = Task(
            title=input_data.title,
            description=input_data.description,
            priority=input_data.priority,
            parent_id=input_data.parent_id,
            tenant_id=input_data.tenant_id or self.default_tenant_id,
            tags=input_data.tags,
            metadata=input_data.metadata,
            due_date=input_data.due_date,
            assignee=input_data.assignee,
        )
        saved = await self.storage.save_task(task)
        await self._emit("task.created", saved)
        return saved

    async def get_task(self, task_id: str, tenant_id: Optional[str] = None) -> Optional[Task]:
        """Get a task by ID."""
        return await self.storage.get_task(task_id, tenant_id or self.default_tenant_id)

    async def update_task(self, input_data: UpdateTaskInput, tenant_id: Optional[str] = None) -> Optional[Task]:
        """Update task fields by ID."""
        tid = tenant_id or self.default_tenant_id
        task = await self.storage.get_task(input_data.id, tid)
        if task is None:
            return None

        old_status = task.status
        if input_data.title is not None:
            task.title = input_data.title
        if input_data.description is not None:
            task.description = input_data.description
        if input_data.status is not None:
            task.status = input_data.status.value if isinstance(input_data.status, TaskStatus) else input_data.status
        if input_data.priority is not None:
            task.priority = input_data.priority.value if isinstance(input_data.priority, TaskPriority) else input_data.priority
        if input_data.tags is not None:
            task.tags = input_data.tags
        if input_data.metadata is not None:
            task.metadata = input_data.metadata
        if input_data.due_date is not None:
            task.due_date = input_data.due_date
        if input_data.assignee is not None:
            task.assignee = input_data.assignee

        saved = await self.storage.save_task(task)
        event_type = "task.status_changed" if input_data.status and old_status != task.status else "task.updated"
        await self._emit(event_type, saved, {"old_status": old_status})
        return saved

    async def update_task_status(self, task_id: str, status: TaskStatus,
                                  tenant_id: Optional[str] = None) -> Optional[Task]:
        """Update task status by ID."""
        return await self.update_task(
            UpdateTaskInput(id=task_id, status=status),
            tenant_id=tenant_id
        )

    async def delete_task(self, task_id: str, tenant_id: Optional[str] = None,
                           cascade: bool = True) -> bool:
        """Delete a task by ID. Optionally cascade to children."""
        tid = tenant_id or self.default_tenant_id
        task = await self.storage.get_task(task_id, tid)
        if task is None:
            return False

        if cascade:
            children = await self.storage.list_tasks(tenant_id=tid, parent_id=task_id)
            for child in children:
                await self.delete_task(child.id, tid, cascade=True)

        deleted = await self.storage.delete_task(task_id, tid)
        if deleted:
            await self._emit("task.deleted", task)
        return deleted

    # ── List & Hierarchy ───────────────────────

    async def list_tasks(self, tenant_id: Optional[str] = None,
                          status: Optional[TaskStatus] = None) -> List[Task]:
        """List all tasks (flat)."""
        return await self.storage.list_tasks(
            tenant_id=tenant_id or self.default_tenant_id,
            status=status
        )

    async def list_tasks_hierarchical(self, tenant_id: Optional[str] = None) -> List[HierarchicalTask]:
        """List all tasks in a hierarchical tree view."""
        tid = tenant_id or self.default_tenant_id
        all_tasks = await self.storage.list_tasks(tenant_id=tid)

        task_map: Dict[str, HierarchicalTask] = {}
        for task in all_tasks:
            deps = await self.storage.get_dependencies(task.id)
            task_map[task.id] = HierarchicalTask(task=task, dependencies=deps)

        roots: List[HierarchicalTask] = []
        for ht in task_map.values():
            if ht.task.parent_id is None:
                roots.append(ht)
            else:
                parent = task_map.get(ht.task.parent_id)
                if parent:
                    parent.children.append(ht)
                else:
                    roots.append(ht)

        return roots

    # ── Bulk Operations ────────────────────────

    async def bulk_write_tasks(self, input_data: BulkWriteInput) -> List[Task]:
        """Bulk create/update tasks."""
        tasks = []
        for task_input in input_data.tasks:
            task_input.tenant_id = input_data.tenant_id
            task = Task(
                title=task_input.title,
                description=task_input.description,
                priority=task_input.priority,
                parent_id=task_input.parent_id,
                tenant_id=task_input.tenant_id,
                tags=task_input.tags,
                metadata=task_input.metadata,
                due_date=task_input.due_date,
                assignee=task_input.assignee,
            )
            tasks.append(task)

        saved_tasks = await self.storage.bulk_save_tasks(tasks)
        for task in saved_tasks:
            await self._emit("task.created", task)
        return saved_tasks

    async def bulk_update_tasks(self, updates: List[UpdateTaskInput],
                                 tenant_id: Optional[str] = None) -> List[Task]:
        """Bulk update existing tasks."""
        results = []
        for update in updates:
            updated = await self.update_task(update, tenant_id=tenant_id)
            if updated:
                results.append(updated)
        return results

    # ── Subtasks & Dependencies ────────────────

    async def create_child_task(self, parent_id: str, input_data: CreateTaskInput,
                                 tenant_id: Optional[str] = None) -> Optional[Task]:
        """Create a child task under a parent."""
        tid = tenant_id or self.default_tenant_id
        parent = await self.storage.get_task(parent_id, tid)
        if parent is None:
            return None

        input_data.parent_id = parent_id
        input_data.tenant_id = tid
        return await self.add_task(input_data)

    async def link_dependency(self, task_id: str, depends_on_id: str,
                               tenant_id: Optional[str] = None) -> Optional[TaskDependency]:
        """Link two tasks with a dependency (task_id depends on depends_on_id)."""
        tid = tenant_id or self.default_tenant_id
        task = await self.storage.get_task(task_id, tid)
        dep_task = await self.storage.get_task(depends_on_id, tid)

        if task is None or dep_task is None:
            return None

        if await self._would_create_cycle(task_id, depends_on_id):
            raise ValueError(
                f"Adding dependency from {task_id} -> {depends_on_id} would create a cycle."
            )

        dep = await self.storage.add_dependency(task_id, depends_on_id)
        await self._emit("task.dependency_added", task, {"depends_on_id": depends_on_id})

        blocked_task = await self.storage.get_task(task_id, tid)
        if blocked_task and blocked_task.status == TaskStatus.PENDING.value:
            await self.update_task_status(task_id, TaskStatus.BLOCKED, tenant_id=tid)

        return dep

    async def _would_create_cycle(self, task_id: str, depends_on_id: str) -> bool:
        """Check if adding a dependency would create a cycle using DFS."""
        if task_id == depends_on_id:
            return True
        visited = set()
        stack = [depends_on_id]
        while stack:
            current = stack.pop()
            if current == task_id:
                return True
            if current in visited:
                continue
            visited.add(current)
            deps = await self.storage.get_dependencies(current)
            stack.extend(deps)
        return False

    async def get_ready_tasks(self, tenant_id: Optional[str] = None) -> List[Task]:
        """List tasks that are ready to work on (no incomplete dependencies)."""
        return await self.storage.get_ready_tasks(
            tenant_id=tenant_id or self.default_tenant_id
        )

    async def get_task_dependencies(self, task_id: str) -> List[str]:
        """Get IDs of tasks that the given task depends on."""
        return await self.storage.get_dependencies(task_id)

    async def get_task_dependents(self, task_id: str) -> List[str]:
        """Get IDs of tasks that depend on the given task."""
        return await self.storage.get_dependents(task_id)

    # ── Completion Propagation ─────────────────

    async def complete_task(self, task_id: str, tenant_id: Optional[str] = None) -> Optional[Task]:
        """Mark a task as completed and unblock dependent tasks if ready."""
        tid = tenant_id or self.default_tenant_id
        task = await self.update_task_status(task_id, TaskStatus.COMPLETED, tenant_id=tid)
        if task is None:
            return None

        dependents = await self.storage.get_dependents(task_id)
        for dep_id in dependents:
            dep_task = await self.storage.get_task(dep_id, tid)
            if dep_task and dep_task.status in (TaskStatus.BLOCKED.value, TaskStatus.BLOCKED):
                all_deps = await self.storage.get_dependencies(dep_id)
                all_done = True
                for d_id in all_deps:
                    d = await self.storage.get_task(d_id, tid)
                    if d is None or d.status not in (TaskStatus.COMPLETED.value, TaskStatus.COMPLETED):
                        all_done = False
                        break
                if all_done:
                    await self.update_task_status(dep_id, TaskStatus.PENDING, tenant_id=tid)

        return task


# ─────────────────────────────────────────────
# Pydantic AI Tool Wrappers
# ─────────────────────────────────────────────

class TodoTools:
    """
    Wraps TodoToolset as callable tools suitable for Pydantic AI agents.
    Each method is a standalone async function that can be registered as a tool.
    """

    def __init__(self, toolset: TodoToolset):
        self.toolset = toolset

    async def list_all_tasks(self, tenant_id: str = "default") -> Dict[str, Any]:
        """List all tasks for a tenant."""
        tasks = await self.toolset.list_tasks(tenant_id=tenant_id)
        return {"tasks": [t.model_dump(mode="json") for t in tasks], "count": len(tasks)}

    async def list_tasks_tree(self, tenant_id: str = "default") -> Dict[str, Any]:
        """List all tasks in hierarchical tree view."""
        tree = await self.toolset.list_tasks_hierarchical(tenant_id=tenant_id)

        def serialize_node(node: HierarchicalTask) -> Dict[str, Any]:
            return {
                "task": node.task.model_dump(mode="json"),
                "dependencies": node.dependencies,
                "children": [serialize_node(c) for c in node.children],
            }

        return {"tree": [serialize_node(n) for n in tree]}

    async def add_task(
        self,
        title: str,
        description: Optional[str] = None,
        priority: str = "medium",
        tenant_id: str = "default",
        tags: Optional[List[str]] = None,
        assignee: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Add a single task."""
        inp = CreateTaskInput(
            title=title,
            description=description,
            priority=TaskPriority(priority),
            tenant_id=tenant_id,
            tags=tags or [],
            assignee=assignee,
        )
        task = await self.toolset.add_task(inp)
        return {"task": task.model_dump(mode="json"), "success": True}

    async def update_task_status(
        self,
        task_id: str,
        status: str,
        tenant_id: str = "default",
    ) -> Dict[str, Any]:
        """Update task status by ID."""
        task = await self.toolset.update_task_status(task_id, TaskStatus(status), tenant_id=tenant_id)
        if task is None:
            return {"success": False, "error": f"Task {task_id} not found"}
        return {"task": task.model_dump(mode="json"), "success": True}

    async def delete_task(
        self,
        task_id: str,
        tenant_id: str = "default",
        cascade: bool = True,
    ) -> Dict[str, Any]:
        """Delete a task by ID."""
        deleted = await self.toolset.delete_task(task_id, tenant_id=tenant_id, cascade=cascade)
        return {"success": deleted, "task_id": task_id}

    async def create_child_task(
        self,
        parent_id: str,
        title: str,
        description: Optional[str] = None,
        priority: str = "medium",
        tenant_id: str = "default",
        assignee: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a child task under a parent task."""
        inp = CreateTaskInput(
            title=title,
            description=description,
            priority=TaskPriority(priority),
            tenant_id=tenant_id,
            assignee=assignee,
        )
        task = await self.toolset.create_child_task(parent_id, inp, tenant_id=tenant_id)
        if task is None:
            return {"success": False, "error": f"Parent task {parent_id} not found"}
        return {"task": task.model_dump(mode="json"), "success": True}

    async def link_dependency(
        self,
        task_id: str,
        depends_on_id: str,
        tenant_id: str = "default",
    ) -> Dict[str, Any]:
        """Link tasks with a dependency relationship."""
        try:
            dep = await self.toolset.link_dependency(task_id, depends_on_id, tenant_id=tenant_id)
            if dep is None:
                return {"success": False, "error": "One or both tasks not found"}
            return {"success": True, "task_id": task_id, "depends_on_id": depends_on_id}
        except ValueError as e:
            return {"success": False, "error": str(e)}

    async def get_ready_tasks(self, tenant_id: str = "default") -> Dict[str, Any]:
        """List tasks that are ready to work on."""
        tasks = await self.toolset.get_ready_tasks(tenant_id=tenant_id)
        return {"tasks": [t.model_dump(mode="json") for t in tasks], "count": len(tasks)}

    async def bulk_write_tasks(
        self,
        tasks: List[Dict[str, Any]],
        tenant_id: str = "default",
    ) -> Dict[str, Any]:
        """Bulk create tasks."""
        task_inputs = []
        for t in tasks:
            task_inputs.append(CreateTaskInput(
                title=t["title"],
                description=t.get("description"),
                priority=TaskPriority(t.get("priority", "medium")),
                tenant_id=tenant_id,
                tags=t.get("tags", []),
                assignee=t.get("assignee"),
                metadata=t.get("metadata", {}),
            ))
        inp = BulkWriteInput(tasks=task_inputs, tenant_id=tenant_id)
        saved = await self.toolset.bulk_write_tasks(inp)
        return {"tasks": [t.model_dump(mode="json") for t in saved], "count": len(saved)}

    async def complete_task(self, task_id: str, tenant_id: str = "default") -> Dict[str, Any]:
        """Mark a task as completed and unblock dependents."""
        task = await self.toolset.complete_task(task_id, tenant_id=tenant_id)
        if task is None:
            return {"success": False, "error": f"Task {task_id} not found"}
        return {"task": task.model_dump(mode="json"), "success": True}


# ─────────────────────────────────────────────
# Factory / Builder
# ─────────────────────────────────────────────

def create_todo_toolset(
    storage_type: str = "memory",
    postgres_dsn: Optional[str] = None,
    default_tenant_id: str = "default",
    event_handlers: Optional[Dict[str, List[Callable]]] = None,
) -> Tuple[TodoToolset, TodoTools]:
    """
    Factory function to create a TodoToolset and its tool wrappers.

    Args:
        storage_type: "memory" or "postgres"
        postgres_dsn: PostgreSQL DSN (required if storage_type="postgres")
        default_tenant_id: Default tenant identifier
        event_handlers: Dict mapping event types to handler lists

    Returns:
        Tuple of (TodoToolset, TodoTools)
    """
    if storage_type == "postgres":
        if not postgres_dsn:
            raise ValueError("postgres_dsn is required for PostgreSQL storage")
        storage = PostgreSQLStorage(dsn=postgres_dsn)
    else:
        storage = InMemoryStorage()

    event_bus = EventBus()
    if event_handlers:
        for event_type, handlers in event_handlers.items():
            for handler in handlers:
                event_bus.on(event_type, handler)

    toolset = TodoToolset(
        storage=storage,
        event_bus=event_bus,
        default_tenant_id=default_tenant_id,
    )
    tools = TodoTools(toolset=toolset)
    return toolset, tools


# ─────────────────────────────────────────────
# Pydantic AI Agent Integration Helper
# ─────────────────────────────────────────────

class TodoAgentDeps(BaseModel):
    """Dependencies model for Pydantic AI agent with todo tools."""
    tenant_id: str = "default"
    tools: Optional[Any] = None

    class Config:
        arbitrary_types_allowed = True


def register_todo_tools_with_agent(agent: Any, tools: TodoTools) -> Any:
    """
    Register all todo tools with a Pydantic AI agent.
    Returns the agent with tools registered.
    """
    if not HAS_PYDANTIC_AI:
        raise ImportError("pydantic_ai is required. Install it with: pip install pydantic-ai")

    @agent.tool_plain
    async def list_all_tasks(tenant_id: str = "default") -> Dict[str, Any]:
        """List all tasks for a tenant."""
        return await tools.list_all_tasks(tenant_id=tenant_id)

    @agent.tool_plain
    async def list_tasks_tree(tenant_id: str = "default") -> Dict[str, Any]:
        """List all tasks in hierarchical tree view."""
        return await tools.list_tasks_tree(tenant_id=tenant_id)

    @agent.tool_plain
    async def add_task(
        title: str,
        description: Optional[str] = None,
        priority: str = "medium",
        tenant_id: str = "default",
        tags: Optional[List[str]] = None,
        assignee: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Add a single task."""
        return await tools.add_task(
            title=title,
            description=description,
            priority=priority,
            tenant_id=tenant_id,
            tags=tags,
            assignee=assignee,
        )

    @agent.tool_plain
    async def update_task_status(
        task_id: str,
        status: str,
        tenant_id: str = "default",
    ) -> Dict[str, Any]:
        """Update task status by ID."""
        return await tools.update_task_status(task_id=task_id, status=status, tenant_id=tenant_id)

    @agent.tool_plain
    async def delete_task(
        task_id: str,
        tenant_id: str = "default",
        cascade: bool = True,
    ) -> Dict[str, Any]:
        """Delete a task by ID."""
        return await tools.delete_task(task_id=task_id, tenant_id=tenant_id, cascade=cascade)

    @agent.tool_plain
    async def create_child_task(
        parent_id: str,
        title: str,
        description: Optional[str] = None,
        priority: str = "medium",
        tenant_id: str = "default",
        assignee: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a child task under a parent task."""
        return await tools.create_child_task(
            parent_id=parent_id,
            title=title,
            description=description,
            priority=priority,
            tenant_id=tenant_id,
            assignee=assignee,
        )

    @agent.tool_plain
    async def link_dependency(
        task_id: str,
        depends_on_id: str,
        tenant_id: str = "default",
    ) -> Dict[str, Any]:
        """Link tasks with a dependency relationship."""
        return await tools.link_dependency(
            task_id=task_id,
            depends_on_id=depends_on_id,
            tenant_id=tenant_id,
        )

    @agent.tool_plain
    async def get_ready_tasks(tenant_id: str = "default") -> Dict[str, Any]:
        """List tasks that are ready to work on."""
        return await tools.get_ready_tasks(tenant_id=tenant_id)

    @agent.tool_plain
    async def bulk_write_tasks(
        tasks: List[Dict[str, Any]],
        tenant_id: str = "default",
    ) -> Dict[str, Any]:
        """Bulk create tasks."""
        return await tools.bulk_write_tasks(tasks=tasks, tenant_id=tenant_id)

    @agent.tool_plain
    async def complete_task(task_id: str, tenant_id: str = "default") -> Dict[str, Any]:
        """Mark a task as completed and unblock dependents."""
        return await tools.complete_task(task_id=task_id, tenant_id=tenant_id)

    return agent


# ─────────────────────────────────────────────
# CLI / Demo
# ─────────────────────────────────────────────

async def _demo():
    """Demonstrate the TodoToolset functionality."""
    print("=== Todo Toolset Demo ===\n")

    toolset, tools = create_todo_toolset(storage_type="memory", default_tenant_id="demo")
    await toolset.initialize()

    print("1. Bulk creating tasks...")
    bulk_result = await tools.bulk_write_tasks(
        tasks=[
            {"title": "Design database schema", "priority": "high", "tags": ["backend", "db"]},
            {"title": "Implement API endpoints", "priority": "high", "tags": ["backend"]},
            {"title": "Write unit tests", "priority": "medium", "tags": ["testing"]},
            {"title": "Deploy to staging", "priority": "medium", "tags": ["devops"]},
        ],
        tenant_id="demo",
    )
    print(f"   Created {bulk_result['count']} tasks")

    task_ids = [t["id"] for t in bulk_result["tasks"]]
    db_task_id = task_ids[0]
    api_task_id = task_ids[1]
    test_task_id = task_ids[2]
    deploy_task_id = task_ids[3]

    print("\n2. Adding a single task...")
    single_result = await tools.add_task(
        title="Project kickoff meeting",
        description="Initial planning meeting",
        priority="critical",
        tenant_id="demo",
        assignee="alice",
    )
    kickoff_id = single_result["task"]["id"]
    print(f"   Added: {single_result['task']['title']} (id={kickoff_id[:8]}...)")

    print("\n3. Creating child tasks...")
    child_result = await tools.create_child_task(
        parent_id=api_task_id,
        title="Implement authentication endpoint",
        description="POST /auth/login",
        priority="high",
        tenant_id="demo",
    )
    print(f"   Child task: {child_result['task']['title']}")

    print("\n4. Linking dependencies...")
    dep1 = await tools.link_dependency(api_task_id, db_task_id, tenant_id="demo")
    dep2 = await tools.link_dependency(test_task_id, api_task_id, tenant_id="demo")
    dep3 = await tools.link_dependency(deploy_task_id, test_task_id, tenant_id="demo")
    print(f"   API depends on DB: {dep1['success']}")
    print(f"   Tests depend on API: {dep2['success']}")
    print(f"   Deploy depends on Tests: {dep3['success']}")

    print("\n5. Ready tasks (no incomplete dependencies)...")
    ready = await tools.get_ready_tasks(tenant_id="demo")
    print(f"   Ready tasks: {[t['title'] for t in ready['tasks']]}")

    print("\n6. Completing DB schema task...")
    complete_result = await tools.complete_task(db_task_id, tenant_id="demo")
    print(f"   Completed: {complete_result['task']['title']}")

    print("\n7. Ready tasks after completing DB schema...")
    ready = await tools.get_ready_tasks(tenant_id="demo")
    print(f"   Ready tasks: {[t['title'] for t in ready['tasks']]}")

    print("\n8. Hierarchical task view...")
    tree = await tools.list_tasks_tree(tenant_id="demo")
    def print_tree(nodes, indent=0):
        for node in nodes:
            prefix = "  " * indent + ("└─ " if indent > 0 else "")
            status = node["task"]["status"]
            deps = f" [deps: {node['dependencies']}]" if node["dependencies"] else ""
            print(f"   {prefix}{node['task']['title']} [{status}]{deps}")
            print_tree(node["children"], indent + 1)
    print_tree(tree["tree"])

    print("\n9. Updating task status...")
    update_result = await tools.update_task_status(kickoff_id, "completed", tenant_id="demo")
    print(f"   Updated: {update_result['task']['title']} -> {update_result['task']['status']}")

    print("\n10. Deleting a task...")
    delete_result = await tools.delete_task(kickoff_id, tenant_id="demo")
    print(f"    Deleted: {delete_result['success']}")

    print("\n11. Final task list...")
    all_tasks = await tools.list_all_tasks(tenant_id="demo")
    print(f"    Total tasks: {all_tasks['count']}")
    for t in all_tasks["tasks"]:
        print(f"    - {t['title']} [{t['status']}]")

    await toolset.close()
    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    asyncio.run(_demo())