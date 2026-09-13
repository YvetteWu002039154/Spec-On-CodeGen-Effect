from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, Generic, List, Optional, Protocol, TypeVar, Literal

# Type aliases
EventCallback = Callable[["TodoEvent"], None]
T = TypeVar("T")

# ==============================================================================
# Events
# ==============================================================================

@dataclass(frozen=True)
class TodoEventType:
    name: str

    # Predefined event types
    CREATED: "TodoEventType"
    UPDATED: "TodoEventType"
    DELETED: "TodoEventType"
    COMPLETED: "TodoEventType"
    STATUS_CHANGED: "TodoEventType"

TodoEventType.CREATED = TodoEventType("created")
TodoEventType.UPDATED = TodoEventType("updated")
TodoEventType.DELETED = TodoEventType("deleted")
TodoEventType.COMPLETED = TodoEventType("completed")
TodoEventType.STATUS_CHANGED = TodoEventType("status_changed")


@dataclass
class TodoEvent:
    event_type: TodoEventType
    todo: "Todo"
    previous_state: Optional["Todo"] = None
    timestamp: Optional[datetime] = None


class TodoEventEmitter:
    def __init__(self) -> None:
        self._listeners: Dict[TodoEventType, List[EventCallback]] = {}

    def on(self, event_type: TodoEventType, callback: EventCallback) -> EventCallback:
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(callback)
        return callback

    def off(self, event_type: TodoEventType, callback: EventCallback) -> bool:
        listeners = self._listeners.get(event_type)
        if listeners and callback in listeners:
            listeners.remove(callback)
            return True
        return False

    def emit(self, event: TodoEvent) -> None:
        listeners = self._listeners.get(event.event_type, [])
        for callback in listeners:
            callback(event)

    def on_created(self, callback: EventCallback) -> EventCallback:
        return self.on(TodoEventType.CREATED, callback)

    def on_updated(self, callback: EventCallback) -> EventCallback:
        return self.on(TodoEventType.UPDATED, callback)

    def on_deleted(self, callback: EventCallback) -> EventCallback:
        return self.on(TodoEventType.DELETED, callback)

    def on_completed(self, callback: EventCallback) -> EventCallback:
        return self.on(TodoEventType.COMPLETED, callback)

    def on_status_changed(self, callback: EventCallback) -> EventCallback:
        return self.on(TodoEventType.STATUS_CHANGED, callback)


# ==============================================================================
# Types
# ==============================================================================

TodoStatus = Literal["pending", "in_progress", "completed", "blocked"]


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
    todo_id: Optional[str] = None
    status: Optional[TodoStatus] = None


@dataclass
class Todo:
    content: str
    active_form: str = ""
    depends_on: Optional[List[str]] = None
    id: Optional[str] = None
    parent_id: Optional[str] = None
    status: TodoStatus = "pending"


# ==============================================================================
# Storage
# ==============================================================================

class AsyncTodoStorageProtocol(ABC):
    @abstractmethod
    async def add_todo(self, todo: Todo) -> Todo:
        ...

    @abstractmethod
    async def get_todo(self, id: str) -> Optional[Todo]:
        ...

    @abstractmethod
    async def get_todos(self) -> List[Todo]:
        ...

    @abstractmethod
    async def remove_todo(self, id: str) -> bool:
        ...

    @abstractmethod
    async def set_todos(self, todos: List[Todo]) -> None:
        ...

    @abstractmethod
    async def update_todo(self, id: str) -> Optional[Todo]:
        ...


class TodoStorageProtocol(ABC):
    todos: List[Todo]

    @abstractmethod
    def __init__(self) -> None:
        self.todos = []


class TodoStorage:
    def __init__(self) -> None:
        self.todos: List[Todo] = []


class AsyncMemoryStorage(AsyncTodoStorageProtocol):
    def __init__(self) -> None:
        self._todos: Dict[str, Todo] = {}

    async def add_todo(self, todo: Todo) -> Todo:
        if todo.id is None:
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
        self._todos.clear()
        for todo in todos:
            if todo.id is None:
                todo.id = str(uuid.uuid4())
            self._todos[todo.id] = todo

    async def update_todo(self, id: str) -> Optional[Todo]:
        return self._todos.get(id)


