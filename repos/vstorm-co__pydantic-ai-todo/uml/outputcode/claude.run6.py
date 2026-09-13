from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Callable, Literal, Optional, Protocol, runtime_checkable
from enum import Enum

try:
    from pydantic import BaseModel, Field
except ImportError:
    raise ImportError("pydantic is required")


# ─────────────────────────────────────────────
# pydantic_ai_todo/types.py
# ─────────────────────────────────────────────

class Todo(BaseModel):
    id: Optional[str] = None
    content: str
    active_form: str
    status: Literal['pending', 'in_progress', 'completed', 'blocked'] = 'pending'
    parent_id: str | None = None
    depends_on: Optional[list[str]] = None


class TodoItem(BaseModel):
    id: str | None = None
    content: Optional[str] = None
    active_form: Optional[str] = None
    status: Optional[Literal['pending', 'in_progress', 'completed', 'blocked']] = None
    parent_id: str | None = None
    depends_on: Optional[list[str]] = None


class TodoStatusUpdate(BaseModel):
    todo_id: Optional[str] = None
    status: Optional[Literal['pending', 'in_progress', 'completed', 'blocked']] = None


# ─────────────────────────────────────────────
# pydantic_ai_todo/events.py
# ─────────────────────────────────────────────

class TodoEventType(Enum):
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    STATUS_CHANGED = "status_changed"
    COMPLETED = "completed"


EventCallback = Callable[["TodoEvent"], None]


class TodoEvent(BaseModel):
    event_type: TodoEventType
    todo: Todo
    previous_state: Todo | None = None
    timestamp: Optional[datetime] = None

    class Config:
        arbitrary_types_allowed = True

    def model_post_init(self, __context: Any) -> None:
        if self.timestamp is None:
            object.__setattr__(self, 'timestamp', datetime.utcnow())


