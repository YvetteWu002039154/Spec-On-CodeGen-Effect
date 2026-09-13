from __future__ import annotations

import asyncio
import datetime
import enum
import typing
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Literal, Optional, TypeVar, Protocol, runtime_checkable

# Type aliases
EventCallback = Callable[['TodoEvent'], Any]


# =====================================================================
# types.py
# =====================================================================

class TodoStatus(Literal['pending', 'in_progress', 'completed', 'blocked']):
    """Valid status values for a Todo."""
    pass


class Todo:
    """Represents a full-fledged todo item."""
    
    def __init__(
        self,
        content: str,
        *,
        id: Optional[str] = None,
        parent_id: Optional[str] = None,
        status: TodoStatus = 'pending',
        active_form: str = '',
        depends_on: Optional[List[str]] = None,
    ) -> None:
        self.id = id
        self.parent_id = parent_id
        self.content = content
        self.status: TodoStatus = status
        self.active_form = active_form
        self.depends_on = depends_on or []

    def __repr__(self) -> str:
        return (
            f"Todo(id={self.id!r}, content={self.content!r}, status={self.status!r})"
        )


class TodoItem:
    """A partial representation of a todo, used for updates."""
    
    def __init__(
        self,
        *,
        id: Optional[str] = None,
        parent_id: Optional[str] = None,
        content: Optional[str] = None,
        status: Optional[TodoStatus] = None,
        active_form: Optional[str] = None,
        depends_on: Optional[List[str]] = None,
    ) -> None:
        self.id = id
        self.parent_id = parent_id
        self.content = content
        self.status = status
        self.active_form = active_form
        self.depends_on = depends_on


class TodoStatusUpdate:
    """Payload for updating a todo's status."""
    
    def __init__(
        self,
        todo_id: Optional[str] = None,
        status: Optional[TodoStatus] = None,
    ) -> None:
        self.todo_id = todo_id
        self.status = status


# =====================================================================
# events.py
# =====================================================================

class TodoEventType(enum.Enum):
    """Enumeration of all possible todo event types."""
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    STATUS_CHANGED = "status_changed"
    COMPLETED = "completed"

    @property
    def name(self) -> str:
        return self.value


class TodoEvent:
    """Event payload for todo modifications."""
    
    def __init__(
        self,
        event_type: TodoEventType,
        todo: Todo,
        *,
        previous_state: Optional[Todo] = None,
        timestamp: Optional[datetime.datetime] = None,
    ) -> None:
        self.event_type = event_type
        self.todo = todo
        self.previous_state = previous_state
        self.timestamp = timestamp or datetime.datetime.now(datetime.timezone.utc)


class TodoEventEmitter:
    """Manages subscriptions and emission of todo events."""
    
    def __init__(self) -> None:
        self._listeners: Dict[TodoEventType, List[EventCallback]] = {
            t: [] for t in TodoEventType
        }
    
    def on(self, event_type: TodoEventType, callback: EventCallback) -> EventCallback:
        """Register a listener for a specific event type."""
        self._listeners[event_type].append(callback)
        return callback
    
    def off(self, event_type: TodoEventType, callback: EventCallback) -> bool:
        """Remove a listener for a specific event type. Returns True if removed."""
        try:
            self._listeners[event_type].remove(callback)
            return True
        except ValueError:
            return False
    
    def emit(self, event: TodoEvent) -> None:
        """Emit an event to all registered listeners of its type."""
        for callback in self._listeners[event.event_type]:
            callback(event)
    
    # Convenience methods
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


# =====================================================================
# storage.py
# =====================================================================

T = TypeVar('T', bound=Todo)


@runtime_checkable
class TodoStorageProtocol(Protocol):
    """Synchronous storage protocol for todo items."""
    todos: List[Todo]
    
    def add_todo(self, todo: Todo) -> Todo: ...
    def get_todo(self, id: str) -> Optional[Todo]: ...
    def get_todos(self) -> List[Todo]: ...
    def remove_todo(self, id: str) -> bool: ...
    def update_todo(self, id: str, updated: TodoItem) -> Optional[Todo]: ...
    def set_todos(self, todos: List[Todo]) -> None: ...


class TodoStorage(TodoStorageProtocol):
    """Synchronous, list-based storage implementation."""
    
    def __init__(self, initial_todos: Optional[List[Todo]] = None) -> None:
        self.todos: List[Todo] = initial_todos or []
        self._id_counter: int = 0
    
    def _generate_id(self) -> str:
        self._id_counter += 1
        return str(self._id_counter)
    
    def add_todo(self, todo: Todo) -> Todo:
        if todo.id is None:
            todo.id = self._generate_id()
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
    
    def update_todo(self, id: str, updated: TodoItem) -> Optional[Todo]:
        todo = self.get_todo(id)
        if todo is None:
            return None
        # Apply partial updates
        if updated.content is not None:
            todo.content = updated.content
        if updated.status is not None:
            todo.status = updated.status
        if updated.active_form is not None:
            todo.active_form = updated.active_form
        if updated.parent_id is not None:
            todo.parent_id = updated.parent_id
        if updated.depends_on is not None:
            todo.depends_on = updated.depends_on
        return todo
    
    def set_todos(self, todos: List[Todo]) -> None:
        self.todos = list(todos)


