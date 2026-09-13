from typing import Optional, Literal, Any, Protocol, Callable, Generic, TypeVar
from datetime import datetime
from dataclasses import dataclass
from enum import Enum, auto

T = TypeVar('T')

class AbstractToolset(Generic[T]):
    pass

@dataclass
class Todo:
    active_form: str
    content: str
    status: Literal['pending', 'in_progress', 'completed', 'blocked']
    id: Optional[str] = None
    parent_id: Optional[str] = None
    depends_on: Optional[list[str]] = None

@dataclass
class TodoItem:
    active_form: Optional[str] = None
    content: Optional[str] = None
    depends_on: Optional[list[str]] = None
    id: Optional[str] = None
    parent_id: Optional[str] = None
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
    previous_state: Optional[Todo] = None
    timestamp: Optional[datetime] = None

EventCallback = Callable[[TodoEvent], None]

class TodoEventEmitter:
    def __init__(self) -> None:
        self._listeners: dict[TodoEventType, list[EventCallback]] = {}

    def emit(self, event: TodoEvent) -> None:
        if event.timestamp is None:
            event.timestamp = datetime.now()
        for callback in self._listeners.get(event.event_type, []):
            callback(event)

    def on(self, event_type: TodoEventType, callback: EventCallback) -> EventCallback:
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(callback)
        return callback

    def off(self, event_type: TodoEventType, callback: EventCallback) -> bool:
        if event_type in self._listeners and callback in self._listeners[event_type]:
            self._listeners[event_type].remove(callback)
            return True
        return False

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
    def get_todo(self, id: str) -> Optional[Todo]: ...
    def get_todos(self) -> list[Todo]: ...
    def remove_todo(self, id: str) -> bool: ...
    def set_todos(self, todos: list[Todo]) -> None: ...
    def update_todo(self, id: str) -> Optional[Todo]: ...

class TodoStorageProtocol(Protocol):
    @property
    def todos(self) -> list[Todo]: ...

class AsyncMemoryStorage:
    def __init__(self) -> None:
        self._todos: dict[str, Todo] = {}

    def add_todo(self, todo: Todo) -> Todo:
        if todo.id is None:
            todo.id = str(len(self._todos) + 1)
        self._todos[todo.id] = todo
        return todo

    def get_todo(self, id: str) -> Optional[Todo]:
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

    def update_todo(self, id: str) -> Optional[Todo]:
        return self._todos.get(id)

class AsyncPostgresStorage:
    def __init__(self) -> None:
        self._todos: dict[str, Todo] = {}
        self._is_initialized: bool = False

    def initialize(self) -> None:
        self._is_initialized = True

    def close(self) -> None:
        self._is_initialized = False

    def add_todo(self, todo: Todo) -> Todo:
        if todo.id is None:
            todo.id = str(len(self._todos) + 1)
        self._todos[todo.id] = todo
        return todo

    def get_todo(self, id: str) -> Optional[Todo]:
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

    def update_todo(self, id: str) -> Optional[Todo]:
        return self._todos.get(id)

class AsyncRedisStorage:
    def __init__(self) -> None:
        self._todos: dict[str, Todo] = {}
        self._is_initialized: bool = False

    def initialize(self) -> None:
        self._is_initialized = True

    def close(self) -> None:
        self._is_initialized = False

    def add_todo(self, todo: Todo) -> Todo:
        if todo.id is None:
            todo.id = str(len(self._todos) + 1)
        self._todos[todo.id] = todo
        return todo

    def get_todo(self, id: str) -> Optional[Todo]:
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

    def update_todo(self, id: str) -> Optional[Todo]:
        return self._todos.get(id)

class TodoStorage:
    def __init__(self) -> None:
        self.todos: list[Todo] = []

class TodoCapability:
    def __init__(
        self,
        enable_subtasks: bool,
        async_storage: Optional[AsyncTodoStorageProtocol] = None,
        storage: Optional[TodoStorageProtocol] = None,
        descriptions: Optional[dict[str, str]] = None
    ) -> None:
        self.enable_subtasks = enable_subtasks
        self.async_storage = async_storage
        self.storage = storage
        self.descriptions = descriptions

    def get_instructions(self) -> Any:
        return "Manage todos."

    def get_serialization_name(self) -> str:
        return "todo_capability"

    def get_toolset(self) -> Optional[AbstractToolset[Any]]:
        return None