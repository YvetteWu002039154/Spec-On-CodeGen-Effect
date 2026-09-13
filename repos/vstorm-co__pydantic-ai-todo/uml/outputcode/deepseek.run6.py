import asyncio
import datetime
import enum
import logging
from typing import Any, Callable, Dict, List, Optional, Union, Literal
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pydantic import BaseModel, Field
from pydantic.types import UUID4
import uuid

# -------------------------------------------------------------------
# Types
# -------------------------------------------------------------------

class TodoStatus(str, enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    blocked = "blocked"

class Todo(BaseModel):
    active_form: str
    content: str
    depends_on: Optional[List[str]] = None
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    parent_id: Optional[str] = None
    status: TodoStatus = TodoStatus.pending

class TodoItem(BaseModel):
    active_form: Optional[str] = None
    content: Optional[str] = None
    depends_on: Optional[List[str]] = None
    id: Optional[str] = None
    parent_id: Optional[str] = None
    status: Optional[TodoStatus] = None

class TodoStatusUpdate(BaseModel):
    status: Optional[TodoStatus] = None
    todo_id: Optional[str] = None

# -------------------------------------------------------------------
# Events
# -------------------------------------------------------------------

class TodoEventType(str, enum.Enum):
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    STATUS_CHANGED = "status_changed"
    COMPLETED = "completed"

EventCallback = Callable[["TodoEvent"], None]

class TodoEvent(BaseModel):
    event_type: TodoEventType
    previous_state: Optional[Todo] = None
    timestamp: Optional[datetime.datetime] = Field(default_factory=datetime.datetime.now)
    todo: Todo

class TodoEventEmitter:
    def __init__(self):
        self._listeners: Dict[TodoEventType, List[EventCallback]] = {
            event_type: [] for event_type in TodoEventType
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
        for callback in self._listeners.get(event.event_type, []):
            try:
                callback(event)
            except Exception as e:
                logging.exception(f"Error in event callback: {e}")

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

# -------------------------------------------------------------------
# Storage Protocols
# -------------------------------------------------------------------

class TodoStorageProtocol(ABC):
    @property
    @abstractmethod
    def todos(self) -> List[Todo]:
        ...

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
    async def update_todo(self, id: str) -> Optional[Todo]:
        ...

    @abstractmethod
    async def set_todos(self, todos: List[Todo]) -> None:
        ...

# -------------------------------------------------------------------
# Concrete Synchronous Storage (in-memory)
# -------------------------------------------------------------------

class TodoStorage(TodoStorageProtocol):
    def __init__(self):
        self._todos: List[Todo] = []

    @property
    def todos(self) -> List[Todo]:
        return self._todos

    def add_todo(self, todo: Todo) -> Todo:
        self._todos.append(todo)
        return todo

    def get_todo(self, id: str) -> Optional[Todo]:
        for todo in self._todos:
            if todo.id == id:
                return todo
        return None

    def get_todos(self) -> List[Todo]:
        return list(self._todos)

    def remove_todo(self, id: str) -> bool:
        for i, todo in enumerate(self._todos):
            if todo.id == id:
                del self._todos[i]
                return True
        return False

    def set_todos(self, todos: List[Todo]) -> None:
        self._todos = list(todos)

    def update_todo(self, id: str) -> Optional[Todo]:
        for i, todo in enumerate(self._todos):
            if todo.id == id:
                # This method signature seems incomplete; likely expects a partial update.
                # We'll return the existing todo (no update) as placeholder.
                return todo
        return None

# -------------------------------------------------------------------
# Async Storage Implementations
# -------------------------------------------------------------------

class AsyncMemoryStorage(AsyncTodoStorageProtocol):
    def __init__(self):
        self._todos: List[Todo] = []
        self._lock = asyncio.Lock()

    async def add_todo(self, todo: Todo) -> Todo:
        async with self._lock:
            self._todos.append(todo)
        return todo

    async def get_todo(self, id: str) -> Optional[Todo]:
        async with self._lock:
            for todo in self._todos:
                if todo.id == id:
                    return todo
        return None

    async def get_todos(self) -> List[Todo]:
        async with self._lock:
            return list(self._todos)

    async def remove_todo(self, id: str) -> bool:
        async with self._lock:
            for i, todo in enumerate(self._todos):
                if todo.id == id:
                    del self._todos[i]
                    return True
            return False

    async def set_todos(self, todos: List[Todo]) -> None:
        async with self._lock:
            self._todos = list(todos)

    async def update_todo(self, id: str) -> Optional[Todo]:
        async with self._lock:
            for todo in self._todos:
                if todo.id == id:
                    return todo  # placeholder: real implementation would merge updates
            return None

class AsyncPostgresStorage(AsyncTodoStorageProtocol):
    def __init__(self, connection_string: str = ""):
        self._connection_string = connection_string
        self._initialized = False

    async def initialize(self) -> None:
        # In real implementation, create tables etc.
        self._initialized = True

    async def close(self) -> None:
        self._initialized = False

    async def add_todo(self, todo: Todo) -> Todo:
        if not self._initialized:
            raise RuntimeError("Storage not initialized")
        # Stub: store in memory for demonstration
        return await self._memory_add(todo)

    async def get_todo(self, id: str) -> Optional[Todo]:
        if not self._initialized:
            raise RuntimeError("Storage not initialized")
        return await self._memory_get(id)

    async def get_todos(self) -> List[Todo]:
        if not self._initialized:
            raise RuntimeError("Storage not initialized")
        return await self._memory_get_all()

    async def remove_todo(self, id: str) -> bool:
        if not self._initialized:
            raise RuntimeError("Storage not initialized")
        return await self._memory_remove(id)

    async def set_todos(self, todos: List[Todo]) -> None:
        if not self._initialized:
            raise RuntimeError("Storage not initialized")
        await self._memory_set_all(todos)

    async def update_todo(self, id: str) -> Optional[Todo]:
        if not self._initialized:
            raise RuntimeError("Storage not initialized")
        return await self._memory_update(id)

    # Private in-memory fallback for demonstration only
    _memory: List[Todo] = []

    async def _memory_add(self, todo: Todo) -> Todo:
        self._memory.append(todo)
        return todo

    async def _memory_get(self, id: str) -> Optional[Todo]:
        for t in self._memory:
            if t.id == id:
                return t
        return None

    async def _memory_get_all(self) -> List[Todo]:
        return list(self._memory)

    async def _memory_remove(self, id: str) -> bool:
        for i, t in enumerate(self._memory):
            if t.id == id:
                del self._memory[i]
                return True
        return False

    async def _memory_set_all(self, todos: List[Todo]) -> None:
        self._memory = list(todos)

    async def _memory_update(self, id: str) -> Optional[Todo]:
        for t in self._memory:
            if t.id == id:
                return t
        return None

class AsyncRedisStorage(AsyncTodoStorageProtocol):
    def __init__(self, redis_url: str = "redis://localhost"):
        self._redis_url = redis_url
        self._initialized = False

    async def initialize(self) -> None:
        self._initialized = True

    async def close(self) -> None:
        self._initialized = False

    async def add_todo(self, todo: Todo) -> Todo:
        if not self._initialized:
            raise RuntimeError("Storage not initialized")
        return await self._memory_add(todo)

    async def get_todo(self, id: str) -> Optional[Todo]:
        if not self._initialized:
            raise RuntimeError("Storage not initialized")
        return await self._memory_get(id)

    async def get_todos(self) -> List[Todo]:
        if not self._initialized:
            raise RuntimeError("Storage not initialized")
        return await self._memory_get_all()

    async def remove_todo(self, id: str) -> bool:
        if not self._initialized:
            raise RuntimeError("Storage not initialized")
        return await self._memory_remove(id)

    async def set_todos(self, todos: List[Todo]) -> None:
        if not self._initialized:
            raise RuntimeError("Storage not initialized")
        await self._memory_set_all(todos)

    async def update_todo(self, id: str) -> Optional[Todo]:
        if not self._initialized:
            raise RuntimeError("Storage not initialized")
        return await self._memory_update(id)

    _memory: List[Todo] = []

    async def _memory_add(self, todo: Todo) -> Todo:
        self._memory.append(todo)
        return todo

    async def _memory_get(self, id: str) -> Optional[Todo]:
        for t in self._memory:
            if t.id == id:
                return t
        return None

    async def _memory_get_all(self) -> List[Todo]:
        return list(self._memory)

    async def _memory_remove(self, id: str) -> bool:
        for i, t in enumerate(self._memory):
            if t.id == id:
                del self._memory[i]
                return True
        return False

    async def _memory_set_all(self, todos: List[Todo]) -> None:
        self._memory = list(todos)

    async def _memory_update(self, id: str) -> Optional[Todo]:
        for t in self._memory:
            if t.id == id:
                return t
        return None

# -------------------------------------------------------------------
# Capability (Pydantic AI Toolset)
# -------------------------------------------------------------------

class AbstractToolset(ABC):
    """Placeholder for pydantic_ai.tools.AbstractToolset"""
    pass

class TodoCapability:
    def __init__(
        self,
        storage: Optional[TodoStorageProtocol] = None,
        async_storage: Optional[AsyncTodoStorageProtocol] = None,
        enable_subtasks: bool = False,
        descriptions: Optional[Dict[str, str]] = None,
    ):
        self.storage = storage
        self.async_storage = async_storage
        self.enable_subtasks = enable_subtasks
        self.descriptions = descriptions or {}

    def get_instructions(self) -> Any:
        return "Manage tasks with Pydantic AI Todo Capability"

    def get_serialization_name(self) -> str:
        return "todo"

    def get_toolset(self) -> Optional[AbstractToolset]:
        # In real implementation, create a toolset from storage.
        return None