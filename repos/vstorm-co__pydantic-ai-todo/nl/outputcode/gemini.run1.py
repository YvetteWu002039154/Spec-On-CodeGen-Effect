import json
import uuid
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from enum import Enum
from typing import List, Optional, Dict, Any, Callable, Union
from pydantic import BaseModel, Field


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
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.TODO
    parent_id: Optional[str] = None
    dependencies: List[str] = Field(default_factory=list)


class EventManager:
    def __init__(self):
        self.callbacks: Dict[EventType, List[Callable[[Dict[str, Any]], None]]] = {
            event: [] for event in EventType
        }
        self.webhooks: Dict[EventType, List[str]] = {
            event: [] for event in EventType
        }

    def register_callback(self, event_type: EventType, callback: Callable[[Dict[str, Any]], None]) -> None:
        self.callbacks[event_type].append(callback)

    def register_webhook(self, event_type: EventType, url: str) -> None:
        self.webhooks[event_type].append(url)

    def emit(self, event_type: EventType, payload: Dict[str, Any]) -> None:
        for callback in self.callbacks[event_type]:
            try:
                callback(payload)
            except Exception:
                pass

        for url in self.webhooks[event_type]:
            try:
                requests.post(
                    url,
                    json={"event": event_type.value, "payload": payload},
                    timeout=5
                )
            except Exception:
                pass


