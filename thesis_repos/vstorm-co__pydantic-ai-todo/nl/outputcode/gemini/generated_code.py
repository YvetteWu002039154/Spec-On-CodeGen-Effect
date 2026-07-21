import json
import urllib.request
import psycopg2
from psycopg2.extras import RealDictCursor
from enum import Enum
from typing import List, Optional, Callable, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime, timezone
from pydantic import BaseModel, Field

class TaskStatus(str, Enum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"

class Task(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    tenant_id: str
    title: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.TODO
    parent_id: Optional[UUID] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    children: List['Task'] = Field(default_factory=list)
    dependencies: List[UUID] = Field(default_factory=list)

Task.model_rebuild()

class EventSystem:
    def __init__(self):
        self._callbacks: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}
        self._webhooks: Dict[str, List[str]] = {}

    def register_callback(self, event: str, func: Callable[[Dict[str, Any]], None]) -> None:
        self._callbacks.setdefault(event, []).append(func)

    def register_webhook(self, event: str, url: str) -> None:
        self._webhooks.setdefault(event, []).append(url)

    def emit(self, event: str, data: Dict[str, Any]) -> None:
        for cb in self._callbacks.get(event, []):
            try:
                cb(data)
            except Exception:
                pass

        for url in self._webhooks.get(event, []):
            try:
                payload = json.dumps(data, default=str).encode('utf-8')
                req = urllib.request.Request(
                    url, 
                    data=payload, 
                    headers={'Content-Type': 'application/json'}
                )
                urllib.request.urlopen(req, timeout=5)
            except Exception:
                pass

class PostgresStorage:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self._init_db()

    def _get_conn(self):
        return psycopg2.connect(self.dsn, cursor_factory=RealDictCursor)

    def _init_db(self) -> None:
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS tasks (
                        id UUID PRIMARY KEY,
                        tenant_id VARCHAR(255) NOT NULL,
                        title VARCHAR(255) NOT NULL,
                        description TEXT,
                        status VARCHAR(50) NOT NULL,
                        parent_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
                        created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                        updated_at TIMESTAMP WITH TIME ZONE NOT NULL
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

    def get_tasks(self, tenant_id: str) -> List[Task]:
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM tasks WHERE tenant_id = %s", (tenant_id,))
                rows = cur.fetchall()

                cur.execute("""
                    SELECT td.task_id, td.depends_on_id
                    FROM task_dependencies td
                    JOIN tasks t ON t.id = td.task_id
                    WHERE t.tenant_id = %s
                """, (tenant_id,))
                dep_rows = cur.fetchall()

        deps_map: Dict[UUID, List[UUID]] = {}
        for row in dep_rows:
            deps_map.setdefault(row['task_id'], []).append(row['depends_on_id'])

        tasks = []
        for row in rows:
            task_data = dict(row)
            task_data['dependencies'] = deps_map.get(task_data['id'], [])
            tasks.append(Task(**task_data))
        return tasks

    def get_task(self, task_id: UUID, tenant_id: str) -> Optional[Task]:
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM tasks WHERE id = %s AND tenant_id = %s", (task_id, tenant_id))
                row = cur.fetchone()
                if not row:
                    return None
                
                cur.execute("SELECT depends_on_id FROM task_dependencies WHERE task_id = %s", (task_id,))
                dep_rows = cur.fetchall()
                
        task_data = dict(row)
        task_data['dependencies'] = [r['depends_on_id'] for r in dep_rows]
        return Task(**task_data)

    def save_task(self, task: Task) -> None:
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO tasks (id, tenant_id, title, description, status, parent_id, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        title = EXCLUDED.title,
                        description = EXCLUDED.description,
                        status = EXCLUDED.status,
                        parent_id = EXCLUDED.parent_id,
                        updated_at = EXCLUDED.updated_at;
                """, (
                    task.id, task.tenant_id, task.title, task.description, 
                    task.status.value, task.parent_id, task.created_at, task.updated_at
                ))
                
                cur.execute("DELETE FROM task_dependencies WHERE task_id = %s", (task.id,))
                for dep_id in task.dependencies:
                    cur.execute("""
                        INSERT INTO task_dependencies (task_id, depends_on_id)
                        VALUES (%s, %s)
                        ON CONFLICT DO NOTHING;
                    """, (task.id, dep_id))
            conn.commit()

    def delete_task(self, task_id: UUID, tenant_id: str) -> None:
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM tasks WHERE id = %s AND tenant_id = %s", (task_id, tenant_id))
            conn.commit()

    def add_dependency(self, task_id: UUID, depends_on_id: UUID) -> None:
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO task_dependencies (task_id, depends_on_id)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING;
                """, (task_id, depends_on_id))
            conn.commit()

class TodoToolset:
    def __init__(self, db_dsn: str):
        self.storage = PostgresStorage(db_dsn)
        self.events = EventSystem()

    def list_tasks(self, tenant_id: str, hierarchical: bool = False) -> List[Task]:
        tasks = self.storage.get_tasks(tenant_id)
        if not hierarchical:
            return tasks

        task_map = {t.id: t for t in tasks}
        root_tasks = []
        
        for t in tasks:
            if t.parent_id and t.parent_id in task_map:
                task_map[t.parent_id].children.append(t)
            else:
                root_tasks.append(t)
                
        return root_tasks

    def bulk_write_tasks(self, tenant_id: str, tasks: List[Task]) -> List[Task]:
        for task in tasks:
            task.tenant_id = tenant_id
            task.updated_at = datetime.now(timezone.utc)
            self.storage.save_task(task)
            
        self.events.emit("tasks_bulk_updated", {
            "tenant_id": tenant_id, 
            "count": len(tasks)
        })
        return tasks

    def add_task(self, tenant_id: str, title: str, description: Optional[str] = None) -> Task:
        task = Task(tenant_id=tenant_id, title=title, description=description)
        self.storage.save_task(task)
        self.events.emit("task_created", task.model_dump(mode='json'))
        return task

    def update_task_status(self, tenant_id: str, task_id: UUID, status: TaskStatus) -> Optional[Task]:
        task = self.storage.get_task(task_id, tenant_id)
        if task:
            task.status = status
            task.updated_at = datetime.now(timezone.utc)
            self.storage.save_task(task)
            self.events.emit("task_updated", task.model_dump(mode='json'))
        return task

    def delete_task(self, tenant_id: str, task_id: UUID) -> None:
        self.storage.delete_task(task_id, tenant_id)
        self.events.emit("task_deleted", {
            "task_id": str(task_id), 
            "tenant_id": tenant_id
        })

    def create_child_task(self, tenant_id: str, parent_id: UUID, title: str, description: Optional[str] = None) -> Task:
        task = Task(
            tenant_id=tenant_id, 
            title=title, 
            description=description, 
            parent_id=parent_id
        )
        self.storage.save_task(task)
        self.events.emit("task_created", task.model_dump(mode='json'))
        return task

    def link_tasks(self, tenant_id: str, task_id: UUID, depends_on_id: UUID) -> None:
        task = self.storage.get_task(task_id, tenant_id)
        if task:
            self.storage.add_dependency(task_id, depends_on_id)
            self.events.emit("tasks_linked", {
                "tenant_id": tenant_id,
                "task_id": str(task_id), 
                "depends_on_id": str(depends_on_id)
            })

    def list_ready_tasks(self, tenant_id: str) -> List[Task]:
        tasks = self.storage.get_tasks(tenant_id)
        task_map = {t.id: t for t in tasks}
        ready_tasks = []
        
        for t in tasks:
            if t.status == TaskStatus.COMPLETED:
                continue
                
            dependencies_met = True
            for dep_id in t.dependencies:
                dep_task = task_map.get(dep_id)
                if dep_task and dep_task.status != TaskStatus.COMPLETED:
                    dependencies_met = False
                    break
                    
            if dependencies_met:
                ready_tasks.append(t)
                
        return ready_tasks