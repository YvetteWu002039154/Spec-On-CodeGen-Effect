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

TodoStatus = Literal["pending", "in_progress", "completed", "blocked"]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return uuid.uuid4().hex


def _validate_status(status: str) -> None:
    if status not in ("pending", "in_progress", "completed", "blocked"):
        raise ValueError(f"Invalid status: {status!r}")


@dataclass
class Todo:
    active_form: str
    content: str
    depends_on: Optional[List[str]] = None
    id: Optional[str] = None
    parent_id: Optional[str] = None
    status: TodoStatus = "pending"

    def __post_init__(self) -> None:
        if self.id is not None and not isinstance(self.id, str):
            raise TypeError("id must be a str or None")
        if not isinstance(self.active_form, str):
            raise TypeError("active_form must be a str")
        if not isinstance(self.content, str):
            raise TypeError("content must be a str")
        if self.parent_id is not None and not isinstance(self.parent_id, str):
            raise TypeError("parent_id must be a str or None")
        _validate_status(self.status)
        if self.depends_on is not None:
            if not isinstance(self.depends_on, list) or not all(isinstance(x, str) for x in self.depends_on):
                raise TypeError("depends_on must be a list[str] or None")


@dataclass
class TodoItem:
    active_form: Optional[str] = None
    content: Optional[str] = None
    depends_on: Optional[List[str]] = None
    id: Optional[str] = None
    parent_id: Optional[str] = None
    status: Optional[TodoStatus] = None

    def __post_init__(self) -> None:
        if self.id is not None and not isinstance(self.id, str):
            raise TypeError("id must be a str or None")
        if self.active_form is not None and not isinstance(self.active_form, str):
            raise TypeError("active_form must be a str or None")
        if self.content is not None and not isinstance(self.content, str):
            raise TypeError("content must be a str or None")
        if self.parent_id is not None and not isinstance(self.parent_id, str):
            raise TypeError("parent_id must be a str or None")
        if self.status is not None:
            _validate_status(self.status)
        if self.depends_on is not None:
            if not isinstance(self.depends_on, list) or not all(isinstance(x, str) for x in self.depends_on):
                raise TypeError("depends_on must be a list[str] or None")


@dataclass
class TodoStatusUpdate:
    status: Optional[TodoStatus] = None
    todo_id: Optional[str] = None

    def __post_init__(self) -> None:
        if self.todo_id is not None and not isinstance(self.todo_id, str):
            raise TypeError("todo_id must be a str or None")
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
            raise TypeError("event_type must be a TodoEventType")
        if not isinstance(self.todo, Todo):
            raise TypeError("todo must be a Todo")
        if self.previous_state is not None and not isinstance(self.previous_state, Todo):
            raise TypeError("previous_state must be a Todo or None")
        if self.timestamp is None:
            self.timestamp = _utc_now()
        elif not isinstance(self.timestamp, datetime):
            raise TypeError("timestamp must be a datetime or None")


EventCallback = Callable[[TodoEvent], Any]


class TodoEventEmitter:
    def __init__(self) -> None:
        self._callbacks: Dict[TodoEventType, List[EventCallback]] = {}

    def on(self, event_type: TodoEventType, callback: EventCallback) -> EventCallback:
        if not isinstance(event_type, TodoEventType):
            raise TypeError("event_type must be a TodoEventType")
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
            raise TypeError("event must be a TodoEvent")
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
    @todos.setter
    def todos(self, value: List[Todo]) -> None: ...


class TodoStorage(TodoStorageProtocol):
    def __init__(self, todos: Optional[List[Todo]] = None) -> None:
        self._todos: List[Todo] = list(todos) if todos is not None else []

    @property
    def todos(self) -> List[Todo]:
        return self._todos

    @todos.setter
    def todos(self, value: List[Todo]) -> None:
        if not isinstance(value, list) or not all(isinstance(t, Todo) for t in value):
            raise TypeError("todos must be a list[Todo]")
        self._todos = value


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
                if t.id is None:
                    t = Todo(
                        active_form=t.active_form,
                        content=t.content,
                        depends_on=list(t.depends_on) if t.depends_on is not None else None,
                        id=_new_id(),
                        parent_id=t.parent_id,
                        status=t.status,
                    )
                self._todos[t.id] = t  # type: ignore[index]

    async def add_todo(self, todo: Todo) -> Todo:
        if not isinstance(todo, Todo):
            raise TypeError("todo must be a Todo")
        if todo.id is None:
            todo = Todo(
                active_form=todo.active_form,
                content=todo.content,
                depends_on=list(todo.depends_on) if todo.depends_on is not None else None,
                id=_new_id(),
                parent_id=todo.parent_id,
                status=todo.status,
            )
        self._todos[todo.id] = todo  # type: ignore[index]
        return todo

    async def get_todo(self, id: str) -> Optional[Todo]:
        if not isinstance(id, str):
            raise TypeError("id must be a str")
        return self._todos.get(id)

    async def get_todos(self) -> List[Todo]:
        return list(self._todos.values())

    async def remove_todo(self, id: str) -> bool:
        if not isinstance(id, str):
            raise TypeError("id must be a str")
        return self._todos.pop(id, None) is not None

    async def set_todos(self, todos: List[Todo]) -> None:
        if not isinstance(todos, list) or not all(isinstance(t, Todo) for t in todos):
            raise TypeError("todos must be a list[Todo]")
        self._todos.clear()
        for t in todos:
            if t.id is None:
                t = Todo(
                    active_form=t.active_form,
                    content=t.content,
                    depends_on=list(t.depends_on) if t.depends_on is not None else None,
                    id=_new_id(),
                    parent_id=t.parent_id,
                    status=t.status,
                )
            self._todos[t.id] = t  # type: ignore[index]

    async def update_todo(self, id: str) -> Optional[Todo]:
        if not isinstance(id, str):
            raise TypeError("id must be a str")
        return self._todos.get(id)


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