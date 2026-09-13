import asyncio
import asyncpg
import json
import logging
from typing import Any, Callable, Dict, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
import aiohttp

# ============= Models =============
@dataclass
class Task:
    id: int
    tenant_id: str
    parent_id: Optional[int]
    title: str
    description: Optional[str]
    status: str  # pending, in_progress, completed, cancelled
    created_at: datetime
    updated_at: datetime
    children: List['Task'] = field(default_factory=list)


# ============= Event System =============
EventCallback = Callable[..., Any]


class EventBus:
    def __init__(self):
        self._sync_listeners: Dict[str, List[EventCallback]] = {}
        self._async_listeners: Dict[str, List[EventCallback]] = {}
        self._webhooks: Dict[str, List[str]] = {}  # event -> list of URLs

    def on(self, event: str, callback: EventCallback, is_async: bool = False):
        if is_async:
            self._async_listeners.setdefault(event, []).append(callback)
        else:
            self._sync_listeners.setdefault(event, []).append(callback)

    def add_webhook(self, event: str, url: str):
        self._webhooks.setdefault(event, []).append(url)

    async def emit(self, event: str, *args, **kwargs):
        # sync listeners
        for cb in self._sync_listeners.get(event, []):
            cb(*args, **kwargs)
        # async listeners
        for cb in self._async_listeners.get(event, []):
            await cb(*args, **kwargs)
        # webhooks
        urls = self._webhooks.get(event, [])
        if urls:
            data = kwargs.get('data', {})
            async with aiohttp.ClientSession() as session:
                for url in urls:
                    try:
                        async with session.post(url, json=data) as resp:
                            if resp.status >= 400:
                                logging.warning(f"Webhook to {url} failed with status {resp.status}")
                    except Exception:
                        logging.exception(f"Webhook dispatch failed for {url}")


