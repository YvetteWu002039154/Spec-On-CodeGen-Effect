from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Literal, Optional, Protocol, runtime_checkable

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────
# pydantic_ai_todo/types.py
# ─────────────────────────────────────────────

class Todo(BaseModel):
    id: Optional[str] = None
    content: str
    active_form: str = ""
    status: Literal["pending", "in_progress", "completed", "blocked"] = "pending"
    depends_on: Optional[List[str]] = None
    parent_id: Optional[str] = None


class TodoItem(BaseModel):
    id: Optional[str] = None
    content: Optional[str] = None
    active_form: Optional[str] = None
    status: Optional[Literal["pending", "in_progress", "completed", "blocked"]] = None
    depends_on: Optional[List[str]] = None
    parent_id: Optional[str] = None


class TodoStatusUpdate(BaseModel):
    todo_id: Optional[str] = None
    status: Optional[Literal["pending", "in_progress", "completed", "blocked"]] = None


# ─────────────────────────────────────────────
# pydantic_ai_todo/events.py
# ─────────────────────────────────────────────

class TodoEventType(str, Enum):
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    STATUS_CHANGED = "status_changed"
    COMPLETED = "completed"

    @property
    def name(self) -> str:  # type: ignore[override]
        return self.value


class TodoEvent(BaseModel):
    event_type: TodoEventType
    todo: Todo
    previous_state: Optional[Todo] = None
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow)


EventCallback = Callable[[TodoEvent], Any]


class TodoEventEmitter:
    def __init__(self) -> None:
        self._listeners: Dict[TodoEventType, List[EventCallback]] = {
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
    def todos(self) -> List[Todo]:
        ...


@runtime_checkable
class AsyncTodoStorageProtocol(Protocol):
    async def get_todos(self) -> List[Todo]:
        ...

    async def get_todo(self, id: str) -> Optional[Todo]:
        ...

    async def add_todo(self, todo: Todo) -> Todo:
        ...

    async def update_todo(self, id: str) -> Optional[Todo]:
        ...

    async def remove_todo(self, id: str) -> bool:
        ...

    async def set_todos(self, todos: List[Todo]) -> None:
        ...


class TodoStorage:
    def __init__(self, todos: Optional[List[Todo]] = None) -> None:
        self._todos: List[Todo] = todos if todos is not None else []

    @property
    def todos(self) -> List[Todo]:
        return self._todos

    def get_todos(self) -> List[Todo]:
        return list(self._todos)

    def get_todo(self, id: str) -> Optional[Todo]:
        for todo in self._todos:
            if todo.id == id:
                return todo
        return None

    def add_todo(self, todo: Todo) -> Todo:
        if todo.id is None:
            todo = todo.model_copy(update={"id": str(uuid.uuid4())})
        self._todos.append(todo)
        return todo

    def update_todo(self, id: str, **kwargs: Any) -> Optional[Todo]:
        for i, todo in enumerate(self._todos):
            if todo.id == id:
                updated = todo.model_copy(update=kwargs)
                self._todos[i] = updated
                return updated
        return None

    def remove_todo(self, id: str) -> bool:
        for i, todo in enumerate(self._todos):
            if todo.id == id:
                self._todos.pop(i)
                return True
        return False

    def set_todos(self, todos: List[Todo]) -> None:
        self._todos = list(todos)


class AsyncMemoryStorage:
    def __init__(self, todos: Optional[List[Todo]] = None) -> None:
        self._todos: List[Todo] = todos if todos is not None else []
        self._lock = asyncio.Lock()

    async def get_todos(self) -> List[Todo]:
        async with self._lock:
            return list(self._todos)

    async def get_todo(self, id: str) -> Optional[Todo]:
        async with self._lock:
            for todo in self._todos:
                if todo.id == id:
                    return todo
            return None

    async def add_todo(self, todo: Todo) -> Todo:
        async with self._lock:
            if todo.id is None:
                todo = todo.model_copy(update={"id": str(uuid.uuid4())})
            self._todos.append(todo)
            return todo

    async def update_todo(self, id: str, **kwargs: Any) -> Optional[Todo]:
        async with self._lock:
            for i, todo in enumerate(self._todos):
                if todo.id == id:
                    updated = todo.model_copy(update=kwargs)
                    self._todos[i] = updated
                    return updated
            return None

    async def remove_todo(self, id: str) -> bool:
        async with self._lock:
            for i, todo in enumerate(self._todos):
                if todo.id == id:
                    self._todos.pop(i)
                    return True
            return False

    async def set_todos(self, todos: List[Todo]) -> None:
        async with self._lock:
            self._todos = list(todos)


class AsyncPostgresStorage:
    def __init__(
        self,
        dsn: str,
        table_name: str = "todos",
    ) -> None:
        self._dsn = dsn
        self._table_name = table_name
        self._pool: Any = None

    async def initialize(self) -> None:
        try:
            import asyncpg  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "asyncpg is required for AsyncPostgresStorage. "
                "Install it with: pip install asyncpg"
            ) from exc

        self._pool = await asyncpg.create_pool(self._dsn)
        async with self._pool.acquire() as conn:
            await conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self._table_name} (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    active_form TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'pending',
                    depends_on JSONB,
                    parent_id TEXT
                )
                """
            )

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    def _row_to_todo(self, row: Any) -> Todo:
        return Todo(
            id=row["id"],
            content=row["content"],
            active_form=row["active_form"],
            status=row["status"],
            depends_on=json.loads(row["depends_on"]) if row["depends_on"] else None,
            parent_id=row["parent_id"],
        )

    async def get_todos(self) -> List[Todo]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(f"SELECT * FROM {self._table_name}")
            return [self._row_to_todo(row) for row in rows]

    async def get_todo(self, id: str) -> Optional[Todo]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                f"SELECT * FROM {self._table_name} WHERE id = $1", id
            )
            return self._row_to_todo(row) if row else None

    async def add_todo(self, todo: Todo) -> Todo:
        if todo.id is None:
            todo = todo.model_copy(update={"id": str(uuid.uuid4())})
        async with self._pool.acquire() as conn:
            await conn.execute(
                f"""
                INSERT INTO {self._table_name} (id, content, active_form, status, depends_on, parent_id)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                todo.id,
                todo.content,
                todo.active_form,
                todo.status,
                json.dumps(todo.depends_on) if todo.depends_on is not None else None,
                todo.parent_id,
            )
        return todo

    async def update_todo(self, id: str, **kwargs: Any) -> Optional[Todo]:
        existing = await self.get_todo(id)
        if existing is None:
            return None
        updated = existing.model_copy(update=kwargs)
        async with self._pool.acquire() as conn:
            await conn.execute(
                f"""
                UPDATE {self._table_name}
                SET content=$2, active_form=$3, status=$4, depends_on=$5, parent_id=$6
                WHERE id=$1
                """,
                updated.id,
                updated.content,
                updated.active_form,
                updated.status,
                json.dumps(updated.depends_on) if updated.depends_on is not None else None,
                updated.parent_id,
            )
        return updated

    async def remove_todo(self, id: str) -> bool:
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                f"DELETE FROM {self._table_name} WHERE id = $1", id
            )
            return result != "DELETE 0"

    async def set_todos(self, todos: List[Todo]) -> None:
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(f"DELETE FROM {self._table_name}")
                for todo in todos:
                    if todo.id is None:
                        todo = todo.model_copy(update={"id": str(uuid.uuid4())})
                    await conn.execute(
                        f"""
                        INSERT INTO {self._table_name} (id, content, active_form, status, depends_on, parent_id)
                        VALUES ($1, $2, $3, $4, $5, $6)
                        """,
                        todo.id,
                        todo.content,
                        todo.active_form,
                        todo.status,
                        json.dumps(todo.depends_on) if todo.depends_on is not None else None,
                        todo.parent_id,
                    )


