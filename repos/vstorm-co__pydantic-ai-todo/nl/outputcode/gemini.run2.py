import json
import uuid
import urllib.request
from enum import Enum
from typing import List, Optional, Dict, Any, Callable
from datetime import datetime, timezone
from pydantic import BaseModel, Field
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor

class TaskStatus(str, Enum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    BLOCKED = "BLOCKED"

class EventType(str, Enum):
    TASK_CREATED = "TASK_CREATED"
    TASK_UPDATED = "TASK_UPDATED"
    TASK_DELETED = "TASK_DELETED"

class Task(BaseModel):
    id: str
    tenant_id: str
    title: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.TODO
    parent_id: Optional[str] = None
    dependencies: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    children: List['Task'] = Field(default_factory=list)

class EventManager:
    def __init__(self):
        self.callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self.webhooks: List[str] = []

    def register_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        self.callbacks.append(callback)

    def register_webhook(self, url: str) -> None:
        self.webhooks.append(url)

    def dispatch(self, event_type: EventType, tenant_id: str, task: Task) -> None:
        payload = {
            "event": event_type.value,
            "tenant_id": tenant_id,
            "task": task.model_dump(mode='json')
        }
        
        for cb in self.callbacks:
            try:
                cb(payload)
            except Exception:
                pass
                
        if self.webhooks:
            data = json.dumps(payload).encode('utf-8')
            headers = {'Content-Type': 'application/json'}
            for url in self.webhooks:
                try:
                    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
                    urllib.request.urlopen(req, timeout=5)
                except Exception:
                    pass

class PostgresStorage:
    def __init__(self, dsn: str):
        self.pool = psycopg2.pool.SimpleConnectionPool(1, 10, dsn)
        self._init_db()

    def _init_db(self) -> None:
        conn = self.pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS tasks (
                        id VARCHAR(36) PRIMARY KEY,
                        tenant_id VARCHAR(255) NOT NULL,
                        title TEXT NOT NULL,
                        description TEXT,
                        status VARCHAR(50) NOT NULL,
                        parent_id VARCHAR(36),
                        dependencies JSONB NOT NULL DEFAULT '[]',
                        created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                        updated_at TIMESTAMP WITH TIME ZONE NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS idx_tasks_tenant ON tasks(tenant_id);
                """)
            conn.commit()
        finally:
            self.pool.putconn(conn)

    def _row_to_task(self, row: dict) -> Task:
        deps = row['dependencies']
        if isinstance(deps, str):
            deps = json.loads(deps)
            
        return Task(
            id=row['id'],
            tenant_id=row['tenant_id'],
            title=row['title'],
            description=row['description'],
            status=TaskStatus(row['status']),
            parent_id=row['parent_id'],
            dependencies=deps,
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )

    def get_all_tasks(self, tenant_id: str) -> List[Task]:
        conn = self.pool.getconn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM tasks WHERE tenant_id = %s ORDER BY created_at ASC", (tenant_id,))
                return [self._row_to_task(row) for row in cur.fetchall()]
        finally:
            self.pool.putconn(conn)

    def get_task(self, tenant_id: str, task_id: str) -> Optional[Task]:
        conn = self.pool.getconn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM tasks WHERE tenant_id = %s AND id = %s", (tenant_id, task_id))
                row = cur.fetchone()
                return self._row_to_task(row) if row else None
        finally:
            self.pool.putconn(conn)

    def save_task(self, task: Task) -> None:
        conn = self.pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO tasks (id, tenant_id, title, description, status, parent_id, dependencies, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    task.id, task.tenant_id, task.title, task.description, 
                    task.status.value, task.parent_id, json.dumps(task.dependencies), 
                    task.created_at, task.updated_at
                ))
            conn.commit()
        finally:
            self.pool.putconn(conn)

    def update_task(self, task: Task) -> None:
        conn = self.pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE tasks SET
                        title = %s, description = %s, status = %s, 
                        parent_id = %s, dependencies = %s, updated_at = %s
                    WHERE id = %s AND tenant_id = %s
                """, (
                    task.title, task.description, task.status.value, 
                    task.parent_id, json.dumps(task.dependencies), task.updated_at,
                    task.id, task.tenant_id
                ))
            conn.commit()
        finally:
            self.pool.putconn(conn)

    def delete_task(self, tenant_id: str, task_id: str) -> None:
        conn = self.pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM tasks WHERE id = %s AND tenant_id = %s", (task_id, tenant_id))
            conn.commit()
        finally:
            self.pool.putconn(conn)

    def save_tasks_bulk(self, tasks: List[Task]) -> None:
        if not tasks:
            return
        conn = self.pool.getconn()
        try:
            with conn.cursor() as cur:
                for task in tasks:
                    cur.execute("""
                        INSERT INTO tasks (id, tenant_id, title, description, status, parent_id, dependencies, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET
                            title = EXCLUDED.title,
                            description = EXCLUDED.description,
                            status = EXCLUDED.status,
                            parent_id = EXCLUDED.parent_id,
                            dependencies = EXCLUDED.dependencies,
                            updated_at = EXCLUDED.updated_at
                    """, (
                        task.id, task.tenant_id, task.title, task.description, 
                        task.status.value, task.parent_id, json.dumps(task.dependencies), 
                        task.created_at, task.updated_at
                    ))
            conn.commit()
        finally:
            self.pool.putconn(conn)

class TodoToolset:
    def __init__(self, db_dsn: str):
        self.storage = PostgresStorage(db_dsn)
        self.events = EventManager()

    def _generate_id(self) -> str:
        return str(uuid.uuid4())

    def list_tasks(self, tenant_id: str, hierarchical: bool = False) -> List[Task]:
        tasks = self.storage.get_all_tasks(tenant_id)
        if not hierarchical:
            return tasks
        
        task_map = {t.id: t for t in tasks}
        roots = []
        for t in tasks:
            if t.parent_id and t.parent_id in task_map:
                task_map[t.parent_id].children.append(t)
            else:
                roots.append(t)
        return roots

    def add_task(self, tenant_id: str, title: str, description: Optional[str] = None, parent_id: Optional[str] = None) -> Task:
        if parent_id and not self.storage.get_task(tenant_id, parent_id):
            raise ValueError(f"Parent task {parent_id} does not exist.")
            
        task = Task(
            id=self._generate_id(),
            tenant_id=tenant_id,
            title=title,
            description=description,
            parent_id=parent_id
        )
        self.storage.save_task(task)
        self.events.dispatch(EventType.TASK_CREATED, tenant_id, task)
        return task

    def bulk_write_tasks(self, tenant_id: str, tasks_data: List[Dict[str, Any]]) -> List[Task]:
        tasks = []
        for data in tasks_data:
            task_id = data.get("id", self._generate_id())
            task = Task(
                id=task_id,
                tenant_id=tenant_id,
                title=data["title"],
                description=data.get("description"),
                status=TaskStatus(data.get("status", TaskStatus.TODO.value)),
                parent_id=data.get("parent_id"),
                dependencies=data.get("dependencies", [])
            )
            tasks.append(task)
            
        self.storage.save_tasks_bulk(tasks)
        
        for t in tasks:
            self.events.dispatch(EventType.TASK_UPDATED, tenant_id, t)
            
        return tasks

    def update_task_status(self, tenant_id: str, task_id: str, status: TaskStatus) -> Task:
        task = self.storage.get_task(tenant_id, task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
            
        task.status = status
        task.updated_at = datetime.now(timezone.utc)
        self.storage.update_task(task)
        self.events.dispatch(EventType.TASK_UPDATED, tenant_id, task)
        return task

    def delete_task(self, tenant_id: str, task_id: str) -> None:
        task = self.storage.get_task(tenant_id, task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
            
        self.storage.delete_task(tenant_id, task_id)
        self.events.dispatch(EventType.TASK_DELETED, tenant_id, task)

    def create_child_task(self, tenant_id: str, parent_id: str, title: str, description: Optional[str] = None) -> Task:
        parent = self.storage.get_task(tenant_id, parent_id)
        if not parent:
            raise ValueError(f"Parent task {parent_id} not found")
            
        return self.add_task(tenant_id, title, description, parent_id)

    def link_tasks(self, tenant_id: str, task_id: str, depends_on_id: str) -> Task:
        task = self.storage.get_task(tenant_id, task_id)
        depends_on = self.storage.get_task(tenant_id, depends_on_id)
        
        if not task:
            raise ValueError(f"Task {task_id} not found")
        if not depends_on:
            raise ValueError(f"Dependency task {depends_on_id} not found")
            
        if depends_on_id not in task.dependencies:
            task.dependencies.append(depends_on_id)
            task.updated_at = datetime.now(timezone.utc)
            self.storage.update_task(task)
            self.events.dispatch(EventType.TASK_UPDATED, tenant_id, task)
            
        return task

    def list_ready_tasks(self, tenant_id: str) -> List[Task]:
        tasks = self.storage.get_all_tasks(tenant_id)
        task_map = {t.id: t for t in tasks}
        ready_tasks = []
        
        for t in tasks:
            if t.status != TaskStatus.TODO:
                continue
                
            is_ready = True
            for dep_id in t.dependencies:
                dep_task = task_map.get(dep_id)
                if not dep_task or dep_task.status != TaskStatus.DONE:
                    is_ready = False
                    break
                    
            if is_ready:
                ready_tasks.append(t)
                
        return ready_tasks