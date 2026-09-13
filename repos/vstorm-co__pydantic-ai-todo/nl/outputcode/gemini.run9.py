import uuid
import json
import urllib.request
from enum import Enum
from typing import List, Optional, Dict, Any, Callable, Union
from datetime import datetime, timezone
from pydantic import BaseModel, Field
import psycopg2
from psycopg2.extras import RealDictCursor

class TaskStatus(str, Enum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"

class EventType(str, Enum):
    TASK_CREATED = "TASK_CREATED"
    TASK_UPDATED = "TASK_UPDATED"
    TASK_DELETED = "TASK_DELETED"

class Task(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    tenant_id: str
    title: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.TODO
    parent_id: Optional[uuid.UUID] = None
    dependencies: List[uuid.UUID] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class HierarchicalTask(Task):
    children: List['HierarchicalTask'] = Field(default_factory=list)

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Enum):
            return obj.value
        return super().default(obj)

class EventSystem:
    def __init__(self):
        self._callbacks: Dict[EventType, List[Callable[[Dict[str, Any]], None]]] = {
            e: [] for e in EventType
        }
        self._webhooks: Dict[EventType, List[str]] = {
            e: [] for e in EventType
        }

    def register_callback(self, event_type: EventType, callback: Callable[[Dict[str, Any]], None]) -> None:
        self._callbacks[event_type].append(callback)

    def register_webhook(self, event_type: EventType, url: str) -> None:
        self._webhooks[event_type].append(url)

    def trigger_event(self, event_type: EventType, payload: Dict[str, Any]) -> None:
        for callback in self._callbacks[event_type]:
            try:
                callback(payload)
            except Exception:
                pass

        if self._webhooks[event_type]:
            data = json.dumps(payload, cls=CustomJSONEncoder).encode('utf-8')
            headers = {'Content-Type': 'application/json'}
            for url in self._webhooks[event_type]:
                try:
                    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
                    urllib.request.urlopen(req, timeout=5)
                except Exception:
                    pass

class Storage:
    def add_task(self, task: Task) -> None:
        raise NotImplementedError

    def get_task(self, tenant_id: str, task_id: uuid.UUID) -> Optional[Task]:
        raise NotImplementedError

    def update_task(self, task: Task) -> None:
        raise NotImplementedError

    def delete_task(self, tenant_id: str, task_id: uuid.UUID) -> None:
        raise NotImplementedError

    def list_tasks(self, tenant_id: str) -> List[Task]:
        raise NotImplementedError

    def bulk_write(self, tasks: List[Task]) -> None:
        raise NotImplementedError

class PostgresStorage(Storage):
    def __init__(self, conn_string: str):
        self.conn_string = conn_string
        self._initialize_db()

    def _get_connection(self):
        return psycopg2.connect(self.conn_string, cursor_factory=RealDictCursor)

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
                        parent_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
                        created_at TIMESTAMPTZ NOT NULL,
                        updated_at TIMESTAMPTZ NOT NULL
                    );
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS task_dependencies (
                        task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
                        depends_on_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
                        PRIMARY KEY (task_id, depends_on_id)
                    );
                """)
                cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_tenant ON tasks(tenant_id);")
            conn.commit()

    def _row_to_task(self, row: Dict[str, Any], dependencies: List[uuid.UUID]) -> Task:
        return Task(
            id=row['id'],
            tenant_id=row['tenant_id'],
            title=row['title'],
            description=row['description'],
            status=TaskStatus(row['status']),
            parent_id=row['parent_id'],
            dependencies=dependencies,
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )

    def add_task(self, task: Task) -> None:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO tasks (id, tenant_id, title, description, status, parent_id, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (task.id, task.tenant_id, task.title, task.description, task.status.value, task.parent_id, task.created_at, task.updated_at))
                
                for dep_id in task.dependencies:
                    cur.execute("""
                        INSERT INTO task_dependencies (task_id, depends_on_id)
                        VALUES (%s, %s)
                    """, (task.id, dep_id))
            conn.commit()

    def get_task(self, tenant_id: str, task_id: uuid.UUID) -> Optional[Task]:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM tasks WHERE id = %s AND tenant_id = %s", (task_id, tenant_id))
                row = cur.fetchone()
                if not row:
                    return None
                
                cur.execute("SELECT depends_on_id FROM task_dependencies WHERE task_id = %s", (task_id,))
                deps = [r['depends_on_id'] for r in cur.fetchall()]
                
        return self._row_to_task(row, deps)

    def update_task(self, task: Task) -> None:
        task.updated_at = datetime.now(timezone.utc)
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE tasks
                    SET title = %s, description = %s, status = %s, parent_id = %s, updated_at = %s
                    WHERE id = %s AND tenant_id = %s
                """, (task.title, task.description, task.status.value, task.parent_id, task.updated_at, task.id, task.tenant_id))
                
                cur.execute("DELETE FROM task_dependencies WHERE task_id = %s", (task.id,))
                for dep_id in task.dependencies:
                    cur.execute("""
                        INSERT INTO task_dependencies (task_id, depends_on_id)
                        VALUES (%s, %s)
                    """, (task.id, dep_id))
            conn.commit()

    def delete_task(self, tenant_id: str, task_id: uuid.UUID) -> None:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM tasks WHERE id = %s AND tenant_id = %s", (task_id, tenant_id))
            conn.commit()

    def list_tasks(self, tenant_id: str) -> List[Task]:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM tasks WHERE tenant_id = %s ORDER BY created_at ASC", (tenant_id,))
                rows = cur.fetchall()
                
                if not rows:
                    return []
                
                task_ids = tuple(r['id'] for r in rows)
                cur.execute("SELECT task_id, depends_on_id FROM task_dependencies WHERE task_id IN %s", (task_ids,))
                dep_rows = cur.fetchall()
                
                deps_map: Dict[uuid.UUID, List[uuid.UUID]] = {tid: [] for tid in task_ids}
                for dr in dep_rows:
                    deps_map[dr['task_id']].append(dr['depends_on_id'])
                    
        return [self._row_to_task(row, deps_map[row['id']]) for row in rows]

    def bulk_write(self, tasks: List[Task]) -> None:
        for task in tasks:
            existing = self.get_task(task.tenant_id, task.id)
            if existing:
                self.update_task(task)
            else:
                self.add_task(task)