class TodoEventEmitter:
    def __init__(self) -> None:
        self._listeners: dict[TodoEventType, list[EventCallback]] = {
            event_type: [] for event_type in TodoEventType
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
        for callback in self._listeners.get(event.event_type, []):
            callback(event)

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


# ─────────────────────────────────────────────
# pydantic_ai_todo/storage.py
# ─────────────────────────────────────────────

@runtime_checkable
class TodoStorageProtocol(Protocol):
    @property
    def todos(self) -> list[Todo]:
        ...

    def get_todos(self) -> list[Todo]:
        ...

    def get_todo(self, id: str) -> Todo | None:
        ...

    def add_todo(self, todo: Todo) -> Todo:
        ...

    def update_todo(self, id: str) -> Todo | None:
        ...

    def remove_todo(self, id: str) -> bool:
        ...

    def set_todos(self, todos: list[Todo]) -> None:
        ...


@runtime_checkable
class AsyncTodoStorageProtocol(Protocol):
    async def get_todos(self) -> list[Todo]:
        ...

    async def get_todo(self, id: str) -> Todo | None:
        ...

    async def add_todo(self, todo: Todo) -> Todo:
        ...

    async def update_todo(self, id: str) -> Todo | None:
        ...

    async def remove_todo(self, id: str) -> bool:
        ...

    async def set_todos(self, todos: list[Todo]) -> None:
        ...


class TodoStorage:
    def __init__(self, todos: list[Todo] | None = None) -> None:
        self._todos: list[Todo] = todos if todos is not None else []

    @property
    def todos(self) -> list[Todo]:
        return self._todos

    def get_todos(self) -> list[Todo]:
        return list(self._todos)

    def get_todo(self, id: str) -> Todo | None:
        for todo in self._todos:
            if todo.id == id:
                return todo
        return None

    def add_todo(self, todo: Todo) -> Todo:
        self._todos.append(todo)
        return todo

    def update_todo(self, id: str) -> Todo | None:
        for todo in self._todos:
            if todo.id == id:
                return todo
        return None

    def remove_todo(self, id: str) -> bool:
        for i, todo in enumerate(self._todos):
            if todo.id == id:
                self._todos.pop(i)
                return True
        return False

    def set_todos(self, todos: list[Todo]) -> None:
        self._todos = list(todos)


class AsyncMemoryStorage:
    def __init__(self) -> None:
        self._todos: list[Todo] = []
        self._lock = asyncio.Lock()

    async def get_todos(self) -> list[Todo]:
        async with self._lock:
            return list(self._todos)

    async def get_todo(self, id: str) -> Todo | None:
        async with self._lock:
            for todo in self._todos:
                if todo.id == id:
                    return todo
            return None

    async def add_todo(self, todo: Todo) -> Todo:
        async with self._lock:
            self._todos.append(todo)
            return todo

    async def update_todo(self, id: str) -> Todo | None:
        async with self._lock:
            for todo in self._todos:
                if todo.id == id:
                    return todo
            return None

    async def remove_todo(self, id: str) -> bool:
        async with self._lock:
            for i, todo in enumerate(self._todos):
                if todo.id == id:
                    self._todos.pop(i)
                    return True
            return False

    async def set_todos(self, todos: list[Todo]) -> None:
        async with self._lock:
            self._todos = list(todos)


class AsyncPostgresStorage:
    def __init__(self, dsn: str = "") -> None:
        self._dsn = dsn
        self._connection: Any = None
        self._todos: list[Todo] = []

    async def initialize(self) -> None:
        pass

    async def close(self) -> None:
        if self._connection is not None:
            try:
                await self._connection.close()
            except Exception:
                pass
            self._connection = None

    async def get_todos(self) -> list[Todo]:
        return list(self._todos)

    async def get_todo(self, id: str) -> Todo | None:
        for todo in self._todos:
            if todo.id == id:
                return todo
        return None

    async def add_todo(self, todo: Todo) -> Todo:
        self._todos.append(todo)
        return todo

    async def update_todo(self, id: str) -> Todo | None:
        for todo in self._todos:
            if todo.id == id:
                return todo
        return None

    async def remove_todo(self, id: str) -> bool:
        for i, todo in enumerate(self._todos):
            if todo.id == id:
                self._todos.pop(i)
                return True
        return False

    async def set_todos(self, todos: list[Todo]) -> None:
        self._todos = list(todos)


class AsyncRedisStorage:
    def __init__(self, url: str = "redis://localhost:6379", key_prefix: str = "todo:") -> None:
        self._url = url
        self._key_prefix = key_prefix
        self._client: Any = None
        self._todos: list[Todo] = []

    async def initialize(self) -> None:
        pass

    async def close(self) -> None:
        if self._client is not None:
            try:
                await self._client.close()
            except Exception:
                pass
            self._client = None

    async def get_todos(self) -> list[Todo]:
        return list(self._todos)

    async def get_todo(self, id: str) -> Todo | None:
        for todo in self._todos:
            if todo.id == id:
                return todo
        return None

    async def add_todo(self, todo: Todo) -> Todo:
        self._todos.append(todo)
        return todo

    async def update_todo(self, id: str) -> Todo | None:
        for todo in self._todos:
            if todo.id == id:
                return todo
        return None

    async def remove_todo(self, id: str) -> bool:
        for i, todo in enumerate(self._todos):
            if todo.id == id:
                self._todos.pop(i)
                return True
        return False

    async def set_todos(self, todos: list[Todo]) -> None:
        self._todos = list(todos)


# ─────────────────────────────────────────────
# pydantic_ai_todo/capability.py
# ─────────────────────────────────────────────

try:
    from typing import AbstractSet
except ImportError:
    pass

try:
    AbstractToolset = Any
except Exception:
    AbstractToolset = Any


class TodoCapability:
    def __init__(
        self,
        storage: TodoStorageProtocol | None = None,
        async_storage: AsyncTodoStorageProtocol | None = None,
        descriptions: dict[str, str] | None = None,
        enable_subtasks: bool = False,
    ) -> None:
        self.storage = storage
        self.async_storage = async_storage
        self.descriptions = descriptions
        self.enable_subtasks = enable_subtasks

    def get_instructions(self) -> Any:
        instructions: list[str] = [
            "You are a helpful assistant that manages a todo list.",
            "You can create, update, delete, and list todos.",
        ]
        if self.enable_subtasks:
            instructions.append("You can also create subtasks for todos.")
        if self.descriptions:
            for key, value in self.descriptions.items():
                instructions.append(f"{key}: {value}")
        return "\n".join(instructions)

    def get_serialization_name(self) -> str:
        return "todo_capability"

    def get_toolset(self) -> Any | None:
        return None