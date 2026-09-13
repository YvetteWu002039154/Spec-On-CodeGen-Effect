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
    Literal,
    Optional,
    Protocol,
    TypeVar,
    Union,
    runtime_checkable,
)

TodoStatus = Literal["pending", "in_progress", "completed", "blocked"]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return uuid.uuid4().hex


def _validate_status(status: str) -> None:
    if status not in ("pending", "in_progress", "completed", "blocked"):
        raise ValueError(f"Invalid status: {status!r}")


def _normalize_depends_on(depends_on: Optional[List[str]]) -> Optional[List[str]]:
    if depends_on is None:
        return None
    if not isinstance(depends_on, list):
        raise TypeError("depends_on must be a list[str] or None")
    for d in depends_on:
        if not isinstance(d, str) or not d:
            raise ValueError("depends_on must contain non-empty strings")
    return list(depends_on)


@dataclass
class Todo:
    active_form: str
    content: str
    depends_on: Optional[List[str]] = None
    id: Optional[str] = None
    parent_id: Optional[str] = None
    status: TodoStatus = "pending"

    def __post_init__(self) -> None:
        if not isinstance(self.active_form, str) or not self.active_form:
            raise ValueError("active_form must be a non-empty string")
        if not isinstance(self.content, str) or not self.content:
            raise ValueError("content must be a non-empty string")
        self.depends_on = _normalize_depends_on(self.depends_on)
        if self.id is not None and (not isinstance(self.id, str) or not self.id):
            raise ValueError("id must be a non-empty string or None")
        if self.parent_id is not None and (not isinstance(self.parent_id, str) or not self.parent_id):
            raise ValueError("parent_id must be a non-empty string or None")
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
        if self.active_form is not None and (not isinstance(self.active_form, str) or not self.active_form):
            raise ValueError("active_form must be a non-empty string or None")
        if self.content is not None and (not isinstance(self.content, str) or not self.content):
            raise ValueError("content must be a non-empty string or None")
        if self.depends_on is not None:
            self.depends_on = _normalize_depends_on(self.depends_on)
        if self.id is not None and (not isinstance(self.id, str) or not self.id):
            raise ValueError("id must be a non-empty string or None")
        if self.parent_id is not None and (not isinstance(self.parent_id, str) or not self.parent_id):
            raise ValueError("parent_id must be a non-empty string or None")
        if self.status is not None:
            _validate_status(self.status)


@dataclass
class TodoStatusUpdate:
    status: Optional[TodoStatus] = None
    todo_id: Optional[str] = None

    def __post_init__(self) -> None:
        if self.todo_id is not None and (not isinstance(self.todo_id, str) or not self.todo_id):
            raise ValueError("todo_id must be a non-empty string or None")
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
            self.timestamp = _utcnow()
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
        if event_type not in self._callbacks:
            return False
        callbacks = self._callbacks[event_type]
        try:
            callbacks.remove(callback)
            if not callbacks:
                del self._callbacks[event_type]
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
    def todos(self) -> List[Todo]:
        ...

    @todos.setter
    def todos(self, value: List[Todo]) -> None:
        ...


