from __future__ import annotations

import asyncio
import datetime
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Protocol,
    TypeVar,
    runtime_checkable,
)
from pydantic import BaseModel, Field

TodoStatus = Literal['pending', 'in_progress', 'completed', 'blocked']


class Todo(BaseModel):
    active_form: str
    content: str
    depends_on: Optional[List[str]] = None
    id: Optional[str] = None
    parent_id: Optional[str] = None
    status: TodoStatus


class TodoItem(BaseModel):
    active_form: Optional[str] = None
    content: Optional[str] = None
    depends_on: Optional[List[str]] = None
    id: Optional[str] = None
    parent_id: Optional[str] = None
    status: Optional[TodoStatus] = None


class TodoStatusUpdate(BaseModel):
    status: Optional[TodoStatus] = None
    todo_id: Optional[str] = None


class TodoEventType(Enum):
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    COMPLETED = "completed"
    STATUS_CHANGED = "status_changed"

    @property
    def name(self) -> str:
        return self.value


class TodoEvent(BaseModel):
    event_type: TodoEventType
    previous_state: Optional[Todo] = None
    timestamp: Optional[datetime.datetime] = None
    todo: Todo


EventCallback = Callable[[TodoEvent], None]


class TodoEventEmitter:
    def __init__(self) -> None:
        self._listeners: Dict[TodoEventType, List[EventCallback]] = {}

    def on(self, event_type: TodoEventType, callback: EventCallback) -> EventCallback:
        self._listeners.setdefault(event_type, []).append(callback)
        return callback

    def off(self, event_type: TodoEventType, callback: EventCallback) -> bool:
        listeners = self._listeners.get(event_type, [])
        if callback in listeners:
            listeners.remove(callback)
            return True
        return False

    def emit(self, event: TodoEvent) -> None:
        for callback in self._listeners.get(event.event_type, []):
            callback(event)

    def on_created(self, callback: EventCallback) -> EventCallback:
        return self.on(TodoEventType.CREATED, callback)

    def on_updated(self, callback: EventCallback) -> EventCallback:
        return self.on(TodoEventType.UPDATED, callback)

    def on_deleted(self, callback: EventCallback) -> EventCallback:
        return self.on(TodoEventType.DELETED, callback)

    def on_completed(self, callback: EventCallback) -> EventCallback:
        return self.on(TodoEventType.COMPLETED, callback)

    def on_status_changed(self, callback: EventCallback) -> EventCallback:
        return self.on(TodoEventType.STATUS_CHANGED, callback)


@runtime_checkable
class TodoStorageProtocol(Protocol):
    todos: List[Todo]


class TodoStorage:
    def __init__(self) -> None:
        self.todos: List[Todo] = []


@runtime_checkable
class AsyncTodoStorageProtocol(Protocol):
    async def add_todo(self, todo: Todo) -> Todo:
        ...

    async def get_todo(self, id: str) -> Optional[Todo]:
        ...

    async def get_todos(self) -> List[Todo]:
        ...

    async def remove_todo(self, id: str) -> bool:
        ...

    async def set_todos(self, todos: List[Todo]) -> None:
        ...

    async def update_todo(self, id: str) -> Optional[Todo]:
        ...


class AsyncMemoryStorage:
    def __init__(self) -> None:
        self._todos: List[Todo] = []
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        pass

    async def close(self) -> None:
        pass

    async def add_todo(self, todo: Todo) -> Todo:
        async with self._lock:
            self._todos.append(todo)
            return todo

    async def get_todo(self, id: str) -> Optional[Todo]:
        async with self._lock:
            for t in self._todos:
                if t.id == id:
                    return t
            return None

    async def get_todos(self) -> List[Todo]:
        async with self._lock:
            return list(self._todos)

    async def remove_todo(self, id: str) -> bool:
        async with self._lock:
            for i, t in enumerate(self._todos):
                if t.id == id:
                    del self._todos[i]
                    return True
            return False

    async def set_todos(self, todos: List[Todo]) -> None:
        async with self._lock:
            self._todos = list(todos)

    async def update_todo(self, id: str) -> Optional[Todo]:
        async with self._lock:
            for i, t in enumerate(self._todos):
                if t.id == id:
                    # Placeholder: actual update logic would be provided externally
                    return t
            return None


class AsyncPostgresStorage:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._pool = None

    async def initialize(self) -> None:
        raise NotImplementedError("PostgreSQL storage is a stub; implement with asyncpg")

    async def close(self) -> None:
        raise NotImplementedError("PostgreSQL storage is a stub; implement with asyncpg")

    async def add_todo(self, todo: Todo) -> Todo:
        raise NotImplementedError("PostgreSQL storage is a stub; implement with asyncpg")

    async def get_todo(self, id: str) -> Optional[Todo]:
        raise NotImplementedError("PostgreSQL storage is a stub; implement with asyncpg")

    async def get_todos(self) -> List[Todo]:
        raise NotImplementedError("PostgreSQL storage is a stub; implement with asyncpg")

    async def remove_todo(self, id: str) -> bool:
        raise NotImplementedError("PostgreSQL storage is a stub; implement with asyncpg")

    async def set_todos(self, todos: List[Todo]) -> None:
        raise NotImplementedError("PostgreSQL storage is a stub; implement with asyncpg")

    async def update_todo(self, id: str) -> Optional[Todo]:
        raise NotImplementedError("PostgreSQL storage is a stub; implement with asyncpg")


class AsyncRedisStorage:
    def __init__(self, url: str) -> None:
        self._url = url
        self._client = None

    async def initialize(self) -> None:
        raise NotImplementedError("Redis storage is a stub; implement with redis.asyncio")

    async def close(self) -> None:
        raise NotImplementedError("Redis storage is a stub; implement with redis.asyncio")

    async def add_todo(self, todo: Todo) -> Todo:
        raise NotImplementedError("Redis storage is a stub; implement with redis.asyncio")

    async def get_todo(self, id: str) -> Optional[Todo]:
        raise NotImplementedError("Redis storage is a stub; implement with redis.asyncio")

    async def get_todos(self) -> List[Todo]:
        raise NotImplementedError("Redis storage is a stub; implement with redis.asyncio")

    async def remove_todo(self, id: str) -> bool:
        raise NotImplementedError("Redis storage is a stub; implement with redis.asyncio")

    async def set_todos(self, todos: List[Todo]) -> None:
        raise NotImplementedError("Redis storage is a stub; implement with redis.asyncio")

    async def update_todo(self, id: str) -> Optional[Todo]:
        raise NotImplementedError("Redis storage is a stub; implement with redis.asyncio")


T = TypeVar('T')


class AbstractToolset(Protocol[T]):
    """Placeholder for an AbstractToolset class."""


class TodoCapability:
    def __init__(
        self,
        async_storage: Optional[AsyncTodoStorageProtocol] = None,
        storage: Optional[TodoStorageProtocol] = None,
        descriptions: Optional[Dict[str, str]] = None,
        enable_subtasks: bool = False,
    ) -> None:
        self.async_storage = async_storage
        self.storage = storage
        self.descriptions = descriptions or {}
        self.enable_subtasks = enable_subtasks

    def get_instructions(self) -> Any:
        return "Todo capability instructions placeholder"

    def get_serialization_name(self) -> str:
        return "todo"

    def get_toolset(self) -> Optional[AbstractToolset[Any]]:
        return None