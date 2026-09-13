from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    Generic,
    List,
    Literal,
    Optional,
    Protocol,
    TypeVar,
    Union,
    runtime_checkable,
)

try:
    import asyncpg  # type: ignore
except Exception:  # pragma: no cover
    asyncpg = None  # type: ignore

try:
    import redis.asyncio as redis  # type: ignore
except Exception:  # pragma: no cover
    redis = None  # type: ignore


TodoStatus = Literal["pending", "in_progress", "completed", "blocked"]


@dataclass
class Todo:
    active_form: str
    content: str
    depends_on: Optional[List[str]] = None
    id: Optional[str] = None
    parent_id: Optional[str] = None
    status: TodoStatus = "pending"

    def __post_init__(self) -> None:
        if self.status not in ("pending", "in_progress", "completed", "blocked"):
            raise ValueError("Invalid status")
        if self.depends_on is not None:
            if not isinstance(self.depends_on, list) or any(not isinstance(x, str) for x in self.depends_on):
                raise ValueError("depends_on must be a list[str] or None")
        if self.id is not None and not isinstance(self.id, str):
            raise ValueError("id must be str or None")
        if self.parent_id is not None and not isinstance(self.parent_id, str):
            raise ValueError("parent_id must be str or None")
        if not isinstance(self.active_form, str):
            raise ValueError("active_form must be str")
        if not isinstance(self.content, str):
            raise ValueError("content must be str")


@dataclass
class TodoItem:
    active_form: Optional[str] = None
    content: Optional[str] = None
    depends_on: Optional[List[str]] = None
    id: Optional[str] = None
    parent_id: Optional[str] = None
    status: Optional[TodoStatus] = None

    def __post_init__(self) -> None:
        if self.status is not None and self.status not in ("pending", "in_progress", "completed", "blocked"):
            raise ValueError("Invalid status")
        if self.depends_on is not None:
            if not isinstance(self.depends_on, list) or any(not isinstance(x, str) for x in self.depends_on):
                raise ValueError("depends_on must be a list[str] or None")
        if self.id is not None and not isinstance(self.id, str):
            raise ValueError("id must be str or None")
        if self.parent_id is not None and not isinstance(self.parent_id, str):
            raise ValueError("parent_id must be str or None")
        if self.active_form is not None and not isinstance(self.active_form, str):
            raise ValueError("active_form must be str or None")
        if self.content is not None and not isinstance(self.content, str):
            raise ValueError("content must be str or None")


@dataclass
class TodoStatusUpdate:
    status: Optional[TodoStatus] = None
    todo_id: Optional[str] = None

    def __post_init__(self) -> None:
        if self.status is not None and self.status not in ("pending", "in_progress", "completed", "blocked"):
            raise ValueError("Invalid status")
        if self.todo_id is not None and not isinstance(self.todo_id, str):
            raise ValueError("todo_id must be str or None")


class TodoEventType(Enum):
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    STATUS_CHANGED = "status_changed"
    COMPLETED = "completed"

    @property
    def name(self) -> str:  # type: ignore[override]
        return super().name


@dataclass
class TodoEvent:
    event_type: TodoEventType
    todo: Todo
    previous_state: Optional[Todo] = None
    timestamp: Optional[datetime] = None

    def __post_init__(self) -> None:
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


EventCallback = Callable[[TodoEvent], Any]


class TodoEventEmitter:
    def __init__(self) -> None:
        self._callbacks: Dict[TodoEventType, List[EventCallback]] = {}

    def on(self, event_type: TodoEventType, callback: EventCallback) -> EventCallback:
        self._callbacks.setdefault(event_type, []).append(callback)
        return callback

    def off(self, event_type: TodoEventType, callback: EventCallback) -> bool:
        callbacks = self._callbacks.get(event_type)
        if not callbacks:
            return False
        try:
            callbacks.remove(callback)
            if not callbacks:
                self._callbacks.pop(event_type, None)
            return True
        except ValueError:
            return False

    def emit(self, event: TodoEvent) -> None:
        callbacks = list(self._callbacks.get(event.event_type, []))
        for cb in callbacks:
            cb(event)

    def on_created(self, callback: EventCallback) -> EventCallback:
        return self.on(TodoEventType.CREATED, callback)

    def on_updated(self, callback: EventCallback) -> EventCallback:
        return self.on(TodoEventType.UPDATED, callback)

    def on_deleted(self, callback: EventCallback) -> EventCallback:
        return self.on(TodoEventType.DELETED, callback)

    def on_status_changed(self, callback: EventCallback) -> EventCallback:
        return self.on(TodoEventType.STATUS_CHANGED, callback)

    def on_completed(self, callback: EventCallback) -> EventCallback:
        return self.on(TodoEventType.COMPLETED, callback)


