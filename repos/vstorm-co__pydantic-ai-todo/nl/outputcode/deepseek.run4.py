import asyncio
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Awaitable, Union

import asyncpg
import aiohttp
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Task(BaseModel):
    id: uuid.UUID
    tenant_id: str
    title: str
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    parent_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime


class TaskWithChildren(Task):
    children: List["TaskWithChildren"] = Field(default_factory=list)


class TodoToolset:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
        self.listeners: Dict[str, List[Callable[..., Awaitable[Any]]]] = {}
        self.webhooks: Dict[str, List[str]] = {}
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    @staticmethod
    async def initialize_database(pool: asyncpg.Pool):
        async with pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id UUID PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'pending',
                    parent_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS idx_tasks_tenant_id ON tasks(tenant_id);
                CREATE TABLE IF NOT EXISTS task_dependencies (
                    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                    depends_on_task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                    PRIMARY KEY (task_id, depends_on_task_id)
                );
            """)

    def add_listener(self, event: str, callback: Callable[..., Awaitable[Any]]):
        self.listeners.setdefault(event, []).append(callback)

    def remove_listener(self, event: str, callback: Callable[..., Awaitable[Any]]):
        if event in self.listeners:
            self.listeners[event] = [cb for cb in self.listeners[event] if cb != callback]

    def register_webhook(self, event: str, url: str):
        self.webhooks.setdefault(event, []).append(url)

    async def _trigger_event(self, event: str, data: Dict[str, Any]):
        for cb in self.listeners.get(event, []):
            try:
                await cb(data)
            except Exception:
                pass  # log silently or handle

        urls = self.webhooks.get(event, [])
        if urls:
            session = await self._get_session()
            for url in urls:
                try:
                    async with session.post(url, json=data) as _:
                        pass
                except Exception:
                    pass

    async def create_task(
        self,
        tenant_id: str,
        title: str,
        description: str = "",
        parent_id: Optional[uuid.UUID] = None,
    ) -> Task:
        task_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO tasks (id, tenant_id, title, description, status, parent_id, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id, tenant_id, title, description, status, parent_id, created_at, updated_at
                """,
                task_id,
                tenant_id,
                title,
                description,
                TaskStatus.PENDING.value,
                parent_id,
                now,
                now,
            )
        task = Task(**dict(row))
        await self._trigger_event("task_created", task.dict())
        return task

    async def get_task(self, task_id: uuid.UUID) -> Optional[Task]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM tasks WHERE id = $1", task_id)
        if row is None:
            return None
        return Task(**dict(row))

    async def list_tasks(self, tenant_id: str, root_only: bool = True) -> List[Task]:
        async with self.pool.acquire() as conn:
            if root_only:
                rows = await conn.fetch(
                    "SELECT * FROM tasks WHERE tenant_id = $1 AND parent_id IS NULL ORDER BY created_at",
                    tenant_id,
                )
            else:
                rows = await conn.fetch(
                    "SELECT * FROM tasks WHERE tenant_id = $1 ORDER BY created_at",
                    tenant_id,
                )
        return [Task(**dict(r)) for r in rows]

    async def list_tasks_hierarchical(self, tenant_id: str) -> List[TaskWithChildren]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM tasks WHERE tenant_id = $1 ORDER BY created_at",
                tenant_id,
            )
        tasks = [Task(**dict(r)) for r in rows]
        tasks_by_id: Dict[uuid.UUID, TaskWithChildren] = {
            t.id: TaskWithChildren(**t.dict(), children=[]) for t in tasks
        }
        roots: List[TaskWithChildren] = []
        for t in tasks_by_id.values():
            if t.parent_id and t.parent_id in tasks_by_id:
                tasks_by_id[t.parent_id].children.append(t)
            else:
                roots.append(t)
        return roots

    async def update_task_status(self, task_id: uuid.UUID, status: TaskStatus) -> Optional[Task]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE tasks SET status = $1, updated_at = NOW()
                WHERE id = $2
                RETURNING *
                """,
                status.value,
                task_id,
            )
        if row is None:
            return None
        task = Task(**dict(row))
        await self._trigger_event("status_changed", {"task": task.dict(), "new_status": status.value})
        return task

    async def delete_task(self, task_id: uuid.UUID) -> bool:
        async with self.pool.acquire() as conn:
            result = await conn.execute("DELETE FROM tasks WHERE id = $1", task_id)
            deleted = result == "DELETE 1"
            if deleted:
                await self._trigger_event("task_deleted", {"task_id": str(task_id)})
            return deleted

    async def create_child_task(
        self,
        parent_task_id: uuid.UUID,
        tenant_id: str,
        title: str,
        description: str = "",
    ) -> Task:
        parent = await self.get_task(parent_task_id)
        if parent is None:
            raise ValueError(f"Parent task {parent_task_id} not found")
        return await self.create_task(
            tenant_id=tenant_id,
            title=title,
            description=description,
            parent_id=parent_task_id,
        )

    async def link_dependency(self, task_id: uuid.UUID, depends_on_task_id: uuid.UUID) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO task_dependencies (task_id, depends_on_task_id)
                VALUES ($1, $2)
                ON CONFLICT DO NOTHING
                """,
                task_id,
                depends_on_task_id,
            )
        await self._trigger_event("dependency_added", {
            "task_id": str(task_id),
            "depends_on_task_id": str(depends_on_task_id),
        })

    async def remove_dependency(self, task_id: uuid.UUID, depends_on_task_id: uuid.UUID) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM task_dependencies WHERE task_id = $1 AND depends_on_task_id = $2",
                task_id,
                depends_on_task_id,
            )

    async def list_tasks_ready_to_work(self, tenant_id: str) -> List[Task]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT t.* FROM tasks t
                WHERE t.tenant_id = $1
                  AND t.status NOT IN ('completed', 'cancelled')
                  AND NOT EXISTS (
                      SELECT 1 FROM task_dependencies d
                      JOIN tasks dep ON d.depends_on_task_id = dep.id
                      WHERE d.task_id = t.id
                        AND dep.status != 'completed'
                  )
                ORDER BY t.created_at
                """,
                tenant_id,
            )
        return [Task(**dict(r)) for r in rows]

    async def bulk_write_tasks(self, tenant_id: str, tasks: List[Dict[str, Any]]) -> List[Task]:
        results: List[Task] = []
        async with self.pool.acquire() as conn:
            for task_data in tasks:
                task_id = task_data.get("id", uuid.uuid4())
                title = task_data["title"]
                description = task_data.get("description", "")
                status = TaskStatus(task_data.get("status", "pending"))
                parent_id = task_data.get("parent_id")
                now = datetime.now(timezone.utc)
                row = await conn.fetchrow(
                    """
                    INSERT INTO tasks (id, tenant_id, title, description, status, parent_id, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (id) DO UPDATE SET
                        title = EXCLUDED.title,
                        description = EXCLUDED.description,
                        status = EXCLUDED.status,
                        parent_id = EXCLUDED.parent_id,
                        updated_at = EXCLUDED.updated_at
                    RETURNING *
                    """,
                    task_id,
                    tenant_id,
                    title,
                    description,
                    status.value,
                    parent_id,
                    now,
                    now,
                )
                task = Task(**dict(row))
                results.append(task)
        return results