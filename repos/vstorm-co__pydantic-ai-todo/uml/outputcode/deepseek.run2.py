import asyncio
import enum
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Protocol,
    runtime_checkable,
    Union,
)

# ============================================================================
# types
# ============================================================================

TodoStatus = Literal["pending", "in_progress", "completed", "blocked"]


@dataclass
class Todo:
    content: str
    active_form: str = ""
    depends_on: Optional[List[str]] = None
    id: Optional[str] = None
    parent_id: Optional[str] = None
    status: TodoStatus = "pending"

    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())
        if self.depends_on is None:
            self.depends_on = []


@dataclass
class TodoItem:
    id: Optional[str] = None
    content: Optional[str] = None
    active_form: Optional[str] = None
    depends_on: Optional[List[str]] = None
    parent_id: Optional[str] = None
    status: Optional[TodoStatus] = None


@dataclass
class TodoStatusUpdate:
    status: Optional[TodoStatus] = None
    todo_id: Optional[str] = None


# ============================================================================
# events
# ============================================================================

class TodoEventType(enum.Enum):
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    STATUS_CHANGED = "status_changed"
    COMPLETED = "completed"


EventCallback = Callable[["TodoEvent"], None]


@dataclass
class TodoEvent:
    todo: Todo
    event_type: TodoEventType
    previous_state: Optional[Todo] = None
    timestamp: Optional[datetime] = field(default_factory=datetime.utcnow)


class TodoEventEmitter:
    def __init__(self) -> None:
        self._listeners: Dict[TodoEventType, List[EventCallback]] = {
            etype: [] for etype in TodoEventType
        }

    def on(self, event_type: TodoEventType, callback: EventCallback) -> EventCallback:
        self._listeners[event_type].append(callback)
        return callback

    def off(self, event_type: TodoEventType, callback: EventCallback) -> bool:
        try:
            self._listeners[event_type].remove(callback)
            return True
        except ValueError:
            return False

    def emit(self, event: TodoEvent) -> None:
        for cb in self._listeners[event.event_type]:
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


# ============================================================================
# storage protocols
# ============================================================================

@runtime_checkable
class TodoStorageProtocol(Protocol):
    todos: List[Todo]

    def add_todo(self, todo: Todo) -> Todo:
        ...

    def get_todo(self, id: str) -> Optional[Todo]:
        ...

    def get_todos(self) -> List[Todo]:
        ...

    def remove_todo(self, id: str) -> bool:
        ...

    def set_todos(self, todos: List[Todo]) -> None:
        ...

    def update_todo(self, id: str) -> Optional[Todo]:
        ...


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


# ============================================================================
# sync storage implementation
# ============================================================================

class TodoStorage:
    def __init__(self) -> None:
        self.todos: List[Todo] = []

    def add_todo(self, todo: Todo) -> Todo:
        self.todos.append(todo)
        return todo

    def get_todo(self, id: str) -> Optional[Todo]:
        for t in self.todos:
            if t.id == id:
                return t
        return None

    def get_todos(self) -> List[Todo]:
        return list(self.todos)

    def remove_todo(self, id: str) -> bool:
        for i, t in enumerate(self.todos):
            if t.id == id:
                del self.todos[i]
                return True
        return False

    def set_todos(self, todos: List[Todo]) -> None:
        self.todos = todos

    def update_todo(self, id: str) -> Optional[Todo]:
        # Placeholder: the actual update would be based on an update object,
        # but the protocol shows no arguments for the delta. Real usage would
        # need more context, so we just return the todo unchanged.
        return self.get_todo(id)


# ============================================================================
# async storage implementations
# ============================================================================

class AsyncMemoryStorage:
    def __init__(self) -> None:
        self._todos: Dict[str, Todo] = {}

    async def add_todo(self, todo: Todo) -> Todo:
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
        self._todos = {t.id: t for t in todos}

    async def update_todo(self, id: str) -> Optional[Todo]:
        # placeholder – real logic would apply partial update
        return self._todos.get(id)


class AsyncPostgresStorage:
    def __init__(self, connection_string: str = "") -> None:
        self._connection_string = connection_string
        self._todos: Dict[str, Todo] = {}

    async def initialize(self) -> None:
        # In a real implementation this would create tables etc.
        pass

    async def close(self) -> None:
        # Clean up connections
        pass

    async def add_todo(self, todo: Todo) -> Todo:
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
        self._todos = {t.id: t for t in todos}

    async def update_todo(self, id: str) -> Optional[Todo]:
        return self._todos.get(id)


class AsyncRedisStorage:
    def __init__(self, redis_url: str = "") -> None:
        self._redis_url = redis_url
        self._todos: Dict[str, Todo] = {}

    async def initialize(self) -> None:
        # Connect to Redis, check health, etc.
        pass

    async def close(self) -> None:
        # Disconnect
        pass

    async def add_todo(self, todo: Todo) -> Todo:
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
        self._todos = {t.id: t for t in todos}

    async def update_todo(self, id: str) -> Optional[Todo]:
        return self._todos.get(id)


# ============================================================================
# capability
# ============================================================================

class AbstractToolset:
    """Placeholder for a toolset base class."""
    pass


class TodoCapability:
    def __init__(
        self,
        storage: Optional[TodoStorageProtocol] = None,
        async_storage: Optional[AsyncTodoStorageProtocol] = None,
        enable_subtasks: bool = False,
        descriptions: Optional[Dict[str, str]] = None,
    ) -> None:
        self.storage = storage
        self.async_storage = async_storage
        self.enable_subtasks = enable_subtasks
        self.descriptions = descriptions

    def get_instructions(self) -> Any:
        # Return agent instructions (placeholder)
        return None

    def get_serialization_name(self) -> str:
        return "todo"

    def get_toolset(self) -> Optional[AbstractToolset]:
        # Return a toolset that uses the storage (placeholder)
        return None