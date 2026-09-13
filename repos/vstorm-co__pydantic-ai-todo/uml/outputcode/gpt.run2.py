from __future__ import annotations

import asyncio
import copy
import json
import os
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
        self._listeners: Dict[TodoEventType, List[EventCallback]] = {}

    def on(self, event_type: TodoEventType, callback: EventCallback) -> EventCallback:
        if not isinstance(event_type, TodoEventType):
            raise TypeError("event_type must be TodoEventType")
        if not callable(callback):
            raise TypeError("callback must be callable")
        self._listeners.setdefault(event_type, []).append(callback)
        return callback

    def off(self, event_type: TodoEventType, callback: EventCallback) -> bool:
        listeners = self._listeners.get(event_type)
        if not listeners:
            return False
        try:
            listeners.remove(callback)
            if not listeners:
                self._listeners.pop(event_type, None)
            return True
        except ValueError:
            return False

    def emit(self, event: TodoEvent) -> None:
        if not isinstance(event, TodoEvent):
            raise TypeError("event must be TodoEvent")
        listeners = list(self._listeners.get(event.event_type, []))
        for cb in listeners:
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
        self._todos: List[Todo] = []
        if todos is not None:
            self.todos = todos

    @property
    def todos(self) -> List[Todo]:
        return self._todos

    @todos.setter
    def todos(self, value: List[Todo]) -> None:
        if not isinstance(value, list) or any(not isinstance(t, Todo) for t in value):
            raise TypeError("todos must be list[Todo]")
        self._todos = list(value)


@runtime_checkable
class AsyncTodoStorageProtocol(Protocol):
    async def add_todo(self, todo: Todo) -> Todo: ...
    async def get_todo(self, id: str) -> Optional[Todo]: ...
    async def get_todos(self) -> List[Todo]: ...
    async def remove_todo(self, id: str) -> bool: ...
    async def set_todos(self, todos: List[Todo]) -> None: ...
    async def update_todo(self, id: str) -> Optional[Todo]: ...


class AsyncMemoryStorage(AsyncTodoStorageProtocol):
    def __init__(self, initial_todos: Optional[List[Todo]] = None) -> None:
        self._lock = asyncio.Lock()
        self._todos: Dict[str, Todo] = {}
        if initial_todos:
            for t in initial_todos:
                tid = t.id or _new_id()
                self._todos[tid] = copy.deepcopy(Todo(**{**t.__dict__, "id": tid}))

    async def add_todo(self, todo: Todo) -> Todo:
        if not isinstance(todo, Todo):
            raise TypeError("todo must be Todo")
        async with self._lock:
            tid = todo.id or _new_id()
            stored = copy.deepcopy(Todo(**{**todo.__dict__, "id": tid}))
            self._todos[tid] = stored
            return copy.deepcopy(stored)

    async def get_todo(self, id: str) -> Optional[Todo]:
        if not isinstance(id, str):
            raise TypeError("id must be str")
        async with self._lock:
            t = self._todos.get(id)
            return copy.deepcopy(t) if t is not None else None

    async def get_todos(self) -> List[Todo]:
        async with self._lock:
            return [copy.deepcopy(t) for t in self._todos.values()]

    async def remove_todo(self, id: str) -> bool:
        if not isinstance(id, str):
            raise TypeError("id must be str")
        async with self._lock:
            return self._todos.pop(id, None) is not None

    async def set_todos(self, todos: List[Todo]) -> None:
        if not isinstance(todos, list) or any(not isinstance(t, Todo) for t in todos):
            raise TypeError("todos must be list[Todo]")
        async with self._lock:
            self._todos.clear()
            for t in todos:
                tid = t.id or _new_id()
                self._todos[tid] = copy.deepcopy(Todo(**{**t.__dict__, "id": tid}))

    async def update_todo(self, id: str) -> Optional[Todo]:
        if not isinstance(id, str):
            raise TypeError("id must be str")
        async with self._lock:
            existing = self._todos.get(id)
            if existing is None:
                return None
            self._todos[id] = copy.deepcopy(existing)
            return copy.deepcopy(self._todos[id])


