from __future__ import annotations

import uuid
import json
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, Callable, Awaitable
from dataclasses import dataclass, field


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class EventType(str, Enum):
    TASK_CREATED = "task_created"
    TASK_UPDATED = "task_updated"
    TASK_DELETED = "task_deleted"
    TASK_COMPLETED = "task_completed"
    TASK_STATUS_CHANGED = "task_status_changed"
    DEPENDENCY_LINKED = "dependency_linked"
    CHILD_TASK_CREATED = "child_task_created"


@dataclass
class Task:
    id: str
    title: str
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    parent_id: Optional[str] = None
    tenant_id: str = "default"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    children: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "parent_id": self.parent_id,
            "tenant_id": self.tenant_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
            "dependencies": self.dependencies,
            "children": self.children,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Task:
        return cls(
            id=data["id"],
            title=data["title"],
            description=data.get("description", ""),
            status=TaskStatus(data.get("status", TaskStatus.PENDING.value)),
            parent_id=data.get("parent_id"),
            tenant_id=data.get("tenant_id", "default"),
            created_at=datetime.fromisoformat(data["created_at"]) if isinstance(data.get("created_at"), str) else data.get("created_at", datetime.utcnow()),
            updated_at=datetime.fromisoformat(data["updated_at"]) if isinstance(data.get("updated_at"), str) else data.get("updated_at", datetime.utcnow()),
            metadata=data.get("metadata", {}),
            dependencies=data.get("dependencies", []),
            children=data.get("children", []),
        )


@dataclass
class TaskEvent:
    event_type: EventType
    task_id: str
    tenant_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "task_id": self.task_id,
            "tenant_id": self.tenant_id,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
        }


EventHandler = Callable[[TaskEvent], Awaitable[None]]


class InMemoryStorage:
    def __init__(self):
        self._tasks: Dict[str, Dict[str, Task]] = {}

    def _get_tenant_store(self, tenant_id: str) -> Dict[str, Task]:
        if tenant_id not in self._tasks:
            self._tasks[tenant_id] = {}
        return self._tasks[tenant_id]

    async def save_task(self, task: Task) -> Task:
        store = self._get_tenant_store(task.tenant_id)
        store[task.id] = task
        return task

    async def get_task(self, task_id: str, tenant_id: str) -> Optional[Task]:
        store = self._get_tenant_store(tenant_id)
        return store.get(task_id)

    async def list_tasks(self, tenant_id: str) -> List[Task]:
        store = self._get_tenant_store(tenant_id)
        return list(store.values())

    async def delete_task(self, task_id: str, tenant_id: str) -> bool:
        store = self._get_tenant_store(tenant_id)
        if task_id in store:
            del store[task_id]
            return True
        return False

    async def bulk_save_tasks(self, tasks: List[Task]) -> List[Task]:
        saved = []
        for task in tasks:
            saved.append(await self.save_task(task))
        return saved


