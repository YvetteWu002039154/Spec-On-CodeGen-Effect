# File: pydantic_ai_todo/__init__.py
```

```python
# File: pydantic_ai_todo/types.py
from __future__ import annotations

import datetime
from enum import Enum
from typing import List, Optional, Literal

from pydantic import BaseModel, Field


class Todo(BaseModel):
    """A full todo item."""
    active_form: str = ""
    content: str = ""
    depends_on: Optional[List[str]] = Field(default_factory=list)
    id: Optional[str] = None
    parent_id: Optional[str] = None
    status: Literal["pending", "in_progress", "completed", "blocked"] = "pending"


class TodoItem(BaseModel):
    """A partial update description for a todo."""
    active_form: Optional[str] = None
    content: Optional[str] = None
    depends_on: Optional[List[str]] = None
    id: Optional[str] = None
    parent_id: Optional[str] = None
    status: Optional[Literal["pending", "in_progress", "completed", "blocked"]] = None


class TodoStatusUpdate(BaseModel):
    """A request to update the status of a todo."""
    status: Optional[Literal["pending", "in_progress", "completed", "blocked"]] = None
    todo_id: Optional[str] = None
```

```python
# File: pydantic_ai_todo/events.py
from __future__ import annotations

import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field

from pydantic_ai_todo.types import Todo


EventCallback = Callable[["TodoEvent"], None]


class TodoEventType(str, Enum):
    CREATED = "created"
    UPDATED = "updated"
    STATUS_CHANGED = "status_changed"
    COMPLETED = "completed"
    DELETED = "deleted"


class TodoEvent(BaseModel):
    event_type: TodoEventType
    todo: Todo
    previous_state: Optional[Todo] = None
    timestamp: Optional[datetime.datetime] = Field(default_factory=datetime.datetime.utcnow)


class TodoEventEmitter:
    """Synchronous event emitter for Todo events."""
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

    def emit(self, event: TodoEvent) -> None:
        for cb in self._listeners.get(event.event_type, []):
            cb(event)
```

```python
# File: pydantic_ai_todo/storage.py
from __future__ import annotations

import abc
import asyncio
import json
import uuid
from typing import Any, Dict, List, Optional, Protocol

import asyncpg
import redis.asyncio as aioredis

from pydantic_ai_todo.types import Todo


# ----------------------------------------------------------------------
# Sync storage protocols
# ----------------------------------------------------------------------
class TodoStorageProtocol(Protocol):
    @property
    def todos(self) -> List[Todo]: ...


class TodoStorage:
    """Simple in‑memory sync storage (for backwards compatibility)."""
    def __init__(self) -> None:
        self._todos: List[Todo] = []

    @property
    def todos(self) -> List[Todo]:
        return self._todos


# ----------------------------------------------------------------------
# Async storage protocol
# ----------------------------------------------------------------------
class AsyncTodoStorageProtocol(abc.ABC):
    @abc.abstractmethod
    async def add_todo(self, todo: Todo) -> Todo: ...

    @abc.abstractmethod
    async def get_todo(self, id: str) -> Optional[Todo]: ...

    @abc.abstractmethod
    async def get_todos(self) -> List[Todo]: ...

    @abc.abstractmethod
    async def remove_todo(self, id: str) -> bool: ...

    @abc.abstractmethod
    async def set_todos(self, todos: List[Todo]) -> None: ...

    @abc.abstractmethod
    async def update_todo(self, id: str) -> Optional[Todo]: ...


# ----------------------------------------------------------------------
# In‑memory async storage
# ----------------------------------------------------------------------
class AsyncMemoryStorage(AsyncTodoStorageProtocol):
    def __init__(self) -> None:
        self._todos: Dict[str, Todo] = {}
        self._lock = asyncio.Lock()

    async def add_todo(self, todo: Todo) -> Todo:
        if not todo.id:
            todo.id = uuid.uuid4().hex
        async with self._lock:
            self._todos[todo.id] = todo
        return todo

    async def get_todo(self, id: str) -> Optional[Todo]:
        async with self._lock:
            return self._todos.get(id)

    async def get_todos(self) -> List[Todo]:
        async with self._lock:
            return list(self._todos.values())

    async def remove_todo(self, id: str) -> bool:
        async with self._lock:
            if id in self._todos:
                del self._todos[id]
                return True
            return False

    async def set_todos(self, todos: List[Todo]) -> None:
        async with self._lock:
            self._todos = {t.id: t for t in todos if t.id is not None}

    async def update_todo(self, id: str) -> Optional[Todo]:
        async with self._lock:
            return self._todos.get(id)


