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
    depends_on_task_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TaskEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str
    task_id: str
    tenant_id: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ─────────────────────────────────────────────
# In-Memory Storage Backend
# ─────────────────────────────────────────────

class InMemoryStorage:
    def __init__(self):
        self._tasks: Dict[str, Task] = {}
        self._dependencies: List[TaskDependency] = []

    async def initialize(self):
        pass

    async def close(self):
        pass

    async def create_task(self, task: Task) -> Task:
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
            if parent_id is None and status is None:
                results.append(task)
                continue
            if status is not None and task.status != status.value:
                continue
            results.append(task)
        return sorted(results, key=lambda t: t.created_at)

    async def update_task(self, task: Task) -> Task:
        task.updated_at = datetime.utcnow()
        self._tasks[task.id] = task
        return task

    async def delete_task(self, task_id: str, tenant_id: str = "default") -> bool:
        task = self._tasks.get(task_id)
        if task and task.tenant_id == tenant_id:
            del self._tasks[task_id]
            self._dependencies = [
                d for d in self._dependencies
                if d.task_id != task_id and d.depends_on_task_id != task_id
            ]
            return True
        return False

    async def bulk_upsert_tasks(self, tasks: List[Task]) -> List[Task]:
        results = []
        for task in tasks:
            task.updated_at = datetime.utcnow()
            self._tasks[task.id] = task
            results.append(task)
        return results

    async def add_dependency(self, task_id: str, depends_on_task_id: str) -> TaskDependency:
        dep = TaskDependency(task_id=task_id, depends_on_task_id=depends_on_task_id)
        self._dependencies.append(dep)
        return dep

    async def get_dependencies(self, task_id: str) -> List[str]:
        return [d.depends_on_task_id for d in self._dependencies if d.task_id == task_id]

    async def get_dependents(self, task_id: str) -> List[str]:
        return [d.task_id for d in self._dependencies if d.depends_on_task_id == task_id]

    async def remove_dependency(self, task_id: str, depends_on_task_id: str) -> bool:
        before = len(self._dependencies)
        self._dependencies = [
            d for d in self._dependencies
            if not (d.task_id == task_id and d.depends_on_task_id == depends_on_task_id)
        ]
        return len(self._dependencies) < before

    async def get_ready_tasks(self, tenant_id: str = "default") -> List[Task]:
        pending_tasks = await self.list_tasks(tenant_id=tenant_id, status=TaskStatus.PENDING)
        ready = []
        for task in pending_tasks:
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


# ─────────────────────────────────────────────
# PostgreSQL Storage Backend
# ─────────────────────────────────────────────

