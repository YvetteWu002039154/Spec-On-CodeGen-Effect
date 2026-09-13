from __future__ import annotations

import asyncio
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
    runtime_checkable,
)

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# pydantic_ai_todo.types
# ---------------------------------------------------------------------------

class Todo(BaseModel):
    id: Optional[str] = None
    content: str
    status: Literal['pending', 'in_progress', 'completed', 'blocked'] = "pending"
    active_form: str = ""
    depends_on: Optional[List[str]] = None
    parent_id: Optional[str] = None  # str | None


class TodoItem(BaseModel):
    id: Optional[str] = None
    content: Optional[str] = None
    status: Optional[Literal['pending', 'in_progress', 'completed', 'blocked']] = None
    active_form: Optional[str] = None
    depends_on: Optional[List[str]] = None
    parent_id: Optional[str] = None


class TodoStatusUpdate(BaseModel):
    todo_id: Optional[str] = None
    status: Optional[Literal['pending', 'in_progress', 'completed', 'blocked']] = None


# ---------------------------------------------------------------------------
# pydantic_ai_todo.events
# ---------------------------------------------------------------------------

class TodoEventType(Enum):
    CREATED = "created"
    UPDATED = "updated"
    COMPLETED = "completed"
    DELETED = "deleted"
    STATUS_CHANGED = "status_changed"

    @property
    def name(self) -> str:
        return self.value


class TodoEvent(BaseModel):
    event_type: TodoEventType
    todo: Todo
    previous_state: Optional[Todo] = None
    timestamp: Optional[datetime] = Field(default_factory=datetime.now)


EventCallback = Callable[[TodoEvent], None]


class TodoEventEmitter:
    def __init__(self) -> None:
        self._listeners: Dict[TodoEventType, List[EventCallback]] = {
            et: [] for et in TodoEventType
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
        for cb in self._listeners[event.event_type]:
            cb(event)

    def on_created(self, callback: EventCallback) -> EventCallback:
        return self.on(TodoEventType.CREATED, callback)

    def on_updated(self, callback: EventCallback) -> EventCallback:
        return self.on(TodoEventType.UPDATED, callback)

    def on_completed(self, callback: EventCallback) -> EventCallback:
        return self.on(TodoEventType.COMPLETED, callback)

    def on_deleted(self, callback: EventCallback) -> EventCallback:
        return self.on(TodoEventType.DELETED, callback)

    def on_status_changed(self, callback: EventCallback) -> EventCallback:
        return self.on(TodoEventType.STATUS_CHANGED, callback)


# ---------------------------------------------------------------------------
# pydantic_ai_todo.storage
# ---------------------------------------------------------------------------

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


@runtime_checkable
class TodoStorageProtocol(Protocol):
    todos: List[Todo]


class TodoStorage:
    def __init__(self) -> None:
        self.todos: List[Todo] = []


class AsyncMemoryStorage:
    def __init__(self) -> None:
        self._todos: Dict[str, Todo] = {}

    async def add_todo(self, todo: Todo) -> Todo:
        if not todo.id:
            todo.id = str(len(self._todos) + 1)
        self._todos[todo.id] = todo
        return todo

    async def get_todo(self, id: str) -> Optional[Todo]:
        return self._todos.get(id)

    async def get_todos(self) -> List[Todo]:
        return list(self._todos.values())

    async def remove_todo(self, id: str) -> bool:
        if id in self._todos:
            del self._todos[id]
            return True
        return False

    async def set_todos(self, todos: List[Todo]) -> None:
        self._todos = {t.id: t for t in todos if t.id}

    async def update_todo(self, id: str) -> Optional[Todo]:
        return self._todos.get(id)


class AsyncPostgresStorage:
    def __init__(self, connection_string: str = "") -> None:
        self._conn: Any = None
        self._initialized: bool = False
        self._todos: Dict[str, Todo] = {}
        self._connection_string = connection_string

    async def initialize(self) -> None:
        # simulate connection
        await asyncio.sleep(0)
        self._initialized = True
        self._todos = {}

    async def close(self) -> None:
        self._initialized = False

    async def add_todo(self, todo: Todo) -> Todo:
        if not self._initialized:
            raise RuntimeError("Storage not initialized")
        if not todo.id:
            todo.id = str(len(self._todos) + 1)
        self._todos[todo.id] = todo
        return todo

    async def get_todo(self, id: str) -> Optional[Todo]:
        if not self._initialized:
            raise RuntimeError("Storage not initialized")
        return self._todos.get(id)

    async def get_todos(self) -> List[Todo]:
        if not self._initialized:
            raise RuntimeError("Storage not initialized")
        return list(self._todos.values())

    async def remove_todo(self, id: str) -> bool:
        if not self._initialized:
            raise RuntimeError("Storage not initialized")
        if id in self._todos:
            del self._todos[id]
            return True
        return False

    async def set_todos(self, todos: List[Todo]) -> None:
        if not self._initialized:
            raise RuntimeError("Storage not initialized")
        self._todos = {t.id: t for t in todos if t.id}

    async def update_todo(self, id: str) -> Optional[Todo]:
        if not self._initialized:
            raise RuntimeError("Storage not initialized")
        return self._todos.get(id)


class AsyncRedisStorage:
    def __init__(self, redis_url: str = "") -> None:
        self._redis: Any = None
        self._initialized: bool = False
        self._url = redis_url

    async def initialize(self) -> None:
        await asyncio.sleep(0)
        self._initialized = True

    async def close(self) -> None:
        self._initialized = False

    async def add_todo(self, todo: Todo) -> Todo:
        if not self._initialized:
            raise RuntimeError("Storage not initialized")
        # simplified: use in‑memory dict backed by redis simulation
        if not todo.id:
            todo.id = str(hash(todo.content))  # not production ready
        return todo

    async def get_todo(self, id: str) -> Optional[Todo]:
        if not self._initialized:
            raise RuntimeError("Storage not initialized")
        return None  # stub

    async def get_todos(self) -> List[Todo]:
        if not self._initialized:
            raise RuntimeError("Storage not initialized")
        return []

    async def remove_todo(self, id: str) -> bool:
        if not self._initialized:
            raise RuntimeError("Storage not initialized")
        return False

    async def set_todos(self, todos: List[Todo]) -> None:
        if not self._initialized:
            raise RuntimeError("Storage not initialized")

    async def update_todo(self, id: str) -> Optional[Todo]:
        if not self._initialized:
            raise RuntimeError("Storage not initialized")
        return None


# ---------------------------------------------------------------------------
# pydantic_ai_todo.capability
# ---------------------------------------------------------------------------

class TodoCapability:
    def __init__(
        self,
        storage: Optional[TodoStorageProtocol] = None,
        async_storage: Optional[AsyncTodoStorageProtocol] = None,
        enable_subtasks: bool = False,
        descriptions: Optional[Dict[str, str]] = None,
    ) -> None:
        self.storage = storage
        self.async_storage = async_storage
        self.enable_subtasks = enable_subtasks
        self.descriptions = descriptions or {}

    def get_instructions(self) -> Any:
        return "Manage todos using available tools."

    def get_serialization_name(self) -> str:
        return "todo"

    def get_toolset(self) -> Optional[Any]:
        # returns an AbstractToolset[Any] | None
        # Placeholder – can be extended by the actual framework integration.
        return None