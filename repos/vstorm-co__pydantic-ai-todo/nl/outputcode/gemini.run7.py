import sqlite3
import json
import uuid
import urllib.request
from enum import Enum
from typing import List, Optional, Dict, Callable
from pydantic import BaseModel, Field

class TaskStatus(str, Enum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"

class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    title: str
    description: str = ""
    status: TaskStatus = TaskStatus.TODO
    parent_id: Optional[str] = None
    dependencies: List[str] = Field(default_factory=list)
    subtasks: List['Task'] = Field(default_factory=list)

class EventSystem:
    def __init__(self):
        self.callbacks: Dict[str, List[Callable]] = {}
        self.webhooks: Dict[str, List[str]] = {}

    def register_callback(self, event_type: str, callback: Callable) -> None:
        if event_type not in self.callbacks:
            self.callbacks[event_type] = []
        self.callbacks[event_type].append(callback)

    def register_webhook(self, event_type: str, url: str) -> None:
        if event_type not in self.webhooks:
            self.webhooks[event_type] = []
        self.webhooks[event_type].append(url)

    def trigger(self, event_type: str, payload: dict) -> None:
        for cb in self.callbacks.get(event_type, []):
            try:
                cb(payload)
            except Exception:
                pass
        
        for url in self.webhooks.get(event_type, []):
            try:
                req = urllib.request.Request(
                    url, 
                    data=json.dumps(payload).encode('utf-8'),
                    headers={'Content-Type': 'application/json'}
                )
                urllib.request.urlopen(req, timeout=5)
            except Exception:
                pass

class PostgresStorage:
    def __init__(self, connection_string: str = ":memory:"):
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
                    description TEXT NOT NULL,
                    status TEXT NOT NULL,
                    parent_id TEXT
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS task_dependencies (
                    task_id TEXT NOT NULL,
                    depends_on_id TEXT NOT NULL,
                    PRIMARY KEY (task_id, depends_on_id)
                )
            """)

    def get_tasks(self, tenant_id: str) -> List[Task]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE tenant_id = ?", (tenant_id,))
        rows = cursor.fetchall()
        
        tasks = []
        for row in rows:
            cursor.execute("SELECT depends_on_id FROM task_dependencies WHERE task_id = ?", (row['id'],))
            deps = [r['depends_on_id'] for r in cursor.fetchall()]
            tasks.append(Task(
                id=row['id'],
                tenant_id=row['tenant_id'],
                title=row['title'],
                description=row['description'],
                status=TaskStatus(row['status']),
                parent_id=row['parent_id'],
                dependencies=deps
            ))
        return tasks

    def get_task(self, tenant_id: str, task_id: str) -> Optional[Task]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE tenant_id = ? AND id = ?", (tenant_id, task_id))
        row = cursor.fetchone()
        if not row:
            return None
        
        cursor.execute("SELECT depends_on_id FROM task_dependencies WHERE task_id = ?", (task_id,))
        deps = [r['depends_on_id'] for r in cursor.fetchall()]
        
        return Task(
            id=row['id'],
            tenant_id=row['tenant_id'],
            title=row['title'],
            description=row['description'],
            status=TaskStatus(row['status']),
            parent_id=row['parent_id'],
            dependencies=deps
        )

    def save_task(self, task: Task) -> None:
        with self.conn:
            self.conn.execute("""
                INSERT INTO tasks (id, tenant_id, title, description, status, parent_id)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title=excluded.title,
                    description=excluded.description,
                    status=excluded.status,
                    parent_id=excluded.parent_id
            """, (task.id, task.tenant_id, task.title, task.description, task.status.value, task.parent_id))
            
            self.conn.execute("DELETE FROM task_dependencies WHERE task_id = ?", (task.id,))
            for dep in task.dependencies:
                self.conn.execute("""
                    INSERT INTO task_dependencies (task_id, depends_on_id)
                    VALUES (?, ?)
                """, (task.id, dep))

    def delete_task(self, tenant_id: str, task_id: str) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM task_dependencies WHERE task_id = ?", (task_id,))
            self.conn.execute("DELETE FROM task_dependencies WHERE depends_on_id = ?", (task_id,))
            self.conn.execute("DELETE FROM tasks WHERE tenant_id = ? AND id = ?", (tenant_id, task_id))

    def get_ready_tasks(self, tenant_id: str) -> List[Task]:
        cursor = self.conn.cursor()
        query = """
            SELECT t.* FROM tasks t
            WHERE t.tenant_id = ? AND t.status != 'DONE'
            AND NOT EXISTS (
                SELECT 1 FROM task_dependencies td
                JOIN tasks dep ON td.depends_on_id = dep.id
                WHERE td.task_id = t.id AND dep.status != 'DONE'
            )
        """
        cursor.execute(query, (tenant_id,))
        rows = cursor.fetchall()
        
        tasks = []
        for row in rows:
            cursor.execute("SELECT depends_on_id FROM task_dependencies WHERE task_id = ?", (row['id'],))
            deps = [r['depends_on_id'] for r in cursor.fetchall()]
            tasks.append(Task(
                id=row['id'],
                tenant_id=row['tenant_id'],
                title=row['title'],
                description=row['description'],
                status=TaskStatus(row['status']),
                parent_id=row['parent_id'],
                dependencies=deps
            ))
        return tasks

class TodoToolset:
    def __init__(self, storage: PostgresStorage, event_system: EventSystem):
        self.storage = storage
        self.events = event_system

    def list_tasks(self, tenant_id: str, hierarchical: bool = False) -> List[Task]:
        tasks = self.storage.get_tasks(tenant_id)
        if not hierarchical:
            return tasks
        
        task_map = {task.id: task for task in tasks}
        root_tasks = []
        
        for task in tasks:
            if task.parent_id and task.parent_id in task_map:
                task_map[task.parent_id].subtasks.append(task)
            else:
                root_tasks.append(task)
                
        return root_tasks

    def bulk_write_tasks(self, tenant_id: str, tasks: List[Task]) -> None:
        for task in tasks:
            if task.tenant_id != tenant_id:
                raise ValueError(f"Task {task.id} does not belong to tenant {tenant_id}")
            self.storage.save_task(task)
            self.events.trigger("task_updated", task.model_dump())

    def add_task(self, tenant_id: str, title: str, description: str = "") -> Task:
        task = Task(tenant_id=tenant_id, title=title, description=description)
        self.storage.save_task(task)
        self.events.trigger("task_created", task.model_dump())
        return task

    def update_task_status(self, tenant_id: str, task_id: str, status: TaskStatus) -> Task:
        task = self.storage.get_task(tenant_id, task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        task.status = status
        self.storage.save_task(task)
        self.events.trigger("task_updated", task.model_dump())
        return task

    def delete_task(self, tenant_id: str, task_id: str) -> None:
        task = self.storage.get_task(tenant_id, task_id)
        if task:
            self.storage.delete_task(tenant_id, task_id)
            self.events.trigger("task_deleted", {"id": task_id, "tenant_id": tenant_id})

    def create_child_task(self, tenant_id: str, parent_id: str, title: str, description: str = "") -> Task:
        parent_task = self.storage.get_task(tenant_id, parent_id)
        if not parent_task:
            raise ValueError(f"Parent task {parent_id} not found")
            
        child_task = Task(
            tenant_id=tenant_id,
            title=title,
            description=description,
            parent_id=parent_id
        )
        self.storage.save_task(child_task)
        self.events.trigger("task_created", child_task.model_dump())
        return child_task

    def link_tasks(self, tenant_id: str, task_id: str, depends_on_id: str) -> None:
        task = self.storage.get_task(tenant_id, task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
            
        depends_on_task = self.storage.get_task(tenant_id, depends_on_id)
        if not depends_on_task:
            raise ValueError(f"Dependency task {depends_on_id} not found")
            
        if depends_on_id not in task.dependencies:
            task.dependencies.append(depends_on_id)
            self.storage.save_task(task)
            self.events.trigger("task_updated", task.model_dump())

    def list_ready_tasks(self, tenant_id: str) -> List[Task]:
        return self.storage.get_ready_tasks(tenant_id)