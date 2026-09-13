# kanchi/app/__init__.py
from .main import app

# kanchi/app/config.py
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Kanchi"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost/kanchi")
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
    WORKER_HEARTBEAT_TIMEOUT: int = 120
    ORPHAN_TASK_TIMEOUT: int = 3600

    class Config:
        env_file = ".env"


settings = Settings()

# kanchi/app/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session

# kanchi/app/models.py
import uuid
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, DateTime, Text, Date, ForeignKey, Enum, JSON, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .database import Base
import enum


class TaskStatus(str, enum.Enum):
    PENDING = "PENDING"
    STARTED = "STARTED"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    RETRY = "RETRY"
    REVOKED = "REVOKED"
    ORPHAN = "ORPHAN"


class WorkerStatus(str, enum.Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"


class Task(Base):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), index=True)
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING, index=True)
    args = Column(JSON, nullable=True)
    kwargs = Column(JSON, nullable=True)
    result = Column(Text, nullable=True)
    traceback = Column(Text, nullable=True)
    worker = Column(String(255), nullable=True, index=True)
    date_done = Column(DateTime, nullable=True)
    retries = Column(Integer, default=0)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    children = relationship("Task", backref="parent", remote_side=[id])


class Worker(Base):
    __tablename__ = "workers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hostname = Column(String(255), unique=True, nullable=False, index=True)
    status = Column(Enum(WorkerStatus), default=WorkerStatus.ONLINE)
    last_heartbeat = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DailyTaskStatistic(Base):
    __tablename__ = "daily_task_statistics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    date = Column(Date, unique=True, nullable=False, index=True)
    total = Column(Integer, default=0)
    succeeded = Column(Integer, default=0)
    failed = Column(Integer, default=0)
    retried = Column(Integer, default=0)
    pending = Column(Integer, default=0)
    revoked = Column(Integer, default=0)
    orphan = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

# kanchi/app/schemas.py
from pydantic import BaseModel, Field, validator
from typing import Optional, Any, List
from datetime import datetime, date
from uuid import UUID
from .models import TaskStatus, WorkerStatus


class TaskBase(BaseModel):
    task_id: str
    name: str
    status: TaskStatus = TaskStatus.PENDING
    args: Optional[Any] = None
    kwargs: Optional[Any] = None
    result: Optional[str] = None
    traceback: Optional[str] = None
    worker: Optional[str] = None
    date_done: Optional[datetime] = None
    retries: int = 0
    parent_id: Optional[UUID] = None


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    status: Optional[TaskStatus] = None
    result: Optional[str] = None
    traceback: Optional[str] = None
    worker: Optional[str] = None
    date_done: Optional[datetime] = None
    retries: Optional[int] = None
    parent_id: Optional[UUID] = None


class TaskResponse(TaskBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class TaskFilterParams(BaseModel):
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    status: Optional[TaskStatus] = None
    name: Optional[str] = None
    worker: Optional[str] = None
    search: Optional[str] = None
    page: int = Field(1, ge=1)
    page_size: int = Field(50, ge=1, le=200)


class WorkerBase(BaseModel):
    hostname: str
    status: WorkerStatus = WorkerStatus.ONLINE


class WorkerCreate(WorkerBase):
    pass


class WorkerUpdate(BaseModel):
    status: Optional[WorkerStatus] = None
    last_heartbeat: Optional[datetime] = None


class WorkerResponse(WorkerBase):
    id: UUID
    last_heartbeat: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class DailyStatResponse(BaseModel):
    id: UUID
    date: date
    total: int
    succeeded: int
    failed: int
    retried: int
    pending: int
    revoked: int
    orphan: int

    class Config:
        orm_mode = True


class WebSocketMessage(BaseModel):
    type: str
    payload: Any

# kanchi/app/websocket_manager.py
from fastapi import WebSocket
from typing import List
import asyncio
import json


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message, default=str))
            except Exception:
                self.disconnect(connection)


manager = ConnectionManager()

# kanchi/app/celery_events.py
import threading
import asyncio
import json
import time
from datetime import datetime
from celery import Celery
from celery.events import EventReceiver
from celery.events.state import State
from .config import settings
from .models import Task, TaskStatus, Worker, WorkerStatus
from .database import async_session
from .websocket_manager import manager
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import logging