@runtime_checkable
class TodoStorageProtocol(Protocol):
    @property
    def todos(self) -> List[Todo]: ...


class TodoStorage(TodoStorageProtocol):
    def __init__(self, todos: Optional[List[Todo]] = None) -> None:
        self._todos: List[Todo] = list(todos) if todos is not None else []

    @property
    def todos(self) -> List[Todo]:
        return self._todos


@runtime_checkable
class AsyncTodoStorageProtocol(Protocol):
    async def add_todo(self, todo: Todo) -> Todo: ...
    async def get_todo(self, id: str) -> Optional[Todo]: ...
    async def get_todos(self) -> List[Todo]: ...
    async def remove_todo(self, id: str) -> bool: ...
    async def set_todos(self, todos: List[Todo]) -> None: ...
    async def update_todo(self, id: str) -> Optional[Todo]: ...


class AsyncMemoryStorage(AsyncTodoStorageProtocol):
    def __init__(self, todos: Optional[List[Todo]] = None) -> None:
        self._todos: Dict[str, Todo] = {}
        if todos:
            for t in todos:
                tid = t.id or self._new_id()
                self._todos[tid] = Todo(
                    active_form=t.active_form,
                    content=t.content,
                    depends_on=list(t.depends_on) if t.depends_on is not None else None,
                    id=tid,
                    parent_id=t.parent_id,
                    status=t.status,
                )
        self._lock = asyncio.Lock()

    def _new_id(self) -> str:
        return uuid.uuid4().hex

    async def add_todo(self, todo: Todo) -> Todo:
        async with self._lock:
            tid = todo.id or self._new_id()
            stored = Todo(
                active_form=todo.active_form,
                content=todo.content,
                depends_on=list(todo.depends_on) if todo.depends_on is not None else None,
                id=tid,
                parent_id=todo.parent_id,
                status=todo.status,
            )
            self._todos[tid] = stored
            return stored

    async def get_todo(self, id: str) -> Optional[Todo]:
        async with self._lock:
            t = self._todos.get(id)
            if t is None:
                return None
            return Todo(
                active_form=t.active_form,
                content=t.content,
                depends_on=list(t.depends_on) if t.depends_on is not None else None,
                id=t.id,
                parent_id=t.parent_id,
                status=t.status,
            )

    async def get_todos(self) -> List[Todo]:
        async with self._lock:
            return [
                Todo(
                    active_form=t.active_form,
                    content=t.content,
                    depends_on=list(t.depends_on) if t.depends_on is not None else None,
                    id=t.id,
                    parent_id=t.parent_id,
                    status=t.status,
                )
                for t in self._todos.values()
            ]

    async def remove_todo(self, id: str) -> bool:
        async with self._lock:
            return self._todos.pop(id, None) is not None

    async def set_todos(self, todos: List[Todo]) -> None:
        async with self._lock:
            self._todos.clear()
            for t in todos:
                tid = t.id or self._new_id()
                self._todos[tid] = Todo(
                    active_form=t.active_form,
                    content=t.content,
                    depends_on=list(t.depends_on) if t.depends_on is not None else None,
                    id=tid,
                    parent_id=t.parent_id,
                    status=t.status,
                )

    async def update_todo(self, id: str) -> Optional[Todo]:
        async with self._lock:
            t = self._todos.get(id)
            if t is None:
                return None
            self._todos[id] = Todo(
                active_form=t.active_form,
                content=t.content,
                depends_on=list(t.depends_on) if t.depends_on is not None else None,
                id=t.id,
                parent_id=t.parent_id,
                status=t.status,
            )
            updated = self._todos[id]
            return Todo(
                active_form=updated.active_form,
                content=updated.content,
                depends_on=list(updated.depends_on) if updated.depends_on is not None else None,
                id=updated.id,
                parent_id=updated.parent_id,
                status=updated.status,
            )


