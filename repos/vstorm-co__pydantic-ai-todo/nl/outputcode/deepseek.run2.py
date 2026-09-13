import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set, Union

import asyncpg
import aiohttp
from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)


# ---------------------------
# Pydantic models for validation
# ---------------------------
class Task(BaseModel):
    id: Optional[str] = None  # UUID string
    tenant_id: str
    title: str = Field(..., min_length=1)
    description: str = ""
    status: str = Field("pending", regex="^(pending|in_progress|completed|blocked|cancelled)$")
    parent_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        extra = "forbid"


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1)
    description: str = ""
    status: str = Field("pending", regex="^(pending|in_progress|completed|blocked|cancelled)$")
    parent_id: Optional[str] = None
    dependencies: Optional[List[str]] = None  # list of task ids this task depends on


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = Field(None, regex="^(pending|in_progress|completed|blocked|cancelled)$")
    parent_id: Optional[str] = None


class DependencyLink(BaseModel):
    task_id: str
    depends_on_id: str

    @validator("depends_on_id")
    def not_same(cls, v, values):
        if "task_id" in values and v == values["task_id"]:
            raise ValueError("A task cannot depend on itself")
        return v


# ---------------------------
# Database Manager
# ---------------------------
class Database:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(self.dsn, min_size=2, max_size=10)
        await self._create_tables()

    async def disconnect(self):
        if self.pool:
            await self.pool.close()

    async def _create_tables(self):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    tenant_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'in_progress', 'completed', 'blocked', 'cancelled')),
                    parent_id UUID REFERENCES tasks(id) ON DELETE SET NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                );
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS task_dependencies (
                    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                    depends_on_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                    PRIMARY KEY (task_id, depends_on_id),
                    CHECK (task_id != depends_on_id)
                );
            """)

    async def execute(self, query: str, *args, **kwargs):
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args, **kwargs)

    async def fetch(self, query: str, *args, **kwargs) -> List[asyncpg.Record]:
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args, **kwargs)

    async def fetchrow(self, query: str, *args, **kwargs) -> Optional[asyncpg.Record]:
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args, **kwargs)

    async def fetchval(self, query: str, *args, **kwargs) -> Any:
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args, **kwargs)


# ---------------------------
# Event System
# ---------------------------
class EventSystem:
    def __init__(self, webhook_urls: Optional[List[str]] = None):
        self._callbacks: Dict[str, List[Callable[[Dict], Coroutine]]] = {}
        self._webhook_urls: List[str] = webhook_urls or []
        self._session: Optional[aiohttp.ClientSession] = None

    async def start(self):
        if self._webhook_urls:
            self._session = aiohttp.ClientSession()

    async def stop(self):
        if self._session:
            await self._session.close()

    def on(self, event_name: str, callback: Callable[[Dict], Coroutine]):
        if event_name not in self._callbacks:
            self._callbacks[event_name] = []
        self._callbacks[event_name].append(callback)

    def off(self, event_name: str, callback: Callable[[Dict], Coroutine]):
        if event_name in self._callbacks:
            try:
                self._callbacks[event_name].remove(callback)
            except ValueError:
                pass

    async def emit(self, event_name: str, payload: Dict):
        # Call local callbacks
        for cb in self._callbacks.get(event_name, []):
            try:
                await cb(payload)
            except Exception as e:
                logger.error(f"Error in callback for {event_name}: {e}")

        # Notify webhooks
        if self._session and self._webhook_urls:
            payload["event"] = event_name
            for url in self._webhook_urls:
                try:
                    async with self._session.post(url, json=payload) as resp:
                        if resp.status != 200:
                            logger.warning(f"Webhook to {url} returned {resp.status}")
                except Exception as e:
                    logger.error(f"Webhook to {url} failed: {e}")


# ---------------------------
# Todo Toolset
# ---------------------------
class TodoToolset:
    """
    A task planning and tracking toolset for Pydantic AI agents.
    Provides hierarchical task management with subtasks, dependencies,
    PostgreSQL storage (multi-tenancy), and an event system for callbacks/webhooks.
    """

    ALLOWED_STATUSES = {"pending", "in_progress", "completed", "blocked", "cancelled"}

    def __init__(
        self,
        db_url: str,
        tenant_id: str,
        webhook_urls: Optional[List[str]] = None,
    ):
        self.tenant_id = tenant_id
        self.db = Database(db_url)
        self.events = EventSystem(webhook_urls)
        self._ready_tasks_cache = set()

    async def connect(self):
        await self.db.connect()
        await self.events.start()

    async def disconnect(self):
        await self.events.stop()
        await self.db.disconnect()

    # ---------- Core CRUD ----------
    async def add_task(self, task: TaskCreate) -> Task:
        """Create a single task."""
        valid_status = task.status if task.status in self.ALLOWED_STATUSES else "pending"
        result = await self.db.fetchrow(
            """
            INSERT INTO tasks (tenant_id, title, description, status, parent_id)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, tenant_id, title, description, status, parent_id, created_at, updated_at
            """,
            self.tenant_id,
            task.title,
            task.description,
            valid_status,
            task.parent_id,
        )
        task_dict = dict(result)
        # add dependencies if provided
        if task.dependencies:
            for dep_id in task.dependencies:
                await self._link_dependency(task_dict["id"], dep_id)
        await self.events.emit("task_created", task_dict)
        return Task(**task_dict)

    async def get_task(self, task_id: str) -> Optional[Task]:
        row = await self.db.fetchrow(
            "SELECT * FROM tasks WHERE id = $1 AND tenant_id = $2",
            task_id,
            self.tenant_id,
        )
        if row:
            return Task(**dict(row))
        return None

    async def update_task_status(self, task_id: str, new_status: str) -> Task:
        """Update status of a task by ID."""
        if new_status not in self.ALLOWED_STATUSES:
            raise ValueError(f"Invalid status: {new_status}")
        old = await self.db.fetchrow(
            "SELECT status FROM tasks WHERE id = $1 AND tenant_id = $2",
            task_id,
            self.tenant_id,
        )
        if not old:
            raise LookupError(f"Task {task_id} not found in tenant {self.tenant_id}")
        old_status = old["status"]
        if old_status == new_status:
            return await self.get_task(task_id)  # no change

        updated = await self.db.fetchrow(
            """
            UPDATE tasks
            SET status = $1, updated_at = NOW()
            WHERE id = $2 AND tenant_id = $3
            RETURNING *
            """,
            new_status,
            task_id,
            self.tenant_id,
        )
        task_dict = dict(updated)
        await self.events.emit(
            "task_status_changed",
            {"task": task_dict, "old_status": old_status, "new_status": new_status},
        )
        return Task(**task_dict)

    async def update_task(self, task_id: str, updates: TaskUpdate) -> Task:
        """Update fields of a task (title, description, status, parent)."""
        set_clauses = []
        params = []
        idx = 1
        if updates.title is not None:
            set_clauses.append(f"title = ${idx}")
            params.append(updates.title)
            idx += 1
        if updates.description is not None:
            set_clauses.append(f"description = ${idx}")
            params.append(updates.description)
            idx += 1
        if updates.status is not None:
            if updates.status not in self.ALLOWED_STATUSES:
                raise ValueError(f"Invalid status: {updates.status}")
            set_clauses.append(f"status = ${idx}")
            params.append(updates.status)
            idx += 1
        if updates.parent_id is not None:
            set_clauses.append(f"parent_id = ${idx}")
            params.append(updates.parent_id)
            idx += 1
        if not set_clauses:
            return await self.get_task(task_id)

        set_clauses.append(f"updated_at = NOW()")
        params.append(task_id)
        params.append(self.tenant_id)
        query = f"""
            UPDATE tasks
            SET {', '.join(set_clauses)}
            WHERE id = ${idx} AND tenant_id = ${idx+1}
            RETURNING *
        """
        updated = await self.db.fetchrow(query, *params)
        if not updated:
            raise LookupError(f"Task {task_id} not found in tenant {self.tenant_id}")
        task_dict = dict(updated)
        await self.events.emit("task_updated", task_dict)
        return Task(**task_dict)

    async def delete_task(self, task_id: str) -> None:
        """Delete a task by ID (and its dependencies will cascade)."""
        row = await self.db.fetchrow(
            "DELETE FROM tasks WHERE id = $1 AND tenant_id = $2 RETURNING *",
            task_id,
            self.tenant_id,
        )
        if not row:
            raise LookupError(f"Task {task_id} not found in tenant {self.tenant_id}")
        await self.events.emit("task_deleted", dict(row))

    # ---------- Hierarchy & Dependencies ----------
    async def create_child_task(self, parent_id: str, title: str, description: str = "") -> Task:
        """Create a subtask under a parent task."""
        parent = await self.get_task(parent_id)
        if not parent:
            raise LookupError(f"Parent task {parent_id} not found in tenant {self.tenant_id}")
        task = TaskCreate(
            title=title,
            description=description,
            parent_id=parent_id,
        )
        return await self.add_task(task)

    async def link_dependency(self, task_id: str, depends_on_id: str) -> None:
        """Add a dependency: task_id depends on depends_on_id."""
        link = DependencyLink(task_id=task_id, depends_on_id=depends_on_id)
        await self._link_dependency(link.task_id, link.depends_on_id)

    async def _link_dependency(self, task_id: str, depends_on_id: str) -> None:
        # check both tasks exist and belong to tenant
        task = await self.get_task(task_id)
        dep = await self.get_task(depends_on_id)
        if not task or not dep:
            raise LookupError("One or both tasks do not exist in this tenant")
        if task_id == depends_on_id:
            raise ValueError("A task cannot depend on itself")
        # basic cycle detection
        if await self._would_create_cycle(task_id, depends_on_id):
            raise ValueError("Adding this dependency would create a cycle")
        try:
            await self.db.execute(
                "INSERT INTO task_dependencies (task_id, depends_on_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
                task_id,
                depends_on_id,
            )
            await self.events.emit(
                "dependency_added", {"task_id": task_id, "depends_on_id": depends_on_id}
            )
        except asyncpg.ForeignKeyViolationError:
            raise LookupError("One or both tasks do not exist")

    async def _would_create_cycle(self, task_id: str, depends_on_id: str) -> bool:
        """
        Check if adding dependency `task_id -> depends_on_id` creates a cycle.
        We walk from depends_on_id following its dependencies to see if we reach task_id.
        """
        visited = set()
        to_visit = [depends_on_id]
        while to_visit:
            current = to_visit.pop()
            if current == task_id:
                return True
            if current in visited:
                continue
            visited.add(current)
            rows = await self.db.fetch(
                "SELECT depends_on_id FROM task_dependencies WHERE task_id = $1",
                current,
            )
            for row in rows:
                to_visit.append(row["depends_on_id"])
        return False

    async def remove_dependency(self, task_id: str, depends_on_id: str) -> None:
        """Remove a dependency."""
        await self.db.execute(
            "DELETE FROM task_dependencies WHERE task_id = $1 AND depends_on_id = $2",
            task_id,
            depends_on_id,
        )

    async def get_dependencies(self, task_id: str) -> List[str]:
        """Return list of task IDs that this task depends on."""
        rows = await self.db.fetch(
            "SELECT depends_on_id FROM task_dependencies WHERE task_id = $1",
            task_id,
        )
        return [row["depends_on_id"] for row in rows]

    async def get_dependents(self, task_id: str) -> List[str]:
        """Return list of task IDs that depend on this task."""
        rows = await self.db.fetch(
            "SELECT task_id FROM task_dependencies WHERE depends_on_id = $1",
            task_id,
        )
        return [row["task_id"] for row in rows]

    # ---------- Listing & Filtering ----------
    async def list_tasks(
        self,
        include_completed: bool = False,
        hierarchy: bool = False,
    ) -> Union[List[Task], List[dict]]:
        """
        List tasks for the tenant.
        If hierarchy=True, returns a nested tree structure.
        """
        query = "SELECT * FROM tasks WHERE tenant_id = $1"
        if not include_completed:
            query += " AND status != 'completed' AND status != 'cancelled'"
        query += " ORDER BY created_at ASC"
        rows = await self.db.fetch(query, self.tenant_id)
        tasks = [Task(**dict(row)) for row in rows]

        if not hierarchy:
            return tasks

        # Build tree
        task_dict = {t.id: t for t in tasks}
        children_map: Dict[Optional[str], List[Task]] = {}
        for t in tasks:
            children_map.setdefault(t.parent_id, []).append(t)
        # Root tasks have parent_id None
        roots = children_map.get(None, [])

        def build_tree(node: Task) -> dict:
            node_dict = node.dict()
            node_dict["children"] = [
                build_tree(child) for child in children_map.get(node.id, [])
            ]
            return node_dict

        return [build_tree(root) for root in roots]

    async def get_ready_tasks(self) -> List[Task]:
        """
        Return tasks that are ready to be worked on.
        A task is ready if its status is NOT 'completed'/'cancelled' AND
        all its dependencies are 'completed'.
        """
        # Query: tasks where status in ('pending','in_progress','blocked') and no
        # dependency exists that is not completed.
        # We can LEFT JOIN dependencies and check that all are completed.
        query = """
        SELECT t.*
        FROM tasks t
        LEFT JOIN task_dependencies d ON t.id = d.task_id
        WHERE t.tenant_id = $1
          AND t.status NOT IN ('completed', 'cancelled')
        GROUP BY t.id
        HAVING EVERY(d.depends_on_id IS NULL OR EXISTS (
            SELECT 1 FROM tasks dep WHERE dep.id = d.depends_on_id AND dep.status = 'completed'
        ))
        ORDER BY t.created_at
        """
        rows = await self.db.fetch(query, self.tenant_id)
        return [Task(**dict(row)) for row in rows]

    async def bulk_write_tasks(self, tasks: List[TaskCreate]) -> List[Task]:
        """
        Insert or update tasks in bulk.
        Tasks without an id will be inserted; tasks with an id will be updated (merged).
        Returns the resulting task list.
        """
        results = []
        for t in tasks:
            if t.id:
                # update existing
                upd = TaskUpdate(
                    title=t.title,
                    description=t.description,
                    status=t.status,
                    parent_id=t.parent_id,
                )
                try:
                    updated = await self.update_task(t.id, upd)
                    results.append(updated)
                except LookupError:
                    # If id not found, fall back to insert with that id? Not safe.
                    # We'll raise or skip; here we raise.
                    raise
            else:
                created = await self.add_task(t)
                results.append(created)
        return results

    # ---------- Additional helpers ----------
    async def get_subtasks(self, task_id: str) -> List[Task]:
        """Get direct children of a task."""
        rows = await self.db.fetch(
            "SELECT * FROM tasks WHERE parent_id = $1 AND tenant_id = $2 ORDER BY created_at",
            task_id,
            self.tenant_id,
        )
        return [Task(**dict(row)) for row in rows]

    def on_event(self, event_name: str, callback: Callable[[Dict], Coroutine]):
        """Register a callback for an event."""
        self.events.on(event_name, callback)

    def off_event(self, event_name: str, callback: Callable[[Dict], Coroutine]):
        """Unregister a callback for an event."""
        self.events.off(event_name, callback)