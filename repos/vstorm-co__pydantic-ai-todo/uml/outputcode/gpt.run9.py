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

T = TypeVar("T")
EventCallback = Callable[["TodoEvent"], Any]


class AbstractToolset(Generic[T], Protocol):
    ...


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
                raise ValueError("depends_on must be a list of strings or None")


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
                raise ValueError("depends_on must be a list of strings or None")


@dataclass
class TodoStatusUpdate:
    status: Optional[TodoStatus] = None
    todo_id: Optional[str] = None

    def __post_init__(self) -> None:
        if self.status is not None and self.status not in ("pending", "in_progress", "completed", "blocked"):
            raise ValueError("Invalid status")


class TodoEventType(Enum):
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    STATUS_CHANGED = "status_changed"
    COMPLETED = "completed"

    @property
    def name(self) -> str:  # type: ignore[override]
        return self.value


@dataclass
class TodoEvent:
    event_type: TodoEventType
    todo: Todo
    previous_state: Optional[Todo] = None
    timestamp: Optional[datetime] = None

    def __post_init__(self) -> None:
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


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
    def todos(self) -> List[Todo]:
        ...

    @todos.setter
    def todos(self, value: List[Todo]) -> None:
        ...


class TodoStorage(TodoStorageProtocol):
    def __init__(self, todos: Optional[List[Todo]] = None) -> None:
        self._todos: List[Todo] = list(todos) if todos is not None else []

    @property
    def todos(self) -> List[Todo]:
        return self._todos

    @todos.setter
    def todos(self, value: List[Todo]) -> None:
        self._todos = list(value)


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


class AsyncMemoryStorage(AsyncTodoStorageProtocol):
    def __init__(self, todos: Optional[List[Todo]] = None) -> None:
        self._todos: Dict[str, Todo] = {}
        if todos:
            for t in todos:
                tid = t.id or uuid.uuid4().hex
                self._todos[tid] = Todo(
                    active_form=t.active_form,
                    content=t.content,
                    depends_on=list(t.depends_on) if t.depends_on is not None else None,
                    id=tid,
                    parent_id=t.parent_id,
                    status=t.status,
                )

    async def add_todo(self, todo: Todo) -> Todo:
        tid = todo.id or uuid.uuid4().hex
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
        return self._todos.pop(id, None) is not None

    async def set_todos(self, todos: List[Todo]) -> None:
        self._todos.clear()
        for t in todos:
            tid = t.id or uuid.uuid4().hex
            self._todos[tid] = Todo(
                active_form=t.active_form,
                content=t.content,
                depends_on=list(t.depends_on) if t.depends_on is not None else None,
                id=tid,
                parent_id=t.parent_id,
                status=t.status,
            )

    async def update_todo(self, id: str) -> Optional[Todo]:
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
        return await self.get_todo(id)


class AsyncPostgresStorage(AsyncTodoStorageProtocol):
    def __init__(self) -> None:
        self._initialized: bool = False
        self._closed: bool = False
        self._mem = AsyncMemoryStorage()

    async def initialize(self) -> None:
        if self._closed:
            raise RuntimeError("Storage is closed")
        self._initialized = True

    async def close(self) -> None:
        self._closed = True

    def _ensure_ready(self) -> None:
        if self._closed:
            raise RuntimeError("Storage is closed")
        if not self._initialized:
            raise RuntimeError("Storage not initialized")

    async def add_todo(self, todo: Todo) -> Todo:
        self._ensure_ready()
        return await self._mem.add_todo(todo)

    async def get_todo(self, id: str) -> Optional[Todo]:
        self._ensure_ready()
        return await self._mem.get_todo(id)

    async def get_todos(self) -> List[Todo]:
        self._ensure_ready()
        return await self._mem.get_todos()

    async def remove_todo(self, id: str) -> bool:
        self._ensure_ready()
        return await self._mem.remove_todo(id)

    async def set_todos(self, todos: List[Todo]) -> None:
        self._ensure_ready()
        await self._mem.set_todos(todos)

    async def update_todo(self, id: str) -> Optional[Todo]:
        self._ensure_ready()
        return await self._mem.update_todo(id)


class AsyncRedisStorage(AsyncTodoStorageProtocol):
    def __init__(self) -> None:
        self._initialized: bool = False
        self._closed: bool = False
        self._mem = AsyncMemoryStorage()

    async def initialize(self) -> None:
        if self._closed:
            raise RuntimeError("Storage is closed")
        self._initialized = True

    async def close(self) -> None:
        self._closed = True

    def _ensure_ready(self) -> None:
        if self._closed:
            raise RuntimeError("Storage is closed")
        if not self._initialized:
            raise RuntimeError("Storage not initialized")

    async def add_todo(self, todo: Todo) -> Todo:
        self._ensure_ready()
        return await self._mem.add_todo(todo)

    async def get_todo(self, id: str) -> Optional[Todo]:
        self._ensure_ready()
        return await self._mem.get_todo(id)

    async def get_todos(self) -> List[Todo]:
        self._ensure_ready()
        return await self._mem.get_todos()

    async def remove_todo(self, id: str) -> bool:
        self._ensure_ready()
        return await self._mem.remove_todo(id)

    async def set_todos(self, todos: List[Todo]) -> None:
        self._ensure_ready()
        await self._mem.set_todos(todos)

    async def update_todo(self, id: str) -> Optional[Todo]:
        self._ensure_ready()
        return await self._mem.update_todo(id)


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
        self.descriptions: Optional[Dict[str, str]] = dict(descriptions) if descriptions is not None else None
        self.enable_subtasks: bool = bool(enable_subtasks)
        self.storage: Optional[TodoStorageProtocol] = storage

    def get_instructions(self) -> Any:
        return self.descriptions

    def get_serialization_name(self) -> str:
        return "todo"

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