class TodoStorage(TodoStorageProtocol):
    def __init__(self, todos: Optional[List[Todo]] = None) -> None:
        self._todos: List[Todo] = []
        if todos is not None:
            self.todos = todos

    @property
    def todos(self) -> List[Todo]:
        return self._todos

    @todos.setter
    def todos(self, value: List[Todo]) -> None:
        if not isinstance(value, list):
            raise TypeError("todos must be a list[Todo]")
        for t in value:
            if not isinstance(t, Todo):
                raise TypeError("todos must be a list[Todo]")
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
            raise TypeError("todo must be a Todo")
        async with self._lock:
            new_todo = todo.copy()
            if not new_todo.id:
                new_todo.id = _new_id()
            self._todos[new_todo.id] = new_todo.copy()
            return new_todo.copy()

    async def get_todo(self, id: str) -> Optional[Todo]:
        if not isinstance(id, str) or not id:
            raise ValueError("id must be a non-empty string")
        async with self._lock:
            t = self._todos.get(id)
            return t.copy() if t is not None else None

    async def get_todos(self) -> List[Todo]:
        async with self._lock:
            return [t.copy() for t in self._todos.values()]

    async def remove_todo(self, id: str) -> bool:
        if not isinstance(id, str) or not id:
            raise ValueError("id must be a non-empty string")
        async with self._lock:
            return self._todos.pop(id, None) is not None

    async def set_todos(self, todos: List[Todo]) -> None:
        if not isinstance(todos, list):
            raise TypeError("todos must be a list[Todo]")
        for t in todos:
            if not isinstance(t, Todo):
                raise TypeError("todos must be a list[Todo]")
        async with self._lock:
            new_map: Dict[str, Todo] = {}
            for t in todos:
                tt = t.copy()
                if not tt.id:
                    tt.id = _new_id()
                new_map[tt.id] = tt.copy()
            self._todos = new_map

    async def update_todo(self, id: str) -> Optional[Todo]:
        if not isinstance(id, str) or not id:
            raise ValueError("id must be a non-empty string")
        async with self._lock:
            t = self._todos.get(id)
            if t is None:
                return None
            self._todos[id] = t.copy()
            return self._todos[id].copy()


class AsyncRedisStorage(AsyncTodoStorageProtocol):
    def __init__(self) -> None:
        self._initialized = False
        self._closed = False
        self._lock = asyncio.Lock()
        self._kv: Dict[str, str] = {}

    async def initialize(self) -> None:
        async with self._lock:
            if self._closed:
                raise RuntimeError("Storage is closed")
            self._initialized = True

    async def close(self) -> None:
        async with self._lock:
            self._closed = True

    def _ensure_ready(self) -> None:
        if self._closed:
            raise RuntimeError("Storage is closed")
        if not self._initialized:
            raise RuntimeError("Storage is not initialized")

    @staticmethod
    def _serialize(todo: Todo) -> str:
        data = {
            "active_form": todo.active_form,
            "content": todo.content,
            "depends_on": todo.depends_on,
            "id": todo.id,
            "parent_id": todo.parent_id,
            "status": todo.status,
        }
        return json.dumps(data, separators=(",", ":"), ensure_ascii=False)

    @staticmethod
    def _deserialize(raw: str) -> Todo:
        data = json.loads(raw)
        return Todo(
            active_form=data["active_form"],
            content=data["content"],
            depends_on=data.get("depends_on"),
            id=data.get("id"),
            parent_id=data.get("parent_id"),
            status=data["status"],
        )

    async def add_todo(self, todo: Todo) -> Todo:
        if not isinstance(todo, Todo):
            raise TypeError("todo must be a Todo")
        async with self._lock:
            self._ensure_ready()
            new_todo = todo.copy()
            if not new_todo.id:
                new_todo.id = _new_id()
            self._kv[new_todo.id] = self._serialize(new_todo)
            return new_todo.copy()

    async def get_todo(self, id: str) -> Optional[Todo]:
        if not isinstance(id, str) or not id:
            raise ValueError("id must be a non-empty string")
        async with self._lock:
            self._ensure_ready()
            raw = self._kv.get(id)
            return self._deserialize(raw) if raw is not None else None

    async def get_todos(self) -> List[Todo]:
        async with self._lock:
            self._ensure_ready()
            return [self._deserialize(v) for v in self._kv.values()]

    async def remove_todo(self, id: str) -> bool:
        if not isinstance(id, str) or not id:
            raise ValueError("id must be a non-empty string")
        async with self._lock:
            self._ensure_ready()
            return self._kv.pop(id, None) is not None

    async def set_todos(self, todos: List[Todo]) -> None:
        if not isinstance(todos, list):
            raise TypeError("todos must be a list[Todo]")
        for t in todos:
            if not isinstance(t, Todo):
                raise TypeError("todos must be a list[Todo]")
        async with self._lock:
            self._ensure_ready()
            new_kv: Dict[str, str] = {}
            for t in todos:
                tt = t.copy()
                if not tt.id:
                    tt.id = _new_id()
                new_kv[tt.id] = self._serialize(tt)
            self._kv = new_kv

    async def update_todo(self, id: str) -> Optional[Todo]:
        if not isinstance(id, str) or not id:
            raise ValueError("id must be a non-empty string")
        async with self._lock:
            self._ensure_ready()
            raw = self._kv.get(id)
            if raw is None:
                return None
            todo = self._deserialize(raw)
            self._kv[id] = self._serialize(todo)
            return todo.copy()