class PostgresStorage:
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self._initialize_schema()

    def _get_connection(self):
        return psycopg2.connect(self.connection_string, cursor_factory=RealDictCursor)

    def _initialize_schema(self) -> None:
        query = """
        CREATE TABLE IF NOT EXISTS tasks (
            id VARCHAR PRIMARY KEY,
            tenant_id VARCHAR NOT NULL,
            title VARCHAR NOT NULL,
            description TEXT,
            status VARCHAR NOT NULL,
            parent_id VARCHAR,
            dependencies JSONB NOT NULL DEFAULT '[]'
        );
        CREATE INDEX IF NOT EXISTS idx_tasks_tenant_id ON tasks(tenant_id);
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query)
            conn.commit()

    def get_tasks(self, tenant_id: str) -> List[Task]:
        query = "SELECT * FROM tasks WHERE tenant_id = %s"
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (tenant_id,))
                rows = cur.fetchall()
        
        tasks = []
        for row in rows:
            if isinstance(row['dependencies'], str):
                row['dependencies'] = json.loads(row['dependencies'])
            tasks.append(Task(**row))
        return tasks

    def get_task(self, tenant_id: str, task_id: str) -> Optional[Task]:
        query = "SELECT * FROM tasks WHERE tenant_id = %s AND id = %s"
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (tenant_id, task_id))
                row = cur.fetchone()
        
        if not row:
            return None
            
        if isinstance(row['dependencies'], str):
            row['dependencies'] = json.loads(row['dependencies'])
        return Task(**row)

    def upsert_task(self, task: Task) -> None:
        query = """
        INSERT INTO tasks (id, tenant_id, title, description, status, parent_id, dependencies)
        VALUES (%(id)s, %(tenant_id)s, %(title)s, %(description)s, %(status)s, %(parent_id)s, %(dependencies)s)
        ON CONFLICT (id) DO UPDATE SET
            title = EXCLUDED.title,
            description = EXCLUDED.description,
            status = EXCLUDED.status,
            parent_id = EXCLUDED.parent_id,
            dependencies = EXCLUDED.dependencies
        """
        data = task.model_dump()
        data['status'] = data['status'].value
        data['dependencies'] = json.dumps(data['dependencies'])
        
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, data)
            conn.commit()

    def delete_task(self, tenant_id: str, task_id: str) -> bool:
        query = "DELETE FROM tasks WHERE tenant_id = %s AND id = %s RETURNING id"
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (tenant_id, task_id))
                deleted = cur.fetchone() is not None
            conn.commit()
        return deleted


class TodoToolset:
    def __init__(self, db_connection_string: str):
        self.storage = PostgresStorage(db_connection_string)
        self.events = EventManager()

    def list_tasks(self, tenant_id: str, hierarchical: bool = False) -> Union[List[Task], List[Dict[str, Any]]]:
        tasks = self.storage.get_tasks(tenant_id)
        if not hierarchical:
            return tasks

        task_dicts = {task.id: task.model_dump() for task in tasks}
        for t in task_dicts.values():
            t['subtasks'] = []

        root_tasks = []
        for t in task_dicts.values():
            parent_id = t.get('parent_id')
            if parent_id and parent_id in task_dicts:
                task_dicts[parent_id]['subtasks'].append(t)
            else:
                root_tasks.append(t)

        return root_tasks

    def bulk_write_tasks(self, tenant_id: str, tasks: List[Task]) -> List[Task]:
        for task in tasks:
            if task.tenant_id != tenant_id:
                raise ValueError(f"Task {task.id} does not belong to tenant {tenant_id}")
            
            existing_task = self.storage.get_task(tenant_id, task.id)
            self.storage.upsert_task(task)
            
            if existing_task:
                self.events.emit(EventType.TASK_UPDATED, task.model_dump())
            else:
                self.events.emit(EventType.TASK_CREATED, task.model_dump())
                
        return tasks

    def add_task(self, tenant_id: str, title: str, description: Optional[str] = None, 
                 parent_id: Optional[str] = None, dependencies: Optional[List[str]] = None) -> Task:
        task = Task(
            tenant_id=tenant_id,
            title=title,
            description=description,
            parent_id=parent_id,
            dependencies=dependencies or []
        )
        self.storage.upsert_task(task)
        self.events.emit(EventType.TASK_CREATED, task.model_dump())
        return task

    def update_task_status(self, tenant_id: str, task_id: str, status: TaskStatus) -> Task:
        task = self.storage.get_task(tenant_id, task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found for tenant {tenant_id}")
            
        task.status = status
        self.storage.upsert_task(task)
        self.events.emit(EventType.TASK_UPDATED, task.model_dump())
        return task

    def delete_task(self, tenant_id: str, task_id: str) -> bool:
        task = self.storage.get_task(tenant_id, task_id)
        if not task:
            return False
            
        success = self.storage.delete_task(tenant_id, task_id)
        if success:
            self.events.emit(EventType.TASK_DELETED, {"id": task_id, "tenant_id": tenant_id})
        return success

    def create_child_task(self, tenant_id: str, parent_id: str, title: str, 
                          description: Optional[str] = None, dependencies: Optional[List[str]] = None) -> Task:
        parent_task = self.storage.get_task(tenant_id, parent_id)
        if not parent_task:
            raise ValueError(f"Parent task {parent_id} not found for tenant {tenant_id}")
            
        return self.add_task(
            tenant_id=tenant_id,
            title=title,
            description=description,
            parent_id=parent_id,
            dependencies=dependencies
        )

    def link_tasks(self, tenant_id: str, task_id: str, depends_on_id: str) -> Task:
        task = self.storage.get_task(tenant_id, task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found for tenant {tenant_id}")
            
        dependency_task = self.storage.get_task(tenant_id, depends_on_id)
        if not dependency_task:
            raise ValueError(f"Dependency task {depends_on_id} not found for tenant {tenant_id}")
            
        if depends_on_id not in task.dependencies:
            task.dependencies.append(depends_on_id)
            self.storage.upsert_task(task)
            self.events.emit(EventType.TASK_UPDATED, task.model_dump())
            
        return task

    def list_ready_tasks(self, tenant_id: str) -> List[Task]:
        all_tasks = self.storage.get_tasks(tenant_id)
        task_map = {task.id: task for task in all_tasks}
        ready_tasks = []
        
        for task in all_tasks:
            if task.status != TaskStatus.TODO:
                continue
                
            is_ready = True
            for dep_id in task.dependencies:
                dep_task = task_map.get(dep_id)
                if not dep_task or dep_task.status != TaskStatus.DONE:
                    is_ready = False
                    break
                    
            if is_ready:
                ready_tasks.append(task)
                
        return ready_tasks