class PostgreSQLStorage:
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self._pool = None

    async def initialize(self):
        try:
            import asyncpg
            self._pool = await asyncpg.create_pool(self.connection_string)
            await self._create_tables()
        except ImportError:
            raise ImportError("asyncpg is required for PostgreSQL storage. Install it with: pip install asyncpg")

    async def _create_tables(self):
        async with self._pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'pending',
                    parent_id TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    metadata JSONB DEFAULT '{}',
                    dependencies JSONB DEFAULT '[]',
                    children JSONB DEFAULT '[]',
                    PRIMARY KEY (id, tenant_id)
                )
            """)

    async def save_task(self, task: Task) -> Task:
        async with self._pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO tasks (id, tenant_id, title, description, status, parent_id, created_at, updated_at, metadata, dependencies, children)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                ON CONFLICT (id, tenant_id) DO UPDATE SET
                    title = EXCLUDED.title,
                    description = EXCLUDED.description,
                    status = EXCLUDED.status,
                    parent_id = EXCLUDED.parent_id,
                    updated_at = EXCLUDED.updated_at,
                    metadata = EXCLUDED.metadata,
                    dependencies = EXCLUDED.dependencies,
                    children = EXCLUDED.children
            """,
            task.id, task.tenant_id, task.title, task.description,
            task.status.value, task.parent_id, task.created_at, task.updated_at,
            json.dumps(task.metadata), json.dumps(task.dependencies), json.dumps(task.children))
        return task

    async def get_task(self, task_id: str, tenant_id: str) -> Optional[Task]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM tasks WHERE id = $1 AND tenant_id = $2",
                task_id, tenant_id
            )
            if row:
                return self._row_to_task(row)
        return None

    async def list_tasks(self, tenant_id: str) -> List[Task]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM tasks WHERE tenant_id = $1 ORDER BY created_at ASC",
                tenant_id
            )
            return [self._row_to_task(row) for row in rows]

    async def delete_task(self, task_id: str, tenant_id: str) -> bool:
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM tasks WHERE id = $1 AND tenant_id = $2",
                task_id, tenant_id
            )
            return result == "DELETE 1"

    async def bulk_save_tasks(self, tasks: List[Task]) -> List[Task]:
        saved = []
        for task in tasks:
            saved.append(await self.save_task(task))
        return saved

    def _row_to_task(self, row) -> Task:
        return Task(
            id=row["id"],
            title=row["title"],
            description=row["description"] or "",
            status=TaskStatus(row["status"]),
            parent_id=row["parent_id"],
            tenant_id=row["tenant_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            metadata=json.loads(row["metadata"]) if isinstance(row["metadata"], str) else (row["metadata"] or {}),
            dependencies=json.loads(row["dependencies"]) if isinstance(row["dependencies"], str) else (row["dependencies"] or []),
            children=json.loads(row["children"]) if isinstance(row["children"], str) else (row["children"] or []),
        )

    async def close(self):
        if self._pool:
            await self._pool.close()


class EventSystem:
    def __init__(self):
        self._handlers: List[EventHandler] = []
        self._webhook_urls: List[str] = []

    def register_handler(self, handler: EventHandler):
        self._handlers.append(handler)

    def register_webhook(self, url: str):
        self._webhook_urls.append(url)

    async def emit(self, event: TaskEvent):
        for handler in self._handlers:
            try:
                await handler(event)
            except Exception:
                pass

        if self._webhook_urls:
            await self._send_webhooks(event)

    async def _send_webhooks(self, event: TaskEvent):
        try:
            import aiohttp
            event_data = event.to_dict()
            async with aiohttp.ClientSession() as session:
                for url in self._webhook_urls:
                    try:
                        async with session.post(url, json=event_data) as response:
                            pass
                    except Exception:
                        pass
        except ImportError:
            pass


class TodoToolset:
    def __init__(
        self,
        storage=None,
        tenant_id: str = "default",
        event_system: Optional[EventSystem] = None,
    ):
        self.storage = storage if storage is not None else InMemoryStorage()
        self.tenant_id = tenant_id
        self.event_system = event_system if event_system is not None else EventSystem()

    def _generate_id(self) -> str:
        return str(uuid.uuid4())

    async def _emit_event(self, event_type: EventType, task_id: str, data: Dict[str, Any] = None):
        event = TaskEvent(
            event_type=event_type,
            task_id=task_id,
            tenant_id=self.tenant_id,
            data=data or {},
        )
        await self.event_system.emit(event)

    async def list_tasks(self, hierarchical: bool = False) -> List[Dict[str, Any]]:
        tasks = await self.storage.list_tasks(self.tenant_id)
        task_dicts = [t.to_dict() for t in tasks]

        if not hierarchical:
            return task_dicts

        return self._build_hierarchy(tasks)

    def _build_hierarchy(self, tasks: List[Task]) -> List[Dict[str, Any]]:
        task_map: Dict[str, Dict[str, Any]] = {}
        for task in tasks:
            d = task.to_dict()
            d["subtasks"] = []
            task_map[task.id] = d

        roots = []
        for task in tasks:
            if task.parent_id and task.parent_id in task_map:
                task_map[task.parent_id]["subtasks"].append(task_map[task.id])
            else:
                roots.append(task_map[task.id])

        return roots

    async def bulk_write_tasks(self, tasks_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        tasks = []
        for data in tasks_data:
            task_id = data.get("id") or self._generate_id()
            existing = await self.storage.get_task(task_id, self.tenant_id)
            if existing:
                if "title" in data:
                    existing.title = data["title"]
                if "description" in data:
                    existing.description = data["description"]
                if "status" in data:
                    existing.status = TaskStatus(data["status"])
                if "metadata" in data:
                    existing.metadata = data["metadata"]
                existing.updated_at = datetime.utcnow()
                tasks.append(existing)
            else:
                task = Task(
                    id=task_id,
                    title=data.get("title", "Untitled"),
                    description=data.get("description", ""),
                    status=TaskStatus(data.get("status", TaskStatus.PENDING.value)),
                    parent_id=data.get("parent_id"),
                    tenant_id=self.tenant_id,
                    metadata=data.get("metadata", {}),
                    dependencies=data.get("dependencies", []),
                    children=data.get("children", []),
                )
                tasks.append(task)

        saved = await self.storage.bulk_save_tasks(tasks)
        results = []
        for task in saved:
            await self._emit_event(EventType.TASK_CREATED, task.id, {"task": task.to_dict()})
            results.append(task.to_dict())
        return results

    async def add_task(
        self,
        title: str,
        description: str = "",
        status: str = TaskStatus.PENDING.value,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        task = Task(
            id=self._generate_id(),
            title=title,
            description=description,
            status=TaskStatus(status),
            tenant_id=self.tenant_id,
            metadata=metadata or {},
        )
        saved = await self.storage.save_task(task)
        await self._emit_event(EventType.TASK_CREATED, saved.id, {"task": saved.to_dict()})
        return saved.to_dict()

    async def update_task_status(self, task_id: str, status: str) -> Optional[Dict[str, Any]]:
        task = await self.storage.get_task(task_id, self.tenant_id)
        if not task:
            return None

        old_status = task.status
        task.status = TaskStatus(status)
        task.updated_at = datetime.utcnow()
        saved = await self.storage.save_task(task)

        await self._emit_event(
            EventType.TASK_STATUS_CHANGED,
            saved.id,
            {"old_status": old_status.value, "new_status": status},
        )

        if task.status == TaskStatus.COMPLETED:
            await self._emit_event(EventType.TASK_COMPLETED, saved.id, {"task": saved.to_dict()})

        return saved.to_dict()

    async def delete_task(self, task_id: str) -> bool:
        task = await self.storage.get_task(task_id, self.tenant_id)
        if not task:
            return False

        if task.parent_id:
            parent = await self.storage.get_task(task.parent_id, self.tenant_id)
            if parent and task_id in parent.children:
                parent.children.remove(task_id)
                parent.updated_at = datetime.utcnow()
                await self.storage.save_task(parent)

        all_tasks = await self.storage.list_tasks(self.tenant_id)
        for other_task in all_tasks:
            if task_id in other_task.dependencies:
                other_task.dependencies.remove(task_id)
                other_task.updated_at = datetime.utcnow()
                await self.storage.save_task(other_task)

        for child_id in task.children:
            await self.delete_task(child_id)

        result = await self.storage.delete_task(task_id, self.tenant_id)
        if result:
            await self._emit_event(EventType.TASK_DELETED, task_id, {"task_id": task_id})
        return result

    async def create_child_task(
        self,
        parent_id: str,
        title: str,
        description: str = "",
        status: str = TaskStatus.PENDING.value,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        parent = await self.storage.get_task(parent_id, self.tenant_id)
        if not parent:
            return None

        child = Task(
            id=self._generate_id(),
            title=title,
            description=description,
            status=TaskStatus(status),
            parent_id=parent_id,
            tenant_id=self.tenant_id,
            metadata=metadata or {},
        )
        saved_child = await self.storage.save_task(child)

        parent.children.append(saved_child.id)
        parent.updated_at = datetime.utcnow()
        await self.storage.save_task(parent)

        await self._emit_event(
            EventType.CHILD_TASK_CREATED,
            saved_child.id,
            {"parent_id": parent_id, "child": saved_child.to_dict()},
        )
        return saved_child.to_dict()

    async def link_dependency(self, task_id: str, depends_on_id: str) -> Optional[Dict[str, Any]]:
        task = await self.storage.get_task(task_id, self.tenant_id)
        if not task:
            return None

        dependency = await self.storage.get_task(depends_on_id, self.tenant_id)
        if not dependency:
            return None

        if depends_on_id not in task.dependencies:
            task.dependencies.append(depends_on_id)
            task.updated_at = datetime.utcnow()
            saved = await self.storage.save_task(task)
            await self._emit_event(
                EventType.DEPENDENCY_LINKED,
                task_id,
                {"task_id": task_id, "depends_on_id": depends_on_id},
            )
            return saved.to_dict()

        return task.to_dict()

    async def list_ready_tasks(self) -> List[Dict[str, Any]]:
        all_tasks = await self.storage.list_tasks(self.tenant_id)
        completed_ids = {t.id for t in all_tasks if t.status == TaskStatus.COMPLETED}

        ready = []
        for task in all_tasks:
            if task.status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED, TaskStatus.IN_PROGRESS):
                continue

            all_deps_completed = all(dep_id in completed_ids for dep_id in task.dependencies)
            if all_deps_completed:
                ready.append(task.to_dict())

        return ready

    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        task = await self.storage.get_task(task_id, self.tenant_id)
        if task:
            return task.to_dict()
        return None

    async def update_task(
        self,
        task_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        task = await self.storage.get_task(task_id, self.tenant_id)
        if not task:
            return None

        if title is not None:
            task.title = title
        if description is not None:
            task.description = description
        if status is not None:
            old_status = task.status
            task.status = TaskStatus(status)
            if old_status != task.status:
                await self._emit_event(
                    EventType.TASK_STATUS_CHANGED,
                    task_id,
                    {"old_status": old_status.value, "new_status": status},
                )
        if metadata is not None:
            task.metadata = metadata

        task.updated_at = datetime.utcnow()
        saved = await self.storage.save_task(task)
        await self._emit_event(EventType.TASK_UPDATED, saved.id, {"task": saved.to_dict()})
        return saved.to_dict()


class TodoTools:
    def __init__(self, toolset: TodoToolset):
        self.toolset = toolset

    async def list_tasks(self, hierarchical: bool = False) -> str:
        tasks = await self.toolset.list_tasks(hierarchical=hierarchical)
        return json.dumps(tasks, indent=2)

    async def bulk_write_tasks(self, tasks: List[Dict[str, Any]]) -> str:
        result = await self.toolset.bulk_write_tasks(tasks)
        return json.dumps(result, indent=2)

    async def add_task(
        self,
        title: str,
        description: str = "",
        status: str = "pending",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        task = await self.toolset.add_task(title, description, status, metadata)
        return json.dumps(task, indent=2)

    async def update_task_status(self, task_id: str, status: str) -> str:
        task = await self.toolset.update_task_status(task_id, status)
        if task is None:
            return json.dumps({"error": f"Task {task_id} not found"})
        return json.dumps(task, indent=2)

    async def delete_task(self, task_id: str) -> str:
        result = await self.toolset.delete_task(task_id)
        return json.dumps({"success": result, "task_id": task_id})

    async def create_child_task(
        self,
        parent_id: str,
        title: str,
        description: str = "",
        status: str = "pending",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        task = await self.toolset.create_child_task(parent_id, title, description, status, metadata)
        if task is None:
            return json.dumps({"error": f"Parent task {parent_id} not found"})
        return json.dumps(task, indent=2)

    async def link_dependency(self, task_id: str, depends_on_id: str) -> str:
        task = await self.toolset.link_dependency(task_id, depends_on_id)
        if task is None:
            return json.dumps({"error": f"Task {task_id} or dependency {depends_on_id} not found"})
        return json.dumps(task, indent=2)

    async def list_ready_tasks(self) -> str:
        tasks = await self.toolset.list_ready_tasks()
        return json.dumps(tasks, indent=2)


def create_todo_toolset(
    storage_type: str = "memory",
    connection_string: Optional[str] = None,
    tenant_id: str = "default",
    event_handlers: Optional[List[EventHandler]] = None,
    webhook_urls: Optional[List[str]] = None,
) -> TodoToolset:
    if storage_type == "postgresql":
        if not connection_string:
            raise ValueError("connection_string is required for PostgreSQL storage")
        storage = PostgreSQLStorage(connection_string)
    else:
        storage = InMemoryStorage()

    event_system = EventSystem()

    if event_handlers:
        for handler in event_handlers:
            event_system.register_handler(handler)

    if webhook_urls:
        for url in webhook_urls:
            event_system.register_webhook(url)

    return TodoToolset(
        storage=storage,
        tenant_id=tenant_id,
        event_system=event_system,
    )


def create_todo_tools(
    storage_type: str = "memory",
    connection_string: Optional[str] = None,
    tenant_id: str = "default",
    event_handlers: Optional[List[EventHandler]] = None,
    webhook_urls: Optional[List[str]] = None,
) -> TodoTools:
    toolset = create_todo_toolset(
        storage_type=storage_type,
        connection_string=connection_string,
        tenant_id=tenant_id,
        event_handlers=event_handlers,
        webhook_urls=webhook_urls,
    )
    return TodoTools(toolset=toolset)