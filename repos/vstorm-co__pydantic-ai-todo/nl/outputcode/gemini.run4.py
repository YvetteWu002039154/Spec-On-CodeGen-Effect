import uuid
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from enum import Enum
from typing import List, Optional, Dict, Any, Callable, Union
from pydantic import BaseModel, Field
from abc import ABC, abstractmethod

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
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    title: str
    description: str = ""
    status: TaskStatus = TaskStatus.TODO
    parent_id: Optional[str] = None
    dependencies: List[str] = Field(default_factory=list)

class Storage(ABC):
    @abstractmethod
    def get_tasks(self, tenant_id: str) -> List[Task]:
        pass

    @abstractmethod
    def get_task(self, tenant_id: str, task_id: str) -> Optional[Task]:
        pass

    @abstractmethod
    def save_task(self, task: Task) -> None:
        pass

    @abstractmethod
    def delete_task(self, tenant_id: str, task_id: str) -> None:
        pass

class PostgresStorage(Storage):
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
                        id VARCHAR(36) PRIMARY KEY,
                        tenant_id VARCHAR(255) NOT NULL,
                        title TEXT NOT NULL,
                        description TEXT,
                        status VARCHAR(50) NOT NULL,
                        parent_id VARCHAR(36)
                    );
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS task_dependencies (
                        task_id VARCHAR(36) NOT NULL,
                        dependency_id VARCHAR(36) NOT NULL,
                        PRIMARY KEY (task_id, dependency_id),
                        FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
                    );
                """)
            conn.commit()

    def get_tasks(self, tenant_id: str) -> List[Task]:
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM tasks WHERE tenant_id = %s", (tenant_id,))
                rows = cur.fetchall()
                
                cur.execute("""
                    SELECT td.task_id, td.dependency_id 
                    FROM task_dependencies td
                    JOIN tasks t ON t.id = td.task_id
                    WHERE t.tenant_id = %s
                """, (tenant_id,))
                dep_rows = cur.fetchall()
                
        deps_by_task: Dict[str, List[str]] = {}
        for row in dep_rows:
            deps_by_task.setdefault(row['task_id'], []).append(row['dependency_id'])
            
        tasks = []
        for row in rows:
            task_data = dict(row)
            task_data['dependencies'] = deps_by_task.get(row['id'], [])
            tasks.append(Task(**task_data))
        return tasks

    def get_task(self, tenant_id: str, task_id: str) -> Optional[Task]:
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM tasks WHERE tenant_id = %s AND id = %s", (tenant_id, task_id))
                row = cur.fetchone()
                if not row:
                    return None
                
                cur.execute("SELECT dependency_id FROM task_dependencies WHERE task_id = %s", (task_id,))
                dep_rows = cur.fetchall()
                
        task_data = dict(row)
        task_data['dependencies'] = [r['dependency_id'] for r in dep_rows]
        return Task(**task_data)

    def save_task(self, task: Task) -> None:
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO tasks (id, tenant_id, title, description, status, parent_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        title = EXCLUDED.title,
                        description = EXCLUDED.description,
                        status = EXCLUDED.status,
                        parent_id = EXCLUDED.parent_id
                """, (task.id, task.tenant_id, task.title, task.description, task.status.value, task.parent_id))
                
                cur.execute("DELETE FROM task_dependencies WHERE task_id = %s", (task.id,))
                for dep_id in task.dependencies:
                    cur.execute("""
                        INSERT INTO task_dependencies (task_id, dependency_id)
                        VALUES (%s, %s)
                    """, (task.id, dep_id))
            conn.commit()

    def delete_task(self, tenant_id: str, task_id: str) -> None:
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM tasks WHERE tenant_id = %s AND id = %s", (tenant_id, task_id))
            conn.commit()