class AsyncPostgresStorage(AsyncTodoStorageProtocol):
    def __init__(self) -> None:
        self._initialized = False
        self._closed = False
        self._lock = asyncio.Lock()
        self._rows: Dict[str, Dict[str, Any]] = {}

    async def initialize(self) -> None:
        async with self._lock:
            if self._closed:
                raise RuntimeError("Storage is closed")
            self._initialized = True

    async def close(self) -> None:
        async with self._lock:
            self._closed = True

    def _ensure_ready(self) -> None:
        if self._closed:
            raise RuntimeError("Storage is closed")
        if not self._initialized:
            raise RuntimeError("Storage is not initialized")

    @staticmethod
    def _to_row(todo: Todo) -> Dict[str, Any]:
        return {
            "id": todo.id,
            "active_form": todo.active_form,
            "content": todo.content,
            "depends_on": copy.deepcopy(todo.depends_on),
            "parent_id": todo.parent_id,
            "status": todo.status,
        }

    @staticmethod
    def _from_row(row: Dict[str, Any]) -> Todo:
        return Todo(
            id=row.get("id"),
            active_form=row["active_form"],
            content=row["content"],
            depends_on=copy.deepcopy(row.get("depends_on")),
            parent_id=row.get("parent_id"),
            status=row["status"],
        )

    async def add_todo(self, todo: Todo) -> Todo:
        if not isinstance(todo, Todo):
            raise TypeError("todo must be a Todo")
        async with self._lock:
            self._ensure_ready()
            new_todo = todo.copy()
            if not new_todo.id:
                new_todo.id = _new_id()
            self._rows[new_todo.id] = self._to_row(new_todo)
            return new_todo.copy()

    async def get_todo(self, id: str) -> Optional[Todo]:
        if not isinstance(id, str) or not id:
            raise ValueError("id must be a non-empty string")
        async with self._lock:
            self._ensure_ready()
            row = self._rows.get(id)
            return self._from_row(row) if row is not None else None

    async def get_todos(self) -> List[Todo]:
        async with self._lock:
            self._ensure_ready()
            return [self._from_row(r) for r in self._rows.values()]

    async def remove_todo(self, id: str) -> bool:
        if not isinstance(id, str) or not id:
            raise ValueError("id must be a non-empty string")
        async with self._lock:
            self._ensure_ready()
            return self._rows.pop(id, None) is not None

    async def set_todos(self, todos: List[Todo]) -> None:
        if not isinstance(todos, list):
            raise TypeError("todos must be a list[Todo]")
        for t in todos:
            if not isinstance(t, Todo):
                raise TypeError("todos must be a list[Todo]")
        async with self._lock:
            self._ensure_ready()
            new_rows: Dict[str, Dict[str, Any]] = {}
            for t in todos:
                tt = t.copy()
                if not tt.id:
                    tt.id = _new_id()
                new_rows[tt.id] = self._to_row(tt)
            self._rows = new_rows

    async def update_todo(self, id: str) -> Optional[Todo]:
        if not isinstance(id, str) or not id:
            raise ValueError("id must be a non-empty string")
        async with self._lock:
            self._ensure_ready()
            row = self._rows.get(id)
            if row is None:
                return None
            todo = self._from_row(row)
            self._rows[id] = self._to_row(todo)
            return todo.copy()


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