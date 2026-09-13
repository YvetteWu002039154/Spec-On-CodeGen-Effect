from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import sys
from datetime import datetime, date, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import uuid4

import uvicorn
from celery.events import EventReceiver
from celery.events.state import State
from celery.utils.serialization import jsonify
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Date,
    Boolean,
    Float,
    ForeignKey,
    Index,
    UniqueConstraint,
    JSON,
    Enum as SAEnum,
    create_engine,
    event,
    select,
    func,
    and_,
    or_,
    text as sa_text,
    update,
    delete,
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, AsyncEngine
from sqlalchemy.orm import (
    declarative_base,
    sessionmaker,
    relationship,
    Session,
    joinedload,
)
from sqlalchemy.pool import NullPool

# ------------------------------------------------------------------------------
# Configuration (environment variables or defaults)
# ------------------------------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./kanchi.db")
SYNC_DATABASE_URL = DATABASE_URL.replace("+aiosqlite", "") if "aiosqlite" in DATABASE_URL else DATABASE_URL.replace("+asyncpg", "").replace("+asyncmy", "")
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger("kanchi")

# ------------------------------------------------------------------------------
# SQLAlchemy setup
# ------------------------------------------------------------------------------
Base = declarative_base()

# Async engine and session
async_engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    poolclass=NullPool,
)
async_session_factory = sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)

# Sync engine (for celery event thread)
sync_engine = create_engine(SYNC_DATABASE_URL, echo=False, future=True)
sync_session_factory = sessionmaker(sync_engine, expire_on_commit=False)

# ------------------------------------------------------------------------------
# Enums
# ------------------------------------------------------------------------------
class TaskStatus(str, Enum):
    PENDING = "PENDING"
    RECEIVED = "RECEIVED"
    STARTED = "STARTED"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    REVOKED = "REVOKED"
    RETRY = "RETRY"
    ORPHAN = "ORPHAN"  # pseudo-state for orphaned tasks

