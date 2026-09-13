from __future__ import annotations

import asyncio
import datetime
import json
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

import asyncpg
import httpx
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class Task(BaseModel):
    id: Optional[int] = None
    tenant_id: str
    title: str
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    parent_id: Optional[int] = None
    created_at: Optional[datetime.datetime] = None
    updated_at: Optional[datetime.datetime] = None

    class Config:
        orm_mode = True


class TaskTree(Task):
    children: List[TaskTree] = []


class EventType(str, Enum):
    TASK_CREATED = "task_created"
    TASK_UPDATED = "task_updated"
    TASK_DELETED = "task_deleted"
    STATUS_CHANGED = "status_changed"
    DEPENDENCY_ADDED = "dependency_added"


class EventManager:
    def __init__(self) -> None:
        self._sync_callbacks: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}
        self._async_callbacks: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}
        self._webhooks: Dict[str, List[str]] = {}
        self._http_client: Optional[httpx.AsyncClient] = None

    def on(self, event: EventType, callback: Callable[[Dict[str, Any]], None]) -> None:
        if asyncio.iscoroutinefunction(callback):
            self._async_callbacks.setdefault(event.value, []).append(callback)
        else:
            self._sync_callbacks.setdefault(event.value, []).append(callback)

    def register_webhook(self, event: EventType, url: str) -> None:
        self._webhooks.setdefault(event.value, []).append(url)

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient()
        return self._http_client

    async def emit(self, event: EventType, data: Dict[str, Any]) -> None:
        # Invoke synchronous callbacks (they may block; consider running in executor)
        for cb in self._sync_callbacks.get(event.value, []):
            cb(data)
        # Await asynchronous callbacks
        for cb in self._async_callbacks.get(event.value, []):
            await cb(data)
        # Fire webhooks (background)
        urls = self._webhooks.get(event.value, [])
        if urls:
            client = await self._ensure_client()
            tasks = [client.post(url, json=data) for url in urls]
            await asyncio.gather(*tasks, return_exceptions=True)

    async def close(self) -> None:
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