class PostgreSQLStorage:
    def __init__(self, dsn: str):
        if not HAS_ASYNCPG:
            raise ImportError("asyncpg is required for PostgreSQL storage. Install it with: pip install asyncpg")
        self._dsn = dsn
        self._pool: Optional[asyncpg.Pool] = None

    async def initialize(self):
        self._pool = await asyncpg.create_pool(self._dsn)
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
                    tags JSONB NOT NULL DEFAULT '[]',
                    metadata JSONB NOT NULL DEFAULT '{}',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    completed_at TIMESTAMPTZ,
                    due_date TIMESTAMPTZ,
                    assignee TEXT
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS task_dependencies (
                    task_id TEXT NOT NULL,
                    depends_on_task_id TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    PRIMARY KEY (task_id, depends_on_task_id)
                )
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_tenant_id ON tasks(tenant_id)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_parent_id ON tasks(parent_id)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)
            """)

    def _row_to_task(self, row) -> Task:
        data = dict(row)
        if isinstance(data.get('tags'), str):
            data['tags'] = json.loads(data['tags'])
        if isinstance(data.get('metadata'), str):
            data['metadata'] = json.loads(data['metadata'])
        return Task(**data)

    async def create_task(self, task: Task) -> Task:
        async with self._pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO tasks (id, title, description, status, priority, parent_id, tenant_id,
                                   tags, metadata, created_at, updated_at, completed_at, due_date, assignee)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9::jsonb, $10, $11, $12, $13, $14)
            """, task.id, task.title, task.description, task.status, task.priority,
                task.parent_id, task.tenant_id, json.dumps(task.tags), json.dumps(task.metadata),
                task.created_at, task.updated_at, task.completed_at, task.due_date, task.assignee)
        return task

    async def get_task(self, task_id: str, tenant_id: str = "default") -> Optional[Task]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM tasks WHERE id = $1 AND tenant_id = $2", task_id, tenant_id
            )
            if row:
                return self._row_to_task(row)
        return None

    async def list_tasks(self, tenant_id: str = "default", parent_id: Optional[str] = None,
                         status: Optional[TaskStatus] = None) -> List[Task]:
        query = "SELECT * FROM tasks WHERE tenant_id = $1"
        params = [tenant_id]
        idx = 2
        if parent_id is not None:
            query += f" AND parent_id = ${idx}"
            params.append(parent_id)
            idx += 1
        if status is not None:
            query += f" AND status = ${idx}"
            params.append(status.value if isinstance(status, TaskStatus) else status)
            idx += 1
        query += " ORDER BY created_at ASC"
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [self._row_to_task(row) for row in rows]

    async def update_task(self, task: Task) -> Task:
        task.updated_at = datetime.utcnow()
        async with self._pool.acquire() as conn:
            await conn.execute("""
                UPDATE tasks SET title=$2, description=$3, status=$4, priority=$5, parent_id=$6,
                    tags=$7::jsonb, metadata=$8::jsonb, updated_at=$9, completed_at=$10,
                    due_date=$11, assignee=$12
                WHERE id=$1 AND tenant_id=$13
            """, task.id, task.title, task.description, task.status, task.priority,
                task.parent_id, json.dumps(task.tags), json.dumps(task.metadata),
                task.updated_at, task.completed_at, task.due_date, task.assignee, task.tenant_id)
        return task

    async def delete_task(self, task_id: str, tenant_id: str = "default") -> bool:
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM tasks WHERE id = $1 AND tenant_id = $2", task_id, tenant_id
            )
            await conn.execute(
                "DELETE FROM task_dependencies WHERE task_id = $1 OR depends_on_task_id = $1", task_id
            )
            return result == "DELETE 1"

    async def bulk_upsert_tasks(self, tasks: List[Task]) -> List[Task]:
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                for task in tasks:
                    task.updated_at = datetime.utcnow()
                    await conn.execute("""
                        INSERT INTO tasks (id, title, description, status, priority, parent_id, tenant_id,
                                           tags, metadata, created_at, updated_at, completed_at, due_date, assignee)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9::jsonb, $10, $11, $12, $13, $14)
                        ON CONFLICT (id) DO UPDATE SET
                            title=EXCLUDED.title, description=EXCLUDED.description,
                            status=EXCLUDED.status, priority=EXCLUDED.priority,
                            parent_id=EXCLUDED.parent_id, tags=EXCLUDED.tags,
                            metadata=EXCLUDED.metadata, updated_at=EXCLUDED.updated_at,
                            completed_at=EXCLUDED.completed_at, due_date=EXCLUDED.due_date,
                            assignee=EXCLUDED.assignee
                    """, task.id, task.title, task.description, task.status, task.priority,
                        task.parent_id, task.tenant_id, json.dumps(task.tags), json.dumps(task.metadata),
                        task.created_at, task.updated_at, task.completed_at, task.due_date, task.assignee)
        return tasks

    async def add_dependency(self, task_id: str, depends_on_task_id: str) -> TaskDependency:
        dep = TaskDependency(task_id=task_id, depends_on_task_id=depends_on_task_id)
        async with self._pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO task_dependencies (task_id, depends_on_task_id, created_at)
                VALUES ($1, $2, $3)
                ON CONFLICT DO NOTHING
            """, dep.task_id, dep.depends_on_task_id, dep.created_at)
        return dep

    async def get_dependencies(self, task_id: str) -> List[str]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT depends_on_task_id FROM task_dependencies WHERE task_id = $1", task_id
            )
            return [row['depends_on_task_id'] for row in rows]

    async def get_dependents(self, task_id: str) -> List[str]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT task_id FROM task_dependencies WHERE depends_on_task_id = $1", task_id
            )
            return [row['task_id'] for row in rows]

    async def remove_dependency(self, task_id: str, depends_on_task_id: str) -> bool:
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM task_dependencies WHERE task_id = $1 AND depends_on_task_id = $2",
                task_id, depends_on_task_id
            )
            return result == "DELETE 1"

    async def get_ready_tasks(self, tenant_id: str = "default") -> List[Task]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT t.* FROM tasks t
                WHERE t.tenant_id = $1
                  AND t.status = 'pending'
                  AND NOT EXISTS (
                      SELECT 1 FROM task_dependencies td
                      JOIN tasks dep ON dep.id = td.depends_on_task_id
                      WHERE td.task_id = t.id
                        AND dep.status != 'completed'
                  )
                ORDER BY t.created_at ASC
            """, tenant_id)
            return [self._row_to_task(row) for row in rows]


