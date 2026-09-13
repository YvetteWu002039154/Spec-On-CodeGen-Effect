from __future__ import annotations

import abc
import asyncio
import json
import uuid
from typing import Any, Dict, List, Optional, Protocol

import asyncpg
import redis.asyncio as aioredis

from pydantic_ai_todo.types import Todo


# ----------------------------------------------------------------------
# Sync storage protocols
# ----------------------------------------------------------------------
class TodoStorageProtocol(Protocol):
    @property
    def todos(self) -> List[Todo]: ...


class TodoStorage:
    """Simple in‑memory sync storage (for backwards compatibility)."""
    def __init__(self) -> None:
        self._todos: List[Todo] = []

    @property
    def todos(self) -> List[Todo]:
        return self._todos


# ----------------------------------------------------------------------
# Async storage protocol
# ----------------------------------------------------------------------
class AsyncTodoStorageProtocol(abc.ABC):
    @abc.abstractmethod
    async def add_todo(self, todo: Todo) -> Todo: ...

    @abc.abstractmethod
    async def get_todo(self, id: str) -> Optional[Todo]: ...

    @abc.abstractmethod
    async def get_todos(self) -> List[Todo]: ...

    @abc.abstractmethod
    async def remove_todo(self, id: str) -> bool: ...

    @abc.abstractmethod
    async def set_todos(self, todos: List[Todo]) -> None: ...

    @abc.abstractmethod
    async def update_todo(self, id: str) -> Optional[Todo]: ...


# ----------------------------------------------------------------------
# In‑memory async storage
# ----------------------------------------------------------------------
class AsyncMemoryStorage(AsyncTodoStorageProtocol):
    def __init__(self) -> None:
        self._todos: Dict[str, Todo] = {}
        self._lock = asyncio.Lock()

    async def add_todo(self, todo: Todo) -> Todo:
        if not todo.id:
            todo.id = uuid.uuid4().hex
        async with self._lock:
            self._todos[todo.id] = todo
        return todo

    async def get_todo(self, id: str) -> Optional[Todo]:
        async with self._lock:
            return self._todos.get(id)

    async def get_todos(self) -> List[Todo]:
        async with self._lock:
            return list(self._todos.values())

    async def remove_todo(self, id: str) -> bool:
        async with self._lock:
            if id in self._todos:
                del self._todos[id]
                return True
            return False

    async def set_todos(self, todos: List[Todo]) -> None:
        async with self._lock:
            self._todos = {t.id: t for t in todos if t.id is not None}

    async def update_todo(self, id: str) -> Optional[Todo]:
        async with self._lock:
            return self._todos.get(id)


# ----------------------------------------------------------------------
# Postgres async storage
# ----------------------------------------------------------------------
class AsyncPostgresStorage(AsyncTodoStorageProtocol):
    def __init__(self, dsn: str = "postgresql://postgres:postgres@localhost:5432/todo") -> None:
        self._dsn = dsn
        self._pool: Optional[asyncpg.Pool] = None

    async def initialize(self) -> None:
        self._pool = await asyncpg.create_pool(self._dsn)
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS todos (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL DEFAULT '',
                    active_form TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'pending',
                    parent_id TEXT,
                    depends_on TEXT[] DEFAULT '{}',
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
                """
            )

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()

    async def _acquire(self) -> asyncpg.Connection:
        if not self._pool:
            raise RuntimeError("Storage not initialized. Call initialize() first.")
        return await self._pool.acquire()

    async def add_todo(self, todo: Todo) -> Todo:
        if not todo.id:
            todo.id = uuid.uuid4().hex
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO todos (id, content, active_form, status, parent_id, depends_on)
                VALUES ($1, $2, $3, $4, $5, $6::text[])
                """,
                todo.id,
                todo.content,
                todo.active_form,
                todo.status,
                todo.parent_id,
                todo.depends_on or [],
            )
        return todo

    async def get_todo(self, id: str) -> Optional[Todo]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM todos WHERE id = $1", id)
            if row is None:
                return None
            return Todo(
                active_form=row["active_form"],
                content=row["content"],
                depends_on=list(row["depends_on"]) if row["depends_on"] else [],
                id=row["id"],
                parent_id=row["parent_id"],
                status=row["status"],
            )

    async def get_todos(self) -> List[Todo]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM todos")
        return [
            Todo(
                active_form=r["active_form"],
                content=r["content"],
                depends_on=list(r["depends_on"]) if r["depends_on"] else [],
                id=r["id"],
                parent_id=r["parent_id"],
                status=r["status"],
            )
            for r in rows
        ]

    async def remove_todo(self, id: str) -> bool:
        async with self._pool.acquire() as conn:
            result = await conn.execute("DELETE FROM todos WHERE id = $1", id)
            return result == "DELETE 1"

    async def set_todos(self, todos: List[Todo]) -> None:
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("DELETE FROM todos")
                for t in todos:
                    await conn.execute(
                        """
                        INSERT INTO todos (id, content, active_form, status, parent_id, depends_on)
                        VALUES ($1, $2, $3, $4, $5, $6::text[])
                        """,
                        t.id or uuid.uuid4().hex,
                        t.content,
                        t.active_form,
                        t.status,
                        t.parent_id,
                        t.depends_on or [],
                    )

    async def update_todo(self, id: str) -> Optional[Todo]:
        return await self.get_todo(id)


# ----------------------------------------------------------------------
# Redis async storage
# ----------------------------------------------------------------------
class AsyncRedisStorage(AsyncTodoStorageProtocol):
    def __init__(self, redis_url: str = "redis://localhost:6379/0") -> None:
        self._redis: Optional[aioredis.Redis] = None
        self._redis_url = redis_url

    async def initialize(self) -> None:
        self._redis = aioredis.from_url(self._redis_url, decode_responses=True)

    async def close(self) -> None:
        if self._redis:
            await self._redis.close()

    def _todo_key(self, todo_id: str) -> str:
        return f"todo:{todo_id}"

    async def add_todo(self, todo: Todo) -> Todo:
        if not todo.id:
            todo.id = uuid.uuid4().hex
        await self._redis.set(self._todo_key(todo.id), todo.model_dump_json())
        await self._redis.sadd("todos:all", todo.id)
        return todo

    async def get_todo(self, id: str) -> Optional[Todo]:
        data = await self._redis.get(self._todo_key(id))
        if data is None:
            return None
        return Todo.model_validate_json(data)

    async def get_todos(self) -> List[Todo]:
        ids = await self._redis.smembers("todos:all")
        if not ids:
            return []
        keys = [self._todo_key(i) for i in ids]
        data = await self._redis.mget(keys)
        todos = []
        for d in data:
            if d:
                todos.append(Todo.model_validate_json(d))
        return todos

    async def remove_todo(self, id: str) -> bool:
        existed = await self._redis.delete(self._todo_key(id))
        if existed:
            await self._redis.srem("todos:all", id)
            return True
        return False

    async def set_todos(self, todos: List[Todo]) -> None:
        # clear everything
        await self._redis.delete("todos:all")
        pipe = self._redis.pipeline()
        for t in todos:
            tid = t.id or uuid.uuid4().hex
            pipe.sadd("todos:all", tid)
            pipe.set(self._todo_key(tid), t.model_dump_json())
        await pipe.execute()

    async def update_todo(self, id: str) -> Optional[Todo]:
        return await self.get_todo(id)

