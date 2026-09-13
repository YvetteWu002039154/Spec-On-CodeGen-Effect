from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Literal,
    Optional,
    Protocol,
    TypeVar,
    Union,
)

# ---------------------------------------------------------------------------
# Types used across the system
# ---------------------------------------------------------------------------

TodoStatus = Literal["pending", "in_progress", "completed", "blocked"]

# ---------------------------------------------------------------------------
# pydantic_ai_todo.types
# ---------------------------------------------------------------------------

@dataclass
class Todo:
    active_form: str
    content: str
    status: TodoStatus = "pending"
    depends_on: Optional[List[str]] = None
    id: Optional[str] = None
    parent_id: Optional[str] = None

@dataclass
class TodoItem:
    active_form: Optional[str] = None
    content: Optional[str] = None
    depends_on: Optional[List[str]] = None
    id: Optional[str] = None
    parent_id: Optional[str] = None
    status: Optional[TodoStatus] = None

@dataclass
class TodoStatusUpdate:
    todo_id: Optional[str] = None
    status: Optional[TodoStatus] = None

# ---------------------------------------------------------------------------
# pydantic_ai_todo.events
# ---------------------------------------------------------------------------

class TodoEventType(Enum):
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    STATUS_CHANGED = "status_changed"
    COMPLETED = "completed"

    @property
    def name(self) -> str:
        return self.value

@dataclass
class TodoEvent:
    event_type: TodoEventType
    todo: Todo
    previous_state: Optional[Todo] = None
    timestamp: Optional[datetime] = field(default_factory=datetime.utcnow)

EventCallback = Callable[[TodoEvent], None]

class TodoEventEmitter:
    def __init__(self) -> None:
        self._listeners: Dict[TodoEventType, List[EventCallback]] = {
            t: [] for t in TodoEventType
        }

    def on(self, event_type: TodoEventType, callback: EventCallback) -> EventCallback:
        self._listeners[event_type].append(callback)
        return callback

    def off(self, event_type: TodoEventType, callback: EventCallback) -> bool:
        try:
            self._listeners[event_type].remove(callback)
            return True
        except ValueError:
            return False

    def emit(self, event: TodoEvent) -> None:
        for listener in self._listeners.get(event.event_type, []):
            listener(event)

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

# ---------------------------------------------------------------------------
# pydantic_ai_todo.storage  (protocols and base classes)
# ---------------------------------------------------------------------------

class TodoStorageProtocol(Protocol):
    todos: List[Todo]

class TodoStorage:
    def __init__(self) -> None:
        self.todos: List[Todo] = []

class AsyncTodoStorageProtocol(ABC):
    @abstractmethod
    async def add_todo(self, todo: Todo) -> Todo:
        ...

    @abstractmethod
    async def get_todo(self, id: str) -> Optional[Todo]:
        ...

    @abstractmethod
    async def get_todos(self) -> List[Todo]:
        ...

    @abstractmethod
    async def remove_todo(self, id: str) -> bool:
        ...

    @abstractmethod
    async def set_todos(self, todos: List[Todo]) -> None:
        ...

    @abstractmethod
    async def update_todo(self, id: str) -> Optional[Todo]:
        ...

# ---------------------------------------------------------------------------
# Concrete async storage implementations
# ---------------------------------------------------------------------------

class AsyncMemoryStorage(AsyncTodoStorageProtocol):
    def __init__(self) -> None:
        self._todos: List[Todo] = []

    async def add_todo(self, todo: Todo) -> Todo:
        self._todos.append(todo)
        return todo

    async def get_todo(self, id: str) -> Optional[Todo]:
        for t in self._todos:
            if t.id == id:
                return t
        return None

    async def get_todos(self) -> List[Todo]:
        return list(self._todos)

    async def remove_todo(self, id: str) -> bool:
        for i, t in enumerate(self._todos):
            if t.id == id:
                del self._todos[i]
                return True
        return False

    async def set_todos(self, todos: List[Todo]) -> None:
        self._todos = list(todos)

    async def update_todo(self, id: str) -> Optional[Todo]:
        for t in self._todos:
            if t.id == id:
                # Return the existing todo as no update data is provided
                return t
        return None


