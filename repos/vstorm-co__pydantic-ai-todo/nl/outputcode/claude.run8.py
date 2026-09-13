from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    import asyncpg
    HAS_ASYNCPG = True
except ImportError:
    HAS_ASYNCPG = False

try:
    from pydantic import BaseModel, Field
    from pydantic_ai import Agent
    from pydantic_ai.tools import Tool
    HAS_PYDANTIC_AI = True
except ImportError:
    HAS_PYDANTIC_AI = False
    from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    parent_id: Optional[str] = None
    tenant_id: str = "default"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True


class TaskDependency(BaseModel):
    task_id: str
    depends_on_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TaskEvent(BaseModel):
    event_type: str
    task_id: str
    tenant_id: str
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class InMemoryStorage:
    def __init__(self):
        self._tasks: Dict[str, Task] = {}
        self._dependencies: List[TaskDependency] = []

    async def initialize(self):
        pass

    async def close(self):
        pass

    async def create_task(self, task: Task) -> Task:
        self._tasks[task.id] = task
        return task

    async def get_task(self, task_id: str, tenant_id: str) -> Optional[Task]:
        task = self._tasks.get(task_id)
        if task and task.tenant_id == tenant_id:
            return task
        return None

    async def list_tasks(self, tenant_id: str, parent_id: Optional[str] = None,
                         status: Optional[TaskStatus] = None) -> List[Task]:
        tasks = [t for t in self._tasks.values() if t.tenant_id == tenant_id]
        if parent_id is not None:
            tasks = [t for t in tasks if t.parent_id == parent_id]
        if status is not None:
            tasks = [t for t in tasks if t.status == status]
        return tasks

    async def update_task(self, task: Task) -> Task:
        task.updated_at = datetime.utcnow()
        self._tasks[task.id] = task
        return task

    async def delete_task(self, task_id: str, tenant_id: str) -> bool:
        task = self._tasks.get(task_id)
        if task and task.tenant_id == tenant_id:
            del self._tasks[task_id]
            self._dependencies = [
                d for d in self._dependencies
                if d.task_id != task_id and d.depends_on_id != task_id
            ]
            return True
        return False

    async def add_dependency(self, dependency: TaskDependency) -> TaskDependency:
        existing = [
            d for d in self._dependencies
            if d.task_id == dependency.task_id and d.depends_on_id == dependency.depends_on_id
        ]
        if not existing:
            self._dependencies.append(dependency)
        return dependency

    async def get_dependencies(self, task_id: str) -> List[TaskDependency]:
        return [d for d in self._dependencies if d.task_id == task_id]

    async def get_dependents(self, task_id: str) -> List[TaskDependency]:
        return [d for d in self._dependencies if d.depends_on_id == task_id]

    async def bulk_upsert_tasks(self, tasks: List[Task]) -> List[Task]:
        result = []
        for task in tasks:
            task.updated_at = datetime.utcnow()
            self._tasks[task.id] = task
            result.append(task)
        return result


