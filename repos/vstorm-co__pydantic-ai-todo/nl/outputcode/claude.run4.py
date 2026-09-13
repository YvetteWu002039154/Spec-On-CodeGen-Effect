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
    tenant_id: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    assignee: Optional[str] = None
    tags: Optional[List[str]] = None
    parent_id: Optional[str] = None


# ─────────────────────────────────────────────
# In-Memory Storage Backend
# ─────────────────────────────────────────────

class InMemoryStorage:
    def __init__(self):
        self._tasks: Dict[str, Task] = {}
        self._dependencies: List[TaskDependency] = []

    async def save_task(self, task: Task) -> Task:
        task.updated_at = datetime.utcnow()
        self._tasks[task.id] = task
        return task

    async def get_task(self, task_id: str, tenant_id: str = "default") -> Optional[Task]:
        task = self._tasks.get(task_id)
        if task and task.tenant_id == tenant_id:
            return task
        return None

    async def list_tasks(self, filter: Optional[TaskFilter] = None) -> List[Task]:
        tasks = list(self._tasks.values())
        if filter:
            if filter.tenant_id:
                tasks = [t for t in tasks if t.tenant_id == filter.tenant_id]
            if filter.status:
                tasks = [t for t in tasks if t.status == filter.status]
            if filter.priority:
                tasks = [t for t in tasks if t.priority == filter.priority]
            if filter.assignee:
                tasks = [t for t in tasks if t.assignee == filter.assignee]
            if filter.tags:
                tasks = [t for t in tasks if any(tag in t.tags for tag in filter.tags)]
            if filter.parent_id is not None:
                tasks = [t for t in tasks if t.parent_id == filter.parent_id]
        return tasks

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
        dep = TaskDependency(task_id=task_id, depends_on_id=depends_on_id)
        self._dependencies.append(dep)
        return dep

    async def get_dependencies(self, task_id: str) -> List[TaskDependency]:
        return [d for d in self._dependencies if d.task_id == task_id]

    async def get_dependents(self, task_id: str) -> List[TaskDependency]:
        return [d for d in self._dependencies if d.depends_on_id == task_id]

    async def remove_dependency(self, task_id: str, depends_on_id: str) -> bool:
        before = len(self._dependencies)
        self._dependencies = [
            d for d in self._dependencies
            if not (d.task_id == task_id and d.depends_on_id == depends_on_id)
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
    def __init__(self, dsn: str):
        if not HAS_ASYNCPG:
            raise ImportError("asyncpg is required for PostgreSQL storage. Install it with: pip install asyncpg")
        self.dsn = dsn
        self._pool: Optional[Any] = None

    async def connect(self):
        self._pool = await asyncpg.create_pool(self.dsn)
        await self._create_tables()

    async def disconnect(self):
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
                    completed_at TIMESTAMPTZ,
                    due_date TIMESTAMPTZ,
                    assignee TEXT
                );
                
                CREATE TABLE IF NOT EXISTS task_dependencies (
                    task_id TEXT NOT NULL,
                    depends_on_id TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    PRIMARY KEY (task_id, depends_on_id)
                );
                
                CREATE INDEX IF NOT EXISTS idx_tasks_tenant_id ON tasks(tenant_id);
                CREATE INDEX IF NOT EXISTS idx_tasks_parent_id ON tasks(parent_id);
                CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
            """)

    def _row_to_task(self, row) -> Task:
        data = dict(row)
        if isinstance(data.get('tags'), str):
            data['tags'] = json.loads(data['tags'])
        if isinstance(data.get('metadata'), str):
            data['metadata'] = json.loads(data['metadata'])
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
                task.parent_id, task.tenant_id,
                json.dumps(task.tags), json.dumps(task.metadata),
                task.created_at, task.updated_at, task.completed_at,
                task.due_date, task.assignee
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

    async def list_tasks(self, filter: Optional[TaskFilter] = None) -> List[Task]:
        conditions = []
        params = []
        idx = 1

        if filter:
            if filter.tenant_id:
                conditions.append(f"tenant_id = ${idx}")
                params.append(filter.tenant_id)
                idx += 1
            if filter.status:
                conditions.append(f"status = ${idx}")
                params.append(filter.status)
                idx += 1
            if filter.priority:
                conditions.append(f"priority = ${idx}")
                params.append(filter.priority)
                idx += 1
            if filter.assignee:
                conditions.append(f"assignee = ${idx}")
                params.append(filter.assignee)
                idx += 1
            if filter.parent_id is not None:
                conditions.append(f"parent_id = ${idx}")
                params.append(filter.parent_id)
                idx += 1

        query = "SELECT * FROM tasks"
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY created_at ASC"

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [self._row_to_task(row) for row in rows]

    async def delete_task(self, task_id: str, tenant_id: str = "default") -> bool:
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM tasks WHERE id = $1 AND tenant_id = $2",
                task_id, tenant_id
            )
            await conn.execute(
                "DELETE FROM task_dependencies WHERE task_id = $1 OR depends_on_id = $1",
                task_id
            )
            return result == "DELETE 1"

    async def add_dependency(self, task_id: str, depends_on_id: str) -> TaskDependency:
        dep = TaskDependency(task_id=task_id, depends_on_id=depends_on_id)
        async with self._pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO task_dependencies (task_id, depends_on_id, created_at)
                VALUES ($1, $2, $3)
                ON CONFLICT DO NOTHING
            """, task_id, depends_on_id, dep.created_at)
        return dep

    async def get_dependencies(self, task_id: str) -> List[TaskDependency]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM task_dependencies WHERE task_id = $1",
                task_id
            )
            return [TaskDependency(**dict(row)) for row in rows]

    async def get_dependents(self, task_id: str) -> List[TaskDependency]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM task_dependencies WHERE depends_on_id = $1",
                task_id
            )
            return [TaskDependency(**dict(row)) for row in rows]

    async def remove_dependency(self, task_id: str, depends_on_id: str) -> bool:
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM task_dependencies WHERE task_id = $1 AND depends_on_id = $2",
                task_id, depends_on_id
            )
            return result == "DELETE 1"

    async def bulk_save_tasks(self, tasks: List[Task]) -> List[Task]:
        saved = []
        for task in tasks:
            saved.append(await self.save_task(task))
        return saved


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
            self._handlers[event_type] = [
                h for h in self._handlers[event_type] if h != handler
            ]

    async def emit(self, event: TaskEvent):
        self._event_history.append(event)
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
        history = self._event_history
        if event_type:
            history = [e for e in history if e.event_type == event_type]
        return history[-limit:]

    def clear_history(self):
        self._event_history.clear()


