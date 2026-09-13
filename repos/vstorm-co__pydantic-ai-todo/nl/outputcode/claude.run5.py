from __future__ import annotations

import uuid
import json
from datetime import datetime
from enum import Enum
from typing import Any, Optional
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
    DEPENDENCY_ADDED = "dependency_added"
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
    metadata: dict[str, Any] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)
    children: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
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
    def from_dict(cls, data: dict[str, Any]) -> Task:
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
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "task_id": self.task_id,
            "tenant_id": self.tenant_id,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
        }


class EventBus:
    def __init__(self):
        self._handlers: dict[EventType, list[Any]] = {}
        self._global_handlers: list[Any] = []

    def subscribe(self, event_type: EventType, handler) -> None:
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def subscribe_all(self, handler) -> None:
        self._global_handlers.append(handler)

    def unsubscribe(self, event_type: EventType, handler) -> None:
        if event_type in self._handlers:
            self._handlers[event_type] = [h for h in self._handlers[event_type] if h != handler]

    def publish(self, event: TaskEvent) -> None:
        handlers = self._handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception:
                pass
        for handler in self._global_handlers:
            try:
                handler(event)
            except Exception:
                pass


class InMemoryStorage:
    def __init__(self):
        self._tasks: dict[str, dict[str, Task]] = {}

    def _get_tenant_store(self, tenant_id: str) -> dict[str, Task]:
        if tenant_id not in self._tasks:
            self._tasks[tenant_id] = {}
        return self._tasks[tenant_id]

    def save(self, task: Task) -> Task:
        store = self._get_tenant_store(task.tenant_id)
        store[task.id] = task
        return task

    def get(self, task_id: str, tenant_id: str) -> Optional[Task]:
        store = self._get_tenant_store(tenant_id)
        return store.get(task_id)

    def delete(self, task_id: str, tenant_id: str) -> bool:
        store = self._get_tenant_store(tenant_id)
        if task_id in store:
            del store[task_id]
            return True
        return False

    def list_all(self, tenant_id: str) -> list[Task]:
        store = self._get_tenant_store(tenant_id)
        return list(store.values())

    def bulk_save(self, tasks: list[Task]) -> list[Task]:
        saved = []
        for task in tasks:
            saved.append(self.save(task))
        return saved


