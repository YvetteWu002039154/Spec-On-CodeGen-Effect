# file: kanchi/__init__.py

# file: kanchi/config.py
import os
from pydantic import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./kanchi.db"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    ORPHAN_TIMEOUT_SECONDS: int = 60
    EVENT_QUEUE_MAXSIZE: int = 1000
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    class Config:
        env_file = ".env"

settings = Settings()

# file: kanchi/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from .config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# file: kanchi/models.py
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, JSON, Float, Date, Enum, ForeignKey
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from .database import Base
import enum

class TaskStatus(str, enum.Enum):
    PENDING = "PENDING"
    RECEIVED = "RECEIVED"
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

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    args = Column(JSON, nullable=True)
    kwargs = Column(JSON, nullable=True)
    status = Column(String, default=TaskStatus.PENDING, index=True)
    worker = Column(String, nullable=True)
    retries = Column(Integer, default=0)
    parent_id = Column(String, nullable=True)  # not used for retries but can be set
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    result = Column(JSON, nullable=True)
    traceback = Column(String, nullable=True)
    exception = Column(String, nullable=True)

class Worker(Base):
    __tablename__ = "workers"

    hostname = Column(String, primary_key=True)
    status = Column(String, default=WorkerStatus.OFFLINE)
    last_heartbeat = Column(DateTime, nullable=True)
    concurrency = Column(Integer, nullable=True)
    queues = Column(JSON, nullable=True)
    # additional fields can be added

class DailyStats(Base):
    __tablename__ = "daily_stats"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    date = Column(Date, nullable=False, index=True)
    total_tasks = Column(Integer, default=0)
    succeeded = Column(Integer, default=0)
    failed = Column(Integer, default=0)
    retried = Column(Integer, default=0)
    avg_runtime = Column(Float, default=0.0)

# file: kanchi/schemas.py
from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime, date

class TaskOut(BaseModel):
    id: str
    task_id: str
    name: str
    args: Optional[Any]
    kwargs: Optional[Any]
    status: str
    worker: Optional[str]
    retries: int
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    result: Optional[Any]
    traceback: Optional[str]
    exception: Optional[str]

    class Config:
        orm_mode = True

class WorkerOut(BaseModel):
    hostname: str
    status: str
    last_heartbeat: Optional[datetime]
    concurrency: Optional[int]
    queues: Optional[Any]

    class Config:
        orm_mode = True

class DailyStatsOut(BaseModel):
    date: date
    total_tasks: int
    succeeded: int
    failed: int
    retried: int
    avg_runtime: float

    class Config:
        orm_mode = True

# file: kanchi/websocket.py
import asyncio
from typing import List
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()

# file: kanchi/tasks_monitor.py
import asyncio
import json
from datetime import datetime
from celery import Celery
from celery.events import EventReceiver
from kombu import Connection
from .config import settings
from .database import SessionLocal
from .models import Task, TaskStatus, Worker, WorkerStatus, DailyStats
from .websocket import manager
import logging

logger = logging.getLogger(__name__)