class AsyncPostgresStorage(AsyncTodoStorageProtocol):
    def __init__(self, dsn: str, table_name: str = "todos") -> None:
        self._dsn = dsn
        self._table = table_name
        self._pool: Any = None

    async def initialize(self) -> None:
        if asyncpg is None:
            raise RuntimeError("asyncpg is not installed")
        if self._pool is None:
            self._pool = await asyncpg.create_pool(dsn=self._dsn)
        async with self._pool.acquire() as conn:
            await conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self._table} (
                    id TEXT PRIMARY KEY,
                    active_form TEXT NOT NULL,
                    content TEXT NOT NULL,
                    depends_on JSONB NULL,
                    parent_id TEXT NULL,
                    status TEXT NOT NULL
                )
                """
            )

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    def _ensure_pool(self) -> Any:
        if self._pool is None:
            raise RuntimeError("Storage not initialized")
        return self._pool

    def _row_to_todo(self, row: Any) -> Todo:
        depends_on = row["depends_on"]
        if depends_on is not None and not isinstance(depends_on, list):
            depends_on = list(depends_on)
        return Todo(
            id=row["id"],
            active_form=row["active_form"],
            content=row["content"],
            depends_on=depends_on,
            parent_id=row["parent_id"],
            status=row["status"],
        )

    async def add_todo(self, todo: Todo) -> Todo:
        pool = self._ensure_pool()
        tid = todo.id or uuid.uuid4().hex
        async with pool.acquire() as conn:
            await conn.execute(
                f"""
                INSERT INTO {self._table} (id, active_form, content, depends_on, parent_id, status)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (id) DO UPDATE SET
                    active_form = EXCLUDED.active_form,
                    content = EXCLUDED.content,
                    depends_on = EXCLUDED.depends_on,
                    parent_id = EXCLUDED.parent_id,
                    status = EXCLUDED.status
                """,
                tid,
                todo.active_form,
                todo.content,
                json.dumps(todo.depends_on) if todo.depends_on is not None else None,
                todo.parent_id,
                todo.status,
            )
            row = await conn.fetchrow(f"SELECT * FROM {self._table} WHERE id = $1", tid)
        if row is None:
            return Todo(
                id=tid,
                active_form=todo.active_form,
                content=todo.content,
                depends_on=list(todo.depends_on) if todo.depends_on is not None else None,
                parent_id=todo.parent_id,
                status=todo.status,
            )
        return self._row_to_todo(row)

    async def get_todo(self, id: str) -> Optional[Todo]:
        pool = self._ensure_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(f"SELECT * FROM {self._table} WHERE id = $1", id)
        if row is None:
            return None
        return self._row_to_todo(row)

    async def get_todos(self) -> List[Todo]:
        pool = self._ensure_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(f"SELECT * FROM {self._table}")
        return [self._row_to_todo(r) for r in rows]

    async def remove_todo(self, id: str) -> bool:
        pool = self._ensure_pool()
        async with pool.acquire() as conn:
            result = await conn.execute(f"DELETE FROM {self._table} WHERE id = $1", id)
        try:
            count = int(str(result).split()[-1])
        except Exception:
            count = 0
        return count > 0

    async def set_todos(self, todos: List[Todo]) -> None:
        pool = self._ensure_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(f"TRUNCATE TABLE {self._table}")
                for t in todos:
                    tid = t.id or uuid.uuid4().hex
                    await conn.execute(
                        f"""
                        INSERT INTO {self._table} (id, active_form, content, depends_on, parent_id, status)
                        VALUES ($1, $2, $3, $4, $5, $6)
                        """,
                        tid,
                        t.active_form,
                        t.content,
                        json.dumps(t.depends_on) if t.depends_on is not None else None,
                        t.parent_id,
                        t.status,
                    )

    async def update_todo(self, id: str) -> Optional[Todo]:
        pool = self._ensure_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(f"SELECT * FROM {self._table} WHERE id = $1", id)
            if row is None:
                return None
            await conn.execute(
                f"""
                UPDATE {self._table}
                SET active_form = $2, content = $3, depends_on = $4, parent_id = $5, status = $6
                WHERE id = $1
                """,
                id,
                row["active_form"],
                row["content"],
                row["depends_on"],
                row["parent_id"],
                row["status"],
            )
            row2 = await conn.fetchrow(f"SELECT * FROM {self._table} WHERE id = $1", id)
        if row2 is None:
            return None
        return self._row_to_todo(row2)


class AsyncRedisStorage(AsyncTodoStorageProtocol):
    def __init__(self, url: str, key: str = "todos") -> None:
        self._url = url
        self._key = key
        self._client: Any = None

    async def initialize(self) -> None:
        if redis is None:
            raise RuntimeError("redis is not installed")
        if self._client is None:
            self._client = redis.from_url(self._url, decode_responses=True)

    async def close(self) -> None:
        if self._client is not None:
            try:
                await self._client.close()
            finally:
                self._client = None

    def _ensure_client(self) -> Any:
        if self._client is None:
            raise RuntimeError("Storage not initialized")
        return self._client

    def _todo_to_dict(self, t: Todo) -> Dict[str, Any]:
        return {
            "id": t.id,
            "active_form": t.active_form,
            "content": t.content,
            "depends_on": t.depends_on,
            "parent_id": t.parent_id,
            "status": t.status,
        }

    def _dict_to_todo(self, d: Dict[str, Any]) -> Todo:
        return Todo(
            id=d.get("id"),
            active_form=d["active_form"],
            content=d["content"],
            depends_on=d.get("depends_on"),
            parent_id=d.get("parent_id"),
            status=d["status"],
        )

    async def _load_all(self) -> Dict[str, Dict[str, Any]]:
        client = self._ensure_client()
        raw = await client.get(self._key)
        if not raw:
            return {}
        data = json.loads(raw)
        if not isinstance(data, dict):
            return {}
        return data

    async def _save_all(self, data: Dict[str, Dict[str, Any]]) -> None:
        client = self._ensure_client()
        await client.set(self._key, json.dumps(data))

    async def add_todo(self, todo: Todo) -> Todo:
        data = await self._load_all()
        tid = todo.id or uuid.uuid4().hex
        stored = Todo(
            id=tid,
            active_form=todo.active_form,
            content=todo.content,
            depends_on=list(todo.depends_on) if todo.depends_on is not None else None,
            parent_id=todo.parent_id,
            status=todo.status,
        )
        data[tid] = self._todo_to_dict(stored)
        await self._save_all(data)
        return stored

    async def get_todo(self, id: str) -> Optional[Todo]:
        data = await self._load_all()
        d = data.get(id)
        if d is None:
            return None
        return self._dict_to_todo(d)

    async def get_todos(self) -> List[Todo]:
        data = await self._load_all()
        return [self._dict_to_todo(d) for d in data.values()]

    async def remove_todo(self, id: str) -> bool:
        data = await self._load_all()
        existed = id in data
        if existed:
            data.pop(id, None)
            await self._save_all(data)
        return existed

    async def set_todos(self, todos: List[Todo]) -> None:
        data: Dict[str, Dict[str, Any]] = {}
        for t in todos:
            tid = t.id or uuid.uuid4().hex
            stored = Todo(
                id=tid,
                active_form=t.active_form,
                content=t.content,
                depends_on=list(t.depends_on) if t.depends_on is not None else None,
                parent_id=t.parent_id,
                status=t.status,
            )
            data[tid] = self._todo_to_dict(stored)
        await self._save_all(data)

    async def update_todo(self, id: str) -> Optional[Todo]:
        data = await self._load_all()
        d = data.get(id)
        if d is None:
            return None
        todo = self._dict_to_todo(d)
        data[id] = self._todo_to_dict(todo)
        await self._save_all(data)
        return todo


T = TypeVar("T")


class AbstractToolset(Protocol, Generic[T]):
    pass


class TodoCapability:
    def __init__(
        self,
        *,
        async_storage: Optional[AsyncTodoStorageProtocol] = None,
        descriptions: Optional[Dict[str, str]] = None,
        enable_subtasks: bool = False,
        storage: Optional[TodoStorageProtocol] = None,
    ) -> None:
        self.async_storage: Optional[AsyncTodoStorageProtocol] = async_storage
        self.descriptions: Optional[Dict[str, str]] = descriptions
        self.enable_subtasks: bool = bool(enable_subtasks)
        self.storage: Optional[TodoStorageProtocol] = storage

    def get_instructions(self) -> Any:
        return None

    def get_serialization_name(self) -> str:
        return "TodoCapability"

    def get_toolset(self) -> Optional[AbstractToolset[Any]]:
        return None


__all__ = [
    "AbstractToolset",
    "AsyncMemoryStorage",
    "AsyncPostgresStorage",
    "AsyncRedisStorage",
    "AsyncTodoStorageProtocol",
    "EventCallback",
    "Todo",
    "TodoCapability",
    "TodoEvent",
    "TodoEventEmitter",
    "TodoEventType",
    "TodoItem",
    "TodoStatusUpdate",
    "TodoStorage",
    "TodoStorageProtocol",
]