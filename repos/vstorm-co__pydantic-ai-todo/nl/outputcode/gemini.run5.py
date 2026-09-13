import uuid
import urllib.request
from enum import Enum
from typing import List, Dict, Optional, Callable, Any
from pydantic import BaseModel, Field
import psycopg2
from psycopg2.extras import RealDictCursor

class TaskStatus(str, Enum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = ""
    parent_id: Optional[str] = None
    dependencies: List[str] = Field(default_factory=list)

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None

class Task(BaseModel):
    id: str
    tenant_id: str
    title: str
    description: str
    status: TaskStatus
    parent_id: Optional[str] = None
    dependencies: List[str] = Field(default_factory=list)
    subtasks: List['Task'] = Field(default_factory=list)

Task.model_rebuild()

class EventType(str, Enum):
    TASK_CREATED = "TASK_CREATED"
    TASK_UPDATED = "TASK_UPDATED"
    TASK_DELETED = "TASK_DELETED"

class Event(BaseModel):
    event_type: EventType
    tenant_id: str
    task_id: str
    payload: Dict[str, Any]

class EventManager:
    def __init__(self):
        self.callbacks: List[Callable[[Event], None]] = []
        self.webhooks: List[str] = []

    def register_callback(self, callback: Callable[[Event], None]) -> None:
        self.callbacks.append(callback)

    def register_webhook(self, url: str) -> None:
        self.webhooks.append(url)

    def trigger(self, event: Event) -> None:
        for callback in self.callbacks:
            try:
                callback(event)
            except Exception:
                pass
        
        if self.webhooks:
            data = event.model_dump_json().encode('utf-8')
            for url in self.webhooks:
                try:
                    req = urllib.request.Request(
                        url,
                        data=data,
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
                        id VARCHAR(36) PRIMARY KEY,
                        tenant_id VARCHAR(255) NOT NULL,
                        title VARCHAR(255) NOT NULL,
                        description TEXT,
                        status VARCHAR(50) NOT NULL,
                        parent_id VARCHAR(36)
                    );
                    CREATE TABLE IF NOT EXISTS task_dependencies (
                        task_id VARCHAR(36) NOT NULL,
                        depends_on_id VARCHAR(36) NOT NULL,
                        PRIMARY KEY (task_id, depends_on_id)
                    );
                """)
            conn.commit()

    def _row_to_task(self, row: dict, dependencies: List[str]) -> Task:
        return Task(
            id=row['id'],
            tenant_id=row['tenant_id'],
            title=row['title'],
            description=row['description'] or "",
            status=TaskStatus(row['status']),
            parent_id=row['parent_id'],
            dependencies=dependencies
        )

    def _get_dependencies(self, cur, task_ids: List[str]) -> Dict[str, List[str]]:
        if not task_ids:
            return {}
        cur.execute("""
            SELECT task_id, depends_on_id 
            FROM task_dependencies 
            WHERE task_id = ANY(%s)
        """, (task_ids,))
        deps: Dict[str, List[str]] = {tid: [] for tid in task_ids}
        for row in cur.fetchall():
            deps[row['task_id']].append(row['depends_on_id'])
        return deps

    def get_tasks(self, tenant_id: str) -> List[Task]:
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM tasks WHERE tenant_id = %s", (tenant_id,))
                rows = cur.fetchall()
                task_ids = [row['id'] for row in rows]
                deps = self._get_dependencies(cur, task_ids)
                return [self._row_to_task(row, deps.get(row['id'], [])) for row in rows]

    def get_task(self, tenant_id: str, task_id: str) -> Optional[Task]:
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM tasks WHERE tenant_id = %s AND id = %s", (tenant_id, task_id))
                row = cur.fetchone()
                if not row:
                    return None
                deps = self._get_dependencies(cur, [task_id])
                return self._row_to_task(row, deps.get(task_id, []))

    def create_task(self, tenant_id: str, task_create: TaskCreate) -> Task:
        task_id = str(uuid.uuid4())
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO tasks (id, tenant_id, title, description, status, parent_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (task_id, tenant_id, task_create.title, task_create.description, TaskStatus.TODO.value, task_create.parent_id))
                
                for dep_id in task_create.dependencies:
                    cur.execute("""
                        INSERT INTO task_dependencies (task_id, depends_on_id)
                        VALUES (%s, %s)
                    """, (task_id, dep_id))
            conn.commit()
        
        task = self.get_task(tenant_id, task_id)
        if not task:
            raise RuntimeError("Failed to create task")
        return task

    def bulk_create_tasks(self, tenant_id: str, tasks: List[TaskCreate]) -> List[Task]:
        created_ids = []
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                for task_create in tasks:
                    task_id = str(uuid.uuid4())
                    cur.execute("""
                        INSERT INTO tasks (id, tenant_id, title, description, status, parent_id)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (task_id, tenant_id, task_create.title, task_create.description, TaskStatus.TODO.value, task_create.parent_id))
                    
                    for dep_id in task_create.dependencies:
                        cur.execute("""
                            INSERT INTO task_dependencies (task_id, depends_on_id)
                            VALUES (%s, %s)
                        """, (task_id, dep_id))
                    created_ids.append(task_id)
            conn.commit()
        
        return [t for tid in created_ids if (t := self.get_task(tenant_id, tid)) is not None]

    def update_task(self, tenant_id: str, task_id: str, update: TaskUpdate) -> Optional[Task]:
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                fields = []
                values = []
                if update.title is not None:
                    fields.append("title = %s")
                    values.append(update.title)
                if update.description is not None:
                    fields.append("description = %s")
                    values.append(update.description)
                if update.status is not None:
                    fields.append("status = %s")
                    values.append(update.status.value)
                
                if fields:
                    query = f"UPDATE tasks SET {', '.join(fields)} WHERE tenant_id = %s AND id = %s"
                    values.extend([tenant_id, task_id])
                    cur.execute(query, tuple(values))
            conn.commit()
        return self.get_task(tenant_id, task_id)

    def bulk_update_tasks(self, tenant_id: str, updates: Dict[str, TaskUpdate]) -> List[Task]:
        updated_ids = []
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                for task_id, update in updates.items():
                    fields = []
                    values = []
                    if update.title is not None:
                        fields.append("title = %s")
                        values.append(update.title)
                    if update.description is not None:
                        fields.append("description = %s")
                        values.append(update.description)
                    if update.status is not None:
                        fields.append("status = %s")
                        values.append(update.status.value)
                    
                    if fields:
                        query = f"UPDATE tasks SET {', '.join(fields)} WHERE tenant_id = %s AND id = %s"
                        values.extend([tenant_id, task_id])
                        cur.execute(query, tuple(values))
                        updated_ids.append(task_id)
            conn.commit()
        return [t for tid in updated_ids if (t := self.get_task(tenant_id, tid)) is not None]

    def delete_task(self, tenant_id: str, task_id: str) -> bool:
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM task_dependencies WHERE task_id = %s OR depends_on_id = %s", (task_id, task_id))
                cur.execute("DELETE FROM tasks WHERE tenant_id = %s AND id = %s", (tenant_id, task_id))
                deleted = cur.rowcount > 0
            conn.commit()
        return deleted

    def add_dependency(self, tenant_id: str, task_id: str, depends_on_id: str) -> None:
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM tasks WHERE tenant_id = %s AND id IN (%s, %s)", (tenant_id, task_id, depends_on_id))
                if len(cur.fetchall()) != 2:
                    raise ValueError("One or both tasks do not exist or do not belong to the tenant.")
                
                cur.execute("""
                    INSERT INTO task_dependencies (task_id, depends_on_id)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                """, (task_id, depends_on_id))
            conn.commit()

    def get_ready_tasks(self, tenant_id: str) -> List[Task]:
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT t.* 
                    FROM tasks t
                    WHERE t.tenant_id = %s AND t.status != %s
                    AND NOT EXISTS (
                        SELECT 1 
                        FROM task_dependencies td
                        JOIN tasks dt ON td.depends_on_id = dt.id
                        WHERE td.task_id = t.id AND dt.status != %s
                    )
                """, (tenant_id, TaskStatus.DONE.value, TaskStatus.DONE.value))
                rows = cur.fetchall()
                task_ids = [row['id'] for row in rows]
                deps = self._get_dependencies(cur, task_ids)
                return [self._row_to_task(row, deps.get(row['id'], [])) for row in rows]

class TodoToolset:
    def __init__(self, db_dsn: str):
        self.storage = PostgresStorage(db_dsn)
        self.events = EventManager()

    def list_tasks(self, tenant_id: str, hierarchical: bool = False) -> List[Task]:
        tasks = self.storage.get_tasks(tenant_id)
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

    def add_task(self, tenant_id: str, task_create: TaskCreate) -> Task:
        task = self.storage.create_task(tenant_id, task_create)
        self.events.trigger(Event(
            event_type=EventType.TASK_CREATED,
            tenant_id=tenant_id,
            task_id=task.id,
            payload=task.model_dump()
        ))
        return task

    def bulk_write_tasks(self, tenant_id: str, tasks: List[TaskCreate]) -> List[Task]:
        created_tasks = self.storage.bulk_create_tasks(tenant_id, tasks)
        for t in created_tasks:
            self.events.trigger(Event(
                event_type=EventType.TASK_CREATED,
                tenant_id=tenant_id,
                task_id=t.id,
                payload=t.model_dump()
            ))
        return created_tasks

    def bulk_update_tasks(self, tenant_id: str, updates: Dict[str, TaskUpdate]) -> List[Task]:
        updated_tasks = self.storage.bulk_update_tasks(tenant_id, updates)
        for t in updated_tasks:
            self.events.trigger(Event(
                event_type=EventType.TASK_UPDATED,
                tenant_id=tenant_id,
                task_id=t.id,
                payload=t.model_dump()
            ))
        return updated_tasks

    def update_task_status(self, tenant_id: str, task_id: str, status: TaskStatus) -> Optional[Task]:
        update = TaskUpdate(status=status)
        task = self.storage.update_task(tenant_id, task_id, update)
        if task:
            self.events.trigger(Event(
                event_type=EventType.TASK_UPDATED,
                tenant_id=tenant_id,
                task_id=task.id,
                payload=task.model_dump()
            ))
        return task

    def delete_task(self, tenant_id: str, task_id: str) -> bool:
        deleted = self.storage.delete_task(tenant_id, task_id)
        if deleted:
            self.events.trigger(Event(
                event_type=EventType.TASK_DELETED,
                tenant_id=tenant_id,
                task_id=task_id,
                payload={}
            ))
        return deleted

    def create_child_task(self, tenant_id: str, parent_id: str, task_create: TaskCreate) -> Task:
        task_create.parent_id = parent_id
        return self.add_task(tenant_id, task_create)

    def link_dependency(self, tenant_id: str, task_id: str, depends_on_id: str) -> Optional[Task]:
        self.storage.add_dependency(tenant_id, task_id, depends_on_id)
        task = self.storage.get_task(tenant_id, task_id)
        if task:
            self.events.trigger(Event(
                event_type=EventType.TASK_UPDATED,
                tenant_id=tenant_id,
                task_id=task_id,
                payload=task.model_dump()
            ))
        return task

    def list_ready_tasks(self, tenant_id: str) -> List[Task]:
        return self.storage.get_ready_tasks(tenant_id)