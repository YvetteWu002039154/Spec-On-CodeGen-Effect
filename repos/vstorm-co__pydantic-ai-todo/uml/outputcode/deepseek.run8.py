from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Protocol,
    Union,
)

# --------------------------------------------------------------
# pydantic_ai_todo.types
# --------------------------------------------------------------

class TodoStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"


@dataclass
class Todo:
    content: str
    active_form: str = ""
    id: Optional[str] = None
    depends_on: Optional[List[str]] = field(default_factory=list)
    parent_id: Optional[str] = None
    status: TodoStatus = TodoStatus.PENDING


@dataclass
class TodoItem:
    content: Optional[str] = None
    active_form: Optional[str] = None
    id: Optional[str] = None
    depends_on: Optional[List[str]] = None
    parent_id: Optional[str] = None
    status: Optional[TodoStatus] = None


@dataclass
class TodoStatusUpdate:
    todo_id: Optional[str] = None
    status: Optional[TodoStatus] = None


# --------------------------------------------------------------
# pydantic_ai_todo.events
# --------------------------------------------------------------

class TodoEventType(Enum):
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    STATUS_CHANGED = "status_changed"
    COMPLETED = "completed"


EventCallback = Callable[["TodoEvent"], None]


@dataclass
class TodoEvent:
    event_type: TodoEventType
    todo: Todo
    previous_state: Optional[Todo] = None
    timestamp: Optional[datetime] = None


class TodoEventEmitter:
    def __init__(self) -> None:
        self._listeners: Dict[TodoEventType, List[EventCallback]] = {
            t: [] for t in TodoEventType
        }

    def on(self, event_type: TodoEventType, callback: EventCallback) -> EventCallback:
        self._listeners[event_type].append(callback)
        return callback

    def off(self, event_type: TodoEventType, callback: EventCallback) -> bool:
        listeners = self._listeners.get(event_type, [])
        if callback in listeners:
            listeners.remove(callback)
            return True
        return False

    def emit(self, event: TodoEvent) -> None:
        for cb in self._listeners.get(event.event_type, []):
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


# --------------------------------------------------------------
# pydantic_ai_todo.storage
# --------------------------------------------------------------

class TodoStorageProtocol(Protocol):
    todos: List[Todo]


class TodoStorage:
    def __init__(self) -> None:
        self.todos: List[Todo] = []


class AsyncTodoStorageProtocol(Protocol):
    async def add_todo(self, todo: Todo) -> Todo: ...
    async def get_todo(self, id: str) -> Optional[Todo]: ...
    async def get_todos(self) -> List[Todo]: ...
    async def remove_todo(self, id: str) -> bool: ...
    async def set_todos(self, todos: List[Todo]) -> None: ...
    async def update_todo(self, id: str) -> Optional[Todo]: ...


class AsyncMemoryStorage:
    def __init__(self) -> None:
        self._storage: Dict[str, Todo] = {}
        self._lock = asyncio.Lock()

    async def add_todo(self, todo: Todo) -> Todo:
        async with self._lock:
            if todo.id is None:
                todo.id = str(len(self._storage) + 1)
            self._storage[todo.id] = todo
            return todo

    async def get_todo(self, id: str) -> Optional[Todo]:
        async with self._lock:
            return self._storage.get(id)

    async def get_todos(self) -> List[Todo]:
        async with self._lock:
            return list(self._storage.values())

    async def remove_todo(self, id: str) -> bool:
        async with self._lock:
            if id in self._storage:
                del self._storage[id]
                return True
            return False

    async def set_todos(self, todos: List[Todo]) -> None:
        async with self._lock:
            self._storage = {t.id: t for t in todos if t.id is not None}

    async def update_todo(self, id: str) -> Optional[Todo]:
        async with self._lock:
            return self._storage.get(id)


class AsyncPostgresStorage:
    def __init__(self, dsn: str = "postgresql://localhost/todos") -> None:
        self._dsn = dsn
        self._memory = AsyncMemoryStorage()

    async def initialize(self) -> None:
        # Simulate table creation
        await asyncio.sleep(0)

    async def close(self) -> None:
        # Simulate connection closing
        await asyncio.sleep(0)

    async def add_todo(self, todo: Todo) -> Todo:
        return await self._memory.add_todo(todo)

    async def get_todo(self, id: str) -> Optional[Todo]:
        return await self._memory.get_todo(id)

    async def get_todos(self) -> List[Todo]:
        return await self._memory.get_todos()

    async def remove_todo(self, id: str) -> bool:
        return await self._memory.remove_todo(id)

    async def set_todos(self, todos: List[Todo]) -> None:
        await self._memory.set_todos(todos)

    async def update_todo(self, id: str) -> Optional[Todo]:
        return await self._memory.update_todo(id)


class AsyncRedisStorage:
    def __init__(self, url: str = "redis://localhost:6379") -> None:
        self._url = url
        self._memory = AsyncMemoryStorage()

    async def initialize(self) -> None:
        await asyncio.sleep(0)

    async def close(self) -> None:
        await asyncio.sleep(0)

    async def add_todo(self, todo: Todo) -> Todo:
        return await self._memory.add_todo(todo)

    async def get_todo(self, id: str) -> Optional[Todo]:
        return await self._memory.get_todo(id)

    async def get_todos(self) -> List[Todo]:
        return await self._memory.get_todos()

    async def remove_todo(self, id: str) -> bool:
        return await self._memory.remove_todo(id)

    async def set_todos(self, todos: List[Todo]) -> None:
        await self._memory.set_todos(todos)

    async def update_todo(self, id: str) -> Optional[Todo]:
        return await self._memory.update_todo(id)


# --------------------------------------------------------------
# pydantic_ai_todo.capability
# --------------------------------------------------------------

class TodoCapability:
    def __init__(
        self,
        *,
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
        return "Manage todos: create, read, update, delete, and change status."

    def get_serialization_name(self) -> str:
        return "todo"

    def get_toolset(self) -> Any:
        return None