class AsyncTodoStorageProtocol(Protocol):
    """Asynchronous storage protocol for todo items."""
    
    async def add_todo(self, todo: Todo) -> Todo: ...
    async def get_todo(self, id: str) -> Optional[Todo]: ...
    async def get_todos(self) -> List[Todo]: ...
    async def remove_todo(self, id: str) -> bool: ...
    async def update_todo(self, id: str, updated: TodoItem) -> Optional[Todo]: ...
    async def set_todos(self, todos: List[Todo]) -> None: ...


class AsyncMemoryStorage(AsyncTodoStorageProtocol):
    """In-memory asynchronous storage."""
    
    def __init__(self) -> None:
        self._todos: Dict[str, Todo] = {}
        self._id_counter: int = 0
    
    def _generate_id(self) -> str:
        self._id_counter += 1
        return str(self._id_counter)
    
    async def add_todo(self, todo: Todo) -> Todo:
        if todo.id is None:
            todo.id = self._generate_id()
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
    
    async def update_todo(self, id: str, updated: TodoItem) -> Optional[Todo]:
        todo = self._todos.get(id)
        if todo is None:
            return None
        if updated.content is not None:
            todo.content = updated.content
        if updated.status is not None:
            todo.status = updated.status
        if updated.active_form is not None:
            todo.active_form = updated.active_form
        if updated.parent_id is not None:
            todo.parent_id = updated.parent_id
        if updated.depends_on is not None:
            todo.depends_on = updated.depends_on
        return todo
    
    async def set_todos(self, todos: List[Todo]) -> None:
        self._todos = {t.id: t for t in todos if t.id is not None}


class AsyncPostgresStorage(AsyncTodoStorageProtocol):
    """Postgres-backed asynchronous storage."""
    
    def __init__(self, dsn: str) -> None:
        self.dsn = dsn
        self._pool = None  # Simulated
    
    async def initialize(self) -> None:
        # In a real implementation, create pool and tables
        self._todos: Dict[str, Todo] = {}
    
    async def close(self) -> None:
        # In a real implementation, close pool
        self._todos.clear()
    
    async def add_todo(self, todo: Todo) -> Todo:
        if todo.id is None:
            import uuid
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
    
    async def update_todo(self, id: str, updated: TodoItem) -> Optional[Todo]:
        todo = self._todos.get(id)
        if todo is None:
            return None
        if updated.content is not None:
            todo.content = updated.content
        if updated.status is not None:
            todo.status = updated.status
        if updated.active_form is not None:
            todo.active_form = updated.active_form
        if updated.parent_id is not None:
            todo.parent_id = updated.parent_id
        if updated.depends_on is not None:
            todo.depends_on = updated.depends_on
        return todo
    
    async def set_todos(self, todos: List[Todo]) -> None:
        self._todos = {t.id: t for t in todos if t.id is not None}


class AsyncRedisStorage(AsyncTodoStorageProtocol):
    """Redis-backed asynchronous storage."""
    
    def __init__(self, url: str) -> None:
        self.url = url
        self._client = None  # Simulated
    
    async def initialize(self) -> None:
        self._data: Dict[str, bytes] = {}
    
    async def close(self) -> None:
        self._data.clear()
    
    async def add_todo(self, todo: Todo) -> Todo:
        if todo.id is None:
            import uuid
            todo.id = str(uuid.uuid4())
        # In a real implementation, serialize and store
        return todo
    
    async def get_todo(self, id: str) -> Optional[Todo]:
        # Fake
        return None
    
    async def get_todos(self) -> List[Todo]:
        return []
    
    async def remove_todo(self, id: str) -> bool:
        # Fake
        return True
    
    async def update_todo(self, id: str, updated: TodoItem) -> Optional[Todo]:
        # Fake
        return None
    
    async def set_todos(self, todos: List[Todo]) -> None:
        pass


# =====================================================================
# capability.py
# =====================================================================

class AbstractToolset(ABC):
    """Placeholder for toolset interface."""
    @abstractmethod
    def register(self, tool: Any) -> None: ...


class TodoCapability:
    """Connects todo storage to a pydantic-ai agent."""
    
    def __init__(
        self,
        *,
        storage: Optional[TodoStorageProtocol] = None,
        async_storage: Optional[AsyncTodoStorageProtocol] = None,
        enable_subtasks: bool = False,
        descriptions: Optional[Dict[str, str]] = None,
    ) -> None:
        self.storage = storage
        self.async_storage = async_storage
        self.enable_subtasks = enable_subtasks
        self.descriptions = descriptions or {}
    
    def get_serialization_name(self) -> str:
        return "todo"
    
    def get_instructions(self) -> Any:
        return (
            "You have access to a todo list. Use it to track tasks and their statuses."
        )
    
    def get_toolset(self) -> Optional[AbstractToolset]:
        # In a real implementation, build and return a toolset with callables
        return None