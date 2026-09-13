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
    due_date: Optional[datetime] = None
    subtasks: List[Task] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)

    class Config:
        use_enum_values = True


class TaskEvent(BaseModel):
    event_type: str
    task_id: str
    tenant_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = Field(default_factory=dict)


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
    dependencies: List[str] = Field(default_factory=list)


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
    due_date: Optional[datetime] = None


class LinkDependencyInput(BaseModel):
    task_id: str
    depends_on_task_id: str
    tenant_id: str = "default"


class ListTasksInput(BaseModel):
    tenant_id: str = "default"
    hierarchical: bool = False
    status_filter: Optional[TaskStatus] = None
    priority_filter: Optional[TaskPriority] = None
    tags_filter: Optional[List[str]] = None


class ReadyTasksInput(BaseModel):
    tenant_id: str = "default"


# ─────────────────────────────────────────────
# Storage Backends
# ─────────────────────────────────────────────

class InMemoryStorage:
    """In-memory storage backend for development/testing."""

    def __init__(self):
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._dependencies: List[Tuple[str, str]] = []

    async def initialize(self):
        pass

    async def close(self):
        pass

    async def save_task(self, task: Task) -> Task:
        task.updated_at = datetime.utcnow()
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
        tags_filter: Optional[List[str]] = None,
    ) -> List[Task]:
        results = []
        for data in self._tasks.values():
            if data.get("tenant_id") != tenant_id:
                continue
            if status_filter and data.get("status") != status_filter:
                continue
            if priority_filter and data.get("priority") != priority_filter:
                continue
            if tags_filter:
                task_tags = data.get("tags", [])
                if not any(tag in task_tags for tag in tags_filter):
                    continue
            results.append(Task(**data))
        return results

    async def delete_task(self, task_id: str, tenant_id: str) -> bool:
        data = self._tasks.get(task_id)
        if data and data.get("tenant_id") == tenant_id:
            del self._tasks[task_id]
            self._dependencies = [
                (a, b) for a, b in self._dependencies
                if a != task_id and b != task_id
            ]
            return True
        return False

    async def add_dependency(self, task_id: str, depends_on_id: str) -> bool:
        pair = (task_id, depends_on_id)
        if pair not in self._dependencies:
            self._dependencies.append(pair)
        return True

    async def get_dependencies(self, task_id: str) -> List[str]:
        return [b for a, b in self._dependencies if a == task_id]

    async def get_dependents(self, task_id: str) -> List[str]:
        return [a for a, b in self._dependencies if b == task_id]

    async def get_all_dependencies(self) -> List[Tuple[str, str]]:
        return list(self._dependencies)

    async def bulk_save_tasks(self, tasks: List[Task]) -> List[Task]:
        saved = []
        for task in tasks:
            saved.append(await self.save_task(task))
        return saved