logger = logging.getLogger(__name__)

celery_app = Celery('kanchi', broker=settings.CELERY_BROKER_URL, backend=settings.CELERY_RESULT_BACKEND)
celery_app.conf.update(
    task_track_started=True,
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
)

async def process_task_event(event: dict, session: AsyncSession):
    try:
        event_type = event['type']
        task_uuid = event['uuid']
        task_name = event.get('name', 'unknown')
        hostname = event.get('hostname', 'unknown')
        timestamp = datetime.fromtimestamp(event.get('timestamp', time.time()))
        args = event.get('args')
        kwargs = event.get('kwargs')
        result = event.get('result')
        traceback = event.get('traceback')
        retries = event.get('retries', 0)
        parent_id_raw = event.get('parent_id')

        if event_type in ('task-sent', 'task-received', 'task-started', 'task-succeeded', 'task-failed', 'task-retried', 'task-revoked'):
            # Map to our statuses
            status_map = {
                'task-sent': TaskStatus.PENDING,
                'task-received': TaskStatus.PENDING,
                'task-started': TaskStatus.STARTED,
                'task-succeeded': TaskStatus.SUCCESS,
                'task-failed': TaskStatus.FAILURE,
                'task-retried': TaskStatus.RETRY,
                'task-revoked': TaskStatus.REVOKED,
            }
            new_status = status_map.get(event_type, TaskStatus.PENDING)

            # Check if task exists
            result = await session.execute(select(Task).where(Task.task_id == task_uuid))
            task = result.scalar_one_or_none()
            if task:
                # update
                task.status = new_status if new_status != TaskStatus.RETRY else TaskStatus.FAILURE  # retry is intermediate
                if event_type == 'task-retried':
                    task.retries = retries
                if event_type == 'task-started':
                    task.worker = hostname
                if event_type in ('task-succeeded', 'task-failed', 'task-retried', 'task-revoked'):
                    task.date_done = timestamp
                    task.result = str(result) if result else None
                    task.traceback = traceback
                if parent_id_raw:
                    parent_result = await session.execute(select(Task).where(Task.task_id == parent_id_raw))
                    parent_task = parent_result.scalar_one_or_none()
                    if parent_task:
                        task.parent_id = parent_task.id
                task.updated_at = timestamp
            else:
                # create new
                new_task = Task(
                    task_id=task_uuid,
                    name=task_name,
                    status=new_status if event_type != 'task-retried' else TaskStatus.FAILURE,
                    args=args,
                    kwargs=kwargs,
                    worker=hostname if event_type == 'task-started' else None,
                    date_done=timestamp if event_type in ('task-succeeded', 'task-failed', 'task-raised') else None,
                    retries=retries if event_type == 'task-retried' else 0,
                    created_at=timestamp,
                    updated_at=timestamp
                )
                session.add(new_task)
            await session.commit()

            # broadcast via websocket
            msg = {
                "type": event_type,
                "payload": {
                    "task_id": task_uuid,
                    "name": task_name,
                    "status": new_status.value if event_type != 'task-retried' else 'RETRY',
                    "worker": hostname,
                    "timestamp": timestamp.isoformat()
                }
            }
            asyncio.ensure_future(manager.broadcast(msg))

        # worker events
        elif event_type in ('worker-online', 'worker-offline', 'worker-heartbeat'):
            hostname = event.get('hostname')
            if not hostname:
                return
            result = await session.execute(select(Worker).where(Worker.hostname == hostname))
            worker = result.scalar_one_or_none()
            if event_type == 'worker-online':
                if not worker:
                    worker = Worker(hostname=hostname, status=WorkerStatus.ONLINE, last_heartbeat=timestamp)
                    session.add(worker)
                else:
                    worker.status = WorkerStatus.ONLINE
                    worker.last_heartbeat = timestamp
            elif event_type == 'worker-offline':
                if worker:
                    worker.status = WorkerStatus.OFFLINE
                    worker.last_heartbeat = timestamp
            elif event_type == 'worker-heartbeat':
                if worker:
                    worker.last_heartbeat = timestamp
                    worker.status = WorkerStatus.ONLINE
                else:
                    worker = Worker(hostname=hostname, status=WorkerStatus.ONLINE, last_heartbeat=timestamp)
                    session.add(worker)
            await session.commit()
    except Exception as e:
        logger.error(f"Error processing event: {e}")
        await session.rollback()
        raise


