from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Callable, Literal, Optional, Protocol, runtime_checkable
from enum import Enum

try:
    from pydantic import BaseModel, Field
except ImportError:
    raise ImportError("pydantic is required")


# ─────────────────────────────────────────────
# pydantic_ai_todo/types.py
# ─────────────────────────────────────────────

class Todo(BaseModel):
    id: Optional[str] = None
    content: str
    active_form: str
    status: Literal['pending', 'in_progress', 'completed', 'blocked'] = 'pending'
    parent_id: str | None = None
    depends_on: Optional[list[str]] = None


class TodoItem(BaseModel):
    id: str | None = None
    content: Optional[str] = None
    active_form: Optional[str] = None
    status: Optional[Literal['pending', 'in_progress', 'completed', 'blocked']] = None
    parent_id: str | None = None
    depends_on: Optional[list[str]] = None


class TodoStatusUpdate(BaseModel):
    todo_id: Optional[str] = None
    status: Optional[Literal['pending', 'in_progress', 'completed', 'blocked']] = None


# ─────────────────────────────────────────────
# pydantic_ai_todo/events.py
# ─────────────────────────────────────────────

class TodoEventType(Enum):
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    STATUS_CHANGED = "status_changed"
    COMPLETED = "completed"


EventCallback = Callable[["TodoEvent"], None]


class TodoEvent(BaseModel):
    event_type: TodoEventType
    todo: Todo
    previous_state: Todo | None = None
    timestamp: Optional[datetime] = None

    model_config = {"arbitrary_types_allowed": True}

    def model_post_init(self, __context: Any) -> None:
        if self.timestamp is None:
            object.__setattr__(self, 'timestamp', datetime.utcnow())


class TodoEventEmitter:
    def __init__(self) -> None:
        self._listeners: dict[TodoEventType, list[EventCallback]] = {
            event_type: [] for event_type in TodoEventType
        }

    def on(self, event_type: TodoEventType, callback: EventCallback) -> EventCallback:
        self._listeners[event_type].append(callback)
        return callback

    def off(self, event_type: TodoEventType, callback: EventCallback) -> bool:
        listeners = self._listeners.get(event_type, [])
        if callback in listeners:
            listeners.remove(callback)
            return True
        return False

    def emit(self, event: TodoEvent) -> None:
        for callback in self._listeners.get(event.event_type, []):
            callback(event)

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


# ─────────────────────────────────────────────
# pydantic_ai_todo/storage.py
# ─────────────────────────────────────────────

@runtime_checkable
class TodoStorageProtocol(Protocol):
    @property
    def todos(self) -> list[Todo]:
        ...

    def get_todos(self) -> list[Todo]:
        ...

    def get_todo(self, id: str) -> Todo | None:
        ...

    def add_todo(self, todo: Todo) -> Todo:
        ...

    def update_todo(self, id: str) -> Todo | None:
        ...

    def remove_todo(self, id: str) -> bool:
        ...

    def set_todos(self, todos: list[Todo]) -> None:
        ...


@runtime_checkable
class AsyncTodoStorageProtocol(Protocol):
    async def get_todos(self) -> list[Todo]:
        ...

    async def get_todo(self, id: str) -> Todo | None:
        ...

    async def add_todo(self, todo: Todo) -> Todo:
        ...

    async def update_todo(self, id: str) -> Todo | None:
        ...

    async def remove_todo(self, id: str) -> bool:
        ...

    async def set_todos(self, todos: list[Todo]) -> None:
        ...


class TodoStorage:
    def __init__(self, todos: list[Todo] | None = None) -> None:
        self._todos: list[Todo] = todos if todos is not None else []

    @property
    def todos(self) -> list[Todo]:
        return self._todos

    @todos.setter
    def todos(self, value: list[Todo]) -> None:
        self._todos = value

    def get_todos(self) -> list[Todo]:
        return list(self._todos)

    def get_todo(self, id: str) -> Todo | None:
        for todo in self._todos:
            if todo.id == id:
                return todo
        return None

    def add_todo(self, todo: Todo) -> Todo:
        if todo.id is None:
            import uuid
            todo = todo.model_copy(update={"id": str(uuid.uuid4())})
        self._todos.append(todo)
        return todo

    def update_todo(self, id: str) -> Todo | None:
        for todo in self._todos:
            if todo.id == id:
                return todo
        return None

    def remove_todo(self, id: str) -> bool:
        for i, todo in enumerate(self._todos):
            if todo.id == id:
                self._todos.pop(i)
                return True
        return False

    def set_todos(self, todos: list[Todo]) -> None:
        self._todos = list(todos)


