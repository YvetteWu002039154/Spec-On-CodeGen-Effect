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


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return uuid.uuid4().hex


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
            raise ValueError(f"Invalid status: {self.status}")
        if self.depends_on is not None:
            if not isinstance(self.depends_on, list) or any(not isinstance(x, str) for x in self.depends_on):
                raise ValueError("depends_on must be a list[str] or None")
        if self.id is not None and not isinstance(self.id, str):
            raise ValueError("id must be str or None")
        if self.parent_id is not None and not isinstance(self.parent_id, str):
            raise ValueError("parent_id must be str or None")
        if not isinstance(self.active_form, str):
            raise ValueError("active_form must be str")
        if not isinstance(self.content, str):
            raise ValueError("content must be str")


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
            raise ValueError(f"Invalid status: {self.status}")
        if self.depends_on is not None:
            if not isinstance(self.depends_on, list) or any(not isinstance(x, str) for x in self.depends_on):
                raise ValueError("depends_on must be a list[str] or None")
        if self.id is not None and not isinstance(self.id, str):
            raise ValueError("id must be str or None")
        if self.parent_id is not None and not isinstance(self.parent_id, str):
            raise ValueError("parent_id must be str or None")
        if self.active_form is not None and not isinstance(self.active_form, str):
            raise ValueError("active_form must be str or None")
        if self.content is not None and not isinstance(self.content, str):
            raise ValueError("content must be str or None")


@dataclass
class TodoStatusUpdate:
    status: Optional[TodoStatus] = None
    todo_id: Optional[str] = None

    def __post_init__(self) -> None:
        if self.status is not None and self.status not in ("pending", "in_progress", "completed", "blocked"):
            raise ValueError(f"Invalid status: {self.status}")
        if self.todo_id is not None and not isinstance(self.todo_id, str):
            raise ValueError("todo_id must be str or None")


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
            self.timestamp = _utcnow()


EventCallback = Callable[[TodoEvent], Any]


class TodoEventEmitter:
    def __init__(self) -> None:
        self._callbacks: Dict[TodoEventType, List[EventCallback]] = {t: [] for t in TodoEventType}

    def on(self, event_type: TodoEventType, callback: EventCallback) -> EventCallback:
        if not isinstance(event_type, TodoEventType):
            raise ValueError("event_type must be a TodoEventType")
        if not callable(callback):
            raise ValueError("callback must be callable")
        self._callbacks[event_type].append(callback)
        return callback

    def off(self, event_type: TodoEventType, callback: EventCallback) -> bool:
        if event_type not in self._callbacks:
            return False
        try:
            self._callbacks[event_type].remove(callback)
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
        if not isinstance(value, list) or any(not isinstance(t, Todo) for t in value):
            raise ValueError("todos must be a list[Todo]")
        self._todos = value


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
    def __init__(self, initial_todos: Optional[List[Todo]] = None) -> None:
        self._todos: Dict[str, Todo] = {}
        if initial_todos:
            for t in initial_todos:
                tid = t.id or _new_id()
                self._todos[tid] = Todo(
                    active_form=t.active_form,
                    content=t.content,
                    depends_on=list(t.depends_on) if t.depends_on is not None else None,
                    id=tid,
                    parent_id=t.parent_id,
                    status=t.status,
                )
        self._lock = asyncio.Lock()

    async def add_todo(self, todo: Todo) -> Todo:
        async with self._lock:
            tid = todo.id or _new_id()
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
        async with self._lock:
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
        async with self._lock:
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
        async with self._lock:
            return self._todos.pop(id, None) is not None

    async def set_todos(self, todos: List[Todo]) -> None:
        if not isinstance(todos, list) or any(not isinstance(t, Todo) for t in todos):
            raise ValueError("todos must be a list[Todo]")
        async with self._lock:
            self._todos.clear()
            for t in todos:
                tid = t.id or _new_id()
                self._todos[tid] = Todo(
                    active_form=t.active_form,
                    content=t.content,
                    depends_on=list(t.depends_on) if t.depends_on is not None else None,
                    id=tid,
                    parent_id=t.parent_id,
                    status=t.status,
                )

    async def update_todo(self, id: str) -> Optional[Todo]:
        async with self._lock:
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
            return Todo(
                active_form=self._todos[id].active_form,
                content=self._todos[id].content,
                depends_on=list(self._todos[id].depends_on) if self._todos[id].depends_on is not None else None,
                id=self._todos[id].id,
                parent_id=self._todos[id].parent_id,
                status=self._todos[id].status,
            )


class AsyncPostgresStorage(AsyncTodoStorageProtocol):
    def __init__(self) -> None:
        self._initialized = False
        self._closed = False
        self._memory = AsyncMemoryStorage()

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
        return await self._memory.add_todo(todo)

    async def get_todo(self, id: str) -> Optional[Todo]:
        self._ensure_ready()
        return await self._memory.get_todo(id)

    async def get_todos(self) -> List[Todo]:
        self._ensure_ready()
        return await self._memory.get_todos()

    async def remove_todo(self, id: str) -> bool:
        self._ensure_ready()
        return await self._memory.remove_todo(id)

    async def set_todos(self, todos: List[Todo]) -> None:
        self._ensure_ready()
        await self._memory.set_todos(todos)

    async def update_todo(self, id: str) -> Optional[Todo]:
        self._ensure_ready()
        return await self._memory.update_todo(id)


class AsyncRedisStorage(AsyncTodoStorageProtocol):
    def __init__(self) -> None:
        self._initialized = False
        self._closed = False
        self._memory = AsyncMemoryStorage()

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
        return await self._memory.add_todo(todo)

    async def get_todo(self, id: str) -> Optional[Todo]:
        self._ensure_ready()
        return await self._memory.get_todo(id)

    async def get_todos(self) -> List[Todo]:
        self._ensure_ready()
        return await self._memory.get_todos()

    async def remove_todo(self, id: str) -> bool:
        self._ensure_ready()
        return await self._memory.remove_todo(id)

    async def set_todos(self, todos: List[Todo]) -> None:
        self._ensure_ready()
        await self._memory.set_todos(todos)

    async def update_todo(self, id: str) -> Optional[Todo]:
        self._ensure_ready()
        return await self._memory.update_todo(id)


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
        return None

    def get_serialization_name(self) -> str:
        return "todo"

    def get_toolset(self) -> Optional[AbstractToolset[Any]]:
        return None


def _todo_to_dict(todo: Todo) -> Dict[str, Any]:
    return {
        "active_form": todo.active_form,
        "content": todo.content,
        "depends_on": todo.depends_on,
        "id": todo.id,
        "parent_id": todo.parent_id,
        "status": todo.status,
    }


def _todo_from_dict(data: Dict[str, Any]) -> Todo:
    return Todo(
        active_form=data["active_form"],
        content=data["content"],
        depends_on=data.get("depends_on"),
        id=data.get("id"),
        parent_id=data.get("parent_id"),
        status=data.get("status", "pending"),
    )


def serialize_todos(todos: List[Todo]) -> str:
    if not isinstance(todos, list) or any(not isinstance(t, Todo) for t in todos):
        raise ValueError("todos must be a list[Todo]")
    return json.dumps([_todo_to_dict(t) for t in todos], ensure_ascii=False)


def deserialize_todos(payload: str) -> List[Todo]:
    data = json.loads(payload)
    if not isinstance(data, list):
        raise ValueError("Invalid payload")
    return [_todo_from_dict(item) for item in data]