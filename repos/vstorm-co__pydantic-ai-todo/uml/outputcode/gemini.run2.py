from typing import Optional, Literal, Any, Callable, Protocol, Generic, TypeVar, List, Dict
from datetime import datetime
from enum import Enum, auto
from dataclasses import dataclass, field
import uuid

T = TypeVar('T')

class AbstractToolset(Generic[T]):
    pass

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

    def on(self, event_type: TodoEventType, callback: EventCallback) -> EventCallback:
        self._listeners[event_type].append(callback)
        return callback

    def off(self, event_type: TodoEventType, callback: EventCallback) -> bool:
        if callback in self._listeners.get(event_type, []):
            self._listeners[event_type].remove(callback)
            return True
        return False

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

class AsyncTodoStorageProtocol(Protocol):
    async def add_todo(self, todo: Todo) -> Todo: ...
    async def get_todo(self, id: str) -> Optional[Todo]: ...
    async def get_todos(self) -> List[Todo]: ...
    async def remove_todo(self, id: str) -> bool: ...
    async def set_todos(self, todos: List[Todo]) -> None: ...
    async def update_todo(self, id: str) -> Optional[Todo]: ...

class TodoStorageProtocol(Protocol):
    todos: List[Todo]

class TodoStorage:
    def __init__(self) -> None:
        self.todos: List[Todo] = []

class AsyncMemoryStorage:
    def __init__(self) -> None:
        self._todos: Dict[str, Todo] = {}

    async def add_todo(self, todo: Todo) -> Todo:
        if not todo.id:
            todo.id = str(uuid.uuid4())
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
        self._todos = {t.id: t for t in todos if t.id is not None}

    async def update_todo(self, id: str) -> Optional[Todo]:
        return self._todos.get(id)

class AsyncPostgresStorage:
    def __init__(self) -> None:
        self._todos: Dict[str, Todo] = {}
        self._initialized: bool = False

    async def initialize(self) -> None:
        self._initialized = True

    async def close(self) -> None:
        self._initialized = False

    async def add_todo(self, todo: Todo) -> Todo:
        if not todo.id:
            todo.id = str(uuid.uuid4())
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
        self._todos = {t.id: t for t in todos if t.id is not None}

    async def update_todo(self, id: str) -> Optional[Todo]:
        return self._todos.get(id)

class AsyncRedisStorage:
    def __init__(self) -> None:
        self._todos: Dict[str, Todo] = {}
        self._initialized: bool = False

    async def initialize(self) -> None:
        self._initialized = True

    async def close(self) -> None:
        self._initialized = False

    async def add_todo(self, todo: Todo) -> Todo:
        if not todo.id:
            todo.id = str(uuid.uuid4())
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
        self._todos = {t.id: t for t in todos if t.id is not None}

    async def update_todo(self, id: str) -> Optional[Todo]:
        return self._todos.get(id)

class TodoCapability:
    def __init__(
        self,
        enable_subtasks: bool,
        async_storage: Optional[AsyncTodoStorageProtocol] = None,
        storage: Optional[TodoStorageProtocol] = None,
        descriptions: Optional[Dict[str, str]] = None
    ) -> None:
        self.enable_subtasks = enable_subtasks
        self.async_storage = async_storage
        self.storage = storage
        self.descriptions = descriptions

    def get_instructions(self) -> Any:
        return "Instructions for TodoCapability"

    def get_serialization_name(self) -> str:
        return "TodoCapability"

    def get_toolset(self) -> Optional[AbstractToolset[Any]]:
        return None