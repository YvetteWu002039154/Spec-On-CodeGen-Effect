import uuid
from typing import Optional, Literal, Any, Protocol, Callable, TypeVar, Generic
from datetime import datetime
from enum import Enum

T = TypeVar('T')

class AbstractToolset(Generic[T]):
    pass

class TodoEventType(Enum):
    CREATED = "CREATED"
    UPDATED = "UPDATED"
    DELETED = "DELETED"
    STATUS_CHANGED = "STATUS_CHANGED"
    COMPLETED = "COMPLETED"

class Todo:
    def __init__(
        self,
        active_form: str,
        content: str,
        status: Literal['pending', 'in_progress', 'completed', 'blocked'],
        depends_on: Optional[list[str]] = None,
        id: Optional[str] = None,
        parent_id: Optional[str] = None
    ):
        self.active_form = active_form
        self.content = content
        self.status = status
        self.depends_on = depends_on if depends_on is not None else []
        self.id = id
        self.parent_id = parent_id

class TodoItem:
    def __init__(
        self,
        active_form: Optional[str] = None,
        content: Optional[str] = None,
        status: Optional[Literal['pending', 'in_progress', 'completed', 'blocked']] = None,
        depends_on: Optional[list[str]] = None,
        id: Optional[str] = None,
        parent_id: Optional[str] = None
    ):
        self.active_form = active_form
        self.content = content
        self.status = status
        self.depends_on = depends_on
        self.id = id
        self.parent_id = parent_id

class TodoStatusUpdate:
    def __init__(
        self,
        status: Optional[Literal['pending', 'in_progress', 'completed', 'blocked']] = None,
        todo_id: Optional[str] = None
    ):
        self.status = status
        self.todo_id = todo_id

class TodoEvent:
    def __init__(
        self,
        event_type: TodoEventType,
        todo: Todo,
        previous_state: Optional[Todo] = None,
        timestamp: Optional[datetime] = None
    ):
        self.event_type = event_type
        self.todo = todo
        self.previous_state = previous_state
        self.timestamp = timestamp or datetime.now()

EventCallback = Callable[[TodoEvent], None]

class TodoEventEmitter:
    def __init__(self):
        self._listeners: dict[TodoEventType, list[EventCallback]] = {
            event_type: [] for event_type in TodoEventType
        }

    def emit(self, event: TodoEvent) -> None:
        for callback in self._listeners.get(event.event_type, []):
            callback(event)

    def off(self, event_type: TodoEventType, callback: EventCallback) -> bool:
        if callback in self._listeners[event_type]:
            self._listeners[event_type].remove(callback)
            return True
        return False

    def on(self, event_type: TodoEventType, callback: EventCallback) -> EventCallback:
        self._listeners[event_type].append(callback)
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
    async def get_todos(self) -> list[Todo]: ...
    async def remove_todo(self, id: str) -> bool: ...
    async def set_todos(self, todos: list[Todo]) -> None: ...
    async def update_todo(self, id: str) -> Optional[Todo]: ...

class TodoStorageProtocol(Protocol):
    @property
    def todos(self) -> list[Todo]: ...

class TodoStorage:
    def __init__(self):
        self.todos: list[Todo] = []

class AsyncMemoryStorage:
    def __init__(self):
        self._todos: dict[str, Todo] = {}

    async def add_todo(self, todo: Todo) -> Todo:
        if not todo.id:
            todo.id = str(uuid.uuid4())
        self._todos[todo.id] = todo
        return todo

    async def get_todo(self, id: str) -> Optional[Todo]:
        return self._todos.get(id)

    async def get_todos(self) -> list[Todo]:
        return list(self._todos.values())

    async def remove_todo(self, id: str) -> bool:
        if id in self._todos:
            del self._todos[id]
            return True
        return False

    async def set_todos(self, todos: list[Todo]) -> None:
        self._todos = {t.id: t for t in todos if t.id}

    async def update_todo(self, id: str) -> Optional[Todo]:
        return self._todos.get(id)

class AsyncPostgresStorage:
    def __init__(self):
        self._todos: dict[str, Todo] = {}

    async def initialize(self) -> None:
        pass

    async def close(self) -> None:
        pass

    async def add_todo(self, todo: Todo) -> Todo:
        if not todo.id:
            todo.id = str(uuid.uuid4())
        self._todos[todo.id] = todo
        return todo

    async def get_todo(self, id: str) -> Optional[Todo]:
        return self._todos.get(id)

    async def get_todos(self) -> list[Todo]:
        return list(self._todos.values())

    async def remove_todo(self, id: str) -> bool:
        if id in self._todos:
            del self._todos[id]
            return True
        return False

    async def set_todos(self, todos: list[Todo]) -> None:
        self._todos = {t.id: t for t in todos if t.id}

    async def update_todo(self, id: str) -> Optional[Todo]:
        return self._todos.get(id)

class AsyncRedisStorage:
    def __init__(self):
        self._todos: dict[str, Todo] = {}

    async def initialize(self) -> None:
        pass

    async def close(self) -> None:
        pass

    async def add_todo(self, todo: Todo) -> Todo:
        if not todo.id:
            todo.id = str(uuid.uuid4())
        self._todos[todo.id] = todo
        return todo

    async def get_todo(self, id: str) -> Optional[Todo]:
        return self._todos.get(id)

    async def get_todos(self) -> list[Todo]:
        return list(self._todos.values())

    async def remove_todo(self, id: str) -> bool:
        if id in self._todos:
            del self._todos[id]
            return True
        return False

    async def set_todos(self, todos: list[Todo]) -> None:
        self._todos = {t.id: t for t in todos if t.id}

    async def update_todo(self, id: str) -> Optional[Todo]:
        return self._todos.get(id)

class TodoCapability:
    def __init__(
        self,
        enable_subtasks: bool,
        async_storage: Optional[AsyncTodoStorageProtocol] = None,
        storage: Optional[TodoStorageProtocol] = None,
        descriptions: Optional[dict[str, str]] = None
    ):
        self.enable_subtasks = enable_subtasks
        self.async_storage = async_storage
        self.storage = storage
        self.descriptions = descriptions

    def get_instructions(self) -> Any:
        return "Instructions for TodoCapability"

    def get_serialization_name(self) -> str:
        return "todo_capability"

    def get_toolset(self) -> Optional[AbstractToolset[Any]]:
        return None