# ----------------------------------------------------------------------
# Postgres async storage
# ----------------------------------------------------------------------
class AsyncPostgresStorage(AsyncTodoStorageProtocol):
    def __init__(self, dsn: str = "postgresql://postgres:postgres@localhost:5432/todo") -> None:
        self._dsn = dsn
        self._pool: Optional[asyncpg.Pool] = None

    async def initialize(self) -> None:
        self._pool = await asyncpg.create_pool(self._dsn)
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS todos (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL DEFAULT '',
                    active_form TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'pending',
                    parent_id TEXT,
                    depends_on TEXT[] DEFAULT '{}',
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
                """
            )

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()

    async def _acquire(self) -> asyncpg.Connection:
        if not self._pool:
            raise RuntimeError("Storage not initialized. Call initialize() first.")
        return await self._pool.acquire()

    async def add_todo(self, todo: Todo) -> Todo:
        if not todo.id:
            todo.id = uuid.uuid4().hex
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO todos (id, content, active_form, status, parent_id, depends_on)
                VALUES ($1, $2, $3, $4, $5, $6::text[])
                """,
                todo.id,
                todo.content,
                todo.active_form,
                todo.status,
                todo.parent_id,
                todo.depends_on or [],
            )
        return todo

    async def get_todo(self, id: str) -> Optional[Todo]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM todos WHERE id = $1", id)
            if row is None:
                return None
            return Todo(
                active_form=row["active_form"],
                content=row["content"],
                depends_on=list(row["depends_on"]) if row["depends_on"] else [],
                id=row["id"],
                parent_id=row["parent_id"],
                status=row["status"],
            )

    async def get_todos(self) -> List[Todo]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM todos")
        return [
            Todo(
                active_form=r["active_form"],
                content=r["content"],
                depends_on=list(r["depends_on"]) if r["depends_on"] else [],
                id=r["id"],
                parent_id=r["parent_id"],
                status=r["status"],
            )
            for r in rows
        ]

    async def remove_todo(self, id: str) -> bool:
        async with self._pool.acquire() as conn:
            result = await conn.execute("DELETE FROM todos WHERE id = $1", id)
            return result == "DELETE 1"

    async def set_todos(self, todos: List[Todo]) -> None:
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("DELETE FROM todos")
                for t in todos:
                    await conn.execute(
                        """
                        INSERT INTO todos (id, content, active_form, status, parent_id, depends_on)
                        VALUES ($1, $2, $3, $4, $5, $6::text[])
                        """,
                        t.id or uuid.uuid4().hex,
                        t.content,
                        t.active_form,
                        t.status,
                        t.parent_id,
                        t.depends_on or [],
                    )

    async def update_todo(self, id: str) -> Optional[Todo]:
        return await self.get_todo(id)