# ─────────────────────────────────────────────
# Core TodoToolset
# ─────────────────────────────────────────────

class TodoToolset:
    def __init__(
        self,
        storage: Optional[Any] = None,
        tenant_id: str = "default",
        event_system: Optional[EventSystem] = None,
    ):
        self.storage = storage or InMemoryStorage()
        self.tenant_id = tenant_id
        self.events = event_system or EventSystem()

    # ── Internal helpers ──────────────────────

    async def _emit(self, event_type: str, task: Task, extra: Optional[Dict] = None):
        payload = {"task": task.dict()}
        if extra:
            payload.update(extra)
        event = TaskEvent(
            event_type=event_type,
            task_id=task.id,
            tenant_id=task.tenant_id,
            payload=payload,
        )
        await self.events.emit(event)

    # ── Public API ────────────────────────────

    async def list_tasks(
        self,
        hierarchical: bool = False,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        assignee: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """List all tasks, optionally as a hierarchical tree."""
        filter = TaskFilter(
            tenant_id=self.tenant_id,
            status=TaskStatus(status) if status else None,
            priority=TaskPriority(priority) if priority else None,
            assignee=assignee,
            tags=tags,
        )
        tasks = await self.storage.list_tasks(filter)

        if not hierarchical:
            return {"tasks": [t.dict() for t in tasks], "count": len(tasks)}

        task_map: Dict[str, Dict] = {t.id: {**t.dict(), "children": []} for t in tasks}
        roots = []
        for task in tasks:
            if task.parent_id and task.parent_id in task_map:
                task_map[task.parent_id]["children"].append(task_map[task.id])
            else:
                roots.append(task_map[task.id])

        return {"tasks": roots, "count": len(tasks)}

    async def add_task(
        self,
        title: str,
        description: Optional[str] = None,
        priority: str = "medium",
        tags: Optional[List[str]] = None,
        assignee: Optional[str] = None,
        due_date: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Add a single task."""
        task = Task(
            title=title,
            description=description,
            priority=TaskPriority(priority),
            tags=tags or [],
            assignee=assignee,
            due_date=due_date,
            metadata=metadata or {},
            tenant_id=self.tenant_id,
        )
        saved = await self.storage.save_task(task)
        await self._emit("task.created", saved)
        return {"task": saved.dict(), "success": True}

    async def bulk_write_tasks(self, tasks_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Bulk create or update tasks."""
        tasks = []
        for data in tasks_data:
            data.setdefault("tenant_id", self.tenant_id)
            task = Task(**data)
            tasks.append(task)

        saved = await self.storage.bulk_save_tasks(tasks)
        for task in saved:
            await self._emit("task.bulk_saved", task)

        return {
            "tasks": [t.dict() for t in saved],
            "count": len(saved),
            "success": True,
        }

    async def update_task_status(
        self,
        task_id: str,
        status: str,
    ) -> Dict[str, Any]:
        """Update the status of a task by ID."""
        task = await self.storage.get_task(task_id, self.tenant_id)
        if not task:
            return {"success": False, "error": f"Task {task_id} not found"}

        old_status = task.status
        task.status = TaskStatus(status)
        if task.status == TaskStatus.COMPLETED:
            task.completed_at = datetime.utcnow()
        elif old_status == TaskStatus.COMPLETED:
            task.completed_at = None

        saved = await self.storage.save_task(task)
        await self._emit("task.status_updated", saved, {"old_status": old_status, "new_status": status})
        return {"task": saved.dict(), "success": True}

    async def update_task(
        self,
        task_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        assignee: Optional[str] = None,
        tags: Optional[List[str]] = None,
        due_date: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Update any field of a task."""
        task = await self.storage.get_task(task_id, self.tenant_id)
        if not task:
            return {"success": False, "error": f"Task {task_id} not found"}

        if title is not None:
            task.title = title
        if description is not None:
            task.description = description
        if status is not None:
            task.status = TaskStatus(status)
            if task.status == TaskStatus.COMPLETED:
                task.completed_at = datetime.utcnow()
        if priority is not None:
            task.priority = TaskPriority(priority)
        if assignee is not None:
            task.assignee = assignee
        if tags is not None:
            task.tags = tags
        if due_date is not None:
            task.due_date = due_date
        if metadata is not None:
            task.metadata.update(metadata)

        saved = await self.storage.save_task(task)
        await self._emit("task.updated", saved)
        return {"task": saved.dict(), "success": True}

    async def delete_task(self, task_id: str) -> Dict[str, Any]:
        """Delete a task by ID."""
        task = await self.storage.get_task(task_id, self.tenant_id)
        if not task:
            return {"success": False, "error": f"Task {task_id} not found"}

        deleted = await self.storage.delete_task(task_id, self.tenant_id)
        if deleted:
            await self._emit("task.deleted", task)
            return {"success": True, "task_id": task_id}
        return {"success": False, "error": "Failed to delete task"}

    async def create_child_task(
        self,
        parent_id: str,
        title: str,
        description: Optional[str] = None,
        priority: str = "medium",
        tags: Optional[List[str]] = None,
        assignee: Optional[str] = None,
        due_date: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a child task under a parent task."""
        parent = await self.storage.get_task(parent_id, self.tenant_id)
        if not parent:
            return {"success": False, "error": f"Parent task {parent_id} not found"}

        task = Task(
            title=title,
            description=description,
            priority=TaskPriority(priority),
            tags=tags or [],
            assignee=assignee,
            due_date=due_date,
            metadata=metadata or {},
            tenant_id=self.tenant_id,
            parent_id=parent_id,
        )
        saved = await self.storage.save_task(task)
        await self._emit("task.child_created", saved, {"parent_id": parent_id})
        return {"task": saved.dict(), "parent": parent.dict(), "success": True}

    async def link_dependency(
        self,
        task_id: str,
        depends_on_id: str,
    ) -> Dict[str, Any]:
        """Link two tasks with a dependency (task_id depends on depends_on_id)."""
        task = await self.storage.get_task(task_id, self.tenant_id)
        if not task:
            return {"success": False, "error": f"Task {task_id} not found"}

        dep_task = await self.storage.get_task(depends_on_id, self.tenant_id)
        if not dep_task:
            return {"success": False, "error": f"Dependency task {depends_on_id} not found"}

        if task_id == depends_on_id:
            return {"success": False, "error": "A task cannot depend on itself"}

        dep = await self.storage.add_dependency(task_id, depends_on_id)

        if task.status == TaskStatus.PENDING and dep_task.status not in (
            TaskStatus.COMPLETED, TaskStatus.CANCELLED
        ):
            task.status = TaskStatus.BLOCKED
            await self.storage.save_task(task)

        event = TaskEvent(
            event_type="task.dependency_linked",
            task_id=task_id,
            tenant_id=self.tenant_id,
            payload={"task_id": task_id, "depends_on_id": depends_on_id},
        )
        await self.events.emit(event)
        return {
            "dependency": dep.dict(),
            "task": task.dict(),
            "depends_on": dep_task.dict(),
            "success": True,
        }

    async def unlink_dependency(self, task_id: str, depends_on_id: str) -> Dict[str, Any]:
        """Remove a dependency link between two tasks."""
        removed = await self.storage.remove_dependency(task_id, depends_on_id)
        if removed:
            event = TaskEvent(
                event_type="task.dependency_unlinked",
                task_id=task_id,
                tenant_id=self.tenant_id,
                payload={"task_id": task_id, "depends_on_id": depends_on_id},
            )
            await self.events.emit(event)
            return {"success": True}
        return {"success": False, "error": "Dependency not found"}

    async def list_ready_tasks(self) -> Dict[str, Any]:
        """List tasks that are ready to work on (no unresolved dependencies)."""
        filter = TaskFilter(tenant_id=self.tenant_id)
        all_tasks = await self.storage.list_tasks(filter)

        ready = []
        for task in all_tasks:
            if task.status not in (TaskStatus.PENDING, TaskStatus.BLOCKED):
                continue

            deps = await self.storage.get_dependencies(task.id)
            if not deps:
                if task.status == TaskStatus.PENDING:
                    ready.append(task)
                continue

            all_resolved = True
            for dep in deps:
                dep_task = await self.storage.get_task(dep.depends_on_id, self.tenant_id)
                if dep_task and dep_task.status not in (TaskStatus.COMPLETED, TaskStatus.CANCELLED):
                    all_resolved = False
                    break

            if all_resolved:
                if task.status == TaskStatus.BLOCKED:
                    task.status = TaskStatus.PENDING
                    await self.storage.save_task(task)
                ready.append(task)

        return {"tasks": [t.dict() for t in ready], "count": len(ready)}

    async def get_task(self, task_id: str) -> Dict[str, Any]:
        """Get a single task by ID."""
        task = await self.storage.get_task(task_id, self.tenant_id)
        if not task:
            return {"success": False, "error": f"Task {task_id} not found"}
        return {"task": task.dict(), "success": True}

    async def get_task_with_subtasks(self, task_id: str) -> Dict[str, Any]:
        """Get a task along with all its subtasks."""
        task = await self.storage.get_task(task_id, self.tenant_id)
        if not task:
            return {"success": False, "error": f"Task {task_id} not found"}

        filter = TaskFilter(tenant_id=self.tenant_id, parent_id=task_id)
        subtasks = await self.storage.list_tasks(filter)

        deps = await self.storage.get_dependencies(task_id)
        dependents = await self.storage.get_dependents(task_id)

        return {
            "task": task.dict(),
            "subtasks": [t.dict() for t in subtasks],
            "dependencies": [d.dict() for d in deps],
            "dependents": [d.dict() for d in dependents],
            "success": True,
        }

    async def complete_task(self, task_id: str) -> Dict[str, Any]:
        """Mark a task as completed and unblock dependent tasks."""
        result = await self.update_task_status(task_id, TaskStatus.COMPLETED)
        if not result.get("success"):
            return result

        dependents = await self.storage.get_dependents(task_id)
        unblocked = []
        for dep in dependents:
            dep_task = await self.storage.get_task(dep.task_id, self.tenant_id)
            if dep_task and dep_task.status == TaskStatus.BLOCKED:
                all_deps = await self.storage.get_dependencies(dep_task.id)
                all_resolved = True
                for d in all_deps:
                    dt = await self.storage.get_task(d.depends_on_id, self.tenant_id)
                    if dt and dt.status not in (TaskStatus.COMPLETED, TaskStatus.CANCELLED):
                        all_resolved = False
                        break
                if all_resolved:
                    dep_task.status = TaskStatus.PENDING
                    await self.storage.save_task(dep_task)
                    await self._emit("task.unblocked", dep_task)
                    unblocked.append(dep_task.dict())

        result["unblocked_tasks"] = unblocked
        return result

    def on_event(self, event_type: str, handler: Callable):
        """Register an event handler."""
        self.events.on(event_type, handler)

    def off_event(self, event_type: str, handler: Callable):
        """Unregister an event handler."""
        self.events.off(event_type, handler)

    def get_event_history(self, event_type: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Get event history."""
        return [e.dict() for e in self.events.get_history(event_type, limit)]


# ─────────────────────────────────────────────
# Pydantic AI Integration
# ─────────────────────────────────────────────

def create_todo_tools(toolset: TodoToolset) -> List[Any]:
    """Create a list of tool functions for use with Pydantic AI agents."""

    async def list_tasks(
        hierarchical: bool = False,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        assignee: Optional[str] = None,
    ) -> str:
        """List all tasks. Set hierarchical=True to see parent/child relationships."""
        result = await toolset.list_tasks(
            hierarchical=hierarchical,
            status=status,
            priority=priority,
            assignee=assignee,
        )
        return json.dumps(result, default=str)

    async def add_task(
        title: str,
        description: Optional[str] = None,
        priority: str = "medium",
        assignee: Optional[str] = None,
    ) -> str:
        """Add a new task with the given title and optional details."""
        result = await toolset.add_task(
            title=title,
            description=description,
            priority=priority,
            assignee=assignee,
        )
        return json.dumps(result, default=str)

    async def bulk_write_tasks(tasks_json: str) -> str:
        """Bulk create or update tasks. tasks_json should be a JSON array of task objects."""
        try:
            tasks_data = json.loads(tasks_json)
        except json.JSONDecodeError as e:
            return json.dumps({"success": False, "error": f"Invalid JSON: {e}"})
        result = await toolset.bulk_write_tasks(tasks_data)
        return json.dumps(result, default=str)

    async def update_task_status(task_id: str, status: str) -> str:
        """Update the status of a task. Valid statuses: pending, in_progress, completed, blocked, cancelled."""
        result = await toolset.update_task_status(task_id, status)
        return json.dumps(result, default=str)

    async def delete_task(task_id: str) -> str:
        """Delete a task by its ID."""
        result = await toolset.delete_task(task_id)
        return json.dumps(result, default=str)

    async def create_child_task(
        parent_id: str,
        title: str,
        description: Optional[str] = None,
        priority: str = "medium",
    ) -> str:
        """Create a subtask under an existing parent task."""
        result = await toolset.create_child_task(
            parent_id=parent_id,
            title=title,
            description=description,
            priority=priority,
        )
        return json.dumps(result, default=str)

    async def link_dependency(task_id: str, depends_on_id: str) -> str:
        """Link two tasks so that task_id depends on depends_on_id being completed first."""
        result = await toolset.link_dependency(task_id, depends_on_id)
        return json.dumps(result, default=str)

    async def list_ready_tasks() -> str:
        """List all tasks that are ready to work on (no blocking dependencies)."""
        result = await toolset.list_ready_tasks()
        return json.dumps(result, default=str)

    async def get_task(task_id: str) -> str:
        """Get details of a specific task including its subtasks and dependencies."""
        result = await toolset.get_task_with_subtasks(task_id)
        return json.dumps(result, default=str)

    async def complete_task(task_id: str) -> str:
        """Mark a task as completed and automatically unblock any dependent tasks."""
        result = await toolset.complete_task(task_id)
        return json.dumps(result, default=str)

    return [
        list_tasks,
        add_task,
        bulk_write_tasks,
        update_task_status,
        delete_task,
        create_child_task,
        link_dependency,
        list_ready_tasks,
        get_task,
        complete_task,
    ]


# ─────────────────────────────────────────────
# Factory / Builder
# ─────────────────────────────────────────────

class TodoToolsetBuilder:
    def __init__(self):
        self._storage = None
        self._tenant_id = "default"
        self._event_system = None
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

    def with_event_handler(self, event_type: str, handler: Callable) -> "TodoToolsetBuilder":
        self._event_handlers.append((event_type, handler))
        return self

    def build(self) -> TodoToolset:
        event_system = EventSystem()
        for event_type, handler in self._event_handlers:
            event_system.on(event_type, handler)

        toolset = TodoToolset(
            storage=self._storage,
            tenant_id=self._tenant_id,
            event_system=event_system,
        )
        return toolset

    async def build_async(self) -> TodoToolset:
        toolset = self.build()
        if isinstance(toolset.storage, PostgreSQLStorage):
            await toolset.storage.connect()
        return toolset


# ─────────────────────────────────────────────
# Convenience factory functions
# ─────────────────────────────────────────────

def create_todo_toolset(
    storage_type: str = "memory",
    postgres_dsn: Optional[str] = None,
    tenant_id: str = "default",
) -> TodoToolset:
    """Create a TodoToolset with the specified storage backend."""
    if storage_type == "postgres":
        if not postgres_dsn:
            raise ValueError("postgres_dsn is required for PostgreSQL storage")
        storage = PostgreSQLStorage(postgres_dsn)
    else:
        storage = InMemoryStorage()

    return TodoToolset(storage=storage, tenant_id=tenant_id)


async def create_todo_toolset_async(
    storage_type: str = "memory",
    postgres_dsn: Optional[str] = None,
    tenant_id: str = "default",
) -> TodoToolset:
    """Async version that also initializes the database connection."""
    toolset = create_todo_toolset(storage_type, postgres_dsn, tenant_id)
    if isinstance(toolset.storage, PostgreSQLStorage):
        await toolset.storage.connect()
    return toolset


# ─────────────────────────────────────────────
# Demo / Example usage
# ─────────────────────────────────────────────

async def _demo():
    print("=== Todo Toolset Demo ===\n")

    toolset = await create_todo_toolset_async(tenant_id="demo-tenant")

    def on_task_event(event: TaskEvent):
        print(f"[EVENT] {event.event_type} | task_id={event.task_id}")

    toolset.on_event("*", on_task_event)

    result = await toolset.add_task(
        title="Build the API",
        description="Implement REST endpoints",
        priority="high",
    )
    api_task_id = result["task"]["id"]
    print(f"Created task: {result['task']['title']} ({api_task_id})")

    result = await toolset.add_task(
        title="Write tests",
        description="Unit and integration tests",
        priority="medium",
    )
    test_task_id = result["task"]["id"]
    print(f"Created task: {result['task']['title']} ({test_task_id})")

    result = await toolset.create_child_task(
        parent_id=api_task_id,
        title="Design database schema",
        priority="high",
    )
    schema_task_id = result["task"]["id"]
    print(f"Created child task: {result['task']['title']} ({schema_task_id})")

    result = await toolset.link_dependency(test_task_id, api_task_id)
    print(f"Linked dependency: tests depend on API")

    result = await toolset.list_ready_tasks()
    print(f"\nReady tasks ({result['count']}):")
    for t in result["tasks"]:
        print(f"  - {t['title']} [{t['status']}]")

    result = await toolset.list_tasks(hierarchical=True)
    print(f"\nAll tasks (hierarchical, {result['count']} total):")
    for t in result["tasks"]:
        print(f"  - {t['title']} [{t['status']}]")
        for child in t.get("children", []):
            print(f"    └─ {child['title']} [{child['status']}]")

    result = await toolset.complete_task(api_task_id)
    print(f"\nCompleted: {api_task_id}")
    print(f"Unblocked tasks: {[t['title'] for t in result.get('unblocked_tasks', [])]}")

    result = await toolset.list_ready_tasks()
    print(f"\nReady tasks after completion ({result['count']}):")
    for t in result["tasks"]:
        print(f"  - {t['title']} [{t['status']}]")

    tools = create_todo_tools(toolset)
    print(f"\nCreated {len(tools)} Pydantic AI tools:")
    for tool in tools:
        print(f"  - {tool.__name__}")

    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    asyncio.run(_demo())