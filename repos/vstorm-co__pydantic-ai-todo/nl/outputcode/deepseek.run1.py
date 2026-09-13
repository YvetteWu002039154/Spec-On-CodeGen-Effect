from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Awaitable, Callable, Iterable, List, Optional, Set

import asyncpg
import aiohttp
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class TaskBase(BaseModel):
    title: str
    description: str = ""
    status: TaskStatus = TaskStatus.TODO
    parent_id: Optional[str] = None


class TaskCreate(TaskBase):
    pass


class TaskUpsert(TaskBase):
    id: Optional[str] = None


class Task(TaskBase):
    id: str
    tenant_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_db_record(cls, record: asyncpg.Record) -> "Task":
        return cls(
            id=str(record["id"]),
            tenant_id=record["tenant_id"],
            title=record["title"],
            description=record["description"],
            status=TaskStatus(record["status"]),
            parent_id=str(record["parent_id"]) if record["parent_id"] else None,
            created_at=record["created_at"].replace(tzinfo=timezone.utc),
            updated_at=record["updated_at"].replace(tzinfo=timezone.utc),
        )


class TaskDependency(BaseModel):
    task_id: str
    depends_on_task_id: str


class EventManager:
    def __init__(self) -> None:
        self._callbacks: dict[str, List[Callable[..., Awaitable[None]]]] = {}
        self._webhooks: dict[str, List[str]] = {}

    def register_callback(self, event: str, callback: Callable[..., Awaitable[None]]) -> None:
        if event not in self._callbacks:
            self._callbacks[event] = []
        self._callbacks[event].append(callback)

    def register_webhook(self, event: str, url: str) -> None:
        if event not in self._webhooks:
            self._webhooks[event] = []
        self._webhooks[event].append(url)

    async def emit(self, event: str, data: dict) -> None:
        tasks = []
        for cb in self._callbacks.get(event, []):
            tasks.append(asyncio.create_task(cb(data)))
        async with aiohttp.ClientSession() as session:
            for url in self._webhooks.get(event, []):
                tasks.append(asyncio.create_task(self._post_webhook(session, url, data)))
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _post_webhook(self, session: aiohttp.ClientSession, url: str, data: dict) -> None:
        try:
            async with session.post(url, json=data) as resp:
                resp.raise_for_status()
        except Exception:
            # log or ignore
            pass