class PostgreSQLStorage:
    """PostgreSQL storage backend for production multi-tenant use."""

    def __init__(self, dsn: str):
        if not HAS_ASYNCPG:
            raise ImportError("asyncpg is required for PostgreSQL storage. Install it with: pip install asyncpg")
        self.dsn = dsn
        self._pool: Optional[asyncpg.Pool] = None

    async def initialize(self):
        self._pool = await asyncpg.create_pool(self.dsn)
        await self._create_tables()

    async def close(self):
        if self._pool:
            await self._pool.close()

    async def _create_tables(self):
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
                    tags JSONB DEFAULT '[]',
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    due_date TIMESTAMPTZ,
                    FOREIGN KEY (parent_id) REFERENCES tasks(id) ON DELETE SET NULL
                );
                CREATE INDEX IF NOT EXISTS idx_tasks_tenant_id ON tasks(tenant_id);
                CREATE INDEX IF NOT EXISTS idx_tasks_parent_id ON tasks(parent_id);
                CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);

                CREATE TABLE IF NOT EXISTS task_dependencies (
                    task_id TEXT NOT NULL,
                    depends_on_id TEXT NOT NULL,
                    PRIMARY KEY (task_id, depends_on_id),
                    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
                    FOREIGN KEY (depends_on_id) REFERENCES tasks(id) ON DELETE CASCADE
                );
            """)

    def _row_to_task(self, row: asyncpg.Record) -> Task:
        return Task(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            status=row["status"],
            priority=row["priority"],
            parent_id=row["parent_id"],
            tenant_id=row["tenant_id"],
            tags=json.loads(row["tags"]) if isinstance(row["tags"], str) else (row["tags"] or []),
            metadata=json.loads(row["metadata"]) if isinstance(row["metadata"], str) else (row["metadata"] or {}),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            due_date=row["due_date"],
        )

    async def save_task(self, task: Task) -> Task:
        task.updated_at = datetime.utcnow()
        async with self._pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO tasks (id, title, description, status, priority, parent_id, tenant_id, tags, metadata, created_at, updated_at, due_date)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9::jsonb, $10, $11, $12)
                ON CONFLICT (id) DO UPDATE SET
                    title = EXCLUDED.title,
                    description = EXCLUDED.description,
                    status = EXCLUDED.status,
                    priority = EXCLUDED.priority,
                    parent_id = EXCLUDED.parent_id,
                    tags = EXCLUDED.tags,
                    metadata = EXCLUDED.metadata,
                    updated_at = EXCLUDED.updated_at,
                    due_date = EXCLUDED.due_date
            """,
                task.id, task.title, task.description, task.status,
                task.priority, task.parent_id, task.tenant_id,
                json.dumps(task.tags), json.dumps(task.metadata),
                task.created_at, task.updated_at, task.due_date
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
        tags_filter: Optional[List[str]] = None,
    ) -> List[Task]:
        query = "SELECT * FROM tasks WHERE tenant_id = $1"
        params = [tenant_id]
        idx = 2
        if status_filter:
            query += f" AND status = ${idx}"
            params.append(status_filter)
            idx += 1
        if priority_filter:
            query += f" AND priority = ${idx}"
            params.append(priority_filter)
            idx += 1
        if tags_filter:
            query += f" AND tags ?| ${idx}::text[]"
            params.append(tags_filter)
            idx += 1
        query += " ORDER BY created_at ASC"
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

    async def add_dependency(self, task_id: str, depends_on_id: str) -> bool:
        async with self._pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO task_dependencies (task_id, depends_on_id)
                VALUES ($1, $2)
                ON CONFLICT DO NOTHING
            """, task_id, depends_on_id)
        return True

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

    async def get_all_dependencies(self) -> List[Tuple[str, str]]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("SELECT task_id, depends_on_id FROM task_dependencies")
            return [(r["task_id"], r["depends_on_id"]) for r in rows]

    async def bulk_save_tasks(self, tasks: List[Task]) -> List[Task]:
        saved = []
        for task in tasks:
            saved.append(await self.save_task(task))
        return saved


# ─────────────────────────────────────────────
# Event System
# ─────────────────────────────────────────────

class EventSystem:
    """Event system for webhooks and callbacks."""

    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}
        self._webhook_urls: Dict[str, List[str]] = {}

    def on(self, event_type: str, handler: Callable):
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def register_webhook(self, event_type: str, url: str):
        if event_type not in self._webhook_urls:
            self._webhook_urls[event_type] = []
        if url not in self._webhook_urls[event_type]:
            self._webhook_urls[event_type].append(url)

    async def emit(self, event: TaskEvent):
        handlers = self._handlers.get(event.event_type, []) + self._handlers.get("*", [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                print(f"Event handler error for {event.event_type}: {e}")

        webhook_urls = self._webhook_urls.get(event.event_type, []) + self._webhook_urls.get("*", [])
        for url in webhook_urls:
            await self._send_webhook(url, event)

    async def _send_webhook(self, url: str, event: TaskEvent):
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                payload = event.dict()
                payload["timestamp"] = payload["timestamp"].isoformat()
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status >= 400:
                        print(f"Webhook to {url} failed with status {resp.status}")
        except ImportError:
            print(f"aiohttp not installed; cannot send webhook to {url}")
        except Exception as e:
            print(f"Webhook error for {url}: {e}")


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
        event_system: Optional[EventSystem] = None,
    ):
        self.storage = storage or InMemoryStorage()
        self.events = event_system or EventSystem()
        self._initialized = False

    async def initialize(self):
        if not self._initialized:
            await self.storage.initialize()
            self._initialized = True

    async def close(self):
        await self.storage.close()

    # ── Internal helpers ──────────────────────────────────────────────

    async def _ensure_initialized(self):
        if not self._initialized:
            await self.initialize()

    async def _build_hierarchy(self, tasks: List[Task]) -> List[Task]:
        task_map: Dict[str, Task] = {t.id: t for t in tasks}
        roots: List[Task] = []

        dep_map: Dict[str, List[str]] = {}
        all_deps = await self.storage.get_all_dependencies()
        for task_id, dep_id in all_deps:
            if task_id not in dep_map:
                dep_map[task_id] = []
            dep_map[task_id].append(dep_id)

        for task in tasks:
            task.subtasks = []
            task.dependencies = dep_map.get(task.id, [])

        for task in tasks:
            if task.parent_id and task.parent_id in task_map:
                parent = task_map[task.parent_id]
                parent.subtasks.append(task)
            else:
                roots.append(task)

        return roots

    # ── Tool Methods ──────────────────────────────────────────────────

    async def list_tasks(
        self,
        tenant_id: str = "default",
        hierarchical: bool = False,
        status_filter: Optional[str] = None,
        priority_filter: Optional[str] = None,
        tags_filter: Optional[List[str]] = None,
    ) -> List[Task]:
        """List all tasks, optionally in hierarchical view."""
        await self._ensure_initialized()
        tasks = await self.storage.list_tasks(
            tenant_id=tenant_id,
            status_filter=status_filter,
            priority_filter=priority_filter,
            tags_filter=tags_filter,
        )
        if hierarchical:
            tasks = await self._build_hierarchy(tasks)
        else:
            all_deps = await self.storage.get_all_dependencies()
            dep_map: Dict[str, List[str]] = {}
            for task_id, dep_id in all_deps:
                if task_id not in dep_map:
                    dep_map[task_id] = []
                dep_map[task_id].append(dep_id)
            for task in tasks:
                task.dependencies = dep_map.get(task.id, [])
        return tasks

    async def bulk_write_tasks(
        self,
        tasks: List[Task],
        tenant_id: str = "default",
    ) -> List[Task]:
        """Bulk create or update tasks."""
        await self._ensure_initialized()
        for task in tasks:
            task.tenant_id = tenant_id
        saved = await self.storage.bulk_save_tasks(tasks)
        for task in saved:
            await self.events.emit(TaskEvent(
                event_type="task.bulk_saved",
                task_id=task.id,
                tenant_id=tenant_id,
                data={"title": task.title, "status": task.status},
            ))
        return saved

    async def add_task(
        self,
        title: str,
        description: Optional[str] = None,
        priority: str = TaskPriority.MEDIUM,
        parent_id: Optional[str] = None,
        tenant_id: str = "default",
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        due_date: Optional[datetime] = None,
        dependencies: Optional[List[str]] = None,
    ) -> Task:
        """Add a single task."""
        await self._ensure_initialized()
        task = Task(
            title=title,
            description=description,
            priority=priority,
            parent_id=parent_id,
            tenant_id=tenant_id,
            tags=tags or [],
            metadata=metadata or {},
            due_date=due_date,
        )
        saved = await self.storage.save_task(task)

        if dependencies:
            for dep_id in dependencies:
                await self.storage.add_dependency(saved.id, dep_id)
            saved.dependencies = dependencies

        await self.events.emit(TaskEvent(
            event_type="task.created",
            task_id=saved.id,
            tenant_id=tenant_id,
            data={"title": saved.title, "priority": saved.priority},
        ))
        return saved

    async def update_task_status(
        self,
        task_id: str,
        status: str,
        tenant_id: str = "default",
    ) -> Optional[Task]:
        """Update task status by ID."""
        await self._ensure_initialized()
        task = await self.storage.get_task(task_id, tenant_id)
        if not task:
            return None
        old_status = task.status
        task.status = status
        updated = await self.storage.save_task(task)
        await self.events.emit(TaskEvent(
            event_type="task.status_changed",
            task_id=task_id,
            tenant_id=tenant_id,
            data={"old_status": old_status, "new_status": status},
        ))
        return updated

    async def delete_task(
        self,
        task_id: str,
        tenant_id: str = "default",
    ) -> bool:
        """Delete task by ID."""
        await self._ensure_initialized()
        deleted = await self.storage.delete_task(task_id, tenant_id)
        if deleted:
            await self.events.emit(TaskEvent(
                event_type="task.deleted",
                task_id=task_id,
                tenant_id=tenant_id,
                data={},
            ))
        return deleted

    async def create_child_task(
        self,
        parent_id: str,
        title: str,
        description: Optional[str] = None,
        priority: str = TaskPriority.MEDIUM,
        tenant_id: str = "default",
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        due_date: Optional[datetime] = None,
    ) -> Optional[Task]:
        """Create a child task under a parent task."""
        await self._ensure_initialized()
        parent = await self.storage.get_task(parent_id, tenant_id)
        if not parent:
            return None
        child = Task(
            title=title,
            description=description,
            priority=priority,
            parent_id=parent_id,
            tenant_id=tenant_id,
            tags=tags or [],
            metadata=metadata or {},
            due_date=due_date,
        )
        saved = await self.storage.save_task(child)
        await self.events.emit(TaskEvent(
            event_type="task.child_created",
            task_id=saved.id,
            tenant_id=tenant_id,
            data={"parent_id": parent_id, "title": saved.title},
        ))
        return saved

    async def link_dependency(
        self,
        task_id: str,
        depends_on_task_id: str,
        tenant_id: str = "default",
    ) -> bool:
        """Link two tasks with a dependency relationship."""
        await self._ensure_initialized()
        task = await self.storage.get_task(task_id, tenant_id)
        dep_task = await self.storage.get_task(depends_on_task_id, tenant_id)
        if not task or not dep_task:
            return False
        if task_id == depends_on_task_id:
            return False
        result = await self.storage.add_dependency(task_id, depends_on_task_id)
        if result:
            await self.events.emit(TaskEvent(
                event_type="task.dependency_linked",
                task_id=task_id,
                tenant_id=tenant_id,
                data={"depends_on": depends_on_task_id},
            ))
        return result

    async def list_ready_tasks(
        self,
        tenant_id: str = "default",
    ) -> List[Task]:
        """
        List tasks that are ready to work on.
        A task is ready if:
        - It is in PENDING or IN_PROGRESS status
        - All its dependencies are COMPLETED
        - It has no incomplete parent task blocking it
        """
        await self._ensure_initialized()
        all_tasks = await self.storage.list_tasks(tenant_id=tenant_id)
        task_map: Dict[str, Task] = {t.id: t for t in all_tasks}

        all_deps = await self.storage.get_all_dependencies()
        dep_map: Dict[str, List[str]] = {}
        for task_id, dep_id in all_deps:
            if task_id not in dep_map:
                dep_map[task_id] = []
            dep_map[task_id].append(dep_id)

        ready = []
        for task in all_tasks:
            if task.status not in (TaskStatus.PENDING, TaskStatus.IN_PROGRESS):
                continue

            deps = dep_map.get(task.id, [])
            all_deps_done = all(
                task_map.get(dep_id, Task(title="", status=TaskStatus.PENDING)).status == TaskStatus.COMPLETED
                for dep_id in deps
            )
            if not all_deps_done:
                continue

            if task.parent_id:
                parent = task_map.get(task.parent_id)
                if parent and parent.status in (TaskStatus.BLOCKED, TaskStatus.CANCELLED):
                    continue

            task.dependencies = deps
            ready.append(task)

        return ready

    async def get_task(self, task_id: str, tenant_id: str = "default") -> Optional[Task]:
        """Get a single task by ID."""
        await self._ensure_initialized()
        task = await self.storage.get_task(task_id, tenant_id)
        if task:
            task.dependencies = await self.storage.get_dependencies(task_id)
        return task

    async def update_task(
        self,
        task_id: str,
        tenant_id: str = "default",
        title: Optional[str] = None,
        description: Optional[str] = None,
        priority: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        due_date: Optional[datetime] = None,
    ) -> Optional[Task]:
        """Update task fields."""
        await self._ensure_initialized()
        task = await self.storage.get_task(task_id, tenant_id)
        if not task:
            return None
        if title is not None:
            task.title = title
        if description is not None:
            task.description = description
        if priority is not None:
            task.priority = priority
        if tags is not None:
            task.tags = tags
        if metadata is not None:
            task.metadata = metadata
        if due_date is not None:
            task.due_date = due_date
        updated = await self.storage.save_task(task)
        await self.events.emit(TaskEvent(
            event_type="task.updated",
            task_id=task_id,
            tenant_id=tenant_id,
            data={"title": updated.title},
        ))
        return updated

    # ── Pydantic AI Tool Registration ─────────────────────────────────

    def get_tools(self) -> List[Dict[str, Any]]:
        """
        Return tool definitions compatible with Pydantic AI agents.
        Each tool is a dict with 'name', 'description', and 'function'.
        """
        return [
            {
                "name": "list_tasks",
                "description": "List all tasks. Supports hierarchical view, filtering by status, priority, and tags.",
                "function": self.list_tasks,
            },
            {
                "name": "bulk_write_tasks",
                "description": "Bulk create or update multiple tasks at once.",
                "function": self.bulk_write_tasks,
            },
            {
                "name": "add_task",
                "description": "Add a single new task with optional priority, tags, metadata, and dependencies.",
                "function": self.add_task,
            },
            {
                "name": "update_task_status",
                "description": "Update the status of a task by its ID.",
                "function": self.update_task_status,
            },
            {
                "name": "delete_task",
                "description": "Delete a task by its ID.",
                "function": self.delete_task,
            },
            {
                "name": "create_child_task",
                "description": "Create a child/subtask under an existing parent task.",
                "function": self.create_child_task,
            },
            {
                "name": "link_dependency",
                "description": "Link two tasks with a dependency: task_id depends on depends_on_task_id.",
                "function": self.link_dependency,
            },
            {
                "name": "list_ready_tasks",
                "description": "List tasks that are ready to work on (all dependencies completed, not blocked).",
                "function": self.list_ready_tasks,
            },
            {
                "name": "get_task",
                "description": "Get a single task by its ID.",
                "function": self.get_task,
            },
            {
                "name": "update_task",
                "description": "Update task fields such as title, description, priority, tags, metadata, or due date.",
                "function": self.update_task,
            },
        ]

    def register_with_agent(self, agent: Any):
        """Register all tools with a Pydantic AI agent if available."""
        if not HAS_PYDANTIC_AI:
            raise ImportError("pydantic_ai is required to register tools with an agent.")
        tools = self.get_tools()
        for tool_def in tools:
            agent.tool(tool_def["function"])
        return agent


# ─────────────────────────────────────────────
# Factory / Convenience Functions
# ─────────────────────────────────────────────

def create_todo_toolset(
    storage_type: str = "memory",
    postgres_dsn: Optional[str] = None,
    event_system: Optional[EventSystem] = None,
) -> TodoToolset:
    """
    Factory function to create a TodoToolset with the specified storage backend.

    Args:
        storage_type: "memory" for in-memory storage, "postgres" for PostgreSQL.
        postgres_dsn: PostgreSQL DSN string (required if storage_type="postgres").
        event_system: Optional custom EventSystem instance.

    Returns:
        A configured TodoToolset instance.
    """
    if storage_type == "postgres":
        if not postgres_dsn:
            raise ValueError("postgres_dsn is required for PostgreSQL storage.")
        storage = PostgreSQLStorage(dsn=postgres_dsn)
    else:
        storage = InMemoryStorage()

    return TodoToolset(storage=storage, event_system=event_system)


# ─────────────────────────────────────────────
# CLI / Demo
# ─────────────────────────────────────────────

async def _demo():
    """Demonstrate the TodoToolset functionality."""
    print("=== Todo Toolset Demo ===\n")

    toolset = create_todo_toolset(storage_type="memory")
    await toolset.initialize()

    events_log = []

    async def on_any_event(event: TaskEvent):
        events_log.append(event)
        print(f"  [EVENT] {event.event_type} | task_id={event.task_id} | data={event.data}")

    toolset.events.on("*", on_any_event)

    print("1. Adding tasks...")
    task1 = await toolset.add_task(
        title="Design database schema",
        description="Create ERD and define tables",
        priority=TaskPriority.HIGH,
        tags=["backend", "database"],
    )
    print(f"   Created: {task1.title} (id={task1.id[:8]}...)")

    task2 = await toolset.add_task(
        title="Implement API endpoints",
        description="REST API for task management",
        priority=TaskPriority.HIGH,
        tags=["backend", "api"],
        dependencies=[task1.id],
    )
    print(f"   Created: {task2.title} (id={task2.id[:8]}...)")

    task3 = await toolset.add_task(
        title="Write unit tests",
        priority=TaskPriority.MEDIUM,
        tags=["testing"],
        dependencies=[task2.id],
    )
    print(f"   Created: {task3.title} (id={task3.id[:8]}...)")

    print("\n2. Creating child task...")
    child = await toolset.create_child_task(
        parent_id=task1.id,
        title="Define users table",
        description="Schema for users",
        priority=TaskPriority.HIGH,
    )
    print(f"   Child task: {child.title} (parent={task1.id[:8]}...)")

    print("\n3. Listing ready tasks (before completing task1)...")
    ready = await toolset.list_ready_tasks()
    print(f"   Ready tasks: {[t.title for t in ready]}")

    print("\n4. Completing task1...")
    updated = await toolset.update_task_status(task1.id, TaskStatus.COMPLETED)
    print(f"   Updated status: {updated.status}")

    print("\n5. Listing ready tasks (after completing task1)...")
    ready = await toolset.list_ready_tasks()
    print(f"   Ready tasks: {[t.title for t in ready]}")

    print("\n6. Bulk write tasks...")
    bulk_tasks = [
        Task(title="Deploy to staging", priority=TaskPriority.MEDIUM, tenant_id="default"),
        Task(title="Deploy to production", priority=TaskPriority.CRITICAL, tenant_id="default"),
    ]
    saved_bulk = await toolset.bulk_write_tasks(bulk_tasks)
    print(f"   Bulk saved: {[t.title for t in saved_bulk]}")

    print("\n7. Hierarchical task list...")
    all_tasks = await toolset.list_tasks(hierarchical=True)
    for t in all_tasks:
        print(f"   [{t.status}] {t.title}")
        for sub in t.subtasks:
            print(f"     └─ [{sub.status}] {sub.title}")

    print("\n8. Deleting a task...")
    deleted = await toolset.delete_task(task3.id)
    print(f"   Deleted task3: {deleted}")

    print("\n9. Available tools:")
    for tool in toolset.get_tools():
        print(f"   - {tool['name']}: {tool['description'][:60]}...")

    print(f"\n10. Total events emitted: {len(events_log)}")

    await toolset.close()
    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    asyncio.run(_demo())