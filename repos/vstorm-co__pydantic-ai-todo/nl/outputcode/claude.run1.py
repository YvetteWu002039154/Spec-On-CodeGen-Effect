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

    # Populated at runtime (not stored directly)
    subtasks: List["Task"] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)

    class Config:
        use_enum_values = True


class TaskDependency(BaseModel):
    task_id: str
    depends_on_id: str
    tenant_id: str = "default"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TaskEvent(BaseModel):
    event_type: str
    task_id: str
    tenant_id: str
    payload: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ─────────────────────────────────────────────
# In-Memory Storage Backend
# ─────────────────────────────────────────────

class InMemoryStorage:
    def __init__(self) -> None:
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._dependencies: List[Dict[str, Any]] = []

    async def initialize(self) -> None:
        pass

    async def close(self) -> None:
        pass

    async def save_task(self, task: Task) -> Task:
        data = task.dict()
        data.pop("subtasks", None)
        data.pop("dependencies", None)
        self._tasks[task.id] = data
        return task

    async def get_task(self, task_id: str, tenant_id: str) -> Optional[Task]:
        data = self._tasks.get(task_id)
        if data and data.get("tenant_id") == tenant_id:
            t = Task(**{k: v for k, v in data.items() if k not in ("subtasks", "dependencies")})
            return t
        return None

    async def list_tasks(self, tenant_id: str, parent_id: Optional[str] = None,
                         status: Optional[str] = None) -> List[Task]:
        results = []
        for data in self._tasks.values():
            if data.get("tenant_id") != tenant_id:
                continue
            if parent_id is not False and data.get("parent_id") != parent_id:
                continue
            if status and data.get("status") != status:
                continue
            results.append(Task(**{k: v for k, v in data.items() if k not in ("subtasks", "dependencies")}))
        return results

    async def delete_task(self, task_id: str, tenant_id: str) -> bool:
        data = self._tasks.get(task_id)
        if data and data.get("tenant_id") == tenant_id:
            del self._tasks[task_id]
            return True
        return False

    async def add_dependency(self, task_id: str, depends_on_id: str, tenant_id: str) -> None:
        for dep in self._dependencies:
            if dep["task_id"] == task_id and dep["depends_on_id"] == depends_on_id and dep["tenant_id"] == tenant_id:
                return
        self._dependencies.append({
            "task_id": task_id,
            "depends_on_id": depends_on_id,
            "tenant_id": tenant_id,
            "created_at": datetime.utcnow().isoformat()
        })

    async def get_dependencies(self, task_id: str, tenant_id: str) -> List[str]:
        return [
            dep["depends_on_id"]
            for dep in self._dependencies
            if dep["task_id"] == task_id and dep["tenant_id"] == tenant_id
        ]

    async def get_dependents(self, task_id: str, tenant_id: str) -> List[str]:
        return [
            dep["task_id"]
            for dep in self._dependencies
            if dep["depends_on_id"] == task_id and dep["tenant_id"] == tenant_id
        ]

    async def remove_dependency(self, task_id: str, depends_on_id: str, tenant_id: str) -> bool:
        before = len(self._dependencies)
        self._dependencies = [
            dep for dep in self._dependencies
            if not (dep["task_id"] == task_id and dep["depends_on_id"] == depends_on_id and dep["tenant_id"] == tenant_id)
        ]
        return len(self._dependencies) < before

    async def bulk_save_tasks(self, tasks: List[Task]) -> List[Task]:
        saved = []
        for task in tasks:
            saved.append(await self.save_task(task))
        return saved


# ─────────────────────────────────────────────
# PostgreSQL Storage Backend
# ─────────────────────────────────────────────