class TodoToolset:
    def __init__(self, storage: Storage, event_system: EventSystem):
        self.storage = storage
        self.event_system = event_system

    def list_all_tasks(self, tenant_id: str, hierarchical: bool = False) -> Union[List[Task], List[HierarchicalTask]]:
        tasks = self.storage.list_tasks(tenant_id)
        if not hierarchical:
            return tasks

        task_dict = {
            task.id: HierarchicalTask(**task.model_dump())
            for task in tasks
        }
        
        root_tasks = []
        for task in task_dict.values():
            if task.parent_id and task.parent_id in task_dict:
                task_dict[task.parent_id].children.append(task)
            else:
                root_tasks.append(task)
                
        return root_tasks

    def bulk_write_tasks(self, tenant_id: str, tasks_data: List[Dict[str, Any]]) -> List[Task]:
        tasks = []
        for data in tasks_data:
            data['tenant_id'] = tenant_id
            tasks.append(Task(**data))
            
        self.storage.bulk_write(tasks)
        
        for task in tasks:
            self.event_system.trigger_event(EventType.TASK_UPDATED, task.model_dump())
            
        return tasks

    def add_task(self, tenant_id: str, title: str, description: Optional[str] = None, parent_id: Optional[uuid.UUID] = None) -> Task:
        if parent_id:
            parent = self.storage.get_task(tenant_id, parent_id)
            if not parent:
                raise ValueError(f"Parent task {parent_id} not found for tenant {tenant_id}")

        task = Task(
            tenant_id=tenant_id,
            title=title,
            description=description,
            parent_id=parent_id
        )
        self.storage.add_task(task)
        self.event_system.trigger_event(EventType.TASK_CREATED, task.model_dump())
        return task

    def update_task_status(self, tenant_id: str, task_id: uuid.UUID, status: TaskStatus) -> Task:
        task = self.storage.get_task(tenant_id, task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
            
        task.status = status
        self.storage.update_task(task)
        self.event_system.trigger_event(EventType.TASK_UPDATED, task.model_dump())
        return task

    def delete_task(self, tenant_id: str, task_id: uuid.UUID) -> None:
        task = self.storage.get_task(tenant_id, task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
            
        self.storage.delete_task(tenant_id, task_id)
        self.event_system.trigger_event(EventType.TASK_DELETED, {"id": str(task_id), "tenant_id": tenant_id})

    def create_child_task(self, tenant_id: str, parent_id: uuid.UUID, title: str, description: Optional[str] = None) -> Task:
        return self.add_task(tenant_id, title, description, parent_id)

    def link_dependency(self, tenant_id: str, task_id: uuid.UUID, depends_on_id: uuid.UUID) -> Task:
        task = self.storage.get_task(tenant_id, task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
            
        dependency = self.storage.get_task(tenant_id, depends_on_id)
        if not dependency:
            raise ValueError(f"Dependency task {depends_on_id} not found")
            
        if depends_on_id not in task.dependencies:
            task.dependencies.append(depends_on_id)
            self.storage.update_task(task)
            self.event_system.trigger_event(EventType.TASK_UPDATED, task.model_dump())
            
        return task

    def list_ready_tasks(self, tenant_id: str) -> List[Task]:
        all_tasks = self.storage.list_tasks(tenant_id)
        task_map = {t.id: t for t in all_tasks}
        ready_tasks = []

        for task in all_tasks:
            if task.status == TaskStatus.DONE:
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