# ─────────────────────────────────────────────
# Event System
# ─────────────────────────────────────────────

class EventSystem:
    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}
        self._event_history: List[TaskEvent] = []

    def on(self, event_type: str, handler: Callable):
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def off(self, event_type: str, handler: Callable):
        if event_type in self._handlers:
            self._handlers[event_type] = [h for h in self._handlers[event_type] if h != handler]

    async def emit(self, event: TaskEvent):
        self._event_history.append(event)
        handlers = self._handlers.get(event.event_type, []) + self._handlers.get("*", [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception:
                pass

    def get_history(self, event_type: Optional[str] = None) -> List[TaskEvent]:
        if event_type:
            return [e for e in self._event_history if e.event_type == event_type]
        return list(self._event_history)


# ─────────────────────────────────────────────
# Core TodoToolset
# ─────────────────────────────────────────────

class TodoToolset:
    def __init__(
        self,
        storage=None,
        tenant_id: str = "default",
        event_system: Optional[EventSystem] = None,
    ):
        self._storage = storage or InMemoryStorage()
        self._tenant_id = tenant_id
        self._events = event_system or EventSystem()

    @property
    def storage(self):
        return self._storage

    @property
    def tenant_id(self) -> str:
        return self._tenant_id

    @property
    def events(self) -> EventSystem:
        return self._events

    async def initialize(self):
        await self._storage.initialize()

    async def close(self):
        await self._storage.close()

    # ── Task CRUD ──────────────────────────────

    async def list_tasks(
        self,
        hierarchical: bool = False,
        status: Optional[TaskStatus] = None,
        parent_id: Optional[str] = None,
    ) -> List[Task]:
        if hierarchical:
            return await self._list_hierarchical(status=status)
        tasks = await self._storage.list_tasks(
            tenant_id=self._tenant_id,
            parent_id=parent_id,
            status=status,
        )
        return tasks

    async def _list_hierarchical(self, status: Optional[TaskStatus] = None) -> List[Task]:
        all_tasks = await self._storage.list_tasks(tenant_id=self._tenant_id, status=status)
        root_tasks = [t for t in all_tasks if t.parent_id is None]
        ordered: List[Task] = []

        def collect(task: Task, depth: int = 0):
            task.metadata["_depth"] = depth
            ordered.append(task)
            children = [t for t in all_tasks if t.parent_id == task.id]
            for child in sorted(children, key=lambda t: t.created_at):
                collect(child, depth + 1)

        for root in sorted(root_tasks, key=lambda t: t.created_at):
            collect(root)
        return ordered

    async def add_task(
        self,
        title: str,
        description: Optional[str] = None,
        priority: TaskPriority = TaskPriority.MEDIUM,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        due_date: Optional[datetime] = None,
        assignee: Optional[str] = None,
    ) -> Task:
        task = Task(
            title=title,
            description=description,
            priority=priority,
            tenant_id=self._tenant_id,
            tags=tags or [],
            metadata=metadata or {},
            due_date=due_date,
            assignee=assignee,
        )
        task = await self._storage.create_task(task)
        await self._events.emit(TaskEvent(
            event_type="task.created",
            task_id=task.id,
            tenant_id=self._tenant_id,
            payload=task.dict(),
        ))
        return task

    async def get_task(self, task_id: str) -> Optional[Task]:
        return await self._storage.get_task(task_id, self._tenant_id)

    async def update_task_status(self, task_id: str, status: TaskStatus) -> Optional[Task]:
        task = await self._storage.get_task(task_id, self._tenant_id)
        if task is None:
            return None
        old_status = task.status
        task.status = status.value if isinstance(status, TaskStatus) else status
        if task.status == TaskStatus.COMPLETED:
            task.completed_at = datetime.utcnow()
        task = await self._storage.update_task(task)
        await self._events.emit(TaskEvent(
            event_type="task.status_changed",
            task_id=task.id,
            tenant_id=self._tenant_id,
            payload={"old_status": old_status, "new_status": task.status},
        ))
        return task

    async def update_task(self, task_id: str, **kwargs) -> Optional[Task]:
        task = await self._storage.get_task(task_id, self._tenant_id)
        if task is None:
            return None
        for key, value in kwargs.items():
            if hasattr(task, key):
                setattr(task, key, value)
        task = await self._storage.update_task(task)
        await self._events.emit(TaskEvent(
            event_type="task.updated",
            task_id=task.id,
            tenant_id=self._tenant_id,
            payload={"updated_fields": list(kwargs.keys())},
        ))
        return task

    async def delete_task(self, task_id: str) -> bool:
        task = await self._storage.get_task(task_id, self._tenant_id)
        if task is None:
            return False
        # Delete children first
        children = await self._storage.list_tasks(tenant_id=self._tenant_id, parent_id=task_id)
        for child in children:
            await self.delete_task(child.id)
        result = await self._storage.delete_task(task_id, self._tenant_id)
        if result:
            await self._events.emit(TaskEvent(
                event_type="task.deleted",
                task_id=task_id,
                tenant_id=self._tenant_id,
                payload={"task_id": task_id},
            ))
        return result

    async def bulk_write_tasks(self, tasks_data: List[Dict[str, Any]]) -> List[Task]:
        tasks = []
        for data in tasks_data:
            if "id" not in data:
                data["id"] = str(uuid.uuid4())
            data.setdefault("tenant_id", self._tenant_id)
            tasks.append(Task(**data))
        result = await self._storage.bulk_upsert_tasks(tasks)
        await self._events.emit(TaskEvent(
            event_type="tasks.bulk_upserted",
            task_id="bulk",
            tenant_id=self._tenant_id,
            payload={"count": len(result)},
        ))
        return result

    # ── Subtasks ───────────────────────────────

    async def create_child_task(
        self,
        parent_id: str,
        title: str,
        description: Optional[str] = None,
        priority: TaskPriority = TaskPriority.MEDIUM,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        due_date: Optional[datetime] = None,
        assignee: Optional[str] = None,
    ) -> Optional[Task]:
        parent = await self._storage.get_task(parent_id, self._tenant_id)
        if parent is None:
            return None
        task = Task(
            title=title,
            description=description,
            priority=priority,
            parent_id=parent_id,
            tenant_id=self._tenant_id,
            tags=tags or [],
            metadata=metadata or {},
            due_date=due_date,
            assignee=assignee,
        )
        task = await self._storage.create_task(task)
        await self._events.emit(TaskEvent(
            event_type="task.child_created",
            task_id=task.id,
            tenant_id=self._tenant_id,
            payload={"parent_id": parent_id, "child_id": task.id},
        ))
        return task

    async def get_children(self, parent_id: str) -> List[Task]:
        return await self._storage.list_tasks(tenant_id=self._tenant_id, parent_id=parent_id)

    # ── Dependencies ───────────────────────────

    async def link_dependency(self, task_id: str, depends_on_task_id: str) -> Optional[TaskDependency]:
        task = await self._storage.get_task(task_id, self._tenant_id)
        dep_task = await self._storage.get_task(depends_on_task_id, self._tenant_id)
        if task is None or dep_task is None:
            return None
        # Prevent self-dependency
        if task_id == depends_on_task_id:
            raise ValueError("A task cannot depend on itself")
        # Check for circular dependency
        if await self._would_create_cycle(task_id, depends_on_task_id):
            raise ValueError(f"Adding dependency would create a circular dependency")
        dep = await self._storage.add_dependency(task_id, depends_on_task_id)
        await self._events.emit(TaskEvent(
            event_type="task.dependency_linked",
            task_id=task_id,
            tenant_id=self._tenant_id,
            payload={"task_id": task_id, "depends_on": depends_on_task_id},
        ))
        return dep

    async def _would_create_cycle(self, task_id: str, new_dep_id: str) -> bool:
        visited = set()
        stack = [new_dep_id]
        while stack:
            current = stack.pop()
            if current == task_id:
                return True
            if current in visited:
                continue
            visited.add(current)
            deps = await self._storage.get_dependencies(current)
            stack.extend(deps)
        return False

    async def unlink_dependency(self, task_id: str, depends_on_task_id: str) -> bool:
        result = await self._storage.remove_dependency(task_id, depends_on_task_id)
        if result:
            await self._events.emit(TaskEvent(
                event_type="task.dependency_unlinked",
                task_id=task_id,
                tenant_id=self._tenant_id,
                payload={"task_id": task_id, "depends_on": depends_on_task_id},
            ))
        return result

    async def get_dependencies(self, task_id: str) -> List[Task]:
        dep_ids = await self._storage.get_dependencies(task_id)
        tasks = []
        for dep_id in dep_ids:
            t = await self._storage.get_task(dep_id, self._tenant_id)
            if t:
                tasks.append(t)
        return tasks

    async def get_dependents(self, task_id: str) -> List[Task]:
        dep_ids = await self._storage.get_dependents(task_id)
        tasks = []
        for dep_id in dep_ids:
            t = await self._storage.get_task(dep_id, self._tenant_id)
            if t:
                tasks.append(t)
        return tasks

    # ── Ready Tasks ────────────────────────────

    async def list_ready_tasks(self) -> List[Task]:
        return await self._storage.get_ready_tasks(self._tenant_id)

    # ── Summary ────────────────────────────────

    async def get_summary(self) -> Dict[str, Any]:
        all_tasks = await self._storage.list_tasks(tenant_id=self._tenant_id)
        status_counts: Dict[str, int] = {}
        for task in all_tasks:
            status_counts[task.status] = status_counts.get(task.status, 0) + 1
        ready = await self.list_ready_tasks()
        return {
            "total": len(all_tasks),
            "by_status": status_counts,
            "ready_to_work": len(ready),
        }


# ─────────────────────────────────────────────
# Pydantic AI Tool Definitions
# ─────────────────────────────────────────────

def create_todo_tools(toolset: TodoToolset) -> List[Dict[str, Any]]:
    """
    Returns a list of tool definitions compatible with Pydantic AI agents.
    Each tool is a dict with 'name', 'description', and 'function'.
    """

    async def list_tasks_tool(
        hierarchical: bool = False,
        status: Optional[str] = None,
        parent_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List all tasks. Supports hierarchical view, filtering by status and parent."""
        task_status = TaskStatus(status) if status else None
        tasks = await toolset.list_tasks(
            hierarchical=hierarchical,
            status=task_status,
            parent_id=parent_id,
        )
        return [t.dict() for t in tasks]

    async def add_task_tool(
        title: str,
        description: Optional[str] = None,
        priority: str = "medium",
        tags: Optional[List[str]] = None,
        assignee: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Add a single new task."""
        task = await toolset.add_task(
            title=title,
            description=description,
            priority=TaskPriority(priority),
            tags=tags,
            assignee=assignee,
        )
        return task.dict()

    async def update_task_status_tool(task_id: str, status: str) -> Optional[Dict[str, Any]]:
        """Update the status of a task by its ID."""
        task = await toolset.update_task_status(task_id, TaskStatus(status))
        return task.dict() if task else None

    async def delete_task_tool(task_id: str) -> bool:
        """Delete a task by its ID (also deletes children)."""
        return await toolset.delete_task(task_id)

    async def bulk_write_tasks_tool(tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Bulk create or update tasks."""
        result = await toolset.bulk_write_tasks(tasks)
        return [t.dict() for t in result]

    async def create_child_task_tool(
        parent_id: str,
        title: str,
        description: Optional[str] = None,
        priority: str = "medium",
        assignee: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Create a child (sub) task under a parent task."""
        task = await toolset.create_child_task(
            parent_id=parent_id,
            title=title,
            description=description,
            priority=TaskPriority(priority),
            assignee=assignee,
        )
        return task.dict() if task else None

    async def link_dependency_tool(task_id: str, depends_on_task_id: str) -> Optional[Dict[str, Any]]:
        """Link two tasks with a dependency relationship."""
        dep = await toolset.link_dependency(task_id, depends_on_task_id)
        return dep.dict() if dep else None

    async def list_ready_tasks_tool() -> List[Dict[str, Any]]:
        """List all tasks that are ready to work on (pending with all dependencies completed)."""
        tasks = await toolset.list_ready_tasks()
        return [t.dict() for t in tasks]

    async def get_task_tool(task_id: str) -> Optional[Dict[str, Any]]:
        """Get a single task by its ID."""
        task = await toolset.get_task(task_id)
        return task.dict() if task else None

    async def get_summary_tool() -> Dict[str, Any]:
        """Get a summary of all tasks including counts by status."""
        return await toolset.get_summary()

    return [
        {"name": "list_tasks", "description": "List all tasks with optional hierarchical view", "function": list_tasks_tool},
        {"name": "add_task", "description": "Add a single new task", "function": add_task_tool},
        {"name": "update_task_status", "description": "Update task status by ID", "function": update_task_status_tool},
        {"name": "delete_task", "description": "Delete a task by ID", "function": delete_task_tool},
        {"name": "bulk_write_tasks", "description": "Bulk create or update tasks", "function": bulk_write_tasks_tool},
        {"name": "create_child_task", "description": "Create a child subtask under a parent", "function": create_child_task_tool},
        {"name": "link_dependency", "description": "Link tasks with a dependency", "function": link_dependency_tool},
        {"name": "list_ready_tasks", "description": "List tasks ready to work on", "function": list_ready_tasks_tool},
        {"name": "get_task", "description": "Get a single task by ID", "function": get_task_tool},
        {"name": "get_summary", "description": "Get task summary statistics", "function": get_summary_tool},
    ]


# ─────────────────────────────────────────────
# Factory helpers
# ─────────────────────────────────────────────

def create_in_memory_toolset(tenant_id: str = "default") -> TodoToolset:
    storage = InMemoryStorage()
    return TodoToolset(storage=storage, tenant_id=tenant_id)


def create_postgres_toolset(dsn: str, tenant_id: str = "default") -> TodoToolset:
    storage = PostgreSQLStorage(dsn=dsn)
    return TodoToolset(storage=storage, tenant_id=tenant_id)


# ─────────────────────────────────────────────
# Context manager support
# ─────────────────────────────────────────────

class TodoToolsetContext:
    def __init__(self, toolset: TodoToolset):
        self._toolset = toolset

    async def __aenter__(self) -> TodoToolset:
        await self._toolset.initialize()
        return self._toolset

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._toolset.close()


def todo_toolset_context(toolset: TodoToolset) -> TodoToolsetContext:
    return TodoToolsetContext(toolset)


# ─────────────────────────────────────────────
# Pydantic AI Agent Integration (if available)
# ─────────────────────────────────────────────

if HAS_PYDANTIC_AI:
    def register_tools_with_agent(agent: Agent, toolset: TodoToolset):
        tools = create_todo_tools(toolset)
        for tool_def in tools:
            agent.tool(tool_def["function"])