def start_celery_event_listener(loop):
    """Run in a separate thread."""
    async def event_loop():
        async with async_session() as session:
            state = State()
            receiver = celery_app.events.Receiver(connection, handlers={
                '*': state.event,
            })
            await receiver.capture(limit=None, timeout=None, wakeup=True)

    def run():
        with celery_app.connection_for_read() as connection:
            while True:
                try:
                    state = State()
                    def on_event(event):
                        asyncio.run_coroutine_threadsafe(
                            process_task_event(event, async_session()),
                            loop
                        )
                    with celery_app.connection_for_read() as conn:
                        recv = EventReceiver(conn, handlers={"*": on_event})
                        recv.capture(limit=None, timeout=None, wakeup=True)
                except Exception as e:
                    logger.error(f"EventListener error: {e}, restarting in 5s")
                    time.sleep(5)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()

# kanchi/app/routers/__init__.py
# empty

# kanchi/app/routers/tasks.py
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, cast, String
from typing import List, Optional
from ..database import get_session
from ..models import Task, TaskStatus
from ..schemas import TaskResponse, TaskFilterParams, WebSocketMessage
from ..websocket_manager import manager
from datetime import date, datetime
import math

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

@router.get("/", response_model=dict)
async def list_tasks(
    status: Optional[TaskStatus] = None,
    name: Optional[str] = None,
    worker: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session)
):
    filters = []
    if status:
        filters.append(Task.status == status)
    if name:
        filters.append(Task.name.ilike(f"%{name}%"))
    if worker:
        filters.append(Task.worker.ilike(f"%{worker}%"))
    if date_from:
        filters.append(Task.created_at >= datetime(date_from.year, date_from.month, date_from.day))
    if date_to:
        filters.append(Task.created_at < datetime(date_to.year, date_to.month, date_to.day) + timedelta(days=1))
    if search:
        search_filter = or_(
            Task.name.ilike(f"%{search}%"),
            Task.task_id.ilike(f"%{search}%"),
            Task.worker.ilike(f"%{search}%"),
            cast(Task.args, String).ilike(f"%{search}%"),
            cast(Task.kwargs, String).ilike(f"%{search}%")
        )
        filters.append(search_filter)

    query = select(Task)
    if filters:
        query = query.where(and_(*filters))
    total_query = select(func.count(Task.id))
    if filters:
        total_query = total_query.where(and_(*filters))
    total = (await session.execute(total_query)).scalar()

    query = query.order_by(Task.created_at.desc()).offset((page-1)*page_size).limit(page_size)
    result = await session.execute(query)
    tasks = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": math.ceil(total / page_size) if total else 1,
        "data": [TaskResponse.from_orm(t) for t in tasks]
    }

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse.from_orm(task)

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # keep connection alive, receive messages if needed
            data = await websocket.receive_text()
            # client might send a filter update, but currently ignored
            pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# kanchi/app/routers/workers.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from ..database import get_session
from ..models import Worker, WorkerStatus
from ..schemas import WorkerResponse
from typing import List

router = APIRouter(prefix="/api/workers", tags=["workers"])

@router.get("/", response_model=List[WorkerResponse])
async def list_workers(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Worker).order_by(Worker.hostname))
    workers = result.scalars().all()
    return [WorkerResponse.from_orm(w) for w in workers]

@router.get("/{hostname}", response_model=WorkerResponse)
async def get_worker(hostname: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Worker).where(Worker.hostname == hostname))
    worker = result.scalar_one_or_none()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    return WorkerResponse.from_orm(worker)

# kanchi/app/routers/stats.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from ..database import get_session
from ..models import DailyTaskStatistic, Task, TaskStatus
from ..schemas import DailyStatResponse
from typing import List, Optional
from datetime import date, datetime, timedelta
import math