class PostgreSQLStorage:
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
                    tags JSONB DEFAULT '[]',
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    completed_at TIMESTAMPTZ,
                    due_date TIMESTAMPTZ,
                    assignee TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_tasks_tenant_id ON tasks(tenant_id);
                CREATE INDEX IF NOT EXISTS idx_tasks_parent_id ON tasks(parent_id);
                CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);

                CREATE TABLE IF NOT EXISTS task_dependencies (
                    task_id TEXT NOT NULL,
                    depends_on_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL DEFAULT 'default',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    PRIMARY KEY (task_id, depends_on_id, tenant_id)
                );
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
                INSERT INTO tasks (id, title, description, status, priority, parent_id, tenant_id,
                    tags, metadata, created_at, updated_at, completed_at, due_date, assignee)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)
                ON CONFLICT (id) DO UPDATE SET
                    title=EXCLUDED.title, description=EXCLUDED.description,
                    status=EXCLUDED.status, priority=EXCLUDED.priority,
                    parent_id=EXCLUDED.parent_id, tags=EXCLUDED.tags,
                    metadata=EXCLUDED.metadata, updated_at=EXCLUDED.updated_at,
                    completed_at=EXCLUDED.completed_at, due_date=EXCLUDED.due_date,
                    assignee=EXCLUDED.assignee
            """,
                task.id, task.title, task.description,
                task.status if isinstance(task.status, str) else task.status.value,
                task.priority if isinstance(task.priority, str) else task.priority.value,
                task.parent_id, task.tenant_id,
                json.dumps(task.tags), json.dumps(task.metadata),
                task.created_at, task.updated_at, task.completed_at,
                task.due_date, task.assignee
            )
        return task

    async def get_task(self, task_id: str, tenant_id: str) -> Optional[Task]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM tasks WHERE id=$1 AND tenant_id=$2", task_id, tenant_id
            )
            if row:
                return self._row_to_task(row)
        return None

    async def list_tasks(self, tenant_id: str, parent_id: Optional[str] = None,
                         status: Optional[str] = None) -> List[Task]:
        query = "SELECT * FROM tasks WHERE tenant_id=$1"
        params: List[Any] = [tenant_id]
        idx = 2
        if parent_id is not False:
            if parent_id is None:
                query += f" AND parent_id IS NULL"
            else:
                query += f" AND parent_id=${idx}"
                params.append(parent_id)
                idx += 1
        if status:
            query += f" AND status=${idx}"
            params.append(status)
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [self._row_to_task(row) for row in rows]

    async def delete_task(self, task_id: str, tenant_id: str) -> bool:
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM tasks WHERE id=$1 AND tenant_id=$2", task_id, tenant_id
            )
            return result.split()[-1] != "0"

    async def add_dependency(self, task_id: str, depends_on_id: str, tenant_id: str) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO task_dependencies (task_id, depends_on_id, tenant_id)
                VALUES ($1, $2, $3) ON CONFLICT DO NOTHING
            """, task_id, depends_on_id, tenant_id)

    async def get_dependencies(self, task_id: str, tenant_id: str) -> List[str]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT depends_on_id FROM task_dependencies WHERE task_id=$1 AND tenant_id=$2",
                task_id, tenant_id
            )
            return [row["depends_on_id"] for row in rows]

    async def get_dependents(self, task_id: str, tenant_id: str) -> List[str]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT task_id FROM task_dependencies WHERE depends_on_id=$1 AND tenant_id=$2",
                task_id, tenant_id
            )
            return [row["task_id"] for row in rows]

    async def remove_dependency(self, task_id: str, depends_on_id: str, tenant_id: str) -> bool:
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM task_dependencies WHERE task_id=$1 AND depends_on_id=$2 AND tenant_id=$3",
                task_id, depends_on_id, tenant_id
            )
            return result.split()[-1] != "0"

    async def bulk_save_tasks(self, tasks: List[Task]) -> List[Task]:
        saved = []
        for task in tasks:
            saved.append(await self.save_task(task))
        return saved


# ─────────────────────────────────────────────
# Event System
# ─────────────────────────────────────────────

class EventSystem:
    def __init__(self) -> None:
        self._handlers: Dict[str, List[Callable]] = {}
        self._webhook_urls: List[str] = []

    def on(self, event_type: str, handler: Callable) -> None:
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def add_webhook(self, url: str) -> None:
        self._webhook_urls.append(url)

    async def emit(self, event: TaskEvent) -> None:
        handlers = self._handlers.get(event.event_type, []) + self._handlers.get("*", [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception:
                pass

        if self._webhook_urls:
            await self._dispatch_webhooks(event)

    async def _dispatch_webhooks(self, event: TaskEvent) -> None:
        try:
            import aiohttp
            payload = event.dict()
            payload["timestamp"] = payload["timestamp"].isoformat()
            async with aiohttp.ClientSession() as session:
                for url in self._webhook_urls:
                    try:
                        await session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=5))
                    except Exception:
                        pass
        except ImportError:
            pass


# ─────────────────────────────────────────────
# Core Todo Toolset
# ─────────────────────────────────────────────