class _JsonFileAsyncStore:
    def __init__(self, path: str) -> None:
        self._path = path
        self._lock = asyncio.Lock()
        self._initialized = False

    async def initialize(self) -> None:
        async with self._lock:
            if self._initialized:
                return
            os.makedirs(os.path.dirname(self._path) or ".", exist_ok=True)
            if not os.path.exists(self._path):
                with open(self._path, "w", encoding="utf-8") as f:
                    json.dump({}, f)
            self._initialized = True

    async def close(self) -> None:
        async with self._lock:
            self._initialized = False

    async def _read_all(self) -> Dict[str, Dict[str, Any]]:
        await self.initialize()
        with open(self._path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("Corrupt storage file")
        return data  # type: ignore[return-value]

    async def _write_all(self, data: Dict[str, Dict[str, Any]]) -> None:
        await self.initialize()
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(data, f)


class AsyncPostgresStorage(AsyncTodoStorageProtocol):
    def __init__(self, path: str = "async_postgres_storage.json") -> None:
        self._store = _JsonFileAsyncStore(path)

    async def initialize(self) -> None:
        await self._store.initialize()

    async def close(self) -> None:
        await self._store.close()

    async def add_todo(self, todo: Todo) -> Todo:
        if not isinstance(todo, Todo):
            raise TypeError("todo must be Todo")
        async with self._store._lock:
            data = await self._store._read_all()
            tid = todo.id or _new_id()
            stored = Todo(**{**todo.__dict__, "id": tid})
            data[tid] = stored.__dict__
            await self._store._write_all(data)
            return copy.deepcopy(stored)

    async def get_todo(self, id: str) -> Optional[Todo]:
        if not isinstance(id, str):
            raise TypeError("id must be str")
        async with self._store._lock:
            data = await self._store._read_all()
            raw = data.get(id)
            return Todo(**raw) if raw is not None else None

    async def get_todos(self) -> List[Todo]:
        async with self._store._lock:
            data = await self._store._read_all()
            return [Todo(**raw) for raw in data.values()]

    async def remove_todo(self, id: str) -> bool:
        if not isinstance(id, str):
            raise TypeError("id must be str")
        async with self._store._lock:
            data = await self._store._read_all()
            existed = id in data
            if existed:
                data.pop(id, None)
                await self._store._write_all(data)
            return existed

    async def set_todos(self, todos: List[Todo]) -> None:
        if not isinstance(todos, list) or any(not isinstance(t, Todo) for t in todos):
            raise TypeError("todos must be list[Todo]")
        async with self._store._lock:
            data: Dict[str, Dict[str, Any]] = {}
            for t in todos:
                tid = t.id or _new_id()
                stored = Todo(**{**t.__dict__, "id": tid})
                data[tid] = stored.__dict__
            await self._store._write_all(data)

    async def update_todo(self, id: str) -> Optional[Todo]:
        if not isinstance(id, str):
            raise TypeError("id must be str")
        async with self._store._lock:
            data = await self._store._read_all()
            raw = data.get(id)
            if raw is None:
                return None
            todo = Todo(**raw)
            data[id] = todo.__dict__
            await self._store._write_all(data)
            return copy.deepcopy(todo)


class AsyncRedisStorage(AsyncTodoStorageProtocol):
    def __init__(self, path: str = "async_redis_storage.json") -> None:
        self._store = _JsonFileAsyncStore(path)

    async def initialize(self) -> None:
        await self._store.initialize()

    async def close(self) -> None:
        await self._store.close()

    async def add_todo(self, todo: Todo) -> Todo:
        if not isinstance(todo, Todo):
            raise TypeError("todo must be Todo")
        async with self._store._lock:
            data = await self._store._read_all()
            tid = todo.id or _new_id()
            stored = Todo(**{**todo.__dict__, "id": tid})
            data[tid] = stored.__dict__
            await self._store._write_all(data)
            return copy.deepcopy(stored)

    async def get_todo(self, id: str) -> Optional[Todo]:
        if not isinstance(id, str):
            raise TypeError("id must be str")
        async with self._store._lock:
            data = await self._store._read_all()
            raw = data.get(id)
            return Todo(**raw) if raw is not None else None

    async def get_todos(self) -> List[Todo]:
        async with self._store._lock:
            data = await self._store._read_all()
            return [Todo(**raw) for raw in data.values()]

    async def remove_todo(self, id: str) -> bool:
        if not isinstance(id, str):
            raise TypeError("id must be str")
        async with self._store._lock:
            data = await self._store._read_all()
            existed = id in data
            if existed:
                data.pop(id, None)
                await self._store._write_all(data)
            return existed

    async def set_todos(self, todos: List[Todo]) -> None:
        if not isinstance(todos, list) or any(not isinstance(t, Todo) for t in todos):
            raise TypeError("todos must be list[Todo]")
        async with self._store._lock:
            data: Dict[str, Dict[str, Any]] = {}
            for t in todos:
                tid = t.id or _new_id()
                stored = Todo(**{**t.__dict__, "id": tid})
                data[tid] = stored.__dict__
            await self._store._write_all(data)

    async def update_todo(self, id: str) -> Optional[Todo]:
        if not isinstance(id, str):
            raise TypeError("id must be str")
        async with self._store._lock:
            data = await self._store._read_all()
            raw = data.get(id)
            if raw is None:
                return None
            todo = Todo(**raw)
            data[id] = todo.__dict__
            await self._store._write_all(data)
            return copy.deepcopy(todo)


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
        return self.__class__.__name__

    def get_toolset(self) -> Optional[AbstractToolset[Any]]:
        return None