class AsyncMemoryStorage:
    def __init__(self) -> None:
        self._todos: list[Todo] = []
        self._lock = asyncio.Lock()

    async def get_todos(self) -> list[Todo]:
        async with self._lock:
            return list(self._todos)

    async def get_todo(self, id: str) -> Todo | None:
        async with self._lock:
            for todo in self._todos:
                if todo.id == id:
                    return todo
            return None

    async def add_todo(self, todo: Todo) -> Todo:
        async with self._lock:
            if todo.id is None:
                import uuid
                todo = todo.model_copy(update={"id": str(uuid.uuid4())})
            self._todos.append(todo)
            return todo

    async def update_todo(self, id: str) -> Todo | None:
        async with self._lock:
            for todo in self._todos:
                if todo.id == id:
                    return todo
            return None

    async def remove_todo(self, id: str) -> bool:
        async with self._lock:
            for i, todo in enumerate(self._todos):
                if todo.id == id:
                    self._todos.pop(i)
                    return True
            return False

    async def set_todos(self, todos: list[Todo]) -> None:
        async with self._lock:
            self._todos = list(todos)


class AsyncPostgresStorage:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._pool: Any = None

    async def initialize(self) -> None:
        try:
            import asyncpg  # type: ignore
            self._pool = await asyncpg.create_pool(self._dsn)
            async with self._pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS todos (
                        id TEXT PRIMARY KEY,
                        content TEXT NOT NULL,
                        active_form TEXT NOT NULL,
                        status TEXT NOT NULL DEFAULT 'pending',
                        parent_id TEXT,
                        depends_on TEXT[]
                    )
                """)
        except ImportError:
            raise ImportError("asyncpg is required for AsyncPostgresStorage")

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    async def get_todos(self) -> list[Todo]:
        if self._pool is None:
            raise RuntimeError("Storage not initialized. Call initialize() first.")
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM todos")
            return [
                Todo(
                    id=row['id'],
                    content=row['content'],
                    active_form=row['active_form'],
                    status=row['status'],
                    parent_id=row['parent_id'],
                    depends_on=list(row['depends_on']) if row['depends_on'] else None,
                )
                for row in rows
            ]

    async def get_todo(self, id: str) -> Todo | None:
        if self._pool is None:
            raise RuntimeError("Storage not initialized. Call initialize() first.")
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM todos WHERE id = $1", id)
            if row is None:
                return None
            return Todo(
                id=row['id'],
                content=row['content'],
                active_form=row['active_form'],
                status=row['status'],
                parent_id=row['parent_id'],
                depends_on=list(row['depends_on']) if row['depends_on'] else None,
            )

    async def add_todo(self, todo: Todo) -> Todo:
        if self._pool is None:
            raise RuntimeError("Storage not initialized. Call initialize() first.")
        import uuid
        if todo.id is None:
            todo = todo.model_copy(update={"id": str(uuid.uuid4())})
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO todos (id, content, active_form, status, parent_id, depends_on)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                todo.id,
                todo.content,
                todo.active_form,
                todo.status,
                todo.parent_id,
                todo.depends_on,
            )
        return todo

    async def update_todo(self, id: str) -> Todo | None:
        return await self.get_todo(id)

    async def remove_todo(self, id: str) -> bool:
        if self._pool is None:
            raise RuntimeError("Storage not initialized. Call initialize() first.")
        async with self._pool.acquire() as conn:
            result = await conn.execute("DELETE FROM todos WHERE id = $1", id)
            return result == "DELETE 1"

    async def set_todos(self, todos: list[Todo]) -> None:
        if self._pool is None:
            raise RuntimeError("Storage not initialized. Call initialize() first.")
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("DELETE FROM todos")
                for todo in todos:
                    import uuid
                    if todo.id is None:
                        todo = todo.model_copy(update={"id": str(uuid.uuid4())})
                    await conn.execute(
                        """
                        INSERT INTO todos (id, content, active_form, status, parent_id, depends_on)
                        VALUES ($1, $2, $3, $4, $5, $6)
                        """,
                        todo.id,
                        todo.content,
                        todo.active_form,
                        todo.status,
                        todo.parent_id,
                        todo.depends_on,
                    )


class AsyncRedisStorage:
    def __init__(self, url: str = "redis://localhost:6379", key_prefix: str = "todo:") -> None:
        self._url = url
        self._key_prefix = key_prefix
        self._client: Any = None
        self._list_key = f"{key_prefix}list"

    async def initialize(self) -> None:
        try:
            import redis.asyncio as aioredis  # type: ignore
            self._client = aioredis.from_url(self._url)
        except ImportError:
            raise ImportError("redis is required for AsyncRedisStorage")

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None

    def _todo_key(self, id: str) -> str:
        return f"{self._key_prefix}{id}"

    async def get_todos(self) -> list[Todo]:
        if self._client is None:
            raise RuntimeError("Storage not initialized. Call initialize() first.")
        import json
        ids = await self._client.lrange(self._list_key, 0, -1)
        todos = []
        for id_bytes in ids:
            id_str = id_bytes.decode() if isinstance(id_bytes, bytes) else id_bytes
            data = await self._client.get(self._todo_key(id_str))
            if data:
                raw = json.loads(data)
                todos.append(Todo(**raw))
        return todos

    async def get_todo(self, id: str) -> Todo | None:
        if self._client is None:
            raise RuntimeError("Storage not initialized. Call initialize() first.")
        import json
        data = await self._client.get(self._todo_key(id))
        if data is None:
            return None
        return Todo(**json.loads(data))

    async def add_todo(self, todo: Todo) -> Todo:
        if self._client is None:
            raise RuntimeError("Storage not initialized. Call initialize() first.")
        import uuid
        import json
        if todo.id is None:
            todo = todo.model_copy(update={"id": str(uuid.uuid4())})
        await self._client.set(self._todo_key(todo.id), json.dumps(todo.model_dump()))
        await self._client.rpush(self._list_key, todo.id)
        return todo

    async def update_todo(self, id: str) -> Todo | None:
        return await self.get_todo(id)

    async def remove_todo(self, id: str) -> bool:
        if self._client is None:
            raise RuntimeError("Storage not initialized. Call initialize() first.")
        result = await self._client.delete(self._todo_key(id))
        await self._client.lrem(self._list_key, 0, id)
        return result > 0

    async def set_todos(self, todos: list[Todo]) -> None:
        if self._client is None:
            raise RuntimeError("Storage not initialized. Call initialize() first.")
        import uuid
        import json
        existing_ids_bytes = await self._client.lrange(self._list_key, 0, -1)
        for id_bytes in existing_ids_bytes:
            id_str = id_bytes.decode() if isinstance(id_bytes, bytes) else id_bytes
            await self._client.delete(self._todo_key(id_str))
        await self._client.delete(self._list_key)
        for todo in todos:
            if todo.id is None:
                todo = todo.model_copy(update={"id": str(uuid.uuid4())})
            await self._client.set(self._todo_key(todo.id), json.dumps(todo.model_dump()))
            await self._client.rpush(self._list_key, todo.id)


# ─────────────────────────────────────────────
# pydantic_ai_todo/capability.py
# ─────────────────────────────────────────────

class TodoCapability:
    def __init__(
        self,
        storage: TodoStorageProtocol | None = None,
        async_storage: AsyncTodoStorageProtocol | None = None,
        descriptions: dict[str, str] | None = None,
        enable_subtasks: bool = False,
    ) -> None:
        self.storage = storage
        self.async_storage = async_storage
        self.descriptions = descriptions
        self.enable_subtasks = enable_subtasks

    def get_instructions(self) -> Any:
        lines = ["You are a todo management assistant."]
        if self.descriptions:
            for key, value in self.descriptions.items():
                lines.append(f"{key}: {value}")
        if self.enable_subtasks:
            lines.append("Subtasks are enabled. You can create hierarchical todos.")
        return "\n".join(lines)

    def get_serialization_name(self) -> str:
        return "todo_capability"

    def get_toolset(self) -> Any | None:
        return None