class TaskToolset:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self.pool = pool
        self.events = EventManager()

    async def initialize(self) -> None:
        await self.pool.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id SERIAL PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'pending',
                parent_id INTEGER REFERENCES tasks(id) ON DELETE SET NULL,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        await self.pool.execute("""
            CREATE TABLE IF NOT EXISTS task_dependencies (
                task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                depends_on_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                PRIMARY KEY (task_id, depends_on_id)
            );
        """)

    async def list_tasks(
        self,
        tenant_id: str,
        parent_id: Optional[int] = None,
        format: str = "flat",
    ) -> Union[List[Task], List[TaskTree]]:
        if parent_id is not None:
            rows = await self.pool.fetch(
                "SELECT * FROM tasks WHERE tenant_id = $1 AND parent_id = $2 ORDER BY created_at",
                tenant_id, parent_id,
            )
        else:
            rows = await self.pool.fetch(
                "SELECT * FROM tasks WHERE tenant_id = $1 ORDER BY created_at",
                tenant_id,
            )
        tasks = [Task(**dict(r)) for r in rows]
        if format == "flat":
            return tasks
        # Build hierarchical tree
        task_map = {t.id: TaskTree(**t.dict(), children=[]) for t in tasks}
        roots = []
        for t in tasks:
            if t.parent_id is not None and t.parent_id in task_map:
                task_map[t.parent_id].children.append(task_map[t.id])
            else:
                roots.append(task_map[t.id])
        return roots

    async def add_task(
        self,
        tenant_id: str,
        title: str,
        description: str = "",
        parent_id: Optional[int] = None,
        status: TaskStatus = TaskStatus.PENDING,
    ) -> Task:
        row = await self.pool.fetchrow(
            "INSERT INTO tasks (tenant_id, title, description, status, parent_id) VALUES ($1, $2, $3, $4, $5) RETURNING *",
            tenant_id, title, description, status.value, parent_id,
        )
        task = Task(**dict(row))
        await self.events.emit(EventType.TASK_CREATED, task.dict())
        return task

    async def update_task_status(
        self,
        task_id: int,
        tenant_id: str,
        new_status: TaskStatus,
    ) -> Task:
        old = await self.pool.fetchrow(
            "SELECT * FROM tasks WHERE id = $1 AND tenant_id = $2 FOR UPDATE",
            task_id, tenant_id,
        )
        if not old:
            raise ValueError(f"Task {task_id} not found for tenant {tenant_id}")
        old_status = old["status"]
        row = await self.pool.fetchrow(
            "UPDATE tasks SET status = $1, updated_at = NOW() WHERE id = $2 AND tenant_id = $3 RETURNING *",
            new_status.value, task_id, tenant_id,
        )
        task = Task(**dict(row))
        if old_status != new_status.value:
            await self.events.emit(EventType.STATUS_CHANGED, {
                "task": task.dict(),
                "old_status": old_status,
                "new_status": new_status.value,
            })
        await self.events.emit(EventType.TASK_UPDATED, task.dict())
        return task

    async def delete_task(self, task_id: int, tenant_id: str) -> bool:
        result = await self.pool.execute(
            "DELETE FROM tasks WHERE id = $1 AND tenant_id = $2",
            task_id, tenant_id,
        )
        deleted = result != "DELETE 0"
        if deleted:
            await self.events.emit(EventType.TASK_DELETED, {"task_id": task_id, "tenant_id": tenant_id})
        return deleted

    async def create_child_task(
        self,
        tenant_id: str,
        parent_id: int,
        title: str,
        description: str = "",
        status: TaskStatus = TaskStatus.PENDING,
    ) -> Task:
        # Verify parent exists and belongs to tenant
        parent = await self.pool.fetchrow(
            "SELECT id FROM tasks WHERE id = $1 AND tenant_id = $2",
            parent_id, tenant_id,
        )
        if not parent:
            raise ValueError("Parent task not found")
        return await self.add_task(tenant_id, title, description, parent_id=parent_id, status=status)

    async def link_tasks(self, task_id: int, depends_on_id: int, tenant_id: str) -> bool:
        # Ensure both tasks belong to tenant
        tasks = await self.pool.fetch(
            "SELECT id FROM tasks WHERE id = ANY($1::int[]) AND tenant_id = $2",
            [task_id, depends_on_id], tenant_id,
        )
        if len(tasks) != 2:
            raise ValueError("One or both tasks not found for tenant")
        try:
            await self.pool.execute(
                "INSERT INTO task_dependencies (task_id, depends_on_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
                task_id, depends_on_id,
            )
        except asyncpg.ForeignKeyViolationError:
            raise ValueError("Invalid dependency: task does not exist")
        await self.events.emit(EventType.DEPENDENCY_ADDED, {
            "task_id": task_id,
            "depends_on_id": depends_on_id,
            "tenant_id": tenant_id,
        })
        return True

    async def list_ready_tasks(self, tenant_id: str) -> List[Task]:
        # Tasks that are pending (or in_progress?) and have all dependencies completed.
        # A task is ready if all its dependencies are in 'completed' status.
        # Use NOT EXISTS for any dependency not completed.
        rows = await self.pool.fetch("""
            SELECT t.*
            FROM tasks t
            WHERE t.tenant_id = $1
              AND t.status IN ('pending', 'in_progress')
              AND NOT EXISTS (
                SELECT 1 FROM task_dependencies d
                JOIN tasks dep ON d.depends_on_id = dep.id
                WHERE d.task_id = t.id
                  AND dep.status != 'completed'
              )
            ORDER BY t.created_at
        """, tenant_id)
        return [Task(**dict(r)) for r in rows]

    async def bulk_write_tasks(self, tenant_id: str, tasks: List[Task]) -> List[Task]:
        results: List[Task] = []
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                for task in tasks:
                    if task.id is not None:
                        # Update existing
                        row = await conn.fetchrow("""
                            UPDATE tasks
                            SET title = $1, description = $2, status = $3, parent_id = $4, updated_at = NOW()
                            WHERE id = $5 AND tenant_id = $6
                            RETURNING *
                        """, task.title, task.description, task.status.value, task.parent_id, task.id, tenant_id)
                        if row:
                            updated = Task(**dict(row))
                            results.append(updated)
                            await self.events.emit(EventType.TASK_UPDATED, updated.dict())
                        else:
                            raise ValueError(f"Task {task.id} not found for tenant {tenant_id}")
                    else:
                        # Insert new
                        row = await conn.fetchrow("""
                            INSERT INTO tasks (tenant_id, title, description, status, parent_id)
                            VALUES ($1, $2, $3, $4, $5)
                            RETURNING *
                        """, tenant_id, task.title, task.description, task.status.value, task.parent_id)
                        created = Task(**dict(row))
                        results.append(created)
                        await self.events.emit(EventType.TASK_CREATED, created.dict())
        return results

    async def close(self) -> None:
        await self.events.close()