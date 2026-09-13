from __future__ import annotations

import asyncio
import copy
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
    Optional,
    Protocol,
    TypeVar,
    Union,
    Literal,
    runtime_checkable,
)

TodoStatus = Literal["pending", "in_progress", "completed", "blocked"]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _validate_status(status: str) -> None:
    if status not in ("pending", "in_progress", "completed", "blocked"):
        raise ValueError(f"Invalid status: {status!r}")


def _ensure_list_str(value: Optional[List[str]]) -> Optional[List[str]]:
    if value is None:
        return None
    if not isinstance(value, list) or any(not isinstance(x, str) for x in value):
        raise TypeError("depends_on must be a list[str] or None")
    return list(value)


@dataclass
class Todo:
    active_form: str
    content: str
    depends_on: Optional[List[str]] = None
    id: Optional[str] = None
    parent_id: Optional[str] = None
    status: TodoStatus = "pending"

    def __post_init__(self) -> None:
        if not isinstance(self.active_form, str):
            raise TypeError("active_form must be str")
        if not isinstance(self.content, str):
            raise TypeError("content must be str")
        self.depends_on = _ensure_list_str(self.depends_on)
        if self.id is not None and not isinstance(self.id, str):
            raise TypeError("id must be str or None")
        if self.parent_id is not None and not isinstance(self.parent_id, str):
            raise TypeError("parent_id must be str or None")
        _validate_status(self.status)

    def copy(self) -> "Todo":
        return copy.deepcopy(self)


@dataclass
class TodoItem:
    active_form: Optional[str] = None
    content: Optional[str] = None
    depends_on: Optional[List[str]] = None
    id: Optional[str] = None
    parent_id: Optional[str] = None
    status: Optional[TodoStatus] = None

    def __post_init__(self) -> None:
        if self.active_form is not None and not isinstance(self.active_form, str):
            raise TypeError("active_form must be str or None")
        if self.content is not None and not isinstance(self.content, str):
            raise TypeError("content must be str or None")
        self.depends_on = _ensure_list_str(self.depends_on)
        if self.id is not None and not isinstance(self.id, str):
            raise TypeError("id must be str or None")
        if self.parent_id is not None and not isinstance(self.parent_id, str):
            raise TypeError("parent_id must be str or None")
        if self.status is not None:
            _validate_status(self.status)


@dataclass
class TodoStatusUpdate:
    status: Optional[TodoStatus] = None
    todo_id: Optional[str] = None

    def __post_init__(self) -> None:
        if self.todo_id is not None and not isinstance(self.todo_id, str):
            raise TypeError("todo_id must be str or None")
        if self.status is not None:
            _validate_status(self.status)


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
        if not isinstance(self.event_type, TodoEventType):
            raise TypeError("event_type must be TodoEventType")
        if not isinstance(self.todo, Todo):
            raise TypeError("todo must be Todo")
        if self.previous_state is not None and not isinstance(self.previous_state, Todo):
            raise TypeError("previous_state must be Todo or None")
        if self.timestamp is None:
            self.timestamp = _utcnow()
        elif not isinstance(self.timestamp, datetime):
            raise TypeError("timestamp must be datetime or None")


EventCallback = Callable[[TodoEvent], Any]


class TodoEventEmitter:
    def __init__(self) -> None:
        self._callbacks: Dict[TodoEventType, List[EventCallback]] = {}

    def on(self, event_type: TodoEventType, callback: EventCallback) -> EventCallback:
        if not isinstance(event_type, TodoEventType):
            raise TypeError("event_type must be TodoEventType")
        if not callable(callback):
            raise TypeError("callback must be callable")
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
        if not isinstance(event, TodoEvent):
            raise TypeError("event must be TodoEvent")
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
        self._todos: List[Todo] = []
        self.todos = todos or []

    @property
    def todos(self) -> List[Todo]:
        return self._todos

    @todos.setter
    def todos(self, value: List[Todo]) -> None:
        if not isinstance(value, list) or any(not isinstance(t, Todo) for t in value):
            raise TypeError("todos must be list[Todo]")
        self._todos = [t.copy() for t in value]


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
    def __init__(self) -> None:
        self._todos: Dict[str, Todo] = {}
        self._lock = asyncio.Lock()

    async def add_todo(self, todo: Todo) -> Todo:
        if not isinstance(todo, Todo):
            raise TypeError("todo must be Todo")
        async with self._lock:
            new_todo = todo.copy()
            if new_todo.id is None:
                new_todo.id = uuid.uuid4().hex
            self._todos[new_todo.id] = new_todo.copy()
            return new_todo.copy()

    async def get_todo(self, id: str) -> Optional[Todo]:
        if not isinstance(id, str):
            raise TypeError("id must be str")
        async with self._lock:
            t = self._todos.get(id)
            return t.copy() if t is not None else None

    async def get_todos(self) -> List[Todo]:
        async with self._lock:
            return [t.copy() for t in self._todos.values()]

    async def remove_todo(self, id: str) -> bool:
        if not isinstance(id, str):
            raise TypeError("id must be str")
        async with self._lock:
            return self._todos.pop(id, None) is not None

    async def set_todos(self, todos: List[Todo]) -> None:
        if not isinstance(todos, list) or any(not isinstance(t, Todo) for t in todos):
            raise TypeError("todos must be list[Todo]")
        async with self._lock:
            new_map: Dict[str, Todo] = {}
            for t in todos:
                tt = t.copy()
                if tt.id is None:
                    tt.id = uuid.uuid4().hex
                new_map[tt.id] = tt.copy()
            self._todos = new_map

    async def update_todo(self, id: str) -> Optional[Todo]:
        if not isinstance(id, str):
            raise TypeError("id must be str")
        async with self._lock:
            t = self._todos.get(id)
            return t.copy() if t is not None else None


class AsyncPostgresStorage(AsyncTodoStorageProtocol):
    def __init__(self) -> None:
        self._initialized = False
        self._closed = False
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
            raise RuntimeError("Storage is not initialized")

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
        self._initialized = False
        self._closed = False
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
            raise RuntimeError("Storage is not initialized")

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


T = TypeVar("T")


class AbstractToolset(Protocol, Generic[T]):
    ...


class TodoCapability:
    def __init__(
        self,
        *,
        async_storage: Optional[AsyncTodoStorageProtocol] = None,
        descriptions: Optional[Dict[str, str]] = None,
        enable_subtasks: bool = False,
        storage: Optional[TodoStorageProtocol] = None,
    ) -> None:
        if async_storage is not None and not isinstance(async_storage, AsyncTodoStorageProtocol):
            raise TypeError("async_storage must implement AsyncTodoStorageProtocol or be None")
        if storage is not None and not isinstance(storage, TodoStorageProtocol):
            raise TypeError("storage must implement TodoStorageProtocol or be None")
        if descriptions is not None:
            if not isinstance(descriptions, dict) or any(
                not isinstance(k, str) or not isinstance(v, str) for k, v in descriptions.items()
            ):
                raise TypeError("descriptions must be dict[str, str] or None")
        if not isinstance(enable_subtasks, bool):
            raise TypeError("enable_subtasks must be bool")

        self.async_storage: Optional[AsyncTodoStorageProtocol] = async_storage
        self.descriptions: Optional[Dict[str, str]] = dict(descriptions) if descriptions is not None else None
        self.enable_subtasks: bool = enable_subtasks
        self.storage: Optional[TodoStorageProtocol] = storage

    def get_instructions(self) -> Any:
        return self.descriptions

    def get_serialization_name(self) -> str:
        return "todo"

    def get_toolset(self) -> Optional[AbstractToolset[Any]]:
        return None