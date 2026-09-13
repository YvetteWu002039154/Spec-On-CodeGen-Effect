from __future__ import annotations

from typing import Optional, Literal, List, Dict, Any, Protocol, Callable, TypeVar
from datetime import datetime
from enum import Enum, auto
from dataclasses import dataclass, field

T = TypeVar('T')

class AbstractToolset(Protocol[T]):
    pass

@dataclass
class Todo:
    active_form: str
    content: str
    status: Literal['pending', 'in_progress', 'completed', 'blocked']
    depends_on: Optional[List[str]] = None
    id: Optional[str] = None
    parent_id: str | None = None

@dataclass
class TodoItem:
    active_form: Optional[str] = None
    content: Optional[str] = None
    depends_on: Optional[List[str]] = None
    id: str | None = None
    parent_id: str | None = None
    status: Optional[Literal['pending', 'in_progress', 'completed', 'blocked']] = None

@dataclass
class TodoStatusUpdate:
    status: Optional[Literal['pending', 'in_progress', 'completed', 'blocked']] = None
    todo_id: Optional[str] = None

class TodoEventType(Enum):
    CREATED = auto()
    UPDATED = auto()
    DELETED = auto()
    STATUS_CHANGED = auto()
    COMPLETED = auto()

@dataclass
class TodoEvent:
    event_type: TodoEventType
    todo: Todo
    previous_state: Todo | None = None
    timestamp: Optional[datetime] = None

EventCallback = Callable[[TodoEvent], None]

class TodoEventEmitter:
    def __init__(self) -> None:
        self._listeners: Dict[TodoEventType, List[EventCallback]] = {
            event_type: [] for event_type in TodoEventType
        }

    def emit(self, event: TodoEvent) -> None:
        if event.timestamp is None:
            event.timestamp = datetime.now()
        for callback in self._listeners.get(event.event_type, []):
            callback(event)

    def off(self, event_type: TodoEventType, callback: EventCallback) -> bool:
        if callback in self._listeners.get(event_type, []):
            self._listeners[event_type].remove(callback)
            return True
        return False

    def on(self, event_type: TodoEventType, callback: EventCallback) -> EventCallback:
        self._listeners.setdefault(event_type, []).append(callback)
        return callback

    def on_completed(self, callback: EventCallback) -> EventCallback:
        return self.on(TodoEventType.COMPLETED, callback)

    def on_created(self, callback: EventCallback) -> EventCallback:
        return self.on(TodoEventType.CREATED, callback)

    def on_deleted(self, callback: EventCallback) -> EventCallback:
        return self.on(TodoEventType.DELETED, callback)

    def on_status_changed(self, callback: EventCallback) -> EventCallback:
        return self.on(TodoEventType.STATUS_CHANGED, callback)

    def on_updated(self, callback: EventCallback) -> EventCallback:
        return self.on(TodoEventType.UPDATED, callback)

class AsyncTodoStorageProtocol(Protocol):
    def add_todo(self, todo: Todo) -> Todo: ...
    def get_todo(self, id: str) -> Todo | None: ...
    def get_todos(self) -> list[Todo]: ...
    def remove_todo(self, id: str) -> bool: ...
    def set_todos(self, todos: list[Todo]) -> None: ...
    def update_todo(self, id: str) -> Todo | None: ...

class TodoStorageProtocol(Protocol):
    todos: list[Todo]

class TodoStorage:
    def __init__(self) -> None:
        self.todos: list[Todo] = []

class AsyncMemoryStorage:
    def __init__(self) -> None:
        self._todos: Dict[str, Todo] = {}

    def add_todo(self, todo: Todo) -> Todo:
        if todo.id is not None:
            self._todos[todo.id] = todo
        return todo

    def get_todo(self, id: str) -> Todo | None:
        return self._todos.get(id)

    def get_todos(self) -> list[Todo]:
        return list(self._todos.values())

    def remove_todo(self, id: str) -> bool:
        if id in self._todos:
            del self._todos[id]
            return True
        return False

    def set_todos(self, todos: list[Todo]) -> None:
        self._todos = {todo.id: todo for todo in todos if todo.id is not None}

    def update_todo(self, id: str) -> Todo | None:
        return self._todos.get(id)

class AsyncPostgresStorage:
    def __init__(self) -> None:
        self._todos: Dict[str, Todo] = {}

    def add_todo(self, todo: Todo) -> Todo:
        if todo.id is not None:
            self._todos[todo.id] = todo
        return todo

    def close(self) -> None:
        pass

    def get_todo(self, id: str) -> Todo | None:
        return self._todos.get(id)

    def get_todos(self) -> list[Todo]:
        return list(self._todos.values())

    def initialize(self) -> None:
        pass

    def remove_todo(self, id: str) -> bool:
        if id in self._todos:
            del self._todos[id]
            return True
        return False

    def set_todos(self, todos: list[Todo]) -> None:
        self._todos = {todo.id: todo for todo in todos if todo.id is not None}

    def update_todo(self, id: str) -> Todo | None:
        return self._todos.get(id)

class AsyncRedisStorage:
    def __init__(self) -> None:
        self._todos: Dict[str, Todo] = {}

    def add_todo(self, todo: Todo) -> Todo:
        if todo.id is not None:
            self._todos[todo.id] = todo
        return todo

    def close(self) -> None:
        pass

    def get_todo(self, id: str) -> Todo | None:
        return self._todos.get(id)

    def get_todos(self) -> list[Todo]:
        return list(self._todos.values())

    def initialize(self) -> None:
        pass

    def remove_todo(self, id: str) -> bool:
        if id in self._todos:
            del self._todos[id]
            return True
        return False

    def set_todos(self, todos: list[Todo]) -> None:
        self._todos = {todo.id: todo for todo in todos if todo.id is not None}

    def update_todo(self, id: str) -> Todo | None:
        return self._todos.get(id)

class TodoCapability:
    def __init__(
        self,
        enable_subtasks: bool,
        async_storage: AsyncTodoStorageProtocol | None = None,
        descriptions: dict[str, str] | None = None,
        storage: TodoStorageProtocol | None = None
    ) -> None:
        self.enable_subtasks = enable_subtasks
        self.async_storage = async_storage
        self.descriptions = descriptions
        self.storage = storage

    def get_instructions(self) -> Any:
        return "Instructions for TodoCapability"

    def get_serialization_name(self) -> str:
        return "todo_capability"

    def get_toolset(self) -> AbstractToolset[Any] | None:
        return None