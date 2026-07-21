from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union
import asyncpg
from asyncpg import Pool, Connection
from pydantic import BaseModel, Field, field_serializer, field_validator, model_serializer


class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"


class Task(BaseModel):
    id: str
    tenant_id: str
    title: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.TODO
    parent_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = dict(from_attributes=True)


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    status: Optional[TaskStatus] = TaskStatus.TODO
    parent_id: Optional[str] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    parent_id: Optional[str] = None


class BulkTaskItem(BaseModel):
    id: Optional[str] = None
    title: str
    description: Optional[str] = None
    status: Optional[TaskStatus] = TaskStatus.TODO
    parent_id: Optional[str] = None


class TaskDependency(BaseModel):
    id: str
    task_id: str
    depends_on_task_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TodoToolset:
    def __init__(self, tenant_id: str, pool: Pool):
        self.tenant_id = tenant_id
        self.pool = pool
        self._event_callbacks: List[Callable[[str, Dict[str, Any]], Any]] = []

    async def initialize_schema(self) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    status TEXT NOT NULL DEFAULT 'todo',
                    parent_id TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    FOREIGN KEY (parent_id) REFERENCES tasks(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS task_dependencies (
                    id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    depends_on_task_id TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
                    FOREIGN KEY (depends_on_task_id) REFERENCES tasks(id) ON DELETE CASCADE,
                    UNIQUE(task_id, depends_on_task_id)
                );

                CREATE INDEX IF NOT EXISTS idx_tasks_tenant ON tasks(tenant_id);
                CREATE INDEX IF NOT EXISTS idx_tasks_parent ON tasks(parent_id);
                CREATE INDEX IF NOT EXISTS idx_task_deps_task ON task_dependencies(task_id);
                CREATE INDEX IF NOT EXISTS idx_task_deps_depends ON task_dependencies(depends_on_task_id);
            """)

    async def _emit(self, event_type: str, data: Dict[str, Any]) -> None:
        tasks = [callback(event_type, data) for callback in self._event_callbacks]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def on_event(self, callback: Callable[[str, Dict[str, Any]], Any]) -> None:
        self._event_callbacks.append(callback)

    async def add_task(self, task: TaskCreate) -> Task:
        now = datetime.now(timezone.utc)
        task_id = str(uuid.uuid4())
        status = task.status or TaskStatus.TODO

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """INSERT INTO tasks (id, tenant_id, title, description, status, parent_id, created_at, updated_at)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                   RETURNING id, tenant_id, title, description, status, parent_id, created_at, updated_at""",
                task_id, self.tenant_id, task.title, task.description, status.value,
                task.parent_id, now, now
            )
            if row is None:
                raise RuntimeError("Failed to insert task")
            new_task = Task.model_validate(row)
        await self._emit("task_created", {"task": new_task.model_dump()})
        return new_task

    async def get_task(self, task_id: str) -> Optional[Task]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, tenant_id, title, description, status, parent_id, created_at, updated_at FROM tasks WHERE id = $1 AND tenant_id = $2",
                task_id, self.tenant_id
            )
            if row is None:
                return None
            return Task.model_validate(row)

    async def update_task_status(self, task_id: str, new_status: TaskStatus) -> Task:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """UPDATE tasks
                   SET status = $1, updated_at = $2
                   WHERE id = $3 AND tenant_id = $4
                   RETURNING id, tenant_id, title, description, status, parent_id, created_at, updated_at""",
                new_status.value, datetime.now(timezone.utc), task_id, self.tenant_id
            )
            if row is None:
                raise ValueError(f"Task {task_id} not found or access denied")
            task = Task.model_validate(row)
        await self._emit("task_status_changed", {"task_id": task_id, "new_status": new_status.value, "task": task.model_dump()})
        return task

    async def delete_task(self, task_id: str) -> None:
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM tasks WHERE id = $1 AND tenant_id = $2",
                task_id, self.tenant_id
            )
            if result == "DELETE 0":
                raise ValueError(f"Task {task_id} not found or access denied")
        await self._emit("task_deleted", {"task_id": task_id})

    async def create_child_task(self, parent_id: str, child: TaskCreate) -> Task:
        parent = await self.get_task(parent_id)
        if parent is None:
            raise ValueError(f"Parent task {parent_id} not found")
        if parent.tenant_id != self.tenant_id:
            raise ValueError("Parent task does not belong to this tenant")
        child_data = child.model_dump(exclude_unset=True)
        child_data["parent_id"] = parent_id
        return await self.add_task(TaskCreate(**child_data))

    async def link_tasks(self, task_id: str, depends_on_task_id: str) -> TaskDependency:
        if task_id == depends_on_task_id:
            raise ValueError("A task cannot depend on itself")
        async with self.pool.acquire() as conn:
            # Check both tasks exist and belong to tenant
            tasks_exist = await conn.fetchval(
                "SELECT COUNT(*) FROM tasks WHERE id = ANY($1::text[]) AND tenant_id = $2",
                [task_id, depends_on_task_id], self.tenant_id
            )
            if tasks_exist != 2:
                raise ValueError("One or both tasks not found or access denied")

            # Check no existing identical dependency
            existing = await conn.fetchval(
                "SELECT id FROM task_dependencies WHERE task_id = $1 AND depends_on_task_id = $2",
                task_id, depends_on_task_id
            )
            if existing:
                raise ValueError("Dependency already exists")

            dep_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            row = await conn.fetchrow(
                """INSERT INTO task_dependencies (id, task_id, depends_on_task_id, created_at)
                   VALUES ($1, $2, $3, $4)
                   RETURNING id, task_id, depends_on_task_id, created_at""",
                dep_id, task_id, depends_on_task_id, now
            )
            if row is None:
                raise RuntimeError("Failed to create dependency")
            dep = TaskDependency.model_validate(row)
        await self._emit("dependency_added", dep.model_dump())
        return dep

    async def list_tasks(self, hierarchical: bool = False) -> List[Task]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, tenant_id, title, description, status, parent_id, created_at, updated_at FROM tasks WHERE tenant_id = $1 ORDER BY created_at",
                self.tenant_id
            )
        tasks = [Task.model_validate(row) for row in rows]
        if not hierarchical:
            return tasks
        else:
            return self._build_hierarchy(tasks)

    def _build_hierarchy(self, tasks: List[Task]) -> List[Task]:
        task_map = {t.id: t for t in tasks}
        roots = []
        for t in tasks:
            if t.parent_id is None or t.parent_id not in task_map:
                roots.append(t)
            else:
                parent = task_map[t.parent_id]
                # Use runtime extension to hold children (we won't modify the model)
                if not hasattr(parent, "subtasks"):
                    setattr(parent, "subtasks", [])
                parent.subtasks.append(t)
        return roots

    async def list_ready_tasks(self) -> List[Task]:
        async with self.pool.acquire() as conn:
            # Ready tasks: status in (TODO, BLOCKED) and all dependencies are completed
            rows = await conn.fetch("""
                SELECT t.id, t.tenant_id, t.title, t.description, t.status, t.parent_id, t.created_at, t.updated_at
                FROM tasks t
                WHERE t.tenant_id = $1
                  AND t.status IN ('todo', 'blocked')
                  AND NOT EXISTS (
                      SELECT 1 FROM task_dependencies td
                      JOIN tasks dep ON td.depends_on_task_id = dep.id
                      WHERE td.task_id = t.id
                        AND dep.status != 'completed'
                  )
            """, self.tenant_id)
        return [Task.model_validate(row) for row in rows]

    async def bulk_write_tasks(self, items: List[BulkTaskItem]) -> List[Task]:
        results = []
        for item in items:
            if item.id:
                # Update
                async with self.pool.acquire() as conn:
                    update_fields = []
                    values = []
                    idx = 1
                    if item.title is not None:
                        update_fields.append(f"title = ${idx}")
                        values.append(item.title)
                        idx += 1
                    if item.description is not None:
                        update_fields.append(f"description = ${idx}")
                        values.append(item.description)
                        idx += 1
                    if item.status is not None:
                        update_fields.append(f"status = ${idx}")
                        values.append(item.status.value)
                        idx += 1
                    if item.parent_id is not None:
                        update_fields.append(f"parent_id = ${idx}")
                        values.append(item.parent_id)
                        idx += 1
                    if not update_fields:
                        row = await conn.fetchrow(
                            "SELECT id, tenant_id, title, description, status, parent_id, created_at, updated_at FROM tasks WHERE id = $1 AND tenant_id = $2",
                            item.id, self.tenant_id
                        )
                        if row is None:
                            raise ValueError(f"Task {item.id} not found or access denied")
                        results.append(Task.model_validate(row))
                        continue
                    update_fields.append(f"updated_at = ${idx}")
                    values.append(datetime.now(timezone.utc))
                    idx += 1
                    values.extend([item.id, self.tenant_id])
                    query = f"UPDATE tasks SET {', '.join(update_fields)} WHERE id = ${idx} AND tenant_id = ${idx+1} RETURNING id, tenant_id, title, description, status, parent_id, created_at, updated_at"
                    row = await conn.fetchrow(query, *values)
                    if row is None:
                        raise ValueError(f"Task {item.id} not found or access denied")
                    task = Task.model_validate(row)
                await self._emit("task_updated", {"task": task.model_dump()})
                results.append(task)
            else:
                # Create
                task = await self.add_task(TaskCreate(
                    title=item.title,
                    description=item.description,
                    status=item.status,
                    parent_id=item.parent_id
                ))
                results.append(task)
        return results