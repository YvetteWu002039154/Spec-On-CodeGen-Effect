from __future__ import annotations

import asyncio
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union

import asyncpg
from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_ai import RunContext

# Tenant context variable (can be set per request)
current_tenant_id: ContextVar[str] = ContextVar("tenant_id", default="default")


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Task(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = Field(default="default")
    title: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    parent_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    children: List[Task] = Field(default_factory=list, exclude=True)

    def dict(self, *args, **kwargs):
        d = super().dict(*args, **kwargs)
        d.pop("children", None)
        return d


# Recursive forward reference
Task.model_rebuild()


class Dependency(BaseModel):
    task_id: str
    depends_on_id: str


class TodoToolset:
    def __init__(
        self,
        db_pool: asyncpg.Pool,
        tenant_id_getter: Optional[Callable[[], str]] = None,
    ):
        self.db_pool = db_pool
        self.tenant_id_getter = tenant_id_getter or (lambda: current_tenant_id.get())
        self.event_handlers: Dict[str, List[Callable]] = {}

    def _get_tenant_id(self) -> str:
        return self.tenant_id_getter()

    async def init_db(self) -> None:
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    parent_id TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS idx_tasks_tenant ON tasks(tenant_id);
                CREATE INDEX IF NOT EXISTS idx_tasks_parent ON tasks(parent_id);

                CREATE TABLE IF NOT EXISTS task_dependencies (
                    task_id TEXT NOT NULL,
                    depends_on_id TEXT NOT NULL,
                    PRIMARY KEY (task_id, depends_on_id),
                    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
                    FOREIGN KEY (depends_on_id) REFERENCES tasks(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_deps_task ON task_dependencies(task_id);
            """)

    def register_event_handler(self, event: str, callback: Callable) -> None:
        if event not in self.event_handlers:
            self.event_handlers[event] = []
        self.event_handlers[event].append(callback)

    async def _emit_event(self, event: str, data: dict) -> None:
        for cb in self.event_handlers.get(event, []):
            if asyncio.iscoroutinefunction(cb):
                await cb(data)
            else:
                await asyncio.get_event_loop().run_in_executor(None, cb, data)

    async def _get_task(self, task_id: str, tenant: str) -> Optional[Task]:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM tasks WHERE id = $1 AND tenant_id = $2",
                task_id,
                tenant,
            )
            if row:
                return Task(**dict(row))
        return None

    async def list_tasks(
        self, ctx: RunContext[Any], hierarchical: bool = False
    ) -> Union[List[Task], List[Task]]:
        """List all tasks for the current tenant."""
        tenant = self._get_tenant_id()
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM tasks WHERE tenant_id = $1 ORDER BY created_at",
                tenant,
            )
            tasks = [Task(**dict(r)) for r in rows]

        if hierarchical:
            task_map = {t.id: t for t in tasks}
            roots = []
            for t in tasks:
                if t.parent_id and t.parent_id in task_map:
                    task_map[t.parent_id].children.append(t)
                else:
                    roots.append(t)
            return roots
        return tasks

    async def bulk_write_tasks(
        self, ctx: RunContext[Any], tasks: List[dict]
    ) -> List[Task]:
        """Upsert multiple tasks (insert or update based on presence of 'id')."""
        tenant = self._get_tenant_id()
        results = []
        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                for task_data in tasks:
                    task_id = task_data.get("id")
                    title = task_data["title"]
                    description = task_data.get("description")
                    status = task_data.get("status", TaskStatus.PENDING)
                    if isinstance(status, TaskStatus):
                        status = status.value
                    parent_id = task_data.get("parent_id")
                    if task_id:
                        # Update existing
                        row = await conn.fetchrow(
                            """
                            UPDATE tasks SET title=$1, description=$2, status=$3, parent_id=$4, updated_at=NOW()
                            WHERE id=$5 AND tenant_id=$6
                            RETURNING *
                            """,
                            title,
                            description,
                            status,
                            parent_id,
                            task_id,
                            tenant,
                        )
                        if not row:
                            raise ValueError(f"Task with id {task_id} not found")
                    else:
                        # Insert new
                        task_id = str(uuid.uuid4())
                        row = await conn.fetchrow(
                            """
                            INSERT INTO tasks (id, tenant_id, title, description, status, parent_id, created_at, updated_at)
                            VALUES ($1, $2, $3, $4, $5, $6, NOW(), NOW())
                            RETURNING *
                            """,
                            task_id,
                            tenant,
                            title,
                            description,
                            status,
                            parent_id,
                        )
                    if row:
                        task = Task(**dict(row))
                        results.append(task)
                        await self._emit_event(
                            "on_task_updated" if task_data.get("id") else "on_task_created",
                            task.dict(),
                        )
        return results

    async def add_task(
        self,
        ctx: RunContext[Any],
        title: str,
        description: Optional[str] = None,
        status: TaskStatus = TaskStatus.PENDING,
        parent_id: Optional[str] = None,
    ) -> Task:
        """Add a single new task."""
        tenant = self._get_tenant_id()
        task_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO tasks (id, tenant_id, title, description, status, parent_id, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $7)
                RETURNING *
                """,
                task_id,
                tenant,
                title,
                description,
                status.value,
                parent_id,
                now,
            )
            task = Task(**dict(row))
            await self._emit_event("on_task_created", task.dict())
            return task

    async def update_task_status(
        self, ctx: RunContext[Any], task_id: str, new_status: TaskStatus
    ) -> Task:
        """Update the status of a task by ID."""
        tenant = self._get_tenant_id()
        async with self.db_pool.acquire() as conn:
            # Get old task for event
            old_row = await conn.fetchrow(
                "SELECT * FROM tasks WHERE id=$1 AND tenant_id=$2",
                task_id,
                tenant,
            )
            if not old_row:
                raise ValueError(f"Task with id {task_id} not found")
            old_status = old_row["status"]
            row = await conn.fetchrow(
                """
                UPDATE tasks SET status=$1, updated_at=NOW()
                WHERE id=$2 AND tenant_id=$3
                RETURNING *
                """,
                new_status.value,
                task_id,
                tenant,
            )
            if not row:
                raise ValueError(f"Task with id {task_id} not found")
            task = Task(**dict(row))
            await self._emit_event(
                "on_task_status_changed",
                {
                    "task": task.dict(),
                    "old_status": old_status,
                    "new_status": new_status.value,
                },
            )
            return task

    async def delete_task(self, ctx: RunContext[Any], task_id: str) -> bool:
        """Delete a task by ID."""
        tenant = self._get_tenant_id()
        async with self.db_pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM tasks WHERE id=$1 AND tenant_id=$2",
                task_id,
                tenant,
            )
            deleted = result == "DELETE 1"
            if deleted:
                await self._emit_event(
                    "on_task_deleted", {"id": task_id, "tenant_id": tenant}
                )
            return deleted

    async def create_child_task(
        self,
        ctx: RunContext[Any],
        parent_id: str,
        title: str,
        description: Optional[str] = None,
        status: TaskStatus = TaskStatus.PENDING,
    ) -> Task:
        """Create a subtask under a given parent."""
        tenant = self._get_tenant_id()
        parent = await self._get_task(parent_id, tenant)
        if not parent:
            raise ValueError(f"Parent task with id {parent_id} not found")
        task_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO tasks (id, tenant_id, title, description, status, parent_id, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $7)
                RETURNING *
                """,
                task_id,
                tenant,
                title,
                description,
                status.value,
                parent_id,
                now,
            )
            task = Task(**dict(row))
            await self._emit_event("on_task_created", task.dict())
            return task

    async def link_tasks(self, ctx: RunContext[Any], task_id: str, depends_on_id: str) -> None:
        """Create a dependency: task_id depends on depends_on_id being completed."""
        tenant = self._get_tenant_id()
        if task_id == depends_on_id:
            raise ValueError("A task cannot depend on itself")
        # Verify both tasks exist
        task = await self._get_task(task_id, tenant)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        dep = await self._get_task(depends_on_id, tenant)
        if not dep:
            raise ValueError(f"Task {depends_on_id} not found")
        # Cycle detection in current dependency graph
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT task_id, depends_on_id FROM task_dependencies"
                " WHERE task_id IN (SELECT id FROM tasks WHERE tenant_id=$1)",
                tenant,
            )
            graph: Dict[str, Set[str]] = {}
            for row in rows:
                graph.setdefault(row["task_id"], set()).add(row["depends_on_id"])
            # Add the new edge temporarily for cycle detection
            graph.setdefault(task_id, set()).add(depends_on_id)
            # DFS to detect cycle
            visited = set()
            rec_stack = set()

            def has_cycle(node: str) -> bool:
                visited.add(node)
                rec_stack.add(node)
                for neighbor in graph.get(node, set()):
                    if neighbor not in visited:
                        if has_cycle(neighbor):
                            return True
                    elif neighbor in rec_stack:
                        return True
                rec_stack.remove(node)
                return False

            if has_cycle(task_id):
                raise ValueError("Adding this dependency would create a cycle")
            # Insert dependency
            await conn.execute(
                """
                INSERT INTO task_dependencies (task_id, depends_on_id)
                VALUES ($1, $2)
                ON CONFLICT DO NOTHING
                """,
                task_id,
                depends_on_id,
            )
            await self._emit_event(
                "on_dependency_added",
                {"task_id": task_id, "depends_on_id": depends_on_id},
            )

    async def list_tasks_ready_to_work_on(self, ctx: RunContext[Any]) -> List[Task]:
        """Return tasks whose dependencies are all completed (or have no dependencies)."""
        tenant = self._get_tenant_id()
        async with self.db_pool.acquire() as conn:
            # Get all non-completed, non-cancelled tasks
            rows = await conn.fetch(
                "SELECT * FROM tasks WHERE tenant_id=$1 AND status NOT IN ('completed', 'cancelled')",
                tenant,
            )
            tasks = [Task(**dict(r)) for r in rows]
            # Get all dependencies for this tenant
            dep_rows = await conn.fetch(
                "SELECT task_id, depends_on_id FROM task_dependencies"
                " WHERE task_id IN (SELECT id FROM tasks WHERE tenant_id=$1)",
                tenant,
            )
            # Build map of task_id -> list of depends_on_id
            dep_map: Dict[str, List[str]] = {}
            for row in dep_rows:
                dep_map.setdefault(row["task_id"], []).append(row["depends_on_id"])
            # Get all tasks that are either completed or not (we need status of dependency targets)
            all_task_statuses: Dict[str, str] = {
                r["id"]: r["status"] for r in rows
            }
            ready = []
            for task in tasks:
                deps = dep_map.get(task.id, [])
                if all(
                    all_task_statuses.get(dep) == "completed" for dep in deps
                ):
                    ready.append(task)
            return ready