router = APIRouter(prefix="/api/stats", tags=["stats"])

@router.get("/daily", response_model=dict)
async def daily_stats(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    session: AsyncSession = Depends(get_session)
):
    query = select(DailyTaskStatistic).order_by(DailyTaskStatistic.date)
    if date_from:
        query = query.where(DailyTaskStatistic.date >= date_from)
    if date_to:
        query = query.where(DailyTaskStatistic.date <= date_to)
    result = await session.execute(query)
    stats = result.scalars().all()
    return {"data": [DailyStatResponse.from_orm(s) for s in stats]}

@router.post("/recalculate", response_model=dict)
async def recalculate_stats(session: AsyncSession = Depends(get_session)):
    # recalculate daily stats for all dates where tasks exist
    # truncate and recompute
    await session.execute("DELETE FROM daily_task_statistics")
    # group by date
    stmt = select(
        func.date(Task.created_at).label('day'),
        func.count(Task.id).label('total'),
        func.count(Task.id).filter(Task.status == TaskStatus.SUCCESS).label('succeeded'),
        func.count(Task.id).filter(Task.status == TaskStatus.FAILURE).label('failed'),
        func.count(Task.id).filter(Task.status == TaskStatus.RETRY).label('retried'),
        func.count(Task.id).filter(Task.status == TaskStatus.PENDING).label('pending'),
        func.count(Task.id).filter(Task.status == TaskStatus.REVOKED).label('revoked'),
        func.count(Task.id).filter(Task.status == TaskStatus.ORPHAN).label('orphan')
    ).group_by(func.date(Task.created_at))
    result = await session.execute(stmt)
    rows = result.fetchall()
    for row in rows:
        date_obj = row[0]
        stat = DailyTaskStatistic(
            date=date_obj,
            total=row[1] or 0,
            succeeded=row[2] or 0,
            failed=row[3] or 0,
            retried=row[4] or 0,
            pending=row[5] or 0,
            revoked=row[6] or 0,
            orphan=row[7] or 0
        )
        session.add(stat)
    await session.commit()
    return {"message": "Stats recalculated successfully"}

# kanchi/app/services/__init__.py
# empty

# kanchi/app/services/orphan_detector.py
import asyncio
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from ..database import async_session
from ..models import Task, TaskStatus, Worker, WorkerStatus
from ..config import settings
import logging

logger = logging.getLogger(__name__)

async def detect_orphan_tasks():
    async with async_session() as session:
        cutoff = datetime.utcnow() - timedelta(seconds=settings.ORPHAN_TASK_TIMEOUT)
        # find tasks in STARTED state for longer than ORPHAN_TASK_TIMEOUT
        result = await session.execute(
            select(Task).where(
                Task.status == TaskStatus.STARTED,
                Task.updated_at < cutoff
            )
        )
        orphans = result.scalars().all()
        for task in orphans:
            # optionally check if worker is still online
            worker = await session.execute(
                select(Worker).where(Worker.hostname == task.worker)
            )
            worker_obj = worker.scalar_one_or_none()
            if worker_obj and worker_obj.status == WorkerStatus.ONLINE:
                # worker is online but task not updated, maybe still running, skip
                continue
            task.status = TaskStatus.ORPHAN
            task.updated_at = datetime.utcnow()
            logger.info(f"Orphan task detected: {task.task_id}")
        await session.commit()

async def orphan_detector_loop():
    while True:
        try:
            await detect_orphan_tasks()
        except Exception as e:
            logger.error(f"Orphan detection error: {e}")
        await asyncio.sleep(600)  # check every 10 minutes

# kanchi/app/main.py
import asyncio
import threading
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .celery_events import start_celery_event_listener
from .services.orphan_detector import orphan_detector_loop
from .database import engine, Base
import logging
import alembic.config
import alembic.command

logger = logging.getLogger(__name__)

def run_migrations():
    alembic_args = ['--raiseerr', 'upgrade', 'head']
    try:
        alembic.config.main(argv=alembic_args)
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise

