import asyncio
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field
from sqlalchemy import (
    Column, DateTime, Enum as SAEnum, ForeignKey, String, Table, Text,
    UniqueConstraint, and_, exists, select, not_,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_scoped_session, create_async_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.sql import func

Base = declarative_base()

# Association table for task dependencies (M:N)
task_dependencies = Table(
    'task_dependencies',
    Base.metadata,
    Column('task_id', UUID(as_uuid=True), ForeignKey('tasks.id', ondelete='CASCADE'), primary_key=True),
    Column('depends_on_id', UUID(as_uuid=True), ForeignKey('tasks.id', ondelete='CASCADE'), primary_key=True),
)

class TaskStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"

class Task(Base):
    __tablename__ = 'tasks'
    __table_args__ = (
        UniqueConstraint('tenant_id', 'id', name='uq_task_tenant_id'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, default='')
    status = Column(SAEnum(TaskStatus), default=TaskStatus.PENDING, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    parent_id = Column(UUID(as_uuid=True), ForeignKey('tasks.id', ondelete='SET NULL'), nullable=True, index=True)

    # Self-referential relationship for parent/children
    parent = relationship('Task', remote_side=[id], back_populates='children', lazy='noload')
    children = relationship('Task', back_populates='parent', lazy='noload',
                            cascade='all, delete-orphan', passive_deletes=True)

    # Dependencies relationship (tasks that this task depends on)
    depends_on = relationship(
        'Task', secondary=task_dependencies,
        primaryjoin=id == task_dependencies.c.task_id,
        secondaryjoin=id == task_dependencies.c.depends_on_id,
        back_populates='dependent_tasks',
        lazy='noload'
    )
    dependent_tasks = relationship(
        'Task', secondary=task_dependencies,
        primaryjoin=id == task_dependencies.c.depends_on_id,
        secondaryjoin=id == task_dependencies.c.task_id,
        back_populates='depends_on',
        lazy='noload'
    )

# Pydantic schema for input/output
class TaskCreate(BaseModel):
    title: str
    description: str = ''
    parent_id: Optional[str] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None

class TaskOut(BaseModel):
    id: str
    tenant_id: str
    title: str
    description: str
    status: TaskStatus
    parent_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            uuid.UUID: str,
            datetime: lambda v: v.isoformat(),
        }

def task_to_dict(task: Task) -> dict:
    return {
        'id': str(task.id),
        'tenant_id': task.tenant_id,
        'title': task.title,
        'description': task.description,
        'status': task.status.value,
        'parent_id': str(task.parent_id) if task.parent_id else None,
        'created_at': task.created_at.isoformat(),
        'updated_at': task.updated_at.isoformat(),
    }

# Event system
class EventManager:
    def __init__(self):
        self._listeners: Dict[str, List[Callable[..., Any]]] = {}

    def register(self, event_type: str, callback: Callable[..., Any]):
        self._listeners.setdefault(event_type, []).append(callback)

    async def emit(self, event_type: str, data: dict):
        for cb in self._listeners.get(event_type, []):
            if asyncio.iscoroutinefunction(cb):
                await cb(data)
            else:
                cb(data)

# Todo Toolset
class TodoToolset:
    def __init__(self, db_url: str, event_manager: Optional[EventManager] = None):
        self.engine = create_async_engine(db_url, echo=False)
        self.Session = async_scoped_session(
            sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False),
            scopefunc=asyncio.current_task
        )
        self.events = event_manager or EventManager()

    async def initialize(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def close(self):
        await self.engine.dispose()

    # Tool methods
    async def list_tasks(self, tenant_id: str, parent_id: Optional[str] = None,
                         include_subtasks: bool = True, hierarchical: bool = False) -> List[dict]:
        async with self.Session() as session:
            if parent_id:
                stmt = select(Task).where(Task.tenant_id == tenant_id, Task.parent_id == parent_id)
            else:
                stmt = select(Task).where(Task.tenant_id == tenant_id, Task.parent_id.is_(None))

            result = await session.execute(stmt)
            tasks = result.scalars().all()

            if hierarchical:
                return await self._build_tree(session, tenant_id, tasks, include_subtasks)
            else:
                return [task_to_dict(t) for t in tasks]

    async def _build_tree(self, session, tenant_id, tasks, include_subtasks) -> List[dict]:
        tree = []
        for task in tasks:
            node = task_to_dict(task)
            if include_subtasks:
                child_stmt = select(Task).where(Task.tenant_id == tenant_id, Task.parent_id == task.id)
                child_result = await session.execute(child_stmt)
                children = child_result.scalars().all()
                node['children'] = await self._build_tree(session, tenant_id, children, include_subtasks)
            else:
                node['children'] = []
            tree.append(node)
        return tree

    async def bulk_write_tasks(self, tenant_id: str, tasks_data: List[Dict[str, Any]]) -> List[dict]:
        created = []
        async with self.Session() as session:
            async with session.begin():
                for item in tasks_data:
                    if 'id' in item and item['id']:
                        task_id = uuid.UUID(item['id'])
                        task = await session.get(Task, task_id)
                        if not task or task.tenant_id != tenant_id:
                            continue
                        for key in ('title', 'description', 'status', 'parent_id'):
                            if key in item:
                                setattr(task, key, item[key])
                        task.updated_at = func.now()
                    else:
                        task = Task(
                            tenant_id=tenant_id,
                            title=item['title'],
                            description=item.get('description', ''),
                            parent_id=item.get('parent_id'),
                            status=item.get('status', TaskStatus.PENDING),
                        )
                        session.add(task)
                    created.append(task_to_dict(task))
        # Emit events
        for t in created:
            await self.events.emit('task.updated', t)
        return created

    async def add_task(self, tenant_id: str, title: str, description: str = '',
                       parent_id: Optional[str] = None) -> dict:
        async with self.Session() as session, session.begin():
            task = Task(
                tenant_id=tenant_id,
                title=title,
                description=description,
                parent_id=parent_id,
            )
            session.add(task)
            await session.flush()
            result = task_to_dict(task)
        await self.events.emit('task.created', result)
        return result

    async def update_task_status(self, tenant_id: str, task_id: str, new_status: TaskStatus) -> dict:
        async with self.Session() as session, session.begin():
            task = await session.get(Task, uuid.UUID(task_id))
            if not task or task.tenant_id != tenant_id:
                raise ValueError(f"Task {task_id} not found for tenant {tenant_id}")
            old_status = task.status
            task.status = new_status
            task.updated_at = func.now()
            result = task_to_dict(task)
        if old_status != new_status:
            await self.events.emit('task.status_changed', {
                'task': result,
                'old_status': old_status.value,
                'new_status': new_status.value,
            })
        return result

    async def delete_task(self, tenant_id: str, task_id: str) -> bool:
        async with self.Session() as session, session.begin():
            task = await session.get(Task, uuid.UUID(task_id))
            if not task or task.tenant_id != tenant_id:
                return False
            await session.delete(task)
            await self.events.emit('task.deleted', {'id': task_id, 'tenant_id': tenant_id})
            return True

    async def create_child_task(self, tenant_id: str, parent_id: str, title: str,
                                description: str = '') -> dict:
        return await self.add_task(tenant_id, title, description, parent_id=parent_id)

    async def link_tasks(self, tenant_id: str, task_id: str, depends_on_id: str) -> bool:
        async with self.Session() as session, session.begin():
            task = await session.get(Task, uuid.UUID(task_id))
            dep = await session.get(Task, uuid.UUID(depends_on_id))
            if not task or not dep or task.tenant_id != tenant_id or dep.tenant_id != tenant_id:
                return False
            if depends_on_id not in [str(d.id) for d in task.depends_on]:
                task.depends_on.append(dep)
            return True

    async def list_ready_tasks(self, tenant_id: str) -> List[dict]:
        async with self.Session() as session:
            # Ready = status not COMPLETED and all dependencies are COMPLETED
            # subquery for tasks that have non-COMPLETED dependency
            dep_incomplete = (
                select(task_dependencies.c.task_id)
                .join(Task, task_dependencies.c.depends_on_id == Task.id)
                .where(
                    task_dependencies.c.task_id == Task.id,
                    Task.status != TaskStatus.COMPLETED
                )
                .correlate(Task)
            )
            stmt = (
                select(Task)
                .where(
                    Task.tenant_id == tenant_id,
                    Task.status != TaskStatus.COMPLETED,
                    ~exists(dep_incomplete)
                )
            )
            result = await session.execute(stmt)
            tasks = result.scalars().all()
            return [task_to_dict(t) for t in tasks]

    def tools(self, tenant_id: str) -> List[Callable[..., Any]]:
        """Returns a list of callable tools bound to this tenant (for use in Pydantic AI).
           Each callable has proper __name__ and docstring."""
        class BoundTool:
            def __init__(self, func, name, doc):
                self.func = func
                self.__name__ = name
                self.__doc__ = doc

            async def __call__(self, *args, **kwargs):
                return await self.func(*args, **kwargs)

        tools = [
            BoundTool(lambda **kw: self.list_tasks(tenant_id=tenant_id, **kw), 'list_tasks',
                      'List all tasks, optionally filtered and hierarchical.'),
            BoundTool(lambda **kw: self.bulk_write_tasks(tenant_id=tenant_id, **kw), 'bulk_write_tasks',
                      'Create or update multiple tasks at once.'),
            BoundTool(lambda **kw: self.add_task(tenant_id=tenant_id, **kw), 'add_task',
                      'Create a new task.'),
            BoundTool(lambda **kw: self.update_task_status(tenant_id=tenant_id, **kw), 'update_task_status',
                      'Update the status of a task by ID.'),
            BoundTool(lambda **kw: self.delete_task(tenant_id=tenant_id, **kw), 'delete_task',
                      'Delete a task by ID.'),
            BoundTool(lambda **kw: self.create_child_task(tenant_id=tenant_id, **kw), 'create_child_task',
                      'Create a child (subtask) for a given parent.'),
            BoundTool(lambda **kw: self.link_tasks(tenant_id=tenant_id, **kw), 'link_tasks',
                      'Add a dependency link between two tasks.'),
            BoundTool(lambda **kw: self.list_ready_tasks(tenant_id=tenant_id, **kw), 'list_ready_tasks',
                      'List all tasks that can be worked on (no incomplete dependencies).'),
        ]
        return tools

# Example usage
async def main():
    DB_URL = "postgresql+asyncpg://user:pass@localhost/testdb"
    toolset = TodoToolset(DB_URL)

    # Setup event listeners (optional)
    toolset.events.register('task.created', lambda d: print(f"Task created: {d['title']}"))
    toolset.events.register('task.status_changed', lambda d: print(f"Status changed: {d['task']['id']} -> {d['new_status']}"))

    await toolset.initialize()
    tenant = "demo-tenant"

    # Add some tasks
    t1 = await toolset.add_task(tenant, "Design system", "High-level architecture")
    t2 = await toolset.add_task(tenant, "Implement backend", "Database and API")
    t3 = await toolset.add_task(tenant, "Write tests", "Coverage", parent_id=t1['id'])

    await toolset.link_tasks(tenant, t2['id'], t1['id'])

    # List
    tasks = await toolset.list_tasks(tenant, hierarchical=True)
    print("Hierarchical tasks:", tasks)

    ready = await toolset.list_ready_tasks(tenant)
    print("Ready tasks:", ready)

    await toolset.update_task_status(tenant, t1['id'], TaskStatus.COMPLETED)
    ready = await toolset.list_ready_tasks(tenant)
    print("Ready after t1 completed:", ready)

    await toolset.close()

if __name__ == "__main__":
    asyncio.run(main())