class AsyncRedisStorage:
    _TODOS_KEY = "todos"

    def __init__(self, url: str = "redis://localhost:6379", key_prefix: str = "pydantic_ai_todo") -> None:
        self._url = url
        self._key_prefix = key_prefix
        self._redis: Any = None

    def _key(self, suffix: str) -> str:
        return f"{self._key_prefix}:{suffix}"

    async def initialize(self) -> None:
        try:
            import redis.asyncio as aioredis  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "redis is required for AsyncRedisStorage. "
                "Install it with: pip install redis"
            ) from exc

        self._redis = await aioredis.from_url(self._url, decode_responses=True)

    async def close(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None

    def _serialize(self, todo: Todo) -> str:
        return todo.model_dump_json()

    def _deserialize(self, data: str) -> Todo:
        return Todo.model_validate_json(data)

    async def get_todos(self) -> List[Todo]:
        raw = await self._redis.lrange(self._key(self._TODOS_KEY), 0, -1)
        return [self._deserialize(item) for item in raw]

    async def get_todo(self, id: str) -> Optional[Todo]:
        todos = await self.get_todos()
        for todo in todos:
            if todo.id == id:
                return todo
        return None

    async def add_todo(self, todo: Todo) -> Todo:
        if todo.id is None:
            todo = todo.model_copy(update={"id": str(uuid.uuid4())})
        await self._redis.rpush(self._key(self._TODOS_KEY), self._serialize(todo))
        return todo

    async def update_todo(self, id: str, **kwargs: Any) -> Optional[Todo]:
        todos = await self.get_todos()
        updated_todo: Optional[Todo] = None
        new_todos: List[Todo] = []
        for todo in todos:
            if todo.id == id:
                updated_todo = todo.model_copy(update=kwargs)
                new_todos.append(updated_todo)
            else:
                new_todos.append(todo)
        if updated_todo is None:
            return None
        await self.set_todos(new_todos)
        return updated_todo

    async def remove_todo(self, id: str) -> bool:
        todos = await self.get_todos()
        new_todos = [t for t in todos if t.id != id]
        if len(new_todos) == len(todos):
            return False
        await self.set_todos(new_todos)
        return True

    async def set_todos(self, todos: List[Todo]) -> None:
        key = self._key(self._TODOS_KEY)
        pipe = self._redis.pipeline()
        pipe.delete(key)
        for todo in todos:
            if todo.id is None:
                todo = todo.model_copy(update={"id": str(uuid.uuid4())})
            pipe.rpush(key, self._serialize(todo))
        await pipe.execute()


# ─────────────────────────────────────────────
# pydantic_ai_todo/capability.py
# ─────────────────────────────────────────────

class AbstractToolset:
    pass


class TodoCapability:
    def __init__(
        self,
        storage: Optional[TodoStorageProtocol] = None,
        async_storage: Optional[AsyncTodoStorageProtocol] = None,
        descriptions: Optional[Dict[str, str]] = None,
        enable_subtasks: bool = False,
    ) -> None:
        self.storage = storage
        self.async_storage = async_storage
        self.descriptions = descriptions
        self.enable_subtasks = enable_subtasks

    def get_instructions(self) -> Any:
        lines = [
            "You are a helpful assistant that manages a todo list.",
            "You can create, update, delete, and list todos.",
        ]
        if self.enable_subtasks:
            lines.append("You can also manage subtasks (todos with a parent_id).")
        return "\n".join(lines)

    def get_serialization_name(self) -> str:
        return "todo_capability"

    def get_toolset(self) -> Optional[AbstractToolset]:
        return None