@asynccontextmanager
async def lifespan(app: FastAPI):
    # run auto-migrations
    run_migrations()
    # create tables if not exists (in case alembic not set up)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # start celery event listener in a thread
    loop = asyncio.get_running_loop()
    start_celery_event_listener(loop)
    # start orphan detector background task
    asyncio.create_task(orphan_detector_loop())
    yield
    # shutdown

app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from .routers import tasks, workers, stats

app.include_router(tasks.router)
app.include_router(workers.router)
app.include_router(stats.router)

# kanchi/app/utils.py
# (empty for now)

# kanchi/alembic.ini
[alembic]
script_location = alembic
sqlalchemy.url = driver://user:pass@localhost/dbname
# In env.py we override the url from config.DATABASE_URL

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S

# kanchi/alembic/env.py
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app.config import settings
from app.database import Base
from app import models

config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL.replace("+asyncpg", ""))  # for sync alembic

fileConfig(config.config_file_name)
target_metadata = Base.metadata

def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

# kanchi/alembic/versions/initial_migration.py
"""initial migration

Revision ID: 001
Revises: None
Create Date: 2023-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('task_id', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('status', sa.Enum('PENDING','STARTED','SUCCESS','FAILURE','RETRY','REVOKED','ORPHAN', name='taskstatus'), nullable=True),
        sa.Column('args', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('kwargs', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('result', sa.Text(), nullable=True),
        sa.Column('traceback', sa.Text(), nullable=True),
        sa.Column('worker', sa.String(255), nullable=True),
        sa.Column('date_done', sa.DateTime(), nullable=True),
        sa.Column('retries', sa.Integer(), nullable=True),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['parent_id'], ['tasks.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('task_id')
    )
    op.create_index(op.f('ix_tasks_created_at'), 'tasks', ['created_at'], unique=False)
    op.create_index(op.f('ix_tasks_name'), 'tasks', ['name'], unique=False)
    op.create_index(op.f('ix_tasks_status'), 'tasks', ['status'], unique=False)
    op.create_index(op.f('ix_tasks_task_id'), 'tasks', ['task_id'], unique=True)
    op.create_index(op.f('ix_tasks_worker'), 'tasks', ['worker'], unique=False)

    op.create_table('workers',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('hostname', sa.String(255), nullable=False),
        sa.Column('status', sa.Enum('ONLINE','OFFLINE', name='workerstatus'), nullable=True),
        sa.Column('last_heartbeat', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('hostname')
    )
    op.create_index(op.f('ix_workers_hostname'), 'workers', ['hostname'], unique=True)

    op.create_table('daily_task_statistics',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('total', sa.Integer(), nullable=True),
        sa.Column('succeeded', sa.Integer(), nullable=True),
        sa.Column('failed', sa.Integer(), nullable=True),
        sa.Column('retried', sa.Integer(), nullable=True),
        sa.Column('pending', sa.Integer(), nullable=True),
        sa.Column('revoked', sa.Integer(), nullable=True),
        sa.Column('orphan', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('date')
    )
    op.create_index(op.f('ix_daily_task_statistics_date'), 'daily_task_statistics', ['date'], unique=True)

def downgrade():
    op.drop_index(op.f('ix_daily_task_statistics_date'), table_name='daily_task_statistics')
    op.drop_table('daily_task_statistics')
    op.drop_index(op.f('ix_workers_hostname'), table_name='workers')
    op.drop_table('workers')
    op.drop_index(op.f('ix_tasks_worker'), table_name='tasks')
    op.drop_index(op.f('ix_tasks_task_id'), table_name='tasks')
    op.drop_index(op.f('ix_tasks_status'), table_name='tasks')
    op.drop_index(op.f('ix_tasks_name'), table_name='tasks')
    op.drop_index(op.f('ix_tasks_created_at'), table_name='tasks')
    op.drop_table('tasks')
    op.execute("DROP TYPE IF EXISTS taskstatus")
    op.execute("DROP TYPE IF EXISTS workerstatus")

# kanchi/run.py
import uvicorn
from app.main import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

# kanchi/requirements.txt
fastapi>=0.100.0
uvicorn[standard]>=0.23.0
sqlalchemy[asyncio]>=2.0.0
asyncpg>=0.28.0
alembic>=1.12.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
celery[redis]>=5.3.0
python-multipart
aiofiles