class WorkerStatus(str, Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"

# ------------------------------------------------------------------------------
# Models
# ------------------------------------------------------------------------------
class TaskModel(Base):
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    task_id = Column(String(36), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    args = Column(Text, nullable=True)       # JSON string
    kwargs = Column(Text, nullable=True)     # JSON string
    status = Column(SAEnum(TaskStatus), default=TaskStatus.PENDING, nullable=False, index=True)
    result = Column(Text, nullable=True)     # JSON string of result or error
    traceback = Column(Text, nullable=True)  # failure traceback
    worker_id = Column(String(36), ForeignKey("workers.id"), nullable=True, index=True)
    date_created = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    date_done = Column(DateTime, nullable=True)
    retries = Column(Integer, default=0)
    parent_id = Column(String(36), ForeignKey("tasks.id"), nullable=True)
    is_orphan = Column(Boolean, default=False, index=True)
    queue = Column(String(100), nullable=True, index=True)
    routing_key = Column(String(100), nullable=True)
    # full-text search vector could be added for PostgreSQL, but for sqlite we use simple LIKE

    worker = relationship("WorkerModel", back_populates="tasks")
    retry_attempts = relationship("TaskRetryModel", back_populates="task", cascade="all, delete-orphan", order_by="TaskRetryModel.retry_number")
    parent = relationship("TaskModel", remote_side=[id], backref="children")   # self-referential

    __table_args__ = (
        Index("ix_tasks_fulltext", "name", "args", "kwargs", "result", postgresql_using="gin"),
    )

class WorkerModel(Base):
    __tablename__ = "workers"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    hostname = Column(String(255), unique=True, nullable=False, index=True)
    status = Column(SAEnum(WorkerStatus), default=WorkerStatus.OFFLINE, nullable=False, index=True)
    last_heartbeat = Column(DateTime, nullable=True)
    pid = Column(Integer, nullable=True)
    # additional metadata
    software_identity = Column(String(255), nullable=True)
    software_version = Column(String(50), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    tasks = relationship("TaskModel", back_populates="worker")

class TaskRetryModel(Base):
    __tablename__ = "task_retries"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    task_id = Column(String(36), ForeignKey("tasks.id"), nullable=False, index=True)
    retry_number = Column(Integer, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    scheduled_at = Column(DateTime, nullable=True)
    exception = Column(Text, nullable=True)
    traceback = Column(Text, nullable=True)

    task = relationship("TaskModel", back_populates="retry_attempts")

    __table_args__ = (
        UniqueConstraint("task_id", "retry_number", name="uq_task_retry_number"),
    )

class DailyTaskStats(Base):
    __tablename__ = "daily_task_stats"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    date = Column(Date, unique=True, nullable=False, index=True)
    total_tasks = Column(Integer, default=0)
    succeeded = Column(Integer, default=0)
    failed = Column(Integer, default=0)
    retried = Column(Integer, default=0)
    orphaned = Column(Integer, default=0)
    pending = Column(Integer, default=0)
    average_duration = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

# ------------------------------------------------------------------------------
# Pydantic Schemas
# ------------------------------------------------------------------------------
class WorkerBase(BaseModel):
    hostname: str
    status: WorkerStatus
    last_heartbeat: Optional[datetime] = None
    pid: Optional[int] = None

class WorkerResponse(WorkerBase):
    id: str
    class Config:
        orm_mode = True

class TaskRetryOut(BaseModel):
    id: str
    retry_number: int
    timestamp: datetime
    scheduled_at: Optional[datetime]
    exception: Optional[str]
    traceback: Optional[str]
    class Config:
        orm_mode = True

class TaskBase(BaseModel):
    task_id: str
    name: str
    args: Optional[str] = None
    kwargs: Optional[str] = None
    status: TaskStatus
    result: Optional[str] = None
    traceback: Optional[str] = None
    worker_id: Optional[str] = None
    date_created: datetime
    date_done: Optional[datetime] = None
    retries: int
    parent_id: Optional[str] = None
    is_orphan: bool = False
    queue: Optional[str] = None
    routing_key: Optional[str] = None

class TaskResponse(TaskBase):
    id: str
    worker: Optional[WorkerResponse] = None
    retry_attempts: List[TaskRetryOut] = []
    class Config:
        orm_mode = True

class TaskFilterParams(BaseModel):
    status: Optional[List[TaskStatus]] = Query(None)
    name: Optional[str] = None
    worker: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    search: Optional[str] = None
    is_orphan: Optional[bool] = None
    order_by: Optional[str] = "date_created"
    order_desc: bool = True
    offset: int = 0
    limit: int = 50

class TaskRetryRequest(BaseModel):
    # retry a task manually
    task_id: str  # the original task_id
    args: Optional[str] = None
    kwargs: Optional[str] = None

class DailyStatsQuery(BaseModel):
    start_date: date
    end_date: date

class DailyStatsResponse(BaseModel):
    date: date
    total_tasks: int
    succeeded: int
    failed: int
    retried: int
    orphaned: int
    pending: int
    average_duration: float
    class Config:
        orm_mode = True

# ------------------------------------------------------------------------------
# WebSocket Manager
# ------------------------------------------------------------------------------
class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast(self, message: dict):
        payload = json.dumps(message, default=str)
        for connection in self.active_connections:
            try:
                await connection.send_text(payload)
            except Exception:
                self.active_connections.discard(connection)

manager = ConnectionManager()

# ------------------------------------------------------------------------------
# Celery Event Receiver (sync) – runs in background thread
# ------------------------------------------------------------------------------
class CeleryEventListener:
    def __init__(self, broker_url: str):
        self.broker_url = broker_url
        self.state = State()
        self.receiver: Optional[EventReceiver] = None
        self.running = False

    def _event_handler(self, event: dict):
        event_type = event.get("type")
        try:
            if event_type == "task-sent":
                self._handle_task_sent(event)
            elif event_type == "task-received":
                self._handle_task_received(event)
            elif event_type == "task-started":
                self._handle_task_started(event)
            elif event_type == "task-succeeded":
                self._handle_task_succeeded(event)
            elif event_type == "task-failed":
                self._handle_task_failed(event)
            elif event_type == "task-retried":
                self._handle_task_retried(event)
            elif event_type == "task-revoked":
                self._handle_task_revoked(event)
            elif event_type == "worker-heartbeat":
                self._handle_worker_heartbeat(event)
            elif event_type == "worker-online":
                self._handle_worker_online(event)
            elif event_type == "worker-offline":
                self._handle_worker_offline(event)
        except Exception:
            logger.exception(f"Error processing event {event_type}")

        # Broadcast to websockets in the main event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.run_coroutine_threadsafe(manager.broadcast({"event": event_type, "data": event}), loop)

    def _sync_db_session(self):
        return sync_session_factory()

    def _handle_task_sent(self, event):
        # task-sent: task_id, name, args, kwargs, queue, etc.
        with self._sync_db_session() as db:
            task = db.query(TaskModel).filter_by(task_id=event["uuid"]).first()
            if not task:
                task = TaskModel(
                    task_id=event["uuid"],
                    name=event["name"],
                    args=event.get("args") or "[]",
                    kwargs=event.get("kwargs") or "{}",
                    status=TaskStatus.PENDING,
                    queue=event.get("queue"),
                    routing_key=event.get("routing_key"),
                )
                db.add(task)
            else:
                task.name = event["name"]
                task.args = event.get("args") or task.args
                task.kwargs = event.get("kwargs") or task.kwargs
                task.queue = event.get("queue") or task.queue
            db.commit()

    def _handle_task_received(self, event):
        with self._sync_db_session() as db:
            task = db.query(TaskModel).filter_by(task_id=event["uuid"]).first()
            if task and task.status == TaskStatus.PENDING:
                task.status = TaskStatus.RECEIVED
                task.worker_id = None  # set later when started
                db.commit()

    def _handle_task_started(self, event):
        with self._sync_db_session() as db:
            task = db.query(TaskModel).filter_by(task_id=event["uuid"]).first()
            if task:
                task.status = TaskStatus.STARTED
                task.date_done = None
                # find worker from hostname
                worker = db.query(WorkerModel).filter_by(hostname=event["hostname"]).first()
                if not worker:
                    worker = WorkerModel(hostname=event["hostname"], status=WorkerStatus.ONLINE, last_heartbeat=datetime.utcnow())
                    db.add(worker)
                    db.flush()
                task.worker_id = worker.id
                db.commit()

    def _handle_task_succeeded(self, event):
        with self._sync_db_session() as db:
            task = db.query(TaskModel).filter_by(task_id=event["uuid"]).first()
            if task:
                task.status = TaskStatus.SUCCESS
                task.result = event.get("result") or None
                task.date_done = datetime.fromtimestamp(event["timestamp"])
                db.commit()

    def _handle_task_failed(self, event):
        with self._sync_db_session() as db:
            task = db.query(TaskModel).filter_by(task_id=event["uuid"]).first()
            if task:
                exception = event.get("exception")
                task.status = TaskStatus.FAILURE
                task.result = json.dumps({"exception": str(exception)} if exception else {})
                task.traceback = event.get("traceback")
                task.date_done = datetime.fromtimestamp(event["timestamp"])
                db.commit()

    def _handle_task_retried(self, event):
        with self._sync_db_session() as db:
            task = db.query(TaskModel).filter_by(task_id=event["uuid"]).first()
            if task:
                # increase retries
                task.retries += 1
                task.status = TaskStatus.RETRY
                # add retry record
                retry_record = TaskRetryModel(
                    task_id=task.id,
                    retry_number=task.retries,
                    timestamp=datetime.fromtimestamp(event["timestamp"]),
                    scheduled_at=datetime.fromtimestamp(event.get("eta")) if event.get("eta") else None,
                    exception=event.get("exception"),
                    traceback=event.get("traceback"),
                )
                db.add(retry_record)
                db.commit()

    def _handle_task_revoked(self, event):
        with self._sync_db_session() as db:
            task = db.query(TaskModel).filter_by(task_id=event["uuid"]).first()
            if task:
                task.status = TaskStatus.REVOKED
                task.date_done = datetime.fromtimestamp(event["timestamp"])
                task.result = "Revoked"
                db.commit()

    def _handle_worker_heartbeat(self, event):
        with self._sync_db_session() as db:
            worker = db.query(WorkerModel).filter_by(hostname=event["hostname"]).first()
            if worker:
                worker.last_heartbeat = datetime.fromtimestamp(event["timestamp"])
                worker.pid = event.get("pid")
                if worker.status != WorkerStatus.ONLINE:
                    worker.status = WorkerStatus.ONLINE
                db.commit()
            else:
                worker = WorkerModel(
                    hostname=event["hostname"],
                    status=WorkerStatus.ONLINE,
                    last_heartbeat=datetime.fromtimestamp(event["timestamp"]),
                    pid=event.get("pid"),
                )
                db.add(worker)
                db.commit()

    def _handle_worker_online(self, event):
        with self._sync_db_session() as db:
            worker = db.query(WorkerModel).filter_by(hostname=event["hostname"]).first()
            if worker:
                worker.status = WorkerStatus.ONLINE
                worker.last_heartbeat = datetime.fromtimestamp(event["timestamp"])
                if event.get("pid") is not None:
                    worker.pid = event["pid"]
                db.commit()
            else:
                worker = WorkerModel(
                    hostname=event["hostname"],
                    status=WorkerStatus.ONLINE,
                    last_heartbeat=datetime.fromtimestamp(event["timestamp"]),
                    pid=event.get("pid"),
                )
                db.add(worker)
                db.commit()

    def _handle_worker_offline(self, event):
        with self._sync_db_session() as db:
            worker = db.query(WorkerModel).filter_by(hostname=event["hostname"]).first()
            if worker:
                worker.status = WorkerStatus.OFFLINE
                db.commit()

    def run(self):
        self.running = True
        try:
            self.receiver = EventReceiver(
                connection=self.broker_url,
                app=None,
                handlers={"*": self._event_handler},
                on_heartbeat_interval=10,
            )
            self.receiver.capture(limit=None, timeout=None, wakeup=True)
        except Exception:
            logger.exception("Failed to start Celery event listener. Continuing without real-time events.")
        finally:
            self.running = False

event_listener = CeleryEventListener(CELERY_BROKER_URL)

# ------------------------------------------------------------------------------
# FastAPI app
# ------------------------------------------------------------------------------
app = FastAPI(title="Kanchi", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------------------
# Startup / Shutdown events
# ------------------------------------------------------------------------------
@app.on_event("startup")
async def startup():
    # Run Alembic migrations
    try:
        subprocess.run(["alembic", "upgrade", "head"], check=True)
        logger.info("Database migrations applied successfully.")
    except Exception as e:
        logger.warning(f"Could not run Alembic migrations: {e}. Assuming schema is up-to-date.")

    # Create tables if not exist (fallback for sqlite without alembic)
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Start Celery event listener in a background thread
    import threading
    th = threading.Thread(target=event_listener.run, daemon=True)
    th.start()

    # Start daily stats calculation and orphan detection scheduler
    asyncio.create_task(scheduler_loop())

@app.on_event("shutdown")
async def shutdown():
    pass

# ------------------------------------------------------------------------------
# Dependency
# ------------------------------------------------------------------------------
async def get_db() -> AsyncSession:
    async with async_session_factory() as session:
        yield session

# ------------------------------------------------------------------------------
# Helper: build task filter query
# ------------------------------------------------------------------------------
def apply_task_filters(query, filters: TaskFilterParams):
    if filters.status:
        query = query.filter(TaskModel.status.in_(filters.status))
    if filters.name:
        query = query.filter(TaskModel.name.ilike(f"%{filters.name}%"))
    if filters.worker:
        # worker hostname or id
        query = query.join(WorkerModel).filter(WorkerModel.hostname.ilike(f"%{filters.worker}%"))
    if filters.date_from:
        query = query.filter(TaskModel.date_created >= filters.date_from)
    if filters.date_to:
        query = query.filter(TaskModel.date_created <= filters.date_to)
    if filters.is_orphan is not None:
        query = query.filter(TaskModel.is_orphan == filters.is_orphan)
    if filters.search:
        # full-text search across name, args, kwargs, result (simple LIKE for sqlite)
        search_term = f"%{filters.search}%"
        query = query.filter(
            or_(
                TaskModel.name.ilike(search_term),
                TaskModel.args.ilike(search_term),
                TaskModel.kwargs.ilike(search_term),
                TaskModel.result.ilike(search_term),
            )
        )
    # ordering
    order_col = getattr(TaskModel, filters.order_by, TaskModel.date_created)
    if filters.order_desc:
        query = query.order_by(order_col.desc())
    else:
        query = query.order_by(order_col)
    return query

# ------------------------------------------------------------------------------
# API Routes
# ------------------------------------------------------------------------------
@app.get("/api/tasks", response_model=List[TaskResponse])
async def list_tasks(
    filters: TaskFilterParams = Depends(),
    db: AsyncSession = Depends(get_db),
):
    query = select(TaskModel).options(joinedload(TaskModel.worker), joinedload(TaskModel.retry_attempts))
    query = apply_task_filters(query, filters)
    query = query.offset(filters.offset).limit(filters.limit)
    result = await db.execute(query)
    tasks = result.unique().scalars().all()
    return tasks

@app.get("/api/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    query = select(TaskModel).options(joinedload(TaskModel.worker), joinedload(TaskModel.retry_attempts)).filter(TaskModel.task_id == task_id)
    result = await db.execute(query)
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@app.post("/api/tasks/retry")
async def retry_task(
    request: TaskRetryRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    # This is a manual retry; we'll just re-send the task using Celery if possible.
    # Here we mock by updating status back to PENDING.
    query = select(TaskModel).filter(TaskModel.task_id == request.task_id)
    result = await db.execute(query)
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status not in [TaskStatus.FAILURE, TaskStatus.REVOKED, TaskStatus.RETRY]:
        raise HTTPException(status_code=400, detail="Can only retry tasks in FAILURE, REVOKED, or RETRY state.")
    
    # Create a new task in pending state as a retry
    new_task = TaskModel(
        task_id=str(uuid4()),  # new id
        name=task.name,
        args=request.args or task.args,
        kwargs=request.kwargs or task.kwargs,
        status=TaskStatus.PENDING,
        parent_id=task.id,
        queue=task.queue,
        routing_key=task.routing_key,
    )
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)
    
    # In a real scenario, you would publish a new message to the broker.
    # Here we just rely on the event listener to pick it up if the Celery producer also sends events.
    # For simulation, we add a background task to send a task-sent event manually.
    background_tasks.add_task(simulate_task_retry_sent, new_task.task_id)
    return {"message": "Task retry initiated", "new_task_id": new_task.task_id}

async def simulate_task_retry_sent(task_id: str):
    # Simulate sending a 'task-sent' event so the listener picks it up.
    # In production, you would use Celery to publish.
    import time
    event = {
        "type": "task-sent",
        "uuid": task_id,
        "name": "retrieved-from-db",  # placeholder
        "args": "[]",
        "kwargs": "{}",
        "queue": "default",
        "timestamp": time.time(),
    }
    # We'll add to the event listener's state manually.
    if event_listener.receiver:
        event_listener._event_handler(event)

@app.get("/api/workers", response_model=List[WorkerResponse])
async def list_workers(
    status: Optional[WorkerStatus] = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(WorkerModel)
    if status:
        query = query.filter(WorkerModel.status == status)
    result = await db.execute(query)
    workers = result.scalars().all()
    return workers

@app.get("/api/workers/{worker_id}", response_model=WorkerResponse)
async def get_worker(
    worker_id: str,
    db: AsyncSession = Depends(get_db),
):
    query = select(WorkerModel).filter(WorkerModel.id == worker_id)
    result = await db.execute(query)
    worker = result.scalars().first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    return worker

@app.get("/api/stats/daily", response_model=List[DailyStatsResponse])
async def daily_stats(
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: AsyncSession = Depends(get_db),
):
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date must be before end_date")
    query = select(DailyTaskStats).filter(
        DailyTaskStats.date >= start_date,
        DailyTaskStats.date <= end_date,
    ).order_by(DailyTaskStats.date)
    result = await db.execute(query)
    stats = result.scalars().all()
    return stats

@app.post("/api/orphans/detect")
async def detect_orphans(db: AsyncSession = Depends(get_db)):
    """Manually trigger orphan detection: mark tasks as orphan if their worker is offline and task is still running."""
    # Find tasks that are in running state (STARTED, RECEIVED) and whose worker is offline or missing
    offline_worker_ids = (
        await db.execute(
            select(WorkerModel.id).filter(WorkerModel.status == WorkerStatus.OFFLINE)
        )
    ).scalars().all()
    
    tasks_to_orphan = await db.execute(
        select(TaskModel).filter(
            TaskModel.status.in_([TaskStatus.STARTED, TaskStatus.RECEIVED]),
            TaskModel.is_orphan == False,
            or_(
                TaskModel.worker_id == None,
                TaskModel.worker_id.in_(offline_worker_ids),
            ),
        )
    )
    for task in tasks_to_orphan.scalars():
        task.is_orphan = True
        # Optionally change status to ORPHAN
        # task.status = TaskStatus.ORPHAN
    await db.commit()
    return {"orphans_detected": tasks_to_orphan.rowcount if hasattr(tasks_to_orphan, 'rowcount') else "unknown"}

# ------------------------------------------------------------------------------
# Daily stats aggregation and orphan detection scheduler
# ------------------------------------------------------------------------------
async def compute_daily_stats(db: AsyncSession, target_date: date = None):
    """Compute stats for a specific date (default yesterday)."""
    if target_date is None:
        target_date = date.today() - timedelta(days=1)
    
    # Check if stats already exist for that date
    existing = await db.execute(
        select(DailyTaskStats).filter(DailyTaskStats.date == target_date)
    )
    if existing.scalars().first():
        return  # already computed
    
    # Aggregate tasks for that day
    day_start = datetime(target_date.year, target_date.month, target_date.day)
    day_end = day_start + timedelta(days=1)
    
    # Using sync style? We'll use raw async query
    total = await db.scalar(
        select(func.count()).where(TaskModel.date_created >= day_start, TaskModel.date_created < day_end)
    )
    succeeded = await db.scalar(
        select(func.count()).where(
            TaskModel.date_created >= day_start,
            TaskModel.date_created < day_end,
            TaskModel.status == TaskStatus.SUCCESS,
        )
    )
    failed = await db.scalar(
        select(func.count()).where(
            TaskModel.date_created >= day_start,
            TaskModel.date_created < day_end,
            TaskModel.status == TaskStatus.FAILURE,
        )
    )
    retried = await db.scalar(
        select(func.count()).where(
            TaskRetryModel.timestamp >= day_start,
            TaskRetryModel.timestamp < day_end,
        )
    )
    orphaned = await db.scalar(
        select(func.count()).where(
            TaskModel.date_created >= day_start,
            TaskModel.date_created < day_end,
            TaskModel.is_orphan == True,
        )
    )
    pending = await db.scalar(
        select(func.count()).where(
            TaskModel.date_created >= day_start,
            TaskModel.date_created < day_end,
            TaskModel.status == TaskStatus.PENDING,
        )
    )
    # Average duration: avg(date_done - date_created) for succeeded tasks
    avg_dur = await db.scalar(
        select(func.avg(
            func.julianday(TaskModel.date_done) - func.julianday(TaskModel.date_created)
        )).where(
            TaskModel.date_created >= day_start,
            TaskModel.date_created < day_end,
            TaskModel.status == TaskStatus.SUCCESS,
            TaskModel.date_done != None,
        )
    )
    # Convert avg from days to seconds
    avg_duration = float(avg_dur * 86400) if avg_dur else 0.0

    stats = DailyTaskStats(
        date=target_date,
        total_tasks=total or 0,
        succeeded=succeeded or 0,
        failed=failed or 0,
        retried=retried or 0,
        orphaned=orphaned or 0,
        pending=pending or 0,
        average_duration=avg_duration,
    )
    db.add(stats)
    await db.commit()

async def orphan_detection_loop():
    """Periodically run orphan detection."""
    while True:
        await asyncio.sleep(60)  # once per minute
        try:
            async with async_session_factory() as db:
                offline_worker_ids_result = await db.execute(
                    select(WorkerModel.id).filter(WorkerModel.status == WorkerStatus.OFFLINE)
                )
                offline_worker_ids = offline_worker_ids_result.scalars().all()
                stmt = (
                    update(TaskModel)
                    .where(
                        TaskModel.status.in_([TaskStatus.STARTED, TaskStatus.RECEIVED]),
                        TaskModel.is_orphan == False,
                        or_(
                            TaskModel.worker_id == None,
                            TaskModel.worker_id.in_(offline_worker_ids),
                        ),
                    )
                    .values(is_orphan=True)
                )
                result = await db.execute(stmt)
                await db.commit()
                if result.rowcount:
                    logger.info(f"Marked {result.rowcount} tasks as orphans.")
        except Exception:
            logger.exception("Error in orphan detection loop")

async def stats_computation_loop():
    """Compute daily stats for yesterday every hour."""
    while True:
        await asyncio.sleep(3600)  # once per hour
        try:
            async with async_session_factory() as db:
                await compute_daily_stats(db, date.today() - timedelta(days=1))
        except Exception:
            logger.exception("Error in stats computation loop")

async def scheduler_loop():
    await asyncio.gather(
        orphan_detection_loop(),
        stats_computation_loop(),
    )

# ------------------------------------------------------------------------------
# WebSocket endpoint
# ------------------------------------------------------------------------------
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive; we don't expect messages from client
            data = await websocket.receive_text()
            # maybe handle commands (ping, etc.)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# ------------------------------------------------------------------------------
# Alembic auto-migration (minimal) - will be called on startup
# We need to ensure that we have a valid alembic.ini and env.py pointing to our Base.metadata.
# For the sake of completeness, we embed a simple env.py that uses our Base.
# This is a simplified approach; in production, you would configure properly.
# ------------------------------------------------------------------------------
# The startup event runs `alembic upgrade head`, which requires a proper alembic configuration.
# We'll create a temporary alembic configuration if not present.
def setup_alembic():
    import tempfile
    from pathlib import Path

    # Check if alembic directory exists; if not, create a minimal one
    if not Path("alembic").exists():
        # Initialize alembic
        subprocess.run([sys.executable, "-m", "alembic", "init", "alembic"], check=True)
        # Modify alembic.ini to point to our sync database
        with open("alembic.ini", "r") as f:
            config_content = f.read()
        config_content = config_content.replace("driver://user:pass@localhost/dbname", SYNC_DATABASE_URL)
        with open("alembic.ini", "w") as f:
            f.write(config_content)
        # Overwrite env.py to use our Base metadata
        env_py_path = Path("alembic/env.py")
        env_py_content = f"""
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from kanchi import Base   # This file is supposed to be named kanchi.py

config = context.config
fileConfig(config.config_file_name)
target_metadata = Base.metadata

def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = engine_from_config(config.get_section(config.config_ini_section), prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
"""
        with open(env_py_path, "w") as f:
            f.write(env_py_content)

# Run setup if this script is main; usually we'd want to do it before starting the app.
if __name__ == "__main__":
    setup_alembic()
    uvicorn.run("kanchi:app", host="0.0.0.0", port=8000, reload=True)
else:
    # If imported (e.g., by uvicorn), do quick setup
    setup_alembic()