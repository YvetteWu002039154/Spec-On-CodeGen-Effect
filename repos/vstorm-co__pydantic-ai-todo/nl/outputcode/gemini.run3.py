import json
import uuid
import urllib.request
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Callable, Union
from pydantic import BaseModel, Field
import psycopg2
from psycopg2.extras import Json

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
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TaskNode(BaseModel):
    task: Task
    children: List["TaskNode"] = Field(default_factory=list)

class EventManager:
    def __init__(self):
        self._callbacks: List[Callable[[EventType, Task], None]] = []
        self._webhooks: List[str] = []

    def register_callback(self, callback: Callable[[EventType, Task], None]) -> None:
        self._callbacks.append(callback)

    def register_webhook(self, url: str) -> None:
        self._webhooks.append(url)

    def emit(self, event_type: EventType, task: Task) -> None:
        for cb in self._callbacks:
            try:
                cb(event_type, task)
            except Exception:
                pass
        
        if self._webhooks:
            payload = json.dumps({
                "event": event_type.value,
                "task": task.model_dump(mode='json')
            }).encode('utf-8')
            
            for url in self._webhooks:
                try:
                    req = urllib.request.Request(
                        url, 
                        data=payload, 
                        headers={'Content-Type': 'application/json'}
                    )
                    urllib.request.urlopen(req, timeout=5)
                except Exception:
                    pass

class Storage:
    def get_all(self, tenant_id: str) -> List[Task]:
        raise NotImplementedError

    def get(self, tenant_id: str, task_id: str) -> Optional[Task]:
        raise NotImplementedError

    def save(self, task: Task) -> None:
        raise NotImplementedError

    def save_many(self, tasks: List[Task]) -> None:
        raise NotImplementedError

    def delete(self, tenant_id: str, task_id: str) -> None:
        raise NotImplementedError

class PostgresStorage(Storage):
    def __init__(self, connection_string: str):
        self.conn_str = connection_string
        self._init_db()

    def _get_connection(self):
        return psycopg2.connect(self.conn_str)

    def _init_db(self) -> None:
        with self._get_connection() as conn:
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
                    )
                """)
                cur.execute("CREATE INDEX IF NOT EXISTS idx_tenant_id ON tasks(tenant_id)")
            conn.commit()

    def _row_to_task(self, row: tuple) -> Task:
        return Task(
            id=row[0],
            tenant_id=row[1],
            title=row[2],
            description=row[3],
            status=TaskStatus(row[4]),
            parent_id=row[5],
            dependencies=row[6] if isinstance(row[6], list) else json.loads(row[6]),
            created_at=row[7],
            updated_at=row[8]
        )

    def get_all(self, tenant_id: str) -> List[Task]:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, tenant_id, title, description, status, parent_id, dependencies, created_at, updated_at 
                    FROM tasks WHERE tenant_id = %s
                """, (tenant_id,))
                rows = cur.fetchall()
                return [self._row_to_task(row) for row in rows]

    def get(self, tenant_id: str, task_id: str) -> Optional[Task]:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, tenant_id, title, description, status, parent_id, dependencies, created_at, updated_at 
                    FROM tasks WHERE tenant_id = %s AND id = %s
                """, (tenant_id, task_id))
                row = cur.fetchone()
                return self._row_to_task(row) if row else None

    def save(self, task: Task) -> None:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
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
                    task.id, task.tenant_id, task.title, task.description, task.status.value,
                    task.parent_id, Json(task.dependencies), task.created_at, task.updated_at
                ))
            conn.commit()

    def save_many(self, tasks: List[Task]) -> None:
        if not tasks:
            return
        with self._get_connection() as conn:
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
                        task.id, task.tenant_id, task.title, task.description, task.status.value,
                        task.parent_id, Json(task.dependencies), task.created_at, task.updated_at
                    ))
            conn.commit()

    def delete(self, tenant_id: str, task_id: str) -> None:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM tasks WHERE tenant_id = %s AND id = %s", (tenant_id, task_id))
            conn.commit()

class TodoToolset:
    def __init__(self, storage: Storage, event_manager: EventManager, tenant_id: str):
        self._storage = storage
        self._event_manager = event_manager
        self._tenant_id = tenant_id

    def list_all_tasks(self, hierarchical: bool = False) -> Union[List[Task], List[TaskNode]]:
        tasks = self._storage.get_all(self._tenant_id)
        if not hierarchical:
            return tasks
        
        task_dict = {task.id: TaskNode(task=task) for task in tasks}
        root_nodes: List[TaskNode] = []
        
        for node in task_dict.values():
            if node.task.parent_id and node.task.parent_id in task_dict:
                task_dict[node.task.parent_id].children.append(node)
            else:
                root_nodes.append(node)
                
        return root_nodes

    def bulk_write_tasks(self, tasks: List[Task]) -> None:
        for task in tasks:
            if task.tenant_id != self._tenant_id:
                raise ValueError(f"Task {task.id} does not belong to tenant {self._tenant_id}")
            task.updated_at = datetime.now(timezone.utc)
            
        self._storage.save_many(tasks)
        for task in tasks:
            self._event_manager.emit(EventType.TASK_UPDATED, task)

    def add_task(self, title: str, description: Optional[str] = None) -> Task:
        task = Task(
            tenant_id=self._tenant_id,
            title=title,
            description=description
        )
        self._storage.save(task)
        self._event_manager.emit(EventType.TASK_CREATED, task)
        return task

    def update_task_status(self, task_id: str, status: TaskStatus) -> Task:
        task = self._storage.get(self._tenant_id, task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        task.status = status
        task.updated_at = datetime.now(timezone.utc)
        self._storage.save(task)
        self._event_manager.emit(EventType.TASK_UPDATED, task)
        return task

    def delete_task(self, task_id: str) -> None:
        task = self._storage.get(self._tenant_id, task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        self._storage.delete(self._tenant_id, task_id)
        self._event_manager.emit(EventType.TASK_DELETED, task)

    def create_child_task(self, parent_id: str, title: str, description: Optional[str] = None) -> Task:
        parent_task = self._storage.get(self._tenant_id, parent_id)
        if not parent_task:
            raise ValueError(f"Parent task {parent_id} not found")
        
        child_task = Task(
            tenant_id=self._tenant_id,
            title=title,
            description=description,
            parent_id=parent_id
        )
        self._storage.save(child_task)
        self._event_manager.emit(EventType.TASK_CREATED, child_task)
        return child_task

    def link_dependency(self, task_id: str, depends_on_id: str) -> Task:
        if task_id == depends_on_id:
            raise ValueError("A task cannot depend on itself")

        task = self._storage.get(self._tenant_id, task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        depends_on_task = self._storage.get(self._tenant_id, depends_on_id)
        if not depends_on_task:
            raise ValueError(f"Dependency task {depends_on_id} not found")
        
        if depends_on_id not in task.dependencies:
            task.dependencies.append(depends_on_id)
            task.updated_at = datetime.now(timezone.utc)
            self._storage.save(task)
            self._event_manager.emit(EventType.TASK_UPDATED, task)
            
        return task

    def list_ready_tasks(self) -> List[Task]:
        tasks = self._storage.get_all(self._tenant_id)
        task_dict = {task.id: task for task in tasks}
        ready_tasks: List[Task] = []
        
        for task in tasks:
            if task.status != TaskStatus.TODO:
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