class PostgreSQLStorage:
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self._conn = None
        self._ensure_schema()

    def _get_connection(self):
        try:
            import psycopg2
            import psycopg2.extras
            if self._conn is None or self._conn.closed:
                self._conn = psycopg2.connect(self.connection_string)
            return self._conn
        except ImportError:
            raise RuntimeError("psycopg2 is required for PostgreSQL storage. Install it with: pip install psycopg2-binary")

    def _ensure_schema(self) -> None:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id VARCHAR(255) NOT NULL,
                    tenant_id VARCHAR(255) NOT NULL DEFAULT 'default',
                    title TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    status VARCHAR(50) DEFAULT 'pending',
                    parent_id VARCHAR(255),
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    metadata JSONB DEFAULT '{}',
                    dependencies JSONB DEFAULT '[]',
                    children JSONB DEFAULT '[]',
                    PRIMARY KEY (id, tenant_id)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_tenant_id ON tasks(tenant_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_parent_id ON tasks(parent_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
            conn.commit()
            cursor.close()
        except Exception:
            pass

    def save(self, task: Task) -> Task:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO tasks (id, tenant_id, title, description, status, parent_id, created_at, updated_at, metadata, dependencies, children)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id, tenant_id) DO UPDATE SET
                title = EXCLUDED.title,
                description = EXCLUDED.description,
                status = EXCLUDED.status,
                parent_id = EXCLUDED.parent_id,
                updated_at = EXCLUDED.updated_at,
                metadata = EXCLUDED.metadata,
                dependencies = EXCLUDED.dependencies,
                children = EXCLUDED.children
        """, (
            task.id,
            task.tenant_id,
            task.title,
            task.description,
            task.status.value,
            task.parent_id,
            task.created_at,
            task.updated_at,
            json.dumps(task.metadata),
            json.dumps(task.dependencies),
            json.dumps(task.children),
        ))
        conn.commit()
        cursor.close()
        return task

    def get(self, task_id: str, tenant_id: str) -> Optional[Task]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, tenant_id, title, description, status, parent_id, created_at, updated_at, metadata, dependencies, children FROM tasks WHERE id = %s AND tenant_id = %s",
            (task_id, tenant_id)
        )
        row = cursor.fetchone()
        cursor.close()
        if row is None:
            return None
        return self._row_to_task(row)

    def delete(self, task_id: str, tenant_id: str) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tasks WHERE id = %s AND tenant_id = %s", (task_id, tenant_id))
        affected = cursor.rowcount
        conn.commit()
        cursor.close()
        return affected > 0

    def list_all(self, tenant_id: str) -> list[Task]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, tenant_id, title, description, status, parent_id, created_at, updated_at, metadata, dependencies, children FROM tasks WHERE tenant_id = %s ORDER BY created_at",
            (tenant_id,)
        )
        rows = cursor.fetchall()
        cursor.close()
        return [self._row_to_task(row) for row in rows]

    def bulk_save(self, tasks: list[Task]) -> list[Task]:
        saved = []
        for task in tasks:
            saved.append(self.save(task))
        return saved

    def _row_to_task(self, row) -> Task:
        (task_id, tenant_id, title, description, status, parent_id,
         created_at, updated_at, metadata, dependencies, children) = row
        if isinstance(metadata, str):
            metadata = json.loads(metadata)
        if isinstance(dependencies, str):
            dependencies = json.loads(dependencies)
        if isinstance(children, str):
            children = json.loads(children)
        return Task(
            id=task_id,
            tenant_id=tenant_id,
            title=title,
            description=description or "",
            status=TaskStatus(status),
            parent_id=parent_id,
            created_at=created_at if isinstance(created_at, datetime) else datetime.fromisoformat(str(created_at)),
            updated_at=updated_at if isinstance(updated_at, datetime) else datetime.fromisoformat(str(updated_at)),
            metadata=metadata or {},
            dependencies=dependencies or [],
            children=children or [],
        )


class TodoToolset:
    def __init__(
        self,
        storage=None,
        tenant_id: str = "default",
        event_bus: Optional[EventBus] = None,
    ):
        self.storage = storage if storage is not None else InMemoryStorage()
        self.tenant_id = tenant_id
        self.event_bus = event_bus if event_bus is not None else EventBus()

    def _generate_id(self) -> str:
        return str(uuid.uuid4())

    def _publish_event(self, event_type: EventType, task: Task, extra_data: Optional[dict] = None) -> None:
        data = task.to_dict()
        if extra_data:
            data.update(extra_data)
        event = TaskEvent(
            event_type=event_type,
            task_id=task.id,
            tenant_id=task.tenant_id,
            data=data,
        )
        self.event_bus.publish(event)

    def list_tasks(self, hierarchical: bool = False) -> list[dict[str, Any]]:
        tasks = self.storage.list_all(self.tenant_id)
        if not hierarchical:
            return [t.to_dict() for t in tasks]
        task_map = {t.id: t.to_dict() for t in tasks}
        for t in tasks:
            task_map[t.id]["subtasks"] = []
        roots = []
        for t in tasks:
            if t.parent_id and t.parent_id in task_map:
                task_map[t.parent_id]["subtasks"].append(task_map[t.id])
            else:
                roots.append(task_map[t.id])
        return roots

    def add_task(
        self,
        title: str,
        description: str = "",
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        task = Task(
            id=self._generate_id(),
            title=title,
            description=description,
            status=TaskStatus.PENDING,
            tenant_id=self.tenant_id,
            metadata=metadata or {},
        )
        saved = self.storage.save(task)
        self._publish_event(EventType.TASK_CREATED, saved)
        return saved.to_dict()

    def bulk_write_tasks(self, tasks_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        tasks = []
        for data in tasks_data:
            task_id = data.get("id") or self._generate_id()
            existing = self.storage.get(task_id, self.tenant_id)
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
        saved_tasks = self.storage.bulk_save(tasks)
        results = []
        for task in saved_tasks:
            self._publish_event(EventType.TASK_UPDATED, task)
            results.append(task.to_dict())
        return results

    def update_task_status(self, task_id: str, status: str) -> Optional[dict[str, Any]]:
        task = self.storage.get(task_id, self.tenant_id)
        if task is None:
            return None
        old_status = task.status
        task.status = TaskStatus(status)
        task.updated_at = datetime.utcnow()
        saved = self.storage.save(task)
        self._publish_event(
            EventType.TASK_STATUS_CHANGED,
            saved,
            {"old_status": old_status.value, "new_status": task.status.value},
        )
        if task.status == TaskStatus.COMPLETED:
            self._publish_event(EventType.TASK_COMPLETED, saved)
        return saved.to_dict()

    def delete_task(self, task_id: str) -> bool:
        task = self.storage.get(task_id, self.tenant_id)
        if task is None:
            return False
        if task.parent_id:
            parent = self.storage.get(task.parent_id, self.tenant_id)
            if parent and task_id in parent.children:
                parent.children.remove(task_id)
                parent.updated_at = datetime.utcnow()
                self.storage.save(parent)
        for child_id in list(task.children):
            self._delete_task_recursive(child_id)
        all_tasks = self.storage.list_all(self.tenant_id)
        for t in all_tasks:
            if task_id in t.dependencies:
                t.dependencies.remove(task_id)
                t.updated_at = datetime.utcnow()
                self.storage.save(t)
        deleted = self.storage.delete(task_id, self.tenant_id)
        if deleted:
            event = TaskEvent(
                event_type=EventType.TASK_DELETED,
                task_id=task_id,
                tenant_id=self.tenant_id,
                data={"task_id": task_id},
            )
            self.event_bus.publish(event)
        return deleted

    def _delete_task_recursive(self, task_id: str) -> None:
        task = self.storage.get(task_id, self.tenant_id)
        if task is None:
            return
        for child_id in list(task.children):
            self._delete_task_recursive(child_id)
        self.storage.delete(task_id, self.tenant_id)

    def create_child_task(
        self,
        parent_id: str,
        title: str,
        description: str = "",
        metadata: Optional[dict[str, Any]] = None,
    ) -> Optional[dict[str, Any]]:
        parent = self.storage.get(parent_id, self.tenant_id)
        if parent is None:
            return None
        child = Task(
            id=self._generate_id(),
            title=title,
            description=description,
            status=TaskStatus.PENDING,
            parent_id=parent_id,
            tenant_id=self.tenant_id,
            metadata=metadata or {},
        )
        saved_child = self.storage.save(child)
        parent.children.append(saved_child.id)
        parent.updated_at = datetime.utcnow()
        self.storage.save(parent)
        self._publish_event(
            EventType.CHILD_TASK_CREATED,
            saved_child,
            {"parent_id": parent_id},
        )
        return saved_child.to_dict()

    def link_dependency(self, task_id: str, depends_on_id: str) -> Optional[dict[str, Any]]:
        task = self.storage.get(task_id, self.tenant_id)
        if task is None:
            return None
        dependency = self.storage.get(depends_on_id, self.tenant_id)
        if dependency is None:
            return None
        if depends_on_id not in task.dependencies:
            task.dependencies.append(depends_on_id)
            task.updated_at = datetime.utcnow()
            saved = self.storage.save(task)
            self._publish_event(
                EventType.DEPENDENCY_ADDED,
                saved,
                {"depends_on_id": depends_on_id},
            )
            return saved.to_dict()
        return task.to_dict()

    def list_ready_tasks(self) -> list[dict[str, Any]]:
        all_tasks = self.storage.list_all(self.tenant_id)
        completed_ids = {t.id for t in all_tasks if t.status == TaskStatus.COMPLETED}
        ready = []
        for task in all_tasks:
            if task.status not in (TaskStatus.PENDING, TaskStatus.BLOCKED):
                continue
            if all(dep_id in completed_ids for dep_id in task.dependencies):
                ready.append(task.to_dict())
        return ready

    def get_task(self, task_id: str) -> Optional[dict[str, Any]]:
        task = self.storage.get(task_id, self.tenant_id)
        if task is None:
            return None
        return task.to_dict()

    def get_tools(self) -> list:
        return [
            self.list_tasks,
            self.add_task,
            self.bulk_write_tasks,
            self.update_task_status,
            self.delete_task,
            self.create_child_task,
            self.link_dependency,
            self.list_ready_tasks,
            self.get_task,
        ]


class TodoToolsetFactory:
    @staticmethod
    def create_in_memory(tenant_id: str = "default", event_bus: Optional[EventBus] = None) -> TodoToolset:
        storage = InMemoryStorage()
        return TodoToolset(storage=storage, tenant_id=tenant_id, event_bus=event_bus)

    @staticmethod
    def create_postgresql(
        connection_string: str,
        tenant_id: str = "default",
        event_bus: Optional[EventBus] = None,
    ) -> TodoToolset:
        storage = PostgreSQLStorage(connection_string)
        return TodoToolset(storage=storage, tenant_id=tenant_id, event_bus=event_bus)


def create_todo_toolset(
    storage_type: str = "memory",
    connection_string: Optional[str] = None,
    tenant_id: str = "default",
    event_bus: Optional[EventBus] = None,
) -> TodoToolset:
    if storage_type == "postgresql":
        if not connection_string:
            raise ValueError("connection_string is required for PostgreSQL storage")
        return TodoToolsetFactory.create_postgresql(connection_string, tenant_id, event_bus)
    return TodoToolsetFactory.create_in_memory(tenant_id, event_bus)


if __name__ == "__main__":
    bus = EventBus()

    def on_event(event: TaskEvent):
        print(f"[EVENT] {event.event_type.value} - Task: {event.task_id}")

    bus.subscribe_all(on_event)

    toolset = create_todo_toolset(tenant_id="demo", event_bus=bus)

    print("=== Adding Tasks ===")
    task1 = toolset.add_task("Design database schema", "Create ERD and table definitions")
    task2 = toolset.add_task("Set up development environment", "Install dependencies and configure tools")
    task3 = toolset.add_task("Implement API endpoints", "Build REST API")

    print(f"Created: {task1['title']} ({task1['id']})")
    print(f"Created: {task2['title']} ({task2['id']})")
    print(f"Created: {task3['title']} ({task3['id']})")

    print("\n=== Creating Child Tasks ===")
    child1 = toolset.create_child_task(task1["id"], "Define users table", "User schema")
    child2 = toolset.create_child_task(task1["id"], "Define tasks table", "Tasks schema")
    print(f"Child: {child1['title']} under {task1['title']}")
    print(f"Child: {child2['title']} under {task1['title']}")

    print("\n=== Linking Dependencies ===")
    toolset.link_dependency(task3["id"], task1["id"])
    toolset.link_dependency(task3["id"], task2["id"])
    print(f"Task '{task3['title']}' depends on '{task1['title']}' and '{task2['title']}'")

    print("\n=== Ready Tasks (before completing dependencies) ===")
    ready = toolset.list_ready_tasks()
    for t in ready:
        print(f"  - {t['title']} (status: {t['status']})")

    print("\n=== Completing Dependencies ===")
    toolset.update_task_status(task1["id"], TaskStatus.COMPLETED.value)
    toolset.update_task_status(task2["id"], TaskStatus.COMPLETED.value)

    print("\n=== Ready Tasks (after completing dependencies) ===")
    ready = toolset.list_ready_tasks()
    for t in ready:
        print(f"  - {t['title']} (status: {t['status']})")

    print("\n=== Hierarchical Task List ===")
    all_tasks = toolset.list_tasks(hierarchical=True)
    for t in all_tasks:
        print(f"  [{t['status']}] {t['title']}")
        for sub in t.get("subtasks", []):
            print(f"    [{sub['status']}] {sub['title']}")

    print("\n=== Bulk Update ===")
    bulk_result = toolset.bulk_write_tasks([
        {"id": task3["id"], "status": TaskStatus.IN_PROGRESS.value},
    ])
    print(f"Bulk updated {len(bulk_result)} tasks")

    print("\n=== Delete Task ===")
    deleted = toolset.delete_task(task2["id"])
    print(f"Deleted task2: {deleted}")

    print("\n=== Final Task List ===")
    final_tasks = toolset.list_tasks()
    for t in final_tasks:
        print(f"  [{t['status']}] {t['title']} (id: {t['id'][:8]}...)")