def process_event(event: dict, session):
    event_type = event['type']
    message = None

    if event_type.startswith('task-'):
        task_id = event['uuid']
        task = session.query(Task).filter(Task.task_id == task_id).first()
        if not task and event_type == 'task-sent':
            task = Task(task_id=task_id, name=event.get('name', ''), args=event.get('args'), kwargs=event.get('kwargs'),
                        status=TaskStatus.PENDING, created_at=datetime.utcnow())
            session.add(task)
            message = {'type': 'task_created', 'task': {'id': task.id, 'task_id': task_id, 'name': task.name}}
        elif task:
            if event_type == 'task-received':
                task.status = TaskStatus.RECEIVED
                task.worker = event.get('hostname')
                message = {'type': 'task_updated', 'task': {'id': task.id, 'status': task.status, 'worker': task.worker}}
            elif event_type == 'task-started':
                task.status = TaskStatus.STARTED
                task.started_at = datetime.utcnow()
                message = {'type': 'task_updated', 'task': {'id': task.id, 'status': task.status, 'started_at': task.started_at.isoformat()}}
            elif event_type == 'task-succeeded':
                task.status = TaskStatus.SUCCESS
                task.completed_at = datetime.utcnow()
                task.result = event.get('result')
                message = {'type': 'task_updated', 'task': {'id': task.id, 'status': task.status, 'completed_at': task.completed_at.isoformat()}}
            elif event_type == 'task-failed':
                task.status = TaskStatus.FAILURE
                task.completed_at = datetime.utcnow()
                task.exception = event.get('exception')
                task.traceback = event.get('traceback')
                message = {'type': 'task_updated', 'task': {'id': task.id, 'status': task.status, 'exception': task.exception}}
            elif event_type == 'task-retried':
                task.status = TaskStatus.RETRY
                task.retries = event.get('retries', 0)
                task.exception = event.get('exception')
                task.traceback = event.get('traceback')
                message = {'type': 'task_updated', 'task': {'id': task.id, 'status': task.status, 'retries': task.retries}}
            elif event_type == 'task-revoked':
                task.status = TaskStatus.REVOKED
                message = {'type': 'task_updated', 'task': {'id': task.id, 'status': task.status}}
        session.commit()

    elif event_type.startswith('worker-'):
        hostname = event['hostname']
        worker = session.query(Worker).filter(Worker.hostname == hostname).first()
        if event_type == 'worker-online':
            if not worker:
                worker = Worker(hostname=hostname, status=WorkerStatus.ONLINE, last_heartbeat=datetime.utcnow())
                session.add(worker)
            else:
                worker.status = WorkerStatus.ONLINE
                worker.last_heartbeat = datetime.utcnow()
            message = {'type': 'worker_update', 'worker': {'hostname': hostname, 'status': 'ONLINE'}}
        elif event_type == 'worker-offline':
            if worker:
                worker.status = WorkerStatus.OFFLINE
                message = {'type': 'worker_update', 'worker': {'hostname': hostname, 'status': 'OFFLINE'}}
        elif event_type == 'worker-heartbeat':
            if worker:
                worker.last_heartbeat = datetime.utcnow()
                if worker.status != WorkerStatus.ONLINE:
                    worker.status = WorkerStatus.ONLINE
                    message = {'type': 'worker_update', 'worker': {'hostname': hostname, 'status': 'ONLINE'}}
            else:
                worker = Worker(hostname=hostname, status=WorkerStatus.ONLINE, last_heartbeat=datetime.utcnow())
                session.add(worker)
                message = {'type': 'worker_update', 'worker': {'hostname': hostname, 'status': 'ONLINE'}}
        session.commit()

    if message:
        # push to websocket manager in main thread via asyncio loop
        loop = asyncio.get_event_loop()
        loop.call_soon_threadsafe(manager.broadcast, message)

def celery_events_listener(app: Celery, event_queue: asyncio.Queue):
    with app.connection() as connection:
        recv = EventReceiver(connection, handlers={
            'task-sent': lambda event: process_event_threadsafe(event, app),
            'task-received': lambda event: process_event_threadsafe(event, app),
            'task-started': lambda event: process_event_threadsafe(event, app),
            'task-succeeded': lambda event: process_event_threadsafe(event, app),
            'task-failed': lambda event: process_event_threadsafe(event, app),
            'task-retried': lambda event: process_event_threadsafe(event, app),
            'task-revoked': lambda event: process_event_threadsafe(event, app),
            'worker-online': lambda event: process_event_threadsafe(event, app),
            'worker-offline': lambda event: process_event_threadsafe(event, app),
            'worker-heartbeat': lambda event: process_event_threadsafe(event, app),
        })
        recv.capture(limit=None, timeout=None, wakeup=True)

def process_event_threadsafe(event, app):
    # create a new session for this thread
    session = SessionLocal()
    try:
        process_event(event, session)
    except Exception as e:
        logger.error(f"Error processing event: {e}", exc_info=True)
        session.rollback()
    finally:
        session.close()

# file: kanchi/endpoints.py
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, datetime
from .database import get_db
from .models import Task, TaskStatus, Worker, DailyStats
from .schemas import TaskOut, WorkerOut, DailyStatsOut
from .websocket import manager
import asyncio

router = APIRouter()

