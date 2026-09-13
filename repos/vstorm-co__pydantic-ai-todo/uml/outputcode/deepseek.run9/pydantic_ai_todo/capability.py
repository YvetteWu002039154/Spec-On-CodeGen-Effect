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
