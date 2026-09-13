import json
import sqlite3
import urllib.request
import uuid
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    BLOCKED = "BLOCKED"


class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    title: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.TODO
    parent_id: Optional[str] = None
    dependencies: List[str] = Field(default_factory=list)


class EventSystem:
    def __init__(self) -> None:
        self.webhooks: List[str] = []
        self.callbacks: List[Callable[[Dict[str, Any]], None]] = []

    def register_webhook(self, url: str) -> None:
        self.webhooks.append(url)

    def register_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        self.callbacks.append(callback)

    def emit(self, event_name: str, payload: Dict[str, Any]) -> None:
        event_data = {"event": event_name, "payload": payload}
        
        for cb in self.callbacks:
            try:
                cb(event_data)
            except Exception:
                pass

        if self.webhooks:
            data_bytes = json.dumps(event_data).encode('utf-8')
            for url in self.webhooks:
                try:
                    req = urllib.request.Request(
                        url, 
                        data=data_bytes, 
                        headers={'Content-Type': 'application/json'}
                    )
                    urllib.request.urlopen(req, timeout=5)
                except Exception:
                    pass


class PostgresStorage:
    def __init__(self, connection_string: str = ":memory:") -> None:
        self.conn = sqlite3.connect(connection_string, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    status TEXT NOT NULL,
                    parent_id TEXT,
                    dependencies TEXT NOT NULL
                )
            """)
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_tenant ON tasks(tenant_id)")

    def _row_to_task(self, row: sqlite3.Row) -> Task:
        return Task(
            id=row["id"],
            tenant_id=row["tenant_id"],
            title=row["title"],
            description=row["description"],
            status=TaskStatus(row["status"]),
            parent_id=row["parent_id"],
            dependencies=json.loads(row["dependencies"])
        )

    def get_task(self, task_id: str, tenant_id: str) -> Optional[Task]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM tasks WHERE id = ? AND tenant_id = ?", (task_id, tenant_id))
        row = cur.fetchone()
        return self._row_to_task(row) if row else None

    def list_tasks(self, tenant_id: str) -> List[Task]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM tasks WHERE tenant_id = ?", (tenant_id,))
        return [self._row_to_task(row) for row in cur.fetchall()]

    def save_task(self, task: Task) -> None:
        with self.conn:
            self.conn.execute("""
                INSERT INTO tasks (id, tenant_id, title, description, status, parent_id, dependencies)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title=excluded.title,
                    description=excluded.description,
                    status=excluded.status,
                    parent_id=excluded.parent_id,
                    dependencies=excluded.dependencies
            """, (
                task.id, task.tenant_id, task.title, task.description,
                task.status.value, task.parent_id, json.dumps(task.dependencies)
            ))

    def bulk_save_tasks(self, tasks: List[Task]) -> None:
        with self.conn:
            self.conn.executemany("""
                INSERT INTO tasks (id, tenant_id, title, description, status, parent_id, dependencies)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title=excluded.title,
                    description=excluded.description,
                    status=excluded.status,
                    parent_id=excluded.parent_id,
                    dependencies=excluded.dependencies
            """, [(
                t.id, t.tenant_id, t.title, t.description,
                t.status.value, t.parent_id, json.dumps(t.dependencies)
            ) for t in tasks])

    def delete_task(self, task_id: str, tenant_id: str) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM tasks WHERE id = ? AND tenant_id = ?", (task_id, tenant_id))


class TodoToolset:
    def __init__(self, storage: PostgresStorage, event_system: EventSystem, tenant_id: str) -> None:
        self.storage = storage
        self.event_system = event_system
        self.tenant_id = tenant_id

    def list_all_tasks(self, hierarchical: bool = False) -> List[Any]:
        tasks = self.storage.list_tasks(self.tenant_id)
        if not hierarchical:
            return tasks

        task_dicts = {t.id: t.model_dump() | {"children": []} for t in tasks}
        root_tasks = []

        for t in tasks:
            if t.parent_id and t.parent_id in task_dicts:
                task_dicts[t.parent_id]["children"].append(task_dicts[t.id])
            else:
                root_tasks.append(task_dicts[t.id])

        return root_tasks

    def bulk_write_tasks(self, tasks: List[Task]) -> None:
        for t in tasks:
            if t.tenant_id != self.tenant_id:
                raise ValueError(f"Task {t.id} does not belong to tenant {self.tenant_id}")
        self.storage.bulk_save_tasks(tasks)
        self.event_system.emit("bulk_write", {"count": len(tasks), "tenant_id": self.tenant_id})

    def add_task(self, title: str, description: Optional[str] = None) -> Task:
        task = Task(tenant_id=self.tenant_id, title=title, description=description)
        self.storage.save_task(task)
        self.event_system.emit("task_added", task.model_dump())
        return task

    def update_task_status(self, task_id: str, status: TaskStatus) -> Task:
        task = self.storage.get_task(task_id, self.tenant_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        task.status = status
        self.storage.save_task(task)
        self.event_system.emit("task_status_updated", task.model_dump())
        return task

    def delete_task(self, task_id: str) -> None:
        task = self.storage.get_task(task_id, self.tenant_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        self.storage.delete_task(task_id, self.tenant_id)
        self.event_system.emit("task_deleted", {"id": task_id, "tenant_id": self.tenant_id})

    def create_child_task(self, parent_id: str, title: str, description: Optional[str] = None) -> Task:
        parent = self.storage.get_task(parent_id, self.tenant_id)
        if not parent:
            raise ValueError(f"Parent task {parent_id} not found")
        child = Task(tenant_id=self.tenant_id, title=title, description=description, parent_id=parent_id)
        self.storage.save_task(child)
        self.event_system.emit("child_task_created", child.model_dump())
        return child

    def link_tasks(self, task_id: str, depends_on_id: str) -> None:
        task = self.storage.get_task(task_id, self.tenant_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        depends_on = self.storage.get_task(depends_on_id, self.tenant_id)
        if not depends_on:
            raise ValueError(f"Dependency task {depends_on_id} not found")

        if depends_on_id not in task.dependencies:
            task.dependencies.append(depends_on_id)
            self.storage.save_task(task)
            self.event_system.emit("tasks_linked", {"task_id": task_id, "depends_on_id": depends_on_id})

    def list_ready_tasks(self) -> List[Task]:
        tasks = self.storage.list_tasks(self.tenant_id)
        task_status_map = {t.id: t.status for t in tasks}
        ready_tasks = []

        for t in tasks:
            if t.status == TaskStatus.DONE:
                continue
            
            is_ready = True
            for dep_id in t.dependencies:
                if task_status_map.get(dep_id) != TaskStatus.DONE:
                    is_ready = False
                    break
            
            if is_ready:
                ready_tasks.append(t)

        return ready_tasks