class TodoToolset:
    def __init__(
        self,
        storage: Optional[Any] = None,
        tenant_id: str = "default",
        event_system: Optional[EventSystem] = None
    ) -> None:
        self._storage = storage or InMemoryStorage()
        self._tenant_id = tenant_id
        self._events = event_system or EventSystem()
        self._initialized = False

    async def initialize(self) -> None:
        if not self._initialized:
            await self._storage.initialize()
            self._initialized = True

    async def close(self) -> None:
        await self._storage.close()

    def set_tenant(self, tenant_id: str) -> None:
        self._tenant_id = tenant_id

    # ── Event helpers ──────────────────────────────────────────────────────

    async def _emit(self, event_type: str, task: Task, extra: Optional[Dict[str, Any]] = None) -> None:
        payload = {"task": task.dict()}
        if extra:
            payload.update(extra)
        event = TaskEvent(
            event_type=event_type,
            task_id=task.id,
            tenant_id=self._tenant_id,
            payload=payload
        )
        await self._events.emit(event)

    # ── List all tasks (hierarchical) ──────────────────────────────────────

    async def list_tasks(
        self,
        hierarchical: bool = False,
        status: Optional[str] = None,
        include_subtasks: bool = True
    ) -> List[Task]:
        await self.initialize()
        if hierarchical:
            return await self._list_hierarchical(status=status)
        tasks = await self._storage.list_tasks(
            tenant_id=self._tenant_id,
            parent_id=False,
            status=status
        )
        if include_subtasks:
            for task in tasks:
                task.dependencies = await self._storage.get_dependencies(task.id, self._tenant_id)
        return tasks

    async def _list_hierarchical(self, status: Optional[str] = None) -> List[Task]:
        root_tasks = await self._storage.list_tasks(
            tenant_id=self._tenant_id,
            parent_id=None,
            status=status
        )
        for task in root_tasks:
            task.subtasks = await self._get_subtasks_recursive(task.id, status)
            task.dependencies = await self._storage.get_dependencies(task.id, self._tenant_id)
        return root_tasks

    async def _get_subtasks_recursive(self, parent_id: str, status: Optional[str] = None) -> List[Task]:
        children = await self._storage.list_tasks(
            tenant_id=self._tenant_id,
            parent_id=parent_id,
            status=status
        )
        for child in children:
            child.subtasks = await self._get_subtasks_recursive(child.id, status)
            child.dependencies = await self._storage.get_dependencies(child.id, self._tenant_id)
        return children

    # ── Add a single task ─────────────────────────────────────────────────

    async def add_task(
        self,
        title: str,
        description: Optional[str] = None,
        priority: str = TaskPriority.MEDIUM,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        due_date: Optional[datetime] = None,
        assignee: Optional[str] = None
    ) -> Task:
        await self.initialize()
        task = Task(
            title=title,
            description=description,
            priority=priority,
            tenant_id=self._tenant_id,
            tags=tags or [],
            metadata=metadata or {},
            due_date=due_date,
            assignee=assignee
        )
        saved = await self._storage.save_task(task)
        await self._emit("task.created", saved)
        return saved

    # ── Bulk write/update tasks ───────────────────────────────────────────

    async def bulk_write_tasks(self, tasks_data: List[Dict[str, Any]]) -> List[Task]:
        await self.initialize()
        tasks = []
        for data in tasks_data:
            data.setdefault("tenant_id", self._tenant_id)
            if "id" in data:
                existing = await self._storage.get_task(data["id"], self._tenant_id)
                if existing:
                    updated_data = existing.dict()
                    updated_data.update(data)
                    updated_data["updated_at"] = datetime.utcnow()
                    task = Task(**{k: v for k, v in updated_data.items() if k not in ("subtasks", "dependencies")})
                else:
                    task = Task(**{k: v for k, v in data.items() if k not in ("subtasks", "dependencies")})
            else:
                task = Task(**{k: v for k, v in data.items() if k not in ("subtasks", "dependencies")})
            tasks.append(task)

        saved_tasks = await self._storage.bulk_save_tasks(tasks)
        for task in saved_tasks:
            await self._emit("task.bulk_saved", task)
        return saved_tasks

    # ── Update task status by ID ──────────────────────────────────────────

    async def update_task_status(self, task_id: str, status: str) -> Optional[Task]:
        await self.initialize()
        task = await self._storage.get_task(task_id, self._tenant_id)
        if not task:
            return None

        old_status = task.status
        task.status = status
        task.updated_at = datetime.utcnow()

        if status == TaskStatus.COMPLETED:
            task.completed_at = datetime.utcnow()

        saved = await self._storage.save_task(task)
        await self._emit("task.status_changed", saved, {"old_status": old_status, "new_status": status})
        return saved

    # ── Update task (general) ─────────────────────────────────────────────

    async def update_task(self, task_id: str, **kwargs: Any) -> Optional[Task]:
        await self.initialize()
        task = await self._storage.get_task(task_id, self._tenant_id)
        if not task:
            return None

        task_data = task.dict()
        for key, value in kwargs.items():
            if key in task_data and key not in ("id", "tenant_id", "subtasks", "dependencies"):
                task_data[key] = value
        task_data["updated_at"] = datetime.utcnow()

        updated_task = Task(**{k: v for k, v in task_data.items() if k not in ("subtasks", "dependencies")})
        saved = await self._storage.save_task(updated_task)
        await self._emit("task.updated", saved)
        return saved

    # ── Delete task by ID ─────────────────────────────────────────────────

    async def delete_task(self, task_id: str, cascade: bool = True) -> bool:
        await self.initialize()
        task = await self._storage.get_task(task_id, self._tenant_id)
        if not task:
            return False

        if cascade:
            subtasks = await self._storage.list_tasks(
                tenant_id=self._tenant_id,
                parent_id=task_id
            )
            for subtask in subtasks:
                await self.delete_task(subtask.id, cascade=True)

        result = await self._storage.delete_task(task_id, self._tenant_id)
        if result:
            await self._emit("task.deleted", task)
        return result

    # ── Create child task ─────────────────────────────────────────────────

    async def create_child_task(
        self,
        parent_id: str,
        title: str,
        description: Optional[str] = None,
        priority: str = TaskPriority.MEDIUM,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        due_date: Optional[datetime] = None,
        assignee: Optional[str] = None
    ) -> Optional[Task]:
        await self.initialize()
        parent = await self._storage.get_task(parent_id, self._tenant_id)
        if not parent:
            return None

        child = Task(
            title=title,
            description=description,
            priority=priority,
            parent_id=parent_id,
            tenant_id=self._tenant_id,
            tags=tags or [],
            metadata=metadata or {},
            due_date=due_date,
            assignee=assignee
        )
        saved = await self._storage.save_task(child)
        await self._emit("task.child_created", saved, {"parent_id": parent_id})
        return saved

    # ── Link tasks with dependency ────────────────────────────────────────

    async def add_dependency(self, task_id: str, depends_on_id: str) -> bool:
        await self.initialize()
        task = await self._storage.get_task(task_id, self._tenant_id)
        depends_on = await self._storage.get_task(depends_on_id, self._tenant_id)

        if not task or not depends_on:
            return False

        if await self._would_create_cycle(task_id, depends_on_id):
            raise ValueError(f"Adding dependency from {task_id} to {depends_on_id} would create a cycle")

        await self._storage.add_dependency(task_id, depends_on_id, self._tenant_id)

        if task.status == TaskStatus.PENDING:
            dep_status = depends_on.status
            if dep_status not in (TaskStatus.COMPLETED, TaskStatus.CANCELLED):
                await self.update_task_status(task_id, TaskStatus.BLOCKED)

        event = TaskEvent(
            event_type="task.dependency_added",
            task_id=task_id,
            tenant_id=self._tenant_id,
            payload={"task_id": task_id, "depends_on_id": depends_on_id}
        )
        await self._events.emit(event)
        return True

    async def _would_create_cycle(self, task_id: str, depends_on_id: str) -> bool:
        if task_id == depends_on_id:
            return True
        visited = set()
        queue = [depends_on_id]
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            if current == task_id:
                return True
            deps = await self._storage.get_dependencies(current, self._tenant_id)
            queue.extend(deps)
        return False

    async def remove_dependency(self, task_id: str, depends_on_id: str) -> bool:
        await self.initialize()
        result = await self._storage.remove_dependency(task_id, depends_on_id, self._tenant_id)
        if result:
            await self._check_and_unblock_task(task_id)
        return result

    async def _check_and_unblock_task(self, task_id: str) -> None:
        task = await self._storage.get_task(task_id, self._tenant_id)
        if not task or task.status != TaskStatus.BLOCKED:
            return

        deps = await self._storage.get_dependencies(task_id, self._tenant_id)
        all_done = True
        for dep_id in deps:
            dep_task = await self._storage.get_task(dep_id, self._tenant_id)
            if dep_task and dep_task.status not in (TaskStatus.COMPLETED, TaskStatus.CANCELLED):
                all_done = False
                break

        if all_done:
            await self.update_task_status(task_id, TaskStatus.PENDING)

    # ── List tasks ready to work on ───────────────────────────────────────

    async def list_ready_tasks(self) -> List[Task]:
        await self.initialize()
        all_tasks = await self._storage.list_tasks(
            tenant_id=self._tenant_id,
            parent_id=False
        )
        ready = []
        for task in all_tasks:
            status = task.status if isinstance(task.status, str) else task.status.value
            if status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED, TaskStatus.IN_PROGRESS):
                continue
            deps = await self._storage.get_dependencies(task.id, self._tenant_id)
            is_ready = True
            for dep_id in deps:
                dep_task = await self._storage.get_task(dep_id, self._tenant_id)
                if dep_task:
                    dep_status = dep_task.status if isinstance(dep_task.status, str) else dep_task.status.value
                    if dep_status not in (TaskStatus.COMPLETED, TaskStatus.CANCELLED):
                        is_ready = False
                        break
            if is_ready:
                task.dependencies = deps
                ready.append(task)
        return ready

    # ── Get single task ───────────────────────────────────────────────────

    async def get_task(self, task_id: str) -> Optional[Task]:
        await self.initialize()
        task = await self._storage.get_task(task_id, self._tenant_id)
        if task:
            task.dependencies = await self._storage.get_dependencies(task_id, self._tenant_id)
            task.subtasks = await self._get_subtasks_recursive(task_id)
        return task

    # ── Get task dependencies ─────────────────────────────────────────────

    async def get_task_dependencies(self, task_id: str) -> List[Task]:
        await self.initialize()
        dep_ids = await self._storage.get_dependencies(task_id, self._tenant_id)
        tasks = []
        for dep_id in dep_ids:
            dep_task = await self._storage.get_task(dep_id, self._tenant_id)
            if dep_task:
                tasks.append(dep_task)
        return tasks

    # ── Get task dependents ───────────────────────────────────────────────

    async def get_task_dependents(self, task_id: str) -> List[Task]:
        await self.initialize()
        dependent_ids = await self._storage.get_dependents(task_id, self._tenant_id)
        tasks = []
        for dep_id in dependent_ids:
            dep_task = await self._storage.get_task(dep_id, self._tenant_id)
            if dep_task:
                tasks.append(dep_task)
        return tasks

    # ── Complete task and unblock dependents ──────────────────────────────

    async def complete_task(self, task_id: str) -> Optional[Task]:
        await self.initialize()
        task = await self.update_task_status(task_id, TaskStatus.COMPLETED)
        if task:
            dependent_ids = await self._storage.get_dependents(task_id, self._tenant_id)
            for dep_id in dependent_ids:
                await self._check_and_unblock_task(dep_id)
        return task

    # ── Event registration ────────────────────────────────────────────────

    def on_event(self, event_type: str, handler: Callable) -> None:
        self._events.on(event_type, handler)

    def add_webhook(self, url: str) -> None:
        self._events.add_webhook(url)