class AsyncPostgresStorage(AsyncTodoStorageProtocol):
    def __init__(self) -> None:
        self._todos: Dict[str, Todo] = {}
        self._initialized = False

    def initialize(self) -> None:
        # In a real implementation, this would set up the database connection
        self._initialized = True

    def close(self) -> None:
        # In a real implementation, this would close the database connection
        self._initialized = False

    async def add_todo(self, todo: Todo) -> Todo:
        if not self._initialized:
            raise RuntimeError("Storage not initialized")
        if todo.id is None:
            todo.id = str(uuid.uuid4())
        self._todos[todo.id] = todo
        return todo

    async def get_todo(self, id: str) -> Optional[Todo]:
        if not self._initialized:
            raise RuntimeError("Storage not initialized")
        return self._todos.get(id)

    async def get_todos(self) -> List[Todo]:
        if not self._initialized:
            raise RuntimeError("Storage not initialized")
        return list(self._todos.values())

    async def remove_todo(self, id: str) -> bool:
        if not self._initialized:
            raise RuntimeError("Storage not initialized")
        if id in self._todos:
            del self._todos[id]
            return True
        return False

    async def set_todos(self, todos: List[Todo]) -> None:
        if not self._initialized:
            raise RuntimeError("Storage not initialized")
        self._todos.clear()
        for todo in todos:
            if todo.id is None:
                todo.id = str(uuid.uuid4())
            self._todos[todo.id] = todo

    async def update_todo(self, id: str) -> Optional[Todo]:
        if not self._initialized:
            raise RuntimeError("Storage not initialized")
        return self._todos.get(id)


class AsyncRedisStorage(AsyncTodoStorageProtocol):
    def __init__(self) -> None:
        self._todos: Dict[str, Todo] = {}
        self._initialized = False

    def initialize(self) -> None:
        # In a real implementation, this would connect to Redis
        self._initialized = True

    def close(self) -> None:
        # In a real implementation, this would close the Redis connection
        self._initialized = False

    async def add_todo(self, todo: Todo) -> Todo:
        if not self._initialized:
            raise RuntimeError("Storage not initialized")
        if todo.id is None:
            todo.id = str(uuid.uuid4())
        self._todos[todo.id] = todo
        return todo

    async def get_todo(self, id: str) -> Optional[Todo]:
        if not self._initialized:
            raise RuntimeError("Storage not initialized")
        return self._todos.get(id)

    async def get_todos(self) -> List[Todo]:
        if not self._initialized:
            raise RuntimeError("Storage not initialized")
        return list(self._todos.values())

    async def remove_todo(self, id: str) -> bool:
        if not self._initialized:
            raise RuntimeError("Storage not initialized")
        if id in self._todos:
            del self._todos[id]
            return True
        return False

    async def set_todos(self, todos: List[Todo]) -> None:
        if not self._initialized:
            raise RuntimeError("Storage not initialized")
        self._todos.clear()
        for todo in todos:
            if todo.id is None:
                todo.id = str(uuid.uuid4())
            self._todos[todo.id] = todo

    async def update_todo(self, id: str) -> Optional[Todo]:
        if not self._initialized:
            raise RuntimeError("Storage not initialized")
        return self._todos.get(id)


# ==============================================================================
# Capability
# ==============================================================================

class AbstractToolset(Generic[T]):
    """Placeholder for an abstract toolset type."""
    def __init__(self) -> None:
        pass


class TodoCapability:
    def __init__(
        self,
        enable_subtasks: bool = False,
        async_storage: Optional[AsyncTodoStorageProtocol] = None,
        storage: Optional[TodoStorageProtocol] = None,
        descriptions: Optional[Dict[str, str]] = None,
    ) -> None:
        self.enable_subtasks = enable_subtasks
        self.async_storage = async_storage
        self.storage = storage
        self.descriptions = descriptions

    def get_instructions(self) -> Any:
        # Stub that returns instructions about the todo capability
        return "Todo management instructions"

    def get_serialization_name(self) -> str:
        return "todo"

    def get_toolset(self) -> Optional[AbstractToolset[Any]]:
        # Return a toolset if available, otherwise None
        return None