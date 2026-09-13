import asyncio
from collections import defaultdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set
from uuid import uuid4

import asyncpg
from pydantic import BaseModel, Field

# ---------- Enums and Models ----------

class TaskStatus(str, Enum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    BLOCKED = "BLOCKED"

class TaskBase(BaseModel):
    title: str
    description: str = ""
    status: TaskStatus = TaskStatus.TODO
    parent_id: Optional[str] = None

class TaskCreate(TaskBase):
    pass  # dependencies added via separate linking

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None

class TaskResponse(TaskBase):
    id: str
    created_at: datetime
    updated_at: datetime
    children: List["TaskResponse"] = []

    class Config:
        orm_mode = True

class TaskDependency(BaseModel):
    dependent_id: str
    dependency_id: str

# ---------- Event System ----------

class EventEmitter:
    """Mixin providing callback and webhook event emission."""

    def __init__(self):
        self._callbacks: Dict[str, List[Callable[..., Coroutine[Any, Any, None]]]] = defaultdict(list)
        self._webhooks: List[str] = []
        self._webhook_session = None  # aiohttp.ClientSession

    def on(self, event: str, callback: Callable[..., Coroutine[Any, Any, None]]) -> None:
        """Register an async callback for the given event."""
        self._callbacks[event].append(callback)

    def off(self, event: str, callback: Callable[..., Coroutine[Any, Any, None]]) -> None:
        """Remove a previously registered callback."""
        if event in self._callbacks:
            self._callbacks[event] = [cb for cb in self._callbacks[event] if cb != callback]

    def add_webhook(self, url: str) -> None:
        """Add a webhook URL to be called on events."""
        self._webhooks.append(url)

    def remove_webhook(self, url: str) -> None:
        """Remove a webhook URL."""
        self._webhooks = [wh for wh in self._webhooks if wh != url]

    async def _emit(self, event: str, payload: Dict[str, Any]) -> None:
        """Fire all registered callbacks and webhooks for the event."""
        for cb in self._callbacks.get(event, []):
            try:
                await cb(payload)
            except Exception:
                # Log error but don't break
                import logging
                logging.exception(f"Callback failed for event {event}")

        # Webhook handling (if session exists)
        if self._webhooks and self._webhook_session:
            for url in self._webhooks:
                try:
                    async with self._webhook_session.post(url, json=payload) as _:
                        pass
                except Exception:
                    import logging
                    logging.exception(f"Webhook failed for URL {url}")

# ---------- Database Helper ----------

def _build_tree(tasks: List[Dict[str, Any]], parent_id: Optional[str] = None) -> List[TaskResponse]:
    """Convert flat task rows into hierarchical TaskResponse objects."""
    children = []
    for row in tasks:
        if row["parent_id"] == parent_id:
            node = TaskResponse(
                id=row["id"],
                title=row["title"],
                description=row["description"],
                status=TaskStatus(row["status"]),
                parent_id=row["parent_id"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                children=[],
            )
            node.children = _build_tree(tasks, node.id)
            children.append(node)
    return children

# ---------- TodoToolset ----------

class TodoToolset(EventEmitter):
    """
    Task planning toolset for Pydantic AI agents.
    Provides hierarchical task management with PostgreSQL storage,
    dependency linking, and an event system.
    """

    def __init__(self, pool: asyncpg.Pool, *, webhook_session: Optional[Any] = None):
        super().__init__()
        self.pool = pool
        self._webhook_session = webhook_session  # aiohttp.ClientSession or None

    async def create_tables(self) -> None:
        """Ensure the required tables exist."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    status TEXT DEFAULT 'TODO',
                    parent_id TEXT,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                );
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS task_dependencies (
                    dependent_id TEXT NOT NULL,
                    dependency_id TEXT NOT NULL,
                    PRIMARY KEY (dependent_id, dependency_id),
                    FOREIGN KEY (dependent_id) REFERENCES tasks(id) ON DELETE CASCADE,
                    FOREIGN KEY (dependency_id) REFERENCES tasks(id) ON DELETE CASCADE
                );
            """)
            # Indexes for common queries
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_tenant ON tasks(tenant_id);")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_parent ON tasks(parent_id);")

    # ----- CRUD Operations -----

    async def list_tasks(self, tenant_id: str, hierarchical: bool = False) -> List[TaskResponse]:
        """Return all tasks for a tenant, optionally as a hierarchy."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, title, description, status, parent_id, created_at, updated_at "
                "FROM tasks WHERE tenant_id = $1 ORDER BY created_at",
                tenant_id,
            )
        if not hierarchical:
            return [TaskResponse(**dict(r)) for r in rows]
        # Build tree
        task_dicts = [dict(r) for r in rows]
        roots = _build_tree(task_dicts, parent_id=None)
        return roots

    async def add_task(self, tenant_id: str, task: TaskCreate) -> TaskResponse:
        """Create a single task and emit a 'task.created' event."""
        task_id = uuid4().hex
        now = datetime.now(timezone.utc)
        async with self.pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO tasks (id, tenant_id, title, description, status, parent_id, created_at, updated_at)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $7)""",
                task_id, tenant_id, task.title, task.description, task.status.value, task.parent_id, now,
            )
        new_task = TaskResponse(
            id=task_id,
            title=task.title,
            description=task.description,
            status=task.status,
            parent_id=task.parent_id,
            created_at=now,
            updated_at=now,
        )
        await self._emit("task.created", new_task.dict())
        return new_task

    async def bulk_write_tasks(self, tenant_id: str, tasks: List[TaskCreate]) -> List[TaskResponse]:
        """Create multiple tasks in bulk. Returns the newly created tasks."""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                results = []
                for task in tasks:
                    task_id = uuid4().hex
                    now = datetime.now(timezone.utc)
                    await conn.execute(
                        """INSERT INTO tasks (id, tenant_id, title, description, status, parent_id, created_at, updated_at)
                           VALUES ($1, $2, $3, $4, $5, $6, $7, $7)""",
                        task_id, tenant_id, task.title, task.description, task.status.value, task.parent_id, now,
                    )
                    new_task = TaskResponse(
                        id=task_id,
                        title=task.title,
                        description=task.description,
                        status=task.status,
                        parent_id=task.parent_id,
                        created_at=now,
                        updated_at=now,
                    )
                    results.append(new_task)
                    await self._emit("task.created", new_task.dict())
        return results

    async def update_task_status(self, tenant_id: str, task_id: str, status: TaskStatus) -> Optional[TaskResponse]:
        """Update the status of a task. Emits 'task.status_changed'."""
        now = datetime.now(timezone.utc)
        async with self.pool.acquire() as conn:
            old_status_row = await conn.fetchrow(
                "SELECT status FROM tasks WHERE id = $1 AND tenant_id = $2",
                task_id, tenant_id,
            )
            if not old_status_row:
                return None
            old_status = old_status_row["status"]
            await conn.execute(
                "UPDATE tasks SET status = $1, updated_at = $2 WHERE id = $3 AND tenant_id = $4",
                status.value, now, task_id, tenant_id,
            )
            row = await conn.fetchrow(
                "SELECT id, title, description, status, parent_id, created_at, updated_at FROM tasks WHERE id = $1",
                task_id,
            )
        result = TaskResponse(**dict(row))
        await self._emit("task.status_changed", {
            "task_id": task_id,
            "old_status": old_status,
            "new_status": status.value,
            "tenant_id": tenant_id,
        })
        return result

    async def delete_task(self, tenant_id: str, task_id: str) -> bool:
        """Delete a task by ID. Emits 'task.deleted'. Returns True if successful."""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM tasks WHERE id = $1 AND tenant_id = $2",
                task_id, tenant_id,
            )
        deleted = result == "DELETE 1"
        if deleted:
            await self._emit("task.deleted", {"task_id": task_id, "tenant_id": tenant_id})
        return deleted

    async def create_child_task(self, tenant_id: str, parent_id: str, task: TaskCreate) -> Optional[TaskResponse]:
        """Create a task as a child of an existing task. Parent must exist."""
        async with self.pool.acquire() as conn:
            parent_exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM tasks WHERE id = $1 AND tenant_id = $2)",
                parent_id, tenant_id,
            )
            if not parent_exists:
                return None
            task.parent_id = parent_id
            return await self.add_task(tenant_id, task)

    # ----- Dependency Management -----

    async def link_tasks_with_dependency(self, tenant_id: str, dependent_id: str, dependency_id: str) -> bool:
        """Make one task depend on another. Both must belong to the tenant."""
        async with self.pool.acquire() as conn:
            # Verify both tasks exist under tenant
            exist = await conn.fetchval(
                """SELECT EXISTS(
                       SELECT 1 FROM tasks WHERE id = $1 AND tenant_id = $2
                   ) AND EXISTS(
                       SELECT 1 FROM tasks WHERE id = $3 AND tenant_id = $2
                   )""",
                dependent_id, tenant_id, dependency_id,
            )
            if not exist:
                return False
            # Prevent circular dependencies (simple check: would create a cycle)
            # For simplicity, we assume no cycles - real implementation would need a full cycle check.
            await conn.execute(
                "INSERT INTO task_dependencies (dependent_id, dependency_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
                dependent_id, dependency_id,
            )
        await self._emit("task.dependency_added", {
            "dependent_id": dependent_id,
            "dependency_id": dependency_id,
            "tenant_id": tenant_id,
        })
        return True

    async def _get_dependency_ids(self, conn, dependent_id: str, tenant_id: str) -> Set[str]:
        """Retrieve dependency IDs for a given task."""
        rows = await conn.fetch(
            "SELECT dependency_id FROM task_dependencies "
            "JOIN tasks ON task_dependencies.dependency_id = tasks.id "
            "WHERE task_dependencies.dependent_id = $1 AND tasks.tenant_id = $2",
            dependent_id, tenant_id,
        )
        return {row["dependency_id"] for row in rows}

    async def list_tasks_ready_to_work_on(self, tenant_id: str) -> List[TaskResponse]:
        """Return tasks that have all dependencies completed and are unblocked."""
        async with self.pool.acquire() as conn:
            # Subquery: tasks whose all dependencies are DONE.
            # We'll fetch eligible tasks in one go using a NOT EXISTS pattern.
            query = """
                SELECT t.id, t.title, t.description, t.status, t.parent_id, t.created_at, t.updated_at
                FROM tasks t
                WHERE t.tenant_id = $1
                  AND t.status = 'TODO'   -- only TODO tasks can be started
                  AND NOT EXISTS (
                      SELECT 1 FROM task_dependencies td
                      JOIN tasks dep ON dep.id = td.dependency_id AND dep.tenant_id = t.tenant_id
                      WHERE td.dependent_id = t.id
                        AND dep.status != 'DONE'
                  )
                  AND NOT EXISTS (
                      -- optional: avoid tasks that have children not done? Not specified.
                      SELECT 1 FROM tasks child
                      WHERE child.parent_id = t.id AND child.status != 'DONE'
                  )
                ORDER BY t.created_at
            """
            rows = await conn.fetch(query, tenant_id)
        return [TaskResponse(**dict(r)) for r in rows]