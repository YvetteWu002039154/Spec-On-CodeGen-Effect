import uuid
import requests
from enum import Enum
from typing import List, Optional, Dict, Any, Callable
from pydantic import BaseModel, Field
import psycopg2
from psycopg2.extras import RealDictCursor

class TaskStatus(str, Enum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"

class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    title: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.TODO
    parent_id: Optional[str] = None
    subtasks: List['Task'] = Field(default_factory=list)

class EventSystem:
    def __init__(self):
        self._callbacks: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}
        self._webhooks: Dict[str, List[str]] = {}

    def subscribe_callback(self, event_type: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        if event_type not in self._callbacks:
            self._callbacks[event_type] = []
        self._callbacks[event_type].append(callback)

    def subscribe_webhook(self, event_type: str, url: str) -> None:
        if event_type not in self._webhooks:
            self._webhooks[event_type] = []
        self._webhooks[event_type].append(url)

    def emit(self, event_type: str, payload: Dict[str, Any]) -> None:
        for callback in self._callbacks.get(event_type, []):
            try:
                callback(payload)
            except Exception:
                pass
        
        for url in self._webhooks.get(event_type, []):
            try:
                requests.post(url, json={"event": event_type, "payload": payload}, timeout=5)
            except Exception:
                pass

class PostgresStorage:
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self._initialize_db()

    def _get_connection(self):
        return psycopg2.connect(self.connection_string, cursor_factory=RealDictCursor)

    def _initialize_db(self) -> None:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS tasks (
                        id UUID PRIMARY KEY,
                        tenant_id VARCHAR(255) NOT NULL,
                        title TEXT NOT NULL,
                        description TEXT,
                        status VARCHAR(50) NOT NULL,
                        parent_id UUID REFERENCES tasks(id) ON DELETE CASCADE
                    );
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS task_dependencies (
                        task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
                        depends_on_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
                        PRIMARY KEY (task_id, depends_on_id)
                    );
                """)
            conn.commit()

    def add_task(self, task: Task) -> Task:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO tasks (id, tenant_id, title, description, status, parent_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (task.id, task.tenant_id, task.title, task.description, task.status.value, task.parent_id))
            conn.commit()
        return task

    def get_task(self, tenant_id: str, task_id: str) -> Optional[Task]:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM tasks WHERE id = %s AND tenant_id = %s", (task_id, tenant_id))
                row = cur.fetchone()
                if not row:
                    return None
                row['id'] = str(row['id'])
                if row['parent_id']:
                    row['parent_id'] = str(row['parent_id'])
                return Task(**row)

    def update_task_status(self, tenant_id: str, task_id: str, status: TaskStatus) -> Optional[Task]:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE tasks SET status = %s WHERE id = %s AND tenant_id = %s RETURNING *
                """, (status.value, task_id, tenant_id))
                row = cur.fetchone()
                if not row:
                    return None
                row['id'] = str(row['id'])
                if row['parent_id']:
                    row['parent_id'] = str(row['parent_id'])
                task = Task(**row)
            conn.commit()
        return task

    def delete_task(self, tenant_id: str, task_id: str) -> bool:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM tasks WHERE id = %s AND tenant_id = %s", (task_id, tenant_id))
                deleted = cur.rowcount > 0
            conn.commit()
        return deleted

    def link_dependency(self, tenant_id: str, task_id: str, depends_on_id: str) -> None:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM tasks WHERE id IN (%s, %s) AND tenant_id = %s", (task_id, depends_on_id, tenant_id))
                if cur.rowcount != 2:
                    raise ValueError("Both tasks must exist and belong to the specified tenant.")
                cur.execute("""
                    INSERT INTO task_dependencies (task_id, depends_on_id)
                    VALUES (%s, %s) ON CONFLICT DO NOTHING
                """, (task_id, depends_on_id))
            conn.commit()

    def list_tasks(self, tenant_id: str) -> List[Task]:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM tasks WHERE tenant_id = %s", (tenant_id,))
                rows = cur.fetchall()
                tasks = []
                for row in rows:
                    row['id'] = str(row['id'])
                    if row['parent_id']:
                        row['parent_id'] = str(row['parent_id'])
                    tasks.append(Task(**row))
                return tasks

    def bulk_write_tasks(self, tenant_id: str, tasks: List[Task]) -> None:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                for task in tasks:
                    cur.execute("""
                        INSERT INTO tasks (id, tenant_id, title, description, status, parent_id)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET
                            title = EXCLUDED.title,
                            description = EXCLUDED.description,
                            status = EXCLUDED.status,
                            parent_id = EXCLUDED.parent_id
                    """, (task.id, tenant_id, task.title, task.description, task.status.value, task.parent_id))
            conn.commit()

    def list_ready_tasks(self, tenant_id: str) -> List[Task]:
        query = """
            SELECT t.* FROM tasks t
            WHERE t.tenant_id = %s AND t.status != 'DONE'
            AND NOT EXISTS (
                SELECT 1 FROM task_dependencies td
                JOIN tasks dep ON td.depends_on_id = dep.id
                WHERE td.task_id = t.id AND dep.status != 'DONE'
            )
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (tenant_id,))
                rows = cur.fetchall()
                tasks = []
                for row in rows:
                    row['id'] = str(row['id'])
                    if row['parent_id']:
                        row['parent_id'] = str(row['parent_id'])
                    tasks.append(Task(**row))
                return tasks

class TodoToolset:
    def __init__(self, db_connection_string: str):
        self.storage = PostgresStorage(db_connection_string)
        self.events = EventSystem()

    def list_tasks(self, tenant_id: str, hierarchical: bool = False) -> List[Task]:
        tasks = self.storage.list_tasks(tenant_id)
        if not hierarchical:
            return tasks
        
        task_dict = {task.id: task for task in tasks}
        root_tasks = []
        for task in tasks:
            if task.parent_id and task.parent_id in task_dict:
                task_dict[task.parent_id].subtasks.append(task)
            else:
                root_tasks.append(task)
        return root_tasks

    def bulk_write_tasks(self, tenant_id: str, tasks: List[Task]) -> None:
        for task in tasks:
            task.tenant_id = tenant_id
        self.storage.bulk_write_tasks(tenant_id, tasks)
        self.events.emit("tasks_bulk_written", {"tenant_id": tenant_id, "count": len(tasks)})

    def add_task(self, tenant_id: str, title: str, description: Optional[str] = None) -> Task:
        task = Task(tenant_id=tenant_id, title=title, description=description)
        created_task = self.storage.add_task(task)
        self.events.emit("task_created", created_task.model_dump())
        return created_task

    def update_task_status(self, tenant_id: str, task_id: str, status: TaskStatus) -> Task:
        updated_task = self.storage.update_task_status(tenant_id, task_id, status)
        if not updated_task:
            raise ValueError(f"Task {task_id} not found for tenant {tenant_id}")
        self.events.emit("task_updated", updated_task.model_dump())
        return updated_task

    def delete_task(self, tenant_id: str, task_id: str) -> bool:
        success = self.storage.delete_task(tenant_id, task_id)
        if success:
            self.events.emit("task_deleted", {"tenant_id": tenant_id, "task_id": task_id})
        return success

    def create_child_task(self, tenant_id: str, parent_id: str, title: str, description: Optional[str] = None) -> Task:
        parent_task = self.storage.get_task(tenant_id, parent_id)
        if not parent_task:
            raise ValueError(f"Parent task {parent_id} not found.")
        
        task = Task(tenant_id=tenant_id, title=title, description=description, parent_id=parent_id)
        created_task = self.storage.add_task(task)
        self.events.emit("child_task_created", created_task.model_dump())
        return created_task

    def link_dependency(self, tenant_id: str, task_id: str, depends_on_id: str) -> None:
        self.storage.link_dependency(tenant_id, task_id, depends_on_id)
        self.events.emit("dependency_linked", {
            "tenant_id": tenant_id,
            "task_id": task_id,
            "depends_on_id": depends_on_id
        })

    def list_ready_tasks(self, tenant_id: str) -> List[Task]:
        return self.storage.list_ready_tasks(tenant_id)