# ============= TodoToolset =============
class TodoToolset:
    def __init__(self, dsn: str, pool: asyncpg.Pool = None):
        self.dsn = dsn
        self._pool = pool
        self.event_bus = EventBus()

    async def initialize(self):
        if self._pool is None:
            self._pool = await asyncpg.create_pool(self.dsn)
        # ensure tables exist
        async with self._pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id SERIAL PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    parent_id INTEGER REFERENCES tasks(id) ON DELETE SET NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS task_dependencies (
                    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                    depends_on_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                    PRIMARY KEY (task_id, depends_on_id)
                );
                CREATE INDEX IF NOT EXISTS idx_tasks_tenant ON tasks(tenant_id);
                CREATE INDEX IF NOT EXISTS idx_tasks_parent ON tasks(parent_id);
                CREATE INDEX IF NOT EXISTS idx_task_deps_task ON task_dependencies(task_id);
                CREATE INDEX IF NOT EXISTS idx_task_deps_dep ON task_dependencies(depends_on_id);
            """)

    async def close(self):
        if self._pool:
            await self._pool.close()

    # ---------- Core operations ----------
    async def add_task(
        self,
        tenant_id: str,
        title: str,
        description: Optional[str] = None,
        parent_id: Optional[int] = None,
        status: str = 'pending',
    ) -> Task:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO tasks (tenant_id, parent_id, title, description, status)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id, tenant_id, parent_id, title, description, status, created_at, updated_at
                """,
                tenant_id, parent_id, title, description, status,
            )
        task = self._row_to_task(row)
        await self.event_bus.emit('task_created', data={'task_id': task.id, 'tenant_id': tenant_id, 'title': title, 'status': status})
        return task

    async def create_child_task(
        self,
        parent_id: int,
        title: str,
        description: Optional[str] = None,
        status: str = 'pending',
    ) -> Task:
        # fetch parent's tenant
        async with self._pool.acquire() as conn:
            parent = await conn.fetchrow("SELECT tenant_id FROM tasks WHERE id=$1", parent_id)
            if not parent:
                raise ValueError(f"Parent task {parent_id} not found")
            tenant_id = parent['tenant_id']
        return await self.add_task(tenant_id, title, description, parent_id, status)

    async def update_task_status(self, task_id: int, status: str) -> Optional[Task]:
        valid_statuses = {'pending', 'in_progress', 'completed', 'cancelled'}
        status = status.lower()
        if status not in valid_statuses:
            raise ValueError(f"Invalid status '{status}'. Must be one of {valid_statuses}")
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    """
                    UPDATE tasks SET status=$1, updated_at=NOW() WHERE id=$2
                    RETURNING id, tenant_id, parent_id, title, description, status, created_at, updated_at
                    """,
                    status, task_id
                )
                if row is None:
                    return None
                task = self._row_to_task(row)
        await self.event_bus.emit('task_status_changed', data={'task_id': task.id, 'new_status': status, 'old_status': 'unknown'})
        return task

    async def delete_task(self, task_id: int) -> bool:
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                # First, get all subtasks recursively
                subtask_ids = await self._get_all_subtasks(conn, task_id)
                all_ids = [task_id] + subtask_ids
                # Remove dependencies that involve any of these tasks
                await conn.execute("DELETE FROM task_dependencies WHERE task_id = ANY($1) OR depends_on_id = ANY($1)", all_ids)
                # Delete all tasks
                result = await conn.execute("DELETE FROM tasks WHERE id = ANY($1)", all_ids)
                deleted_count = int(result.split()[-1])  # e.g. "DELETE 3"
                if deleted_count == 0:
                    return False
        await self.event_bus.emit('task_deleted', data={'task_id': task_id, 'cascade_deleted': subtask_ids})
        return True

    async def _get_all_subtasks(self, conn, parent_id: int) -> List[int]:
        """Recursively gets all child IDs under a parent."""
        children = await conn.fetch("SELECT id FROM tasks WHERE parent_id=$1", parent_id)
        child_ids = [r['id'] for r in children]
        for cid in child_ids:
            child_ids.extend(await self._get_all_subtasks(conn, cid))
        return child_ids

    async def get_task(self, task_id: int) -> Optional[Task]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, tenant_id, parent_id, title, description, status, created_at, updated_at FROM tasks WHERE id=$1",
                task_id
            )
            if row:
                return self._row_to_task(row)
        return None

    async def list_tasks(self, tenant_id: str, hierarchical: bool = True) -> Union[List[Task], Dict]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, tenant_id, parent_id, title, description, status, created_at, updated_at FROM tasks WHERE tenant_id=$1 ORDER BY created_at",
                tenant_id
            )
            tasks = [self._row_to_task(r) for r in rows]
            if not hierarchical:
                return tasks
            # Build tree
            task_map = {t.id: t for t in tasks}
            roots = []
            for t in tasks:
                if t.parent_id is None:
                    roots.append(t)
                else:
                    parent = task_map.get(t.parent_id)
                    if parent:
                        parent.children.append(t)
                    else:
                        # orphan, treat as root
                        roots.append(t)
            return roots

    async def bulk_write(self, tasks_data: List[Dict[str, Any]], tenant_id: str) -> List[Task]:
        """
        tasks_data: list of dicts with keys: id (optional for update), parent_id, title, description, status.
        If id present, update; else insert.
        """
        results = []
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                for item in tasks_data:
                    task_id = item.get('id')
                    if task_id:
                        # update
                        fields = {
                            'title': item.get('title'),
                            'description': item.get('description'),
                            'status': item.get('status'),
                            'parent_id': item.get('parent_id'),
                        }
                        updates = []
                        params = []
                        for k, v in fields.items():
                            if v is not None:
                                updates.append(f"{k}=${len(params)+1}")
                                params.append(v)
                        if not updates:
                            continue
                        params.append(task_id)
                        params.append(tenant_id)
                        row = await conn.fetchrow(
                            f"UPDATE tasks SET {', '.join(updates)}, updated_at=NOW() WHERE id=${len(params)-1} AND tenant_id=${len(params)} RETURNING id, tenant_id, parent_id, title, description, status, created_at, updated_at",
                            *params
                        )
                        if row:
                            results.append(self._row_to_task(row))
                    else:
                        # insert
                        row = await conn.fetchrow(
                            """
                            INSERT INTO tasks (tenant_id, parent_id, title, description, status)
                            VALUES ($1, $2, $3, $4, $5)
                            RETURNING id, tenant_id, parent_id, title, description, status, created_at, updated_at
                            """,
                            tenant_id,
                            item.get('parent_id'),
                            item['title'],
                            item.get('description'),
                            item.get('status', 'pending'),
                        )
                        results.append(self._row_to_task(row))
        for task in results:
            await self.event_bus.emit('task_created_or_updated', data={'task_id': task.id, 'tenant_id': tenant_id, 'title': task.title, 'status': task.status})
        return results

    async def link_tasks_with_dependency(self, task_id: int, depends_on_task_id: int) -> bool:
        if task_id == depends_on_task_id:
            raise ValueError("A task cannot depend on itself")
        # Check no circular dependency
        if await self._would_create_circular_dependency(task_id, depends_on_task_id):
            raise ValueError("Adding this dependency would create a circular dependency")
        async with self._pool.acquire() as conn:
            try:
                await conn.execute(
                    "INSERT INTO task_dependencies (task_id, depends_on_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
                    task_id, depends_on_task_id
                )
            except asyncpg.ForeignKeyViolationError:
                raise ValueError("One or both tasks do not exist")
        await self.event_bus.emit('dependency_added', data={'task_id': task_id, 'depends_on': depends_on_task_id})
        return True

    async def _would_create_circular_dependency(self, task_id: int, new_dep: int) -> bool:
        # traverse dependencies upward from new_dep; if we find task_id, circular
        visited = set()
        async with self._pool.acquire() as conn:
            to_check = [new_dep]
            while to_check:
                current = to_check.pop()
                if current == task_id:
                    return True
                if current in visited:
                    continue
                visited.add(current)
                deps = await conn.fetch("SELECT depends_on_id FROM task_dependencies WHERE task_id=$1", current)
                to_check.extend(r['depends_on_id'] for r in deps)
        return False

    async def list_tasks_ready_to_work(self, tenant_id: str) -> List[Task]:
        """
        Returns tasks that are not completed/cancelled and have all dependencies satisfied (all depends_on tasks are completed).
        """
        async with self._pool.acquire() as conn:
            # Get all tasks for tenant
            rows = await conn.fetch(
                """
                SELECT t.id, t.tenant_id, t.parent_id, t.title, t.description, t.status, t.created_at, t.updated_at
                FROM tasks t
                WHERE t.tenant_id = $1 AND t.status NOT IN ('completed', 'cancelled')
                """,
                tenant_id
            )
            tasks = [self._row_to_task(r) for r in rows]
            ready = []
            for task in tasks:
                # check dependencies
                dep_rows = await conn.fetch(
                    "SELECT depends_on_id FROM task_dependencies WHERE task_id=$1", task.id
                )
                if not dep_rows:
                    ready.append(task)
                    continue
                all_deps_completed = True
                for dr in dep_rows:
                    dep_status_row = await conn.fetchrow("SELECT status FROM tasks WHERE id=$1", dr['depends_on_id'])
                    if not dep_status_row or dep_status_row['status'] != 'completed':
                        all_deps_completed = False
                        break
                if all_deps_completed:
                    ready.append(task)
        return ready

    def _row_to_task(self, row) -> Task:
        return Task(
            id=row['id'],
            tenant_id=row['tenant_id'],
            parent_id=row['parent_id'],
            title=row['title'],
            description=row['description'],
            status=row['status'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
        )

    # Convenience method for Pydantic AI tool integration
    def register_tools(self, agent):
        """
        Register all methods as tools on a Pydantic AI agent.
        Assumes agent has a `tool` decorator or registration method.
        This is a stub; actual implementation depends on the agent framework.
        """
        pass