@router.get("/tasks", response_model=List[TaskOut])
def list_tasks(
    status: Optional[str] = None,
    name: Optional[str] = None,
    worker: Optional[str] = None,
    search: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    query = db.query(Task)
    if status:
        query = query.filter(Task.status == status)
    if name:
        query = query.filter(Task.name.ilike(f"%{name}%"))
    if worker:
        query = query.filter(Task.worker == worker)
    if search:
        like = f"%{search}%"
        query = query.filter(
            (Task.name.ilike(like)) |
            (Task.task_id.ilike(like)) |
            (Task.worker.ilike(like)) |
            (Task.exception.ilike(like))
        )
    if date_from:
        query = query.filter(Task.created_at >= datetime(date_from.year, date_from.month, date_from.day))
    if date_to:
        query = query.filter(Task.created_at < datetime(date_to.year, date_to.month, date_to.day) + timedelta(days=1))
    tasks = query.order_by(Task.created_at.desc()).offset(skip).limit(limit).all()
    return tasks

@router.get("/tasks/{task_id}", response_model=TaskOut)
def get_task(task_id: str, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.get("/workers", response_model=List[WorkerOut])
def list_workers(db: Session = Depends(get_db)):
    return db.query(Worker).all()

@router.get("/stats/daily", response_model=List[DailyStatsOut])
def daily_stats(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: Session = Depends(get_db)
):
    query = db.query(DailyStats)
    if date_from:
        query = query.filter(DailyStats.date >= date_from)
    if date_to:
        query = query.filter(DailyStats.date <= date_to)
    return query.order_by(DailyStats.date).all()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # keep connection alive, all data sent via broadcast
            await asyncio.sleep(3600)  # just keep alive
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# file: kanchi/main.py
import asyncio
from fastapi import FastAPI
from celery import Celery
from .config import settings
from .database import engine, Base, SessionLocal
from .endpoints import router
from .tasks_monitor import celery_events_listener
from .websocket import manager
import threading

celery_app = Celery(broker=settings.CELERY_BROKER_URL)

def start_celery_listener(loop):
    # start background thread
    def run():
        celery_events_listener(celery_app, None)  # event queue not used in this version
    thread = threading.Thread(target=run, daemon=True)
    thread.start()

async def orphan_detection_loop():
    from .models import Task, TaskStatus, Worker
    from datetime import datetime, timedelta
    while True:
        await asyncio.sleep(settings.ORPHAN_TIMEOUT_SECONDS)
        try:
            db = SessionLocal()
            threshold = datetime.utcnow() - timedelta(seconds=settings.ORPHAN_TIMEOUT_SECONDS)
            stale_tasks = db.query(Task).filter(
                Task.status.in_([TaskStatus.STARTED, TaskStatus.RECEIVED])
            ).all()
            orphans = []
            for task in stale_tasks:
                if task.worker:
                    worker = db.query(Worker).filter(Worker.hostname == task.worker).first()
                    if not worker or (worker.last_heartbeat and worker.last_heartbeat < threshold):
                        task.status = TaskStatus.ORPHAN
                        orphans.append(task)
                else:
                    # no worker assigned yet, maybe still received but lost
                    if task.updated_at and task.updated_at < threshold:
                        task.status = TaskStatus.ORPHAN
                        orphans.append(task)
            if orphans:
                db.commit()
                for task in orphans:
                    await manager.broadcast({'type': 'task_updated', 'task': {'id': task.id, 'status': 'ORPHAN'}})
        except Exception as e:
            import logging
            logging.error(f"Orphan detection error: {e}", exc_info=True)
        finally:
            db.close()

app = FastAPI(title="Kanchi", version="0.1.0")
app.include_router(router)

@app.on_event("startup")
async def startup_event():
    # create tables if not exist (Alembic handles migrations otherwise)
    Base.metadata.create_all(bind=engine)
    loop = asyncio.get_running_loop()
    start_celery_listener(loop)
    asyncio.create_task(orphan_detection_loop())

# file: run.py
import uvicorn
from kanchi.config import settings
from kanchi.main import app

if __name__ == "__main__":
    uvicorn.run(app, host=settings.APP_HOST, port=settings.APP_PORT)

# file: alembic.ini
[alembic]
script_location = alembic
sqlalchemy.url = sqlite:///./kanchi.db

# file: alembic/env.py
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from kanchi.database import Base
from kanchi.models import Task, Worker, DailyStats  # noqa: F401

config = context.config
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

# file: alembic/versions/001_initial.py
"""initial migration

Revision ID: 001
Revises: 
Create Date: 2023-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('tasks',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('task_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('args', sa.JSON(), nullable=True),
        sa.Column('kwargs', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('worker', sa.String(), nullable=True),
        sa.Column('retries', sa.Integer(), nullable=True),
        sa.Column('parent_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('result', sa.JSON(), nullable=True),
        sa.Column('traceback', sa.String(), nullable=True),
        sa.Column('exception', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('task_id')
    )
    op.create_index('ix_tasks_name', 'tasks', ['name'])
    op.create_index('ix_tasks_status', 'tasks', ['status'])
    op.create_index('ix_tasks_task_id', 'tasks', ['task_id'])

    op.create_table('workers',
        sa.Column('hostname', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('last_heartbeat', sa.DateTime(), nullable=True),
        sa.Column('concurrency', sa.Integer(), nullable=True),
        sa.Column('queues', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('hostname')
    )

    op.create_table('daily_stats',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('total_tasks', sa.Integer(), nullable=True),
        sa.Column('succeeded', sa.Integer(), nullable=True),
        sa.Column('failed', sa.Integer(), nullable=True),
        sa.Column('retried', sa.Integer(), nullable=True),
        sa.Column('avg_runtime', sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_daily_stats_date', 'date')
    )

def downgrade():
    op.drop_table('daily_stats')
    op.drop_table('workers')
    op.drop_index('ix_tasks_task_id', table_name='tasks')
    op.drop_index('ix_tasks_status', table_name='tasks')
    op.drop_index('ix_tasks_name', table_name='tasks')
    op.drop_table('tasks')

# file: requirements.txt
fastapi==0.100.0
uvicorn==0.22.0
sqlalchemy==2.0.19
alembic==1.11.1
celery==5.3.1
kombu==5.3.1
redis==4.6.0
pydantic==2.0.3
python-dotenv==1.0.0