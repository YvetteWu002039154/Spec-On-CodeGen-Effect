from typing import Optional, Literal, Any, Callable, Protocol, Dict, List, Generic, TypeVar
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field

T = TypeVar('T')

class AbstractToolset(Generic[T]):
    pass

class TodoEventType(Enum):
    CREATED = "CREATED"
    UPDATED = "UPDATED"
    DELETED = "DELETED"
    STATUS_CHANGED = "STATUS_CHANGED"
    COMPLETED = "COMPLETED"

@dataclass
class Todo:
    active_form: str
    content: str
    status: Literal['pending', 'in_progress', 'completed', 'blocked']
    depends_on: Optional[List[str]] = None
    id: Optional[str] = None
    parent_id: Optional[str] = None

@dataclass
class TodoItem:
    active_form: Optional[str] = None
    content: Optional[str] = None
    status: Optional[Literal['pending', 'in_progress', 'completed', 'blocked']] = None
    depends_on: Optional[List[str]] = None
    id: Optional[str] = None
    parent_id: Optional[str] = None

@dataclass
class TodoStatusUpdate:
    status: Optional[Literal['pending', 'in_progress', 'completed', 'blocked']] = None
    todo_id: Optional[str] = None

@dataclass
class TodoEvent:
    event_type: TodoEventType
    todo: Todo
    previous_state: Optional[Todo] = None
    timestamp: Optional[datetime] = field(default_factory=datetime.now)

EventCallback = Callable[[TodoEvent], None]

class TodoEventEmitter:
    def __init__(self) -> None:
        self._listeners: Dict[TodoEventType, List[EventCallback]] = {
            event_type: [] for event_type in TodoEventType
        }

    def emit(self, event: TodoEvent) -> None:
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
    async def add_todo(self, todo: Todo) -> Todo: ...
    async def get_todo(self, id: str) -> Optional[Todo]: ...
    async def get_todos(self) -> List[Todo]: ...
    async def remove_todo(self, id: str) -> bool: ...
    async def set_todos(self, todos: List[Todo]) -> None: ...
    async def update_todo(self, id: str) -> Optional[Todo]: ...

class TodoStorageProtocol(Protocol):
    todos: List[Todo]

class AsyncMemoryStorage(AsyncTodoStorageProtocol):
    def __init__(self) -> None:
        self._todos: Dict[str, Todo] = {}

    async def add_todo(self, todo: Todo) -> Todo:
        if todo.id is None:
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
        self._todos = {todo.id: todo for todo in todos if todo.id is not None}

    async def update_todo(self, id: str) -> Optional[Todo]:
        return self._todos.get(id)

class AsyncPostgresStorage(AsyncTodoStorageProtocol):
    def __init__(self) -> None:
        self._todos: Dict[str, Todo] = {}
        self._is_initialized: bool = False

    async def initialize(self) -> None:
        self._is_initialized = True

    async def close(self) -> None:
        self._is_initialized = False

    async def add_todo(self, todo: Todo) -> Todo:
        if todo.id is None:
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
        self._todos = {todo.id: todo for todo in todos if todo.id is not None}

    async def update_todo(self, id: str) -> Optional[Todo]:
        return self._todos.get(id)

class AsyncRedisStorage(AsyncTodoStorageProtocol):
    def __init__(self) -> None:
        self._todos: Dict[str, Todo] = {}
        self._is_initialized: bool = False

    async def initialize(self) -> None:
        self._is_initialized = True

    async def close(self) -> None:
        self._is_initialized = False

    async def add_todo(self, todo: Todo) -> Todo:
        if todo.id is None:
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
        self._todos = {todo.id: todo for todo in todos if todo.id is not None}

    async def update_todo(self, id: str) -> Optional[Todo]:
        return self._todos.get(id)

class TodoStorage(TodoStorageProtocol):
    def __init__(self) -> None:
        self.todos: List[Todo] = []

class TodoCapability:
    def __init__(
        self,
        enable_subtasks: bool,
        async_storage: Optional[AsyncTodoStorageProtocol] = None,
        descriptions: Optional[Dict[str, str]] = None,
        storage: Optional[TodoStorageProtocol] = None
    ) -> None:
        self.enable_subtasks = enable_subtasks
        self.async_storage = async_storage
        self.descriptions = descriptions
        self.storage = storage

    def get_instructions(self) -> Any:
        return "Instructions for TodoCapability"

    def get_serialization_name(self) -> str:
        return "TodoCapability"

    def get_toolset(self) -> Optional[AbstractToolset[Any]]:
        return None