class PostgreSQLStorage:
    def __init__(self, dsn: str):
        if not HAS_ASYNCPG:
            raise ImportError("asyncpg is required for PostgreSQL storage")
        self._dsn = dsn
        self._pool: Optional[asyncpg.Pool] = None

    async def initialize(self):
        self._pool = await asyncpg.create_pool(self._dsn)
        await self._create_tables()

    async def close(self):
        if self._pool:
            await self._pool.close()

    async def _create_tables(self):
        async with self._pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    priority TEXT NOT NULL DEFAULT 'medium',
                    parent_id TEXT,
                    tenant_id TEXT NOT NULL DEFAULT 'default',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    metadata JSONB NOT NULL DEFAULT '{}'
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS task_dependencies (
                    task_id TEXT NOT NULL,
                    depends_on_id TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    PRIMARY KEY (task_id, depends_on_id)
                )
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_tenant_id ON tasks(tenant_id)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_parent_id ON tasks(parent_id)
            """)

    def _row_to_task(self, row) -> Task:
        return Task(
            id=row['id'],
            title=row['title'],
            description=row['description'],
            status=TaskStatus(row['status']),
            priority=TaskPriority(row['priority']),
            parent_id=row['parent_id'],
            tenant_id=row['tenant_id'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            metadata=json.loads(row['metadata']) if isinstance(row['metadata'], str) else (row['metadata'] or {})
        )

    async def create_task(self, task: Task) -> Task:
        async with self._pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO tasks (id, title, description, status, priority, parent_id, tenant_id, created_at, updated_at, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """, task.id, task.title, task.description, task.status,
                task.priority, task.parent_id, task.tenant_id,
                task.created_at, task.updated_at, json.dumps(task.metadata))
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

    async def list_tasks(self, tenant_id: str, parent_id: Optional[str] = None,
                         status: Optional[TaskStatus] = None) -> List[Task]:
        query = "SELECT * FROM tasks WHERE tenant_id = $1"
        params = [tenant_id]
        idx = 2
        if parent_id is not None:
            query += f" AND parent_id = ${idx}"
            params.append(parent_id)
            idx += 1
        if status is not None:
            query += f" AND status = ${idx}"
            params.append(status.value if isinstance(status, TaskStatus) else status)
            idx += 1
        query += " ORDER BY created_at ASC"
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [self._row_to_task(row) for row in rows]

    async def update_task(self, task: Task) -> Task:
        task.updated_at = datetime.utcnow()
        async with self._pool.acquire() as conn:
            await conn.execute("""
                UPDATE tasks SET title=$2, description=$3, status=$4, priority=$5,
                parent_id=$6, updated_at=$7, metadata=$8
                WHERE id=$1 AND tenant_id=$9
            """, task.id, task.title, task.description, task.status,
                task.priority, task.parent_id, task.updated_at,
                json.dumps(task.metadata), task.tenant_id)
        return task

    async def delete_task(self, task_id: str, tenant_id: str) -> bool:
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM tasks WHERE id=$1 AND tenant_id=$2",
                task_id, tenant_id
            )
            await conn.execute(
                "DELETE FROM task_dependencies WHERE task_id=$1 OR depends_on_id=$1",
                task_id
            )
            return result != "DELETE 0"

    async def add_dependency(self, dependency: TaskDependency) -> TaskDependency:
        async with self._pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO task_dependencies (task_id, depends_on_id, created_at)
                VALUES ($1, $2, $3)
                ON CONFLICT (task_id, depends_on_id) DO NOTHING
            """, dependency.task_id, dependency.depends_on_id, dependency.created_at)
        return dependency

    async def get_dependencies(self, task_id: str) -> List[TaskDependency]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM task_dependencies WHERE task_id=$1", task_id
            )
            return [TaskDependency(
                task_id=row['task_id'],
                depends_on_id=row['depends_on_id'],
                created_at=row['created_at']
            ) for row in rows]

    async def get_dependents(self, task_id: str) -> List[TaskDependency]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM task_dependencies WHERE depends_on_id=$1", task_id
            )
            return [TaskDependency(
                task_id=row['task_id'],
                depends_on_id=row['depends_on_id'],
                created_at=row['created_at']
            ) for row in rows]

    async def bulk_upsert_tasks(self, tasks: List[Task]) -> List[Task]:
        result = []
        async with self._pool.acquire() as conn:
            for task in tasks:
                task.updated_at = datetime.utcnow()
                await conn.execute("""
                    INSERT INTO tasks (id, title, description, status, priority, parent_id, tenant_id, created_at, updated_at, metadata)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    ON CONFLICT (id) DO UPDATE SET
                        title=EXCLUDED.title,
                        description=EXCLUDED.description,
                        status=EXCLUDED.status,
                        priority=EXCLUDED.priority,
                        parent_id=EXCLUDED.parent_id,
                        updated_at=EXCLUDED.updated_at,
                        metadata=EXCLUDED.metadata
                """, task.id, task.title, task.description, task.status,
                    task.priority, task.parent_id, task.tenant_id,
                    task.created_at, task.updated_at, json.dumps(task.metadata))
                result.append(task)
        return result


class EventSystem:
    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}
        self._global_handlers: List[Callable] = []

    def on(self, event_type: str, handler: Callable):
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def on_any(self, handler: Callable):
        self._global_handlers.append(handler)

    async def emit(self, event: TaskEvent):
        handlers = self._handlers.get(event.event_type, [])
        all_handlers = handlers + self._global_handlers
        for handler in all_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception:
                pass


class TodoToolset:
    def __init__(
        self,
        storage=None,
        tenant_id: str = "default",
        event_system: Optional[EventSystem] = None
    ):
        self._storage = storage or InMemoryStorage()
        self._tenant_id = tenant_id
        self._events = event_system or EventSystem()
        self._initialized = False

    async def initialize(self):
        if not self._initialized:
            await self._storage.initialize()
            self._initialized = True

    async def close(self):
        await self._storage.close()

    async def _ensure_initialized(self):
        if not self._initialized:
            await self.initialize()

    async def _emit(self, event_type: str, task_id: str, data: Dict[str, Any]):
        event = TaskEvent(
            event_type=event_type,
            task_id=task_id,
            tenant_id=self._tenant_id,
            data=data
        )
        await self._events.emit(event)

    async def list_tasks(
        self,
        hierarchical: bool = False,
        status: Optional[str] = None,
        parent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        await self._ensure_initialized()
        status_enum = TaskStatus(status) if status else None
        tasks = await self._storage.list_tasks(
            tenant_id=self._tenant_id,
            parent_id=parent_id,
            status=status_enum
        )

        if hierarchical:
            return {"tasks": self._build_hierarchy(tasks), "total": len(tasks)}

        return {"tasks": [t.dict() for t in tasks], "total": len(tasks)}

    def _build_hierarchy(self, tasks: List[Task]) -> List[Dict[str, Any]]:
        task_map: Dict[str, Dict[str, Any]] = {}
        for task in tasks:
            task_dict = task.dict()
            task_dict['children'] = []
            task_map[task.id] = task_dict

        roots = []
        for task in tasks:
            if task.parent_id and task.parent_id in task_map:
                task_map[task.parent_id]['children'].append(task_map[task.id])
            else:
                roots.append(task_map[task.id])

        return roots

    async def add_task(
        self,
        title: str,
        description: Optional[str] = None,
        priority: str = "medium",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        await self._ensure_initialized()
        task = Task(
            title=title,
            description=description,
            priority=TaskPriority(priority),
            tenant_id=self._tenant_id,
            metadata=metadata or {}
        )
        created = await self._storage.create_task(task)
        await self._emit("task.created", created.id, {"task": created.dict()})
        return {"task": created.dict(), "success": True}

    async def bulk_write_tasks(self, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        await self._ensure_initialized()
        task_objects = []
        for task_data in tasks:
            if 'id' not in task_data:
                task_data['id'] = str(uuid.uuid4())
            task_data['tenant_id'] = self._tenant_id
            if 'status' in task_data:
                task_data['status'] = TaskStatus(task_data['status'])
            if 'priority' in task_data:
                task_data['priority'] = TaskPriority(task_data['priority'])
            task_objects.append(Task(**task_data))

        updated = await self._storage.bulk_upsert_tasks(task_objects)
        for task in updated:
            await self._emit("task.bulk_upserted", task.id, {"task": task.dict()})

        return {
            "tasks": [t.dict() for t in updated],
            "count": len(updated),
            "success": True
        }

    async def update_task_status(
        self,
        task_id: str,
        status: str
    ) -> Dict[str, Any]:
        await self._ensure_initialized()
        task = await self._storage.get_task(task_id, self._tenant_id)
        if not task:
            return {"success": False, "error": f"Task {task_id} not found"}

        old_status = task.status
        task.status = TaskStatus(status)
        updated = await self._storage.update_task(task)
        await self._emit("task.status_changed", task_id, {
            "old_status": old_status,
            "new_status": status,
            "task": updated.dict()
        })
        return {"task": updated.dict(), "success": True}

    async def delete_task(self, task_id: str) -> Dict[str, Any]:
        await self._ensure_initialized()
        task = await self._storage.get_task(task_id, self._tenant_id)
        if not task:
            return {"success": False, "error": f"Task {task_id} not found"}

        children = await self._storage.list_tasks(
            tenant_id=self._tenant_id,
            parent_id=task_id
        )
        for child in children:
            await self.delete_task(child.id)

        deleted = await self._storage.delete_task(task_id, self._tenant_id)
        if deleted:
            await self._emit("task.deleted", task_id, {"task_id": task_id})
        return {"success": deleted, "task_id": task_id}

    async def create_child_task(
        self,
        parent_id: str,
        title: str,
        description: Optional[str] = None,
        priority: str = "medium",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        await self._ensure_initialized()
        parent = await self._storage.get_task(parent_id, self._tenant_id)
        if not parent:
            return {"success": False, "error": f"Parent task {parent_id} not found"}

        task = Task(
            title=title,
            description=description,
            priority=TaskPriority(priority),
            parent_id=parent_id,
            tenant_id=self._tenant_id,
            metadata=metadata or {}
        )
        created = await self._storage.create_task(task)
        await self._emit("task.child_created", created.id, {
            "parent_id": parent_id,
            "task": created.dict()
        })
        return {"task": created.dict(), "parent_id": parent_id, "success": True}

    async def link_dependency(
        self,
        task_id: str,
        depends_on_id: str
    ) -> Dict[str, Any]:
        await self._ensure_initialized()
        task = await self._storage.get_task(task_id, self._tenant_id)
        if not task:
            return {"success": False, "error": f"Task {task_id} not found"}

        dep_task = await self._storage.get_task(depends_on_id, self._tenant_id)
        if not dep_task:
            return {"success": False, "error": f"Dependency task {depends_on_id} not found"}

        if task_id == depends_on_id:
            return {"success": False, "error": "A task cannot depend on itself"}

        if await self._would_create_cycle(task_id, depends_on_id):
            return {"success": False, "error": "Adding this dependency would create a cycle"}

        dependency = TaskDependency(task_id=task_id, depends_on_id=depends_on_id)
        await self._storage.add_dependency(dependency)
        await self._emit("task.dependency_linked", task_id, {
            "task_id": task_id,
            "depends_on_id": depends_on_id
        })
        return {
            "success": True,
            "task_id": task_id,
            "depends_on_id": depends_on_id
        }

    async def _would_create_cycle(self, task_id: str, depends_on_id: str) -> bool:
        visited = set()
        queue = [depends_on_id]
        while queue:
            current = queue.pop(0)
            if current == task_id:
                return True
            if current in visited:
                continue
            visited.add(current)
            deps = await self._storage.get_dependencies(current)
            for dep in deps:
                queue.append(dep.depends_on_id)
        return False

    async def list_ready_tasks(self) -> Dict[str, Any]:
        await self._ensure_initialized()
        all_tasks = await self._storage.list_tasks(tenant_id=self._tenant_id)
        ready_tasks = []

        for task in all_tasks:
            if task.status not in (TaskStatus.PENDING, TaskStatus.BLOCKED):
                continue

            deps = await self._storage.get_dependencies(task.id)
            if not deps:
                if task.status == TaskStatus.PENDING:
                    ready_tasks.append(task)
                continue

            all_deps_completed = True
            for dep in deps:
                dep_task = await self._storage.get_task(dep.depends_on_id, self._tenant_id)
                if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                    all_deps_completed = False
                    break

            if all_deps_completed:
                if task.status == TaskStatus.BLOCKED:
                    task.status = TaskStatus.PENDING
                    await self._storage.update_task(task)
                ready_tasks.append(task)

        return {"tasks": [t.dict() for t in ready_tasks], "total": len(ready_tasks)}

    async def get_task(self, task_id: str) -> Dict[str, Any]:
        await self._ensure_initialized()
        task = await self._storage.get_task(task_id, self._tenant_id)
        if not task:
            return {"success": False, "error": f"Task {task_id} not found"}
        deps = await self._storage.get_dependencies(task_id)
        dependents = await self._storage.get_dependents(task_id)
        return {
            "task": task.dict(),
            "dependencies": [d.dict() for d in deps],
            "dependents": [d.dict() for d in dependents],
            "success": True
        }

    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "list_tasks",
                "description": "List all tasks, optionally in hierarchical view",
                "function": self.list_tasks
            },
            {
                "name": "add_task",
                "description": "Add a single new task",
                "function": self.add_task
            },
            {
                "name": "bulk_write_tasks",
                "description": "Bulk write or update multiple tasks at once",
                "function": self.bulk_write_tasks
            },
            {
                "name": "update_task_status",
                "description": "Update the status of a task by ID",
                "function": self.update_task_status
            },
            {
                "name": "delete_task",
                "description": "Delete a task by ID (also deletes children)",
                "function": self.delete_task
            },
            {
                "name": "create_child_task",
                "description": "Create a child task under a parent task",
                "function": self.create_child_task
            },
            {
                "name": "link_dependency",
                "description": "Link two tasks with a dependency relationship",
                "function": self.link_dependency
            },
            {
                "name": "list_ready_tasks",
                "description": "List tasks that are ready to work on (no incomplete dependencies)",
                "function": self.list_ready_tasks
            },
            {
                "name": "get_task",
                "description": "Get a single task by ID with its dependencies",
                "function": self.get_task
            }
        ]


class TodoToolsetFactory:
    @staticmethod
    def create_in_memory(
        tenant_id: str = "default",
        event_system: Optional[EventSystem] = None
    ) -> TodoToolset:
        storage = InMemoryStorage()
        return TodoToolset(storage=storage, tenant_id=tenant_id, event_system=event_system)

    @staticmethod
    def create_postgresql(
        dsn: str,
        tenant_id: str = "default",
        event_system: Optional[EventSystem] = None
    ) -> TodoToolset:
        storage = PostgreSQLStorage(dsn=dsn)
        return TodoToolset(storage=storage, tenant_id=tenant_id, event_system=event_system)


class MultiTenantTodoManager:
    def __init__(self, storage_factory: Callable[[str], Any] = None):
        self._toolsets: Dict[str, TodoToolset] = {}
        self._storage_factory = storage_factory or (lambda tenant_id: InMemoryStorage())

    def get_toolset(self, tenant_id: str) -> TodoToolset:
        if tenant_id not in self._toolsets:
            storage = self._storage_factory(tenant_id)
            self._toolsets[tenant_id] = TodoToolset(
                storage=storage,
                tenant_id=tenant_id
            )
        return self._toolsets[tenant_id]

    async def initialize_all(self):
        for toolset in self._toolsets.values():
            await toolset.initialize()

    async def close_all(self):
        for toolset in self._toolsets.values():
            await toolset.close()


async def create_todo_toolset(
    storage_type: str = "memory",
    dsn: Optional[str] = None,
    tenant_id: str = "default",
    event_system: Optional[EventSystem] = None
) -> TodoToolset:
    if storage_type == "postgresql":
        if not dsn:
            raise ValueError("DSN is required for PostgreSQL storage")
        toolset = TodoToolsetFactory.create_postgresql(
            dsn=dsn,
            tenant_id=tenant_id,
            event_system=event_system
        )
    else:
        toolset = TodoToolsetFactory.create_in_memory(
            tenant_id=tenant_id,
            event_system=event_system
        )
    await toolset.initialize()
    return toolset


if __name__ == "__main__":
    async def demo():
        print("=== Todo Toolset Demo ===\n")

        toolset = await create_todo_toolset(tenant_id="demo_tenant")

        result = await toolset.add_task(
            title="Build API",
            description="Create REST API endpoints",
            priority="high"
        )
        api_task_id = result["task"]["id"]
        print(f"Created task: {result['task']['title']} (ID: {api_task_id})")

        result = await toolset.add_task(
            title="Write Tests",
            description="Write unit and integration tests",
            priority="medium"
        )
        test_task_id = result["task"]["id"]
        print(f"Created task: {result['task']['title']} (ID: {test_task_id})")

        result = await toolset.add_task(
            title="Deploy Application",
            description="Deploy to production",
            priority="high"
        )
        deploy_task_id = result["task"]["id"]
        print(f"Created task: {result['task']['title']} (ID: {deploy_task_id})")

        result = await toolset.create_child_task(
            parent_id=api_task_id,
            title="Design API Schema",
            description="Define request/response schemas",
            priority="high"
        )
        print(f"\nCreated child task: {result['task']['title']}")

        result = await toolset.link_dependency(
            task_id=test_task_id,
            depends_on_id=api_task_id
        )
        print(f"\nLinked dependency: Tests depend on API (success: {result['success']})")

        result = await toolset.link_dependency(
            task_id=deploy_task_id,
            depends_on_id=test_task_id
        )
        print(f"Linked dependency: Deploy depends on Tests (success: {result['success']})")

        result = await toolset.list_ready_tasks()
        print(f"\nReady tasks ({result['total']}):")
        for task in result["tasks"]:
            print(f"  - {task['title']} [{task['status']}]")

        result = await toolset.list_tasks(hierarchical=True)
        print(f"\nAll tasks (hierarchical, total: {result['total']}):")
        for task in result["tasks"]:
            print(f"  - {task['title']} [{task['status']}]")
            for child in task.get("children", []):
                print(f"    - {child['title']} [{child['status']}]")

        result = await toolset.update_task_status(api_task_id, "completed")
        print(f"\nUpdated API task status to: {result['task']['status']}")

        result = await toolset.list_ready_tasks()
        print(f"\nReady tasks after completing API ({result['total']}):")
        for task in result["tasks"]:
            print(f"  - {task['title']} [{task['status']}]")

        bulk_tasks = [
            {"title": "Task A", "priority": "low"},
            {"title": "Task B", "priority": "medium"},
            {"title": "Task C", "priority": "high"},
        ]
        result = await toolset.bulk_write_tasks(bulk_tasks)
        print(f"\nBulk created {result['count']} tasks")

        result = await toolset.delete_task(api_task_id)
        print(f"\nDeleted API task (success: {result['success']})")

        result = await toolset.list_tasks()
        print(f"\nRemaining tasks: {result['total']}")

        print("\n=== Available Tools ===")
        for tool in toolset.get_tools():
            print(f"  - {tool['name']}: {tool['description']}")

        await toolset.close()
        print("\nDemo completed successfully!")

    asyncio.run(demo())