# ----------------------------------------------------------------------
# Redis async storage
# ----------------------------------------------------------------------
class AsyncRedisStorage(AsyncTodoStorageProtocol):
    def __init__(self, redis_url: str = "redis://localhost:6379/0") -> None:
        self._redis: Optional[aioredis.Redis] = None
        self._redis_url = redis_url

    async def initialize(self) -> None:
        self._redis = aioredis.from_url(self._redis_url, decode_responses=True)

    async def close(self) -> None:
        if self._redis:
            await self._redis.close()

    def _todo_key(self, todo_id: str) -> str:
        return f"todo:{todo_id}"

    async def add_todo(self, todo: Todo) -> Todo:
        if not todo.id:
            todo.id = uuid.uuid4().hex
        await self._redis.set(self._todo_key(todo.id), todo.model_dump_json())
        await self._redis.sadd("todos:all", todo.id)
        return todo

    async def get_todo(self, id: str) -> Optional[Todo]:
        data = await self._redis.get(self._todo_key(id))
        if data is None:
            return None
        return Todo.model_validate_json(data)

    async def get_todos(self) -> List[Todo]:
        ids = await self._redis.smembers("todos:all")
        if not ids:
            return []
        keys = [self._todo_key(i) for i in ids]
        data = await self._redis.mget(keys)
        todos = []
        for d in data:
            if d:
                todos.append(Todo.model_validate_json(d))
        return todos

    async def remove_todo(self, id: str) -> bool:
        existed = await self._redis.delete(self._todo_key(id))
        if existed:
            await self._redis.srem("todos:all", id)
            return True
        return False

    async def set_todos(self, todos: List[Todo]) -> None:
        # clear everything
        await self._redis.delete("todos:all")
        pipe = self._redis.pipeline()
        for t in todos:
            tid = t.id or uuid.uuid4().hex
            pipe.sadd("todos:all", tid)
            pipe.set(self._todo_key(tid), t.model_dump_json())
        await pipe.execute()

    async def update_todo(self, id: str) -> Optional[Todo]:
        return await self.get_todo(id)
```

```python
# File: pydantic_ai_todo/capability.py
from __future__ import annotations

import abc
from typing import Any, Dict, List, Optional, Type, Union

from pydantic_ai_todo.storage import AsyncTodoStorageProtocol, TodoStorageProtocol


# Minimal abstract toolset definition (works without pydantic‑ai)
class AbstractToolset(abc.ABC):
    @abc.abstractmethod
    def get_tools(self) -> List[Any]:
        ...


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
        self.descriptions = descriptions or {}

    def get_instructions(self) -> str:
        return (
            "You can manage a todo list. Use the provided tools to add, view, "
            "update, and delete todos."
        )

    def get_serialization_name(self) -> str:
        return "todo"

    def get_toolset(self) -> Optional[AbstractToolset]:
        """Build a toolset wrapping the available storage."""
        if self.async_storage:
            # async toolset
            return _AsyncTodoToolset(self.async_storage, self.enable_subtasks)
        elif self.storage:
            # sync toolset
            return _SyncTodoToolset(self.storage, self.enable_subtasks)
        return None


class _SyncTodoToolset(AbstractToolset):
    def __init__(self, storage: TodoStorageProtocol, enable_subtasks: bool) -> None:
        self._storage = storage
        self._enable_subtasks = enable_subtasks

    def get_tools(self) -> List[Any]:
        # Minimal representation of a tool – in a real scenario you would use
        # pydantic_ai.Tool or similar.
        return [
            _Tool(
                name="list_todos",
                description="List all todos",
                func=self._list_todos,
            ),
            _Tool(
                name="add_todo",
                description="Add a new todo",
                func=self._add_todo,
            ),
            # further tools omitted for brevity
        ]

    def _list_todos(self) -> List[dict]:
        return [t.model_dump() for t in self._storage.todos]

    def _add_todo(self, content: str) -> dict:
        todo = Todo(content=content)
        self._storage._todos.append(todo)  # direct list access for sync storage
        return todo.model_dump()


class _AsyncTodoToolset(AbstractToolset):
    def __init__(self, storage: AsyncTodoStorageProtocol, enable_subtasks: bool) -> None:
        self._storage = storage
        self._enable_subtasks = enable_subtasks

    def get_tools(self) -> List[Any]:
        return [
            _Tool(
                name="list_todos",
                description="List all todos",
                func=self._list_todos,
                is_async=True,
            ),
            _Tool(
                name="add_todo",
                description="Add a new todo",
                func=self._add_todo,
                is_async=True,
            ),
        ]

    async def _list_todos(self) -> List[dict]:
        todos = await self._storage.get_todos()
        return [t.model_dump() for t in todos]

    async def _add_todo(self, content: str) -> dict:
        todo = Todo(content=content)
        await self._storage.add_todo(todo)
        return todo.model_dump()


class _Tool:
    """Placeholder tool representation."""
    def __init__(self, name: str, description: str, func, is_async: bool = False):
        self.name = name
        self.description = description
        self.func = func
        self.is_async = is_async

# circular imports resolving
from pydantic_ai_todo.types import Todo