# ─────────────────────────────────────────────
# Pydantic AI Tool Definitions
# ─────────────────────────────────────────────

class TodoTools:
    def __init__(self, toolset: TodoToolset) -> None:
        self._toolset = toolset

    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "list_tasks",
                "description": "List all tasks. Supports hierarchical view showing parent-child relationships.",
                "function": self.list_tasks
            },
            {
                "name": "bulk_write_tasks",
                "description": "Bulk create or update multiple tasks at once.",
                "function": self.bulk_write_tasks
            },
            {
                "name": "add_task",
                "description": "Add a single new task.",
                "function": self.add_task
            },
            {
                "name": "update_task_status",
                "description": "Update the status of a task by its ID.",
                "function": self.update_task_status
            },
            {
                "name": "delete_task",
                "description": "Delete a task by its ID.",
                "function": self.delete_task
            },
            {
                "name": "create_child_task",
                "description": "Create a subtask under a parent task.",
                "function": self.create_child_task
            },
            {
                "name": "add_dependency",
                "description": "Link two tasks so one depends on the other.",
                "function": self.add_dependency
            },
            {
                "name": "list_ready_tasks",
                "description": "List tasks that are ready to work on (no pending dependencies).",
                "function": self.list_ready_tasks
            },
        ]

    async def list_tasks(
        self,
        hierarchical: bool = False,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        tasks = await self._toolset.list_tasks(hierarchical=hierarchical, status=status)
        return {
            "tasks": [t.dict() for t in tasks],
            "count": len(tasks)
        }

    async def bulk_write_tasks(self, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        saved = await self._toolset.bulk_write_tasks(tasks)
        return {
            "tasks": [t.dict() for t in saved],
            "count": len(saved)
        }

    async def add_task(
        self,
        title: str,
        description: Optional[str] = None,
        priority: str = "medium",
        tags: Optional[List[str]] = None,
        assignee: Optional[str] = None
    ) -> Dict[str, Any]:
        task = await self._toolset.add_task(
            title=title,
            description=description,
            priority=priority,
            tags=tags,
            assignee=assignee
        )
        return task.dict()

    async def update_task_status(self, task_id: str, status: str) -> Dict[str, Any]:
        task = await self._toolset.update_task_status(task_id, status)
        if task:
            return {"success": True, "task": task.dict()}
        return {"success": False, "error": f"Task {task_id} not found"}

    async def delete_task(self, task_id: str, cascade: bool = True) -> Dict[str, Any]:
        result = await self._toolset.delete_task(task_id, cascade=cascade)
        return {"success": result, "task_id": task_id}

    async def create_child_task(
        self,
        parent_id: str,
        title: str,
        description: Optional[str] = None,
        priority: str = "medium",
        assignee: Optional[str] = None
    ) -> Dict[str, Any]:
        task = await self._toolset.create_child_task(
            parent_id=parent_id,
            title=title,
            description=description,
            priority=priority,
            assignee=assignee
        )
        if task:
            return {"success": True, "task": task.dict()}
        return {"success": False, "error": f"Parent task {parent_id} not found"}

    async def add_dependency(self, task_id: str, depends_on_id: str) -> Dict[str, Any]:
        try:
            result = await self._toolset.add_dependency(task_id, depends_on_id)
            return {"success": result, "task_id": task_id, "depends_on_id": depends_on_id}
        except ValueError as e:
            return {"success": False, "error": str(e)}

    async def list_ready_tasks(self) -> Dict[str, Any]:
        tasks = await self._toolset.list_ready_tasks()
        return {
            "tasks": [t.dict() for t in tasks],
            "count": len(tasks)
        }


# ─────────────────────────────────────────────
# Factory / Builder
# ─────────────────────────────────────────────

class TodoToolsetBuilder:
    def __init__(self) -> None:
        self._storage: Optional[Any] = None
        self._tenant_id: str = "default"
        self._event_system: Optional[EventSystem] = None
        self._webhooks: List[str] = []
        self._event_handlers: List[Tuple[str, Callable]] = []

    def with_memory_storage(self) -> "TodoToolsetBuilder":
        self._storage = InMemoryStorage()
        return self

    def with_postgres_storage(self, dsn: str) -> "TodoToolsetBuilder":
        self._storage = PostgreSQLStorage(dsn)
        return self

    def with_tenant(self, tenant_id: str) -> "TodoToolsetBuilder":
        self._tenant_id = tenant_id
        return self

    def with_webhook(self, url: str) -> "TodoToolsetBuilder":
        self._webhooks.append(url)
        return self

    def on_event(self, event_type: str, handler: Callable) -> "TodoToolsetBuilder":
        self._event_handlers.append((event_type, handler))
        return self

    def build(self) -> TodoToolset:
        event_system = EventSystem()
        for url in self._webhooks:
            event_system.add_webhook(url)
        for event_type, handler in self._event_handlers:
            event_system.on(event_type, handler)

        toolset = TodoToolset(
            storage=self._storage or InMemoryStorage(),
            tenant_id=self._tenant_id,
            event_system=event_system
        )
        return toolset


# ─────────────────────────────────────────────
# Convenience factory function
# ─────────────────────────────────────────────

def create_todo_toolset(
    storage_type: str = "memory",
    postgres_dsn: Optional[str] = None,
    tenant_id: str = "default",
    webhooks: Optional[List[str]] = None
) -> TodoToolset:
    builder = TodoToolsetBuilder().with_tenant(tenant_id)

    if storage_type == "postgres" and postgres_dsn:
        builder.with_postgres_storage(postgres_dsn)
    else:
        builder.with_memory_storage()

    for url in (webhooks or []):
        builder.with_webhook(url)

    return builder.build()


def create_todo_tools(toolset: Optional[TodoToolset] = None, **kwargs: Any) -> TodoTools:
    if toolset is None:
        toolset = create_todo_toolset(**kwargs)
    return TodoTools(toolset)


# ─────────────────────────────────────────────
# Multi-tenant Manager
# ─────────────────────────────────────────────

class MultiTenantTodoManager:
    def __init__(self, storage: Optional[Any] = None) -> None:
        self._storage = storage or InMemoryStorage()
        self._toolsets: Dict[str, TodoToolset] = {}
        self._event_system = EventSystem()

    async def initialize(self) -> None:
        await self._storage.initialize()

    async def close(self) -> None:
        await self._storage.close()

    def get_toolset(self, tenant_id: str) -> TodoToolset:
        if tenant_id not in self._toolsets:
            self._toolsets[tenant_id] = TodoToolset(
                storage=self._storage,
                tenant_id=tenant_id,
                event_system=self._event_system
            )
            self._toolsets[tenant_id]._initialized = True
        return self._toolsets[tenant_id]

    def get_tools(self, tenant_id: str) -> TodoTools:
        return TodoTools(self.get_toolset(tenant_id))

    def on_event(self, event_type: str, handler: Callable) -> None:
        self._event_system.on(event_type, handler)

    def add_webhook(self, url: str) -> None:
        self._event_system.add_webhook(url)


# ─────────────────────────────────────────────
# CLI / Demo
# ─────────────────────────────────────────────

async def _demo() -> None:
    print("=== Todo Toolset Demo ===\n")

    toolset = create_todo_toolset(tenant_id="demo")
    tools = TodoTools(toolset)

    toolset.on_event("task.created", lambda e: print(f"[EVENT] Task created: {e.payload['task']['title']}"))
    toolset.on_event("task.status_changed", lambda e: print(f"[EVENT] Status changed: {e.payload['new_status']}"))

    print("1. Adding tasks...")
    t1 = await tools.add_task("Design database schema", priority="high")
    t2 = await tools.add_task("Implement API endpoints", priority="high")
    t3 = await tools.add_task("Write tests", priority="medium")
    t4 = await tools.add_task("Deploy to production", priority="critical")

    print(f"\n2. Creating subtask under '{t1['title']}'...")
    child = await tools.create_child_task(
        parent_id=t1["id"],
        title="Define entity relationships",
        description="Map out all entity relationships"
    )
    print(f"   Created: {child['task']['title']}")

    print("\n3. Adding dependencies...")
    await tools.add_dependency(t2["id"], t1["id"])
    await tools.add_dependency(t3["id"], t2["id"])
    await tools.add_dependency(t4["id"], t3["id"])
    print("   Dependencies set: t1 -> t2 -> t3 -> t4")

    print("\n4. Listing ready tasks...")
    ready = await tools.list_ready_tasks()
    print(f"   Ready tasks: {[t['title'] for t in ready['tasks']]}")

    print("\n5. Completing task 1...")
    await tools.update_task_status(t1["id"], "completed")

    print("\n6. Listing ready tasks after completing t1...")
    ready = await tools.list_ready_tasks()
    print(f"   Ready tasks: {[t['title'] for t in ready['tasks']]}")

    print("\n7. Listing all tasks (hierarchical)...")
    all_tasks = await tools.list_tasks(hierarchical=True)
    for task in all_tasks["tasks"]:
        print(f"   [{task['status']}] {task['title']}")
        for sub in task.get("subtasks", []):
            print(f"     └─ [{sub['status']}] {sub['title']}")

    print("\n8. Bulk write tasks...")
    bulk_result = await tools.bulk_write_tasks([
        {"title": "Task A", "priority": "low"},
        {"title": "Task B", "priority": "medium"},
        {"title": "Task C", "priority": "high"},
    ])
    print(f"   Bulk created {bulk_result['count']} tasks")

    print("\n9. Deleting a task...")
    del_result = await tools.delete_task(t4["id"])
    print(f"   Deleted: {del_result['success']}")

    print("\n10. Final task list...")
    final = await tools.list_tasks()
    print(f"   Total tasks: {final['count']}")

    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    asyncio.run(_demo())