async def init_db(pool: asyncpg.Pool) -> None:
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'todo',
                parent_id UUID REFERENCES tasks(id) ON DELETE SET NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS task_dependencies (
                task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                depends_on_task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                PRIMARY KEY (task_id, depends_on_task_id)
            );
        """)
        # ensure gen_random_uuid extension
        await conn.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")


class TodoToolset:
    def __init__(
        self,
        pool: asyncpg.Pool,
        event_manager: Optional[EventManager] = None,
    ) -> None:
        self.pool = pool
        self.event_manager = event_manager or EventManager()

    async def _run_events(self, event: str, tenant_id: str, task_data: dict) -> None:
        task_data["tenant_id"] = tenant_id
        await self.event_manager.emit(event, task_data)

    async def list_tasks(self, tenant_id: str, hierarchical: bool = False) -> List[Task]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM tasks WHERE tenant_id = $1 ORDER BY created_at",
                tenant_id,
            )
            tasks = [Task.from_db_record(r) for r in rows]
            if not hierarchical:
                return tasks
            # Group by parent_id
            children_map: dict[Optional[str], List[Task]] = {}
            for t in tasks:
                children_map.setdefault(t.parent_id, []).append(t)
            # Build tree: start with those having parent_id None
            root_tasks = children_map.get(None, [])
            result = []
            for task in root_tasks:
                result.append(task)
                self._collect_children(task, children_map, result, level=1)
            return result

    def _collect_children(self, parent: Task, children_map: dict, result: list, level: int) -> None:
        kids = children_map.get(parent.id, [])
        for kid in kids:
            result.append(kid)
            self._collect_children(kid, children_map, result, level + 1)

    async def bulk_write_tasks(self, tenant_id: str, tasks: List[TaskUpsert]) -> List[Task]:
        created_tasks = []
        for task_data in tasks:
            if task_data.id:
                # update existing
                updated = await self._update_task_in_db(tenant_id, task_data.id, task_data)
                if updated:
                    created_tasks.append(updated)
                    await self._run_events("task.updated", tenant_id, updated.model_dump())
            else:
                # create new
                new_task = await self._insert_task(tenant_id, task_data)
                created_tasks.append(new_task)
                await self._run_events("task.created", tenant_id, new_task.model_dump())
        return created_tasks

    async def add_task(self, tenant_id: str, task: TaskCreate) -> Task:
        new_task = await self._insert_task(tenant_id, task)
        await self._run_events("task.created", tenant_id, new_task.model_dump())
        return new_task

    async def update_task_status(self, tenant_id: str, task_id: str, status: TaskStatus) -> Task:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "UPDATE tasks SET status = $1, updated_at = now() WHERE id = $2 AND tenant_id = $3 RETURNING *",
                status.value,
                uuid.UUID(task_id),
                tenant_id,
            )
            if row is None:
                raise ValueError(f"Task {task_id} not found for tenant {tenant_id}")
            task = Task.from_db_record(row)
            await self._run_events("task.status_changed", tenant_id, task.model_dump())
            return task

    async def delete_task(self, tenant_id: str, task_id: str) -> bool:
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM tasks WHERE id = $1 AND tenant_id = $2",
                uuid.UUID(task_id),
                tenant_id,
            )
            deleted = result == "DELETE 1"
            if deleted:
                await self._run_events("task.deleted", tenant_id, {"id": task_id})
            return deleted

    async def create_child_task(self, tenant_id: str, parent_id: str, task: TaskCreate) -> Task:
        # Ensure parent exists
        async with self.pool.acquire() as conn:
            parent_exists = await conn.fetchval(
                "SELECT 1 FROM tasks WHERE id = $1 AND tenant_id = $2",
                uuid.UUID(parent_id),
                tenant_id,
            )
            if not parent_exists:
                raise ValueError(f"Parent task {parent_id} not found")
            task_data = task.model_dump()
            task_data.pop("parent_id", None)
            task_in = TaskCreate(parent_id=parent_id, **task_data)
            return await self.add_task(tenant_id, task_in)

    async def link_tasks_dependency(self, tenant_id: str, task_id: str, depends_on_id: str) -> None:
        if task_id == depends_on_id:
            raise ValueError("A task cannot depend on itself")
        # Ensure both tasks exist and belong to tenant
        async with self.pool.acquire() as conn:
            tasks = await conn.fetch(
                "SELECT id FROM tasks WHERE id = ANY($1) AND tenant_id = $2",
                [uuid.UUID(task_id), uuid.UUID(depends_on_id)],
                tenant_id,
            )
            ids = {str(r["id"]) for r in tasks}
            if len(ids) != 2:
                missing = {task_id, depends_on_id} - ids
                raise ValueError(f"Tasks not found: {missing}")
            await conn.execute(
                "INSERT INTO task_dependencies (task_id, depends_on_task_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
                uuid.UUID(task_id),
                uuid.UUID(depends_on_id),
            )
        await self._run_events(
            "task.dependency_added",
            tenant_id,
            {"task_id": task_id, "depends_on_task_id": depends_on_id},
        )

    async def list_tasks_ready_to_work_on(self, tenant_id: str) -> List[Task]:
        """
        A task is ready if:
        - its status is not DONE or CANCELLED
        - all its dependencies are DONE
        """
        async with self.pool.acquire() as conn:
            query = """
            SELECT t.* FROM tasks t
            WHERE t.tenant_id = $1
              AND t.status NOT IN ('done', 'cancelled')
              AND NOT EXISTS (
                SELECT 1 FROM task_dependencies d
                JOIN tasks dep ON dep.id = d.depends_on_task_id
                WHERE d.task_id = t.id
                  AND dep.status != 'done'
              )
            ORDER BY t.created_at
            """
            rows = await conn.fetch(query, tenant_id)
            return [Task.from_db_record(r) for r in rows]

    async def _insert_task(self, tenant_id: str, task_data: TaskBase) -> Task:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """INSERT INTO tasks (tenant_id, title, description, status, parent_id)
                   VALUES ($1, $2, $3, $4, $5)
                   RETURNING *""",
                tenant_id,
                task_data.title,
                task_data.description,
                task_data.status.value,
                uuid.UUID(task_data.parent_id) if task_data.parent_id else None,
            )
            return Task.from_db_record(row)

    async def _update_task_in_db(self, tenant_id: str, task_id: str, task_data: TaskUpsert) -> Optional[Task]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """UPDATE tasks SET title = $1, description = $2, status = $3, parent_id = $4,
                          updated_at = now()
                   WHERE id = $5 AND tenant_id = $6
                   RETURNING *""",
                task_data.title,
                task_data.description,
                task_data.status.value,
                uuid.UUID(task_data.parent_id) if task_data.parent_id else None,
                uuid.UUID(task_id),
                tenant_id,
            )
            if row is None:
                return None
            return Task.from_db_record(row)