class EventManager:
    def __init__(self):
        self.callbacks: Dict[EventType, List[Callable[[Dict[str, Any]], None]]] = {e: [] for e in EventType}
        self.webhooks: Dict[EventType, List[str]] = {e: [] for e in EventType}

    def register_callback(self, event_type: EventType, callback: Callable[[Dict[str, Any]], None]) -> None:
        self.callbacks[event_type].append(callback)

    def register_webhook(self, event_type: EventType, url: str) -> None:
        self.webhooks[event_type].append(url)

    def emit(self, event_type: EventType, payload: Dict[str, Any]) -> None:
        for cb in self.callbacks[event_type]:
            try:
                cb(payload)
            except Exception:
                pass
        
        for url in self.webhooks[event_type]:
            try:
                requests.post(url, json={"event": event_type.value, "payload": payload}, timeout=5)
            except Exception:
                pass

class TodoToolset:
    def __init__(self, storage: Storage, event_manager: EventManager, tenant_id: str):
        self.storage = storage
        self.event_manager = event_manager
        self.tenant_id = tenant_id

    def list_all_tasks(self, hierarchical: bool = False) -> Union[List[Task], List[Dict[str, Any]]]:
        tasks = self.storage.get_tasks(self.tenant_id)
        if not hierarchical:
            return tasks

        task_dict = {t.id: t.model_dump() for t in tasks}
        for t in task_dict.values():
            t['subtasks'] = []

        hierarchy = []
        for t in tasks:
            if t.parent_id and t.parent_id in task_dict:
                task_dict[t.parent_id]['subtasks'].append(task_dict[t.id])
            else:
                hierarchy.append(task_dict[t.id])
                
        return hierarchy

    def bulk_write_tasks(self, tasks: List[Task]) -> None:
        for task in tasks:
            if task.tenant_id != self.tenant_id:
                raise ValueError(f"Task {task.id} does not belong to tenant {self.tenant_id}")
            self.storage.save_task(task)
            self.event_manager.emit(EventType.TASK_UPDATED, task.model_dump())

    def add_task(self, title: str, description: str = "") -> Task:
        task = Task(tenant_id=self.tenant_id, title=title, description=description)
        self.storage.save_task(task)
        self.event_manager.emit(EventType.TASK_CREATED, task.model_dump())
        return task

    def update_task_status(self, task_id: str, status: TaskStatus) -> Task:
        task = self.storage.get_task(self.tenant_id, task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        task.status = status
        self.storage.save_task(task)
        self.event_manager.emit(EventType.TASK_UPDATED, task.model_dump())
        return task

    def delete_task(self, task_id: str) -> None:
        task = self.storage.get_task(self.tenant_id, task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
            
        self.storage.delete_task(self.tenant_id, task_id)
        self.event_manager.emit(EventType.TASK_DELETED, {"id": task_id, "tenant_id": self.tenant_id})

    def create_child_task(self, parent_id: str, title: str, description: str = "") -> Task:
        parent = self.storage.get_task(self.tenant_id, parent_id)
        if not parent:
            raise ValueError(f"Parent task {parent_id} not found")
            
        task = Task(tenant_id=self.tenant_id, title=title, description=description, parent_id=parent_id)
        self.storage.save_task(task)
        self.event_manager.emit(EventType.TASK_CREATED, task.model_dump())
        return task

    def link_dependency(self, task_id: str, dependency_id: str) -> Task:
        task = self.storage.get_task(self.tenant_id, task_id)
        dep = self.storage.get_task(self.tenant_id, dependency_id)
        
        if not task or not dep:
            raise ValueError("Task or dependency not found")
            
        if dependency_id not in task.dependencies:
            task.dependencies.append(dependency_id)
            self.storage.save_task(task)
            self.event_manager.emit(EventType.TASK_UPDATED, task.model_dump())
            
        return task

    def list_ready_tasks(self) -> List[Task]:
        tasks = self.storage.get_tasks(self.tenant_id)
        task_dict = {t.id: t for t in tasks}
        ready_tasks = []

        for task in tasks:
            if task.status == TaskStatus.DONE:
                continue
            
            is_ready = True
            for dep_id in task.dependencies:
                dep_task = task_dict.get(dep_id)
                if not dep_task or dep_task.status != TaskStatus.DONE:
                    is_ready = False
                    break
            
            if is_ready:
                ready_tasks.append(task)
                
        return ready_tasks