class AsyncPostgresStorage(AsyncTodoStorageProtocol):
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._pool = None

    async def initialize(self) -> None:
        import asyncpg
        self._pool = await asyncpg.create_pool(dsn=self._dsn)

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()

    async def add_todo(self, todo: Todo) -> Todo:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """INSERT INTO todos (id, active_form, content, status, depends_on, parent_id)
                   VALUES ($1, $2, $3, $4, $5, $6) RETURNING *""",
                todo.id, todo.active_form, todo.content, todo.status,
                todo.depends_on, todo.parent_id,
            )
            return self._row_to_todo(row)

    async def get_todo(self, id: str) -> Optional[Todo]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM todos WHERE id = $1", id
            )
            return self._row_to_todo(row) if row else None

    async def get_todos(self) -> List[Todo]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM todos")
            return [self._row_to_todo(r) for r in rows]

    async def remove_todo(self, id: str) -> bool:
        async with self._pool.acquire() as conn:
            result = await conn.execute("DELETE FROM todos WHERE id = $1", id)
            return result == "DELETE 1"

    async def set_todos(self, todos: List[Todo]) -> None:
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("DELETE FROM todos")
                for todo in todos:
                    await conn.execute(
                        """INSERT INTO todos (id, active_form, content, status, depends_on, parent_id)
                           VALUES ($1, $2, $3, $4, $5, $6)""",
                        todo.id, todo.active_form, todo.content, todo.status,
                        todo.depends_on, todo.parent_id,
                    )

    async def update_todo(self, id: str) -> Optional[Todo]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM todos WHERE id = $1", id)
            if row is None:
                return None
            # The spec only provides an id, so we return the existing row unchanged.
            return self._row_to_todo(row)

    @staticmethod
    def _row_to_todo(row: Any) -> Todo:
        return Todo(
            id=row["id"],
            active_form=row["active_form"],
            content=row["content"],
            status=row["status"],
            depends_on=row["depends_on"],
            parent_id=row["parent_id"],
        )


class AsyncRedisStorage(AsyncTodoStorageProtocol):
    def __init__(self, redis_url: str) -> None:
        self._redis_url = redis_url
        self._client = None

    async def initialize(self) -> None:
        import redis.asyncio as aioredis
        self._client = aioredis.from_url(self._redis_url)

    async def close(self) -> None:
        if self._client:
            await self._client.close()

    async def add_todo(self, todo: Todo) -> Todo:
        key = f"todo:{todo.id}"
        await self._client.hset(key, mapping=self._todo_to_dict(todo))
        return todo

    async def get_todo(self, id: str) -> Optional[Todo]:
        data = await self._client.hgetall(f"todo:{id}")
        if not data:
            return None
        return self._dict_to_todo(data)

    async def get_todos(self) -> List[Todo]:
        keys = []
        async for key in self._client.scan_iter(match="todo:*"):
            keys.append(key)
        todos = []
        for key in keys:
            data = await self._client.hgetall(key)
            if data:
                todos.append(self._dict_to_todo(data))
        return todos

    async def remove_todo(self, id: str) -> bool:
        return await self._client.delete(f"todo:{id}") > 0

    async def set_todos(self, todos: List[Todo]) -> None:
        # Remove all existing todo keys
        keys = []
        async for key in self._client.scan_iter(match="todo:*"):
            keys.append(key)
        if keys:
            await self._client.delete(*keys)
        for todo in todos:
            await self._client.hset(f"todo:{todo.id}", mapping=self._todo_to_dict(todo))

    async def update_todo(self, id: str) -> Optional[Todo]:
        data = await self._client.hgetall(f"todo:{id}")
        if not data:
            return None
        # No update data provided; return the existing todo unchanged.
        return self._dict_to_todo(data)

    @staticmethod
    def _todo_to_dict(todo: Todo) -> Dict[str, str]:
        return {
            "id": todo.id or "",
            "active_form": todo.active_form,
            "content": todo.content,
            "status": todo.status,
            "depends_on": ",".join(todo.depends_on) if todo.depends_on else "",
            "parent_id": todo.parent_id or "",
        }

    @staticmethod
    def _dict_to_todo(data: Dict[bytes, bytes]) -> Todo:
        def b(key: str) -> str:
            return data.get(key.encode(), b"").decode()

        depends_raw = b("depends_on")
        depends_list = depends_raw.split(",") if depends_raw else []
        parent_raw = b("parent_id")
        parent = parent_raw if parent_raw else None

        return Todo(
            id=b("id"),
            active_form=b("active_form"),
            content=b("content"),
            status=b("status"),  # type: ignore
            depends_on=depends_list or None,
            parent_id=parent,
        )

# ---------------------------------------------------------------------------
# pydantic_ai_todo.capability  (simplified tool integration)
# ---------------------------------------------------------------------------

T = TypeVar("T")

class AbstractToolset(Generic[T]):
    pass  # Implementation not specified, kept as placeholder

class TodoCapability:
    def __init__(
        self,
        storage: Optional[TodoStorageProtocol] = None,
        async_storage: Optional[AsyncTodoStorageProtocol] = None,
        descriptions: Optional[Dict[str, str]] = None,
        enable_subtasks: bool = False,
    ) -> None:
        self.storage = storage
        self.async_storage = async_storage
        self.descriptions = descriptions
        self.enable_subtasks = enable_subtasks

    def get_instructions(self) -> Any:
        return self.descriptions or {}

    def get_serialization_name(self) -> str:
        return self.__class__.__name__

    def get_toolset(self) -> Optional[AbstractToolset[Any]]:
        # Placeholder – no concrete toolset provided in the spec
        return None