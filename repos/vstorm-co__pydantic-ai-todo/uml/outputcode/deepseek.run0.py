from __future__ import annotations

import asyncio
import json
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (
    Any,
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

# ---------------------------------------------------------------------------
# Pydantic AI types placeholders (if not available)
# ---------------------------------------------------------------------------

T = TypeVar('T')

class AbstractToolset(ABC, Generic[T]):
    """Abstract base for tool sets used by Pydantic AI."""
    @abstractmethod
    def get_tools(self) -> list[Any]:
        ...

# ---------------------------------------------------------------------------
# types module
# ---------------------------------------------------------------------------

TodoStatus = Literal['pending', 'in_progress', 'completed', 'blocked']


@dataclass
class Todo:
    active_form: str
    content: str
    status: TodoStatus
    id: Optional[str] = None
    depends_on: Optional[list[str]] = None
    parent_id: Optional[str] = None


@dataclass
class TodoItem:
    active_form: Optional[str] = None
    content: Optional[str] = None
    depends_on: Optional[list[str]] = None
    id: Optional[str] = None
    parent_id: Optional[str] = None
    status: Optional[TodoStatus] = None


@dataclass
class TodoStatusUpdate:
    status: Optional[TodoStatus] = None
    todo_id: Optional[str] = None


# ---------------------------------------------------------------------------
# events module
# ---------------------------------------------------------------------------

class TodoEventType(str, Enum):
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    COMPLETED = "completed"
    STATUS_CHANGED = "status_changed"

    @property
    def name(self) -> str:
        return self._name_


EventCallback = Callable[['TodoEvent'], None]


@dataclass
class TodoEvent:
    event_type: TodoEventType
    todo: Todo
    previous_state: Optional[Todo] = None
    timestamp: Optional[datetime] = None


class TodoEventEmitter:
    def __init__(self) -> None:
        self._listeners: Dict[TodoEventType, list[EventCallback]] = {
            etype: [] for etype in TodoEventType
        }

    def on(self, event_type: TodoEventType, callback: EventCallback) -> EventCallback:
        self._listeners[event_type].append(callback)
        return callback

    def off(self, event_type: TodoEventType, callback: EventCallback) -> bool:
        listeners = self._listeners[event_type]
        try:
            listeners.remove(callback)
            return True
        except ValueError:
            return False

    def emit(self, event: TodoEvent) -> None:
        event.timestamp = event.timestamp or datetime.now()
        for callback in self._listeners[event.event_type]:
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


# ---------------------------------------------------------------------------
# storage module - protocols and implementations
# ---------------------------------------------------------------------------

@runtime_checkable
class TodoStorageProtocol(Protocol):
    """Synchronous storage protocol."""
    todos: list[Todo]

    def add_todo(self, todo: Todo) -> Todo:
        ...

    def get_todo(self, id: str) -> Optional[Todo]:
        ...

    def get_todos(self) -> list[Todo]:
        ...

    def remove_todo(self, id: str) -> bool:
        ...

    def set_todos(self, todos: list[Todo]) -> None:
        ...

    def update_todo(self, id: str) -> Optional[Todo]:
        ...


@runtime_checkable
class AsyncTodoStorageProtocol(Protocol):
    """Asynchronous storage protocol."""
    async def add_todo(self, todo: Todo) -> Todo:
        ...

    async def get_todo(self, id: str) -> Optional[Todo]:
        ...

    async def get_todos(self) -> list[Todo]:
        ...

    async def remove_todo(self, id: str) -> bool:
        ...

    async def set_todos(self, todos: list[Todo]) -> None:
        ...

    async def update_todo(self, id: str) -> Optional[Todo]:
        ...


class TodoStorage:
    """Simple in-memory synchronous storage."""
    def __init__(self, initial_todos: Optional[list[Todo]] = None) -> None:
        self.todos: list[Todo] = initial_todos or []

    def add_todo(self, todo: Todo) -> Todo:
        if not todo.id:
            todo.id = str(uuid.uuid4())
        self.todos.append(todo)
        return todo

    def get_todo(self, id: str) -> Optional[Todo]:
        for t in self.todos:
            if t.id == id:
                return t
        return None

    def get_todos(self) -> list[Todo]:
        return list(self.todos)

    def remove_todo(self, id: str) -> bool:
        for i, t in enumerate(self.todos):
            if t.id == id:
                self.todos.pop(i)
                return True
        return False

    def set_todos(self, todos: list[Todo]) -> None:
        self.todos = list(todos)

    def update_todo(self, id: str) -> Optional[Todo]:
        todo = self.get_todo(id)
        return todo  # no actual update logic? The UML shows just returning Todo or None.
        # We'll implement a basic update by finding and returning.


class AsyncMemoryStorage:
    """Asynchronous in-memory storage."""
    def __init__(self) -> None:
        self._todos: list[Todo] = []

    async def add_todo(self, todo: Todo) -> Todo:
        if not todo.id:
            todo.id = str(uuid.uuid4())
        self._todos.append(todo)
        return todo

    async def get_todo(self, id: str) -> Optional[Todo]:
        for t in self._todos:
            if t.id == id:
                return t
        return None

    async def get_todos(self) -> list[Todo]:
        return list(self._todos)

    async def remove_todo(self, id: str) -> bool:
        for i, t in enumerate(self._todos):
            if t.id == id:
                self._todos.pop(i)
                return True
        return False

    async def set_todos(self, todos: list[Todo]) -> None:
        self._todos = list(todos)

    async def update_todo(self, id: str) -> Optional[Todo]:
        return await self.get_todo(id)


class AsyncPostgresStorage:
    """PostgreSQL async storage using asyncpg."""
    def __init__(self, dsn: str, table_name: str = "todos") -> None:
        self._dsn = dsn
        self._table = table_name
        self._pool = None

    async def initialize(self) -> None:
        import asyncpg
        self._pool = await asyncpg.create_pool(self._dsn)
        async with self._pool.acquire() as conn:
            await conn.execute(f'''
                CREATE TABLE IF NOT EXISTS {self._table} (
                    id TEXT PRIMARY KEY,
                    active_form TEXT NOT NULL,
                    content TEXT NOT NULL,
                    status TEXT NOT NULL,
                    depends_on JSONB,
                    parent_id TEXT
                )
            ''')

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()

    async def add_todo(self, todo: Todo) -> Todo:
        if not todo.id:
            todo.id = str(uuid.uuid4())
        async with self._pool.acquire() as conn:
            await conn.execute(
                f"INSERT INTO {self._table} (id, active_form, content, status, depends_on, parent_id) "
                f"VALUES ($1, $2, $3, $4, $5, $6)",
                todo.id, todo.active_form, todo.content, todo.status,
                json.dumps(todo.depends_on) if todo.depends_on else None,
                todo.parent_id,
            )
        return todo

    async def get_todo(self, id: str) -> Optional[Todo]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(f"SELECT * FROM {self._table} WHERE id = $1", id)
            if row is None:
                return None
            return self._row_to_todo(row)

    async def get_todos(self) -> list[Todo]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(f"SELECT * FROM {self._table}")
            return [self._row_to_todo(r) for r in rows]

    async def remove_todo(self, id: str) -> bool:
        async with self._pool.acquire() as conn:
            result = await conn.execute(f"DELETE FROM {self._table} WHERE id = $1", id)
            # In asyncpg, DELETE returns the command; we check rowcount via a SELECT or just rely on the command tag.
            # Simplification: re-fetch to confirm deletion.
            row = await conn.fetchrow(f"SELECT id FROM {self._table} WHERE id = $1", id)
            return row is None

    async def set_todos(self, todos: list[Todo]) -> None:
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(f"DELETE FROM {self._table}")
                for todo in todos:
                    await conn.execute(
                        f"INSERT INTO {self._table} (id, active_form, content, status, depends_on, parent_id) "
                        f"VALUES ($1, $2, $3, $4, $5, $6)",
                        todo.id or str(uuid.uuid4()), todo.active_form, todo.content,
                        todo.status,
                        json.dumps(todo.depends_on) if todo.depends_on else None,
                        todo.parent_id,
                    )

    async def update_todo(self, id: str) -> Optional[Todo]:
        return await self.get_todo(id)

    def _row_to_todo(self, row: Any) -> Todo:
        depends_on = row['depends_on']
        if isinstance(depends_on, str):
            depends_on = json.loads(depends_on) if depends_on else None
        return Todo(
            id=row['id'],
            active_form=row['active_form'],
            content=row['content'],
            status=row['status'],
            depends_on=depends_on,
            parent_id=row['parent_id'],
        )


class AsyncRedisStorage:
    """Redis async storage using redis.asyncio."""
    def __init__(self, redis_url: str = "redis://localhost", key_prefix: str = "todo") -> None:
        self._redis_url = redis_url
        self._key_prefix = key_prefix
        self._client = None

    async def initialize(self) -> None:
        import redis.asyncio as aioredis
        self._client = aioredis.from_url(self._redis_url, decode_responses=True)

    async def close(self) -> None:
        if self._client:
            await self._client.close()

    def _todo_key(self, todo_id: str) -> str:
        return f"{self._key_prefix}:{todo_id}"

    async def add_todo(self, todo: Todo) -> Todo:
        if not todo.id:
            todo.id = str(uuid.uuid4())
        key = self._todo_key(todo.id)
        data = {
            'id': todo.id,
            'active_form': todo.active_form,
            'content': todo.content,
            'status': todo.status,
            'depends_on': json.dumps(todo.depends_on) if todo.depends_on else '',
            'parent_id': todo.parent_id or '',
        }
        await self._client.hset(key, mapping=data)
        return todo

    async def get_todo(self, id: str) -> Optional[Todo]:
        key = self._todo_key(id)
        data = await self._client.hgetall(key)
        if not data:
            return None
        depends_on_str = data.get('depends_on', '')
        depends_on = json.loads(depends_on_str) if depends_on_str else None
        parent_id = data.get('parent_id')
        if parent_id == '':
            parent_id = None
        return Todo(
            id=data['id'],
            active_form=data['active_form'],
            content=data['content'],
            status=data['status'],
            depends_on=depends_on,
            parent_id=parent_id,
        )

    async def get_todos(self) -> list[Todo]:
        keys = await self._client.keys(f"{self._key_prefix}:*")
        todos = []
        for key in keys:
            data = await self._client.hgetall(key)
            depends_on_str = data.get('depends_on', '')
            depends_on = json.loads(depends_on_str) if depends_on_str else None
            parent_id = data.get('parent_id')
            if parent_id == '':
                parent_id = None
            todos.append(Todo(
                id=data['id'],
                active_form=data['active_form'],
                content=data['content'],
                status=data['status'],
                depends_on=depends_on,
                parent_id=parent_id,
            ))
        return todos

    async def remove_todo(self, id: str) -> bool:
        key = self._todo_key(id)
        return await self._client.delete(key) > 0

    async def set_todos(self, todos: list[Todo]) -> None:
        await self._client.flushdb()  # naive approach
        for todo in todos:
            await self.add_todo(todo)

    async def update_todo(self, id: str) -> Optional[Todo]:
        return await self.get_todo(id)


# ---------------------------------------------------------------------------
# capability module
# ---------------------------------------------------------------------------

class TodoCapability:
    """Pydantic AI capability for managing todos."""
    def __init__(
        self,
        storage: Optional[TodoStorageProtocol] = None,
        async_storage: Optional[AsyncTodoStorageProtocol] = None,
        enable_subtasks: bool = True,
        descriptions: Optional[dict[str, str]] = None,
    ) -> None:
        self.storage = storage
        self.async_storage = async_storage
        self.enable_subtasks = enable_subtasks
        self.descriptions = descriptions or {}
        self.event_emitter = TodoEventEmitter()

    def get_instructions(self) -> Any:
        return (
            "You can manage the user's todo list using the provided tools. "
            "Each todo has a content, status, and optional dependencies."
        )

    def get_serialization_name(self) -> str:
        return "todo"

    def get_toolset(self) -> Optional[AbstractToolset[Any]]:
        return TodoToolset(self)


class TodoToolset(AbstractToolset[Any]):
    def __init__(self, capability: TodoCapability) -> None:
        self._capability = capability
        self._emitter = capability.event_emitter

    def get_tools(self) -> list[Any]:
        tools = [
            self._tool_add_todo,
            self._tool_get_todos,
            self._tool_update_todo_status,
            self._tool_delete_todo,
        ]
        if self._capability.enable_subtasks:
            tools.append(self._tool_add_subtask)
            tools.append(self._tool_get_subtasks)
        return tools

    # The actual tool functions (these will be decorated/inspected by pydantic-ai)
    def _tool_add_todo(self, content: str, active_form: str = "task") -> Todo:
        """Add a new todo item."""
        todo = Todo(active_form=active_form, content=content, status='pending')
        storage = self._capability.async_storage or self._capability.storage
        if isinstance(storage, AsyncTodoStorageProtocol):
            loop = asyncio.get_event_loop()
            saved = loop.run_until_complete(storage.add_todo(todo))
        else:
            saved = self._capability.storage.add_todo(todo)
        self._emitter.emit(TodoEvent(event_type=TodoEventType.CREATED, todo=saved))
        return saved

    def _tool_get_todos(self) -> list[Todo]:
        """Retrieve all todo items."""
        storage = self._capability.async_storage or self._capability.storage
        if isinstance(storage, AsyncTodoStorageProtocol):
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(storage.get_todos())
        return self._capability.storage.get_todos()

    def _tool_update_todo_status(self, todo_id: str, status: TodoStatus) -> Optional[Todo]:
        """Update the status of a todo."""
        storage = self._capability.async_storage or self._capability.storage
        if isinstance(storage, AsyncTodoStorageProtocol):
            loop = asyncio.get_event_loop()
            todo = loop.run_until_complete(storage.get_todo(todo_id))
        else:
            todo = self._capability.storage.get_todo(todo_id)
        if todo is None:
            return None
        previous = Todo(**todo.__dict__)  # copy
        todo.status = status
        # update in storage
        if isinstance(storage, AsyncTodoStorageProtocol):
            loop.run_until_complete(storage.add_todo(todo))  # overwrite by id
        else:
            self._capability.storage.add_todo(todo)  # will overwrite?
        self._emitter.emit(TodoEvent(
            event_type=TodoEventType.STATUS_CHANGED,
            todo=todo,
            previous_state=previous,
        ))
        return todo

    def _tool_delete_todo(self, todo_id: str) -> bool:
        """Delete a todo by ID."""
        storage = self._capability.async_storage or self._capability.storage
        if isinstance(storage, AsyncTodoStorageProtocol):
            loop = asyncio.get_event_loop()
            todo = loop.run_until_complete(storage.get_todo(todo_id))
            if todo:
                loop.run_until_complete(storage.remove_todo(todo_id))
        else:
            todo = self._capability.storage.get_todo(todo_id)
            if todo:
                self._capability.storage.remove_todo(todo_id)
        if todo:
            self._emitter.emit(TodoEvent(event_type=TodoEventType.DELETED, todo=todo))
            return True
        return False

    def _tool_add_subtask(self, parent_id: str, content: str, active_form: str = "subtask") -> Optional[Todo]:
        """Add a subtask to a parent todo."""
        storage = self._capability.async_storage or self._capability.storage
        if isinstance(storage, AsyncTodoStorageProtocol):
            loop = asyncio.get_event_loop()
            parent = loop.run_until_complete(storage.get_todo(parent_id))
        else:
            parent = self._capability.storage.get_todo(parent_id)
        if parent is None:
            return None
        subtask = Todo(
            active_form=active_form,
            content=content,
            status='pending',
            parent_id=parent.id,
        )
        if isinstance(storage, AsyncTodoStorageProtocol):
            saved = loop.run_until_complete(storage.add_todo(subtask))
        else:
            saved = self._capability.storage.add_todo(subtask)
        self._emitter.emit(TodoEvent(event_type=TodoEventType.CREATED, todo=saved))
        return saved

    def _tool_get_subtasks(self, parent_id: str) -> list[Todo]:
        """Get all subtasks of a parent todo."""
        storage = self._capability.async_storage or self._capability.storage
        if isinstance(storage, AsyncTodoStorageProtocol):
            loop = asyncio.get_event_loop()
            todos = loop.run_until_complete(storage.get_todos())
        else:
            todos = self._capability.storage.get_todos()
        return [t for t in todos if t.parent_id == parent_id]


# ---------------------------------------------------------------------------
# Convenience exports
# ---------------------------------------------------------------------------

__all__ = [
    # types
    'Todo',
    'TodoItem',
    'TodoStatusUpdate',
    # events
    'TodoEventType',
    'TodoEvent',
    'TodoEventEmitter',
    # storage
    'TodoStorageProtocol',
    'AsyncTodoStorageProtocol',
    'TodoStorage',
    'AsyncMemoryStorage',
    'AsyncPostgresStorage',
    'AsyncRedisStorage',
    # capability
    'TodoCapability',
    'TodoToolset',
]