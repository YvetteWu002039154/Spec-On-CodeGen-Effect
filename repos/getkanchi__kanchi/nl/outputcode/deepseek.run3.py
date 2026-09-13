from __future__ import annotations

import asyncio
import datetime
import enum
import logging
import threading
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict, List, Optional, Set
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import (
    Column,
    DateTime,
    Enum as SAEnum,
    Float,
    Integer,
    String,
    Text,
    create_engine,
    func,
    select,
    and_,
    or_,
    event as sa_event,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# Optional Celery import: graceful fallback if missing
try:
    from celery import Celery
    from celery.events import EventReceiver
    from celery.events.state import State as CeleryState
except ImportError:
    Celery = None  # type: ignore
    EventReceiver = None
    CeleryState = None

logger = logging.getLogger("kanchi")
logging.basicConfig(level=logging.INFO)

# ---------------------------------------------------------------------------
# Database configuration
# ---------------------------------------------------------------------------
SQLALCHEMY_DATABASE_URL = "sqlite:///./kanchi.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class TaskState(str, enum.Enum):
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


# ---------------------------------------------------------------------------
# SQLAlchemy Models
# ---------------------------------------------------------------------------
class Task(Base):
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    celery_id = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), index=True)
    status = Column(String(50), default=TaskState.PENDING.value)
    worker = Column(String(255), nullable=True)
    args = Column(Text, nullable=True)
    kwargs = Column(Text, nullable=True)
    result = Column(Text, nullable=True)
    traceback = Column(Text, nullable=True)
    retries = Column(Integer, default=0)
    queue = Column(String(255), nullable=True)
    runtime = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    sent_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    succeeded_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    eta = Column(DateTime, nullable=True)
    expires = Column(DateTime, nullable=True)

    # Fields used for full-text search (SQLite FTS is not used for simplicity)
    __table_args__ = ()


class Worker(Base):
    __tablename__ = "workers"

    hostname = Column(String(255), primary_key=True)
    status = Column(String(50), default=WorkerStatus.ONLINE.value)
    last_heartbeat = Column(DateTime, nullable=True)
    active = Column(Integer, default=0)
    processed = Column(Integer, default=0)
    loadavg = Column(String(50), nullable=True)
    sw_ident = Column(String(255), nullable=True)
    sw_ver = Column(String(255), nullable=True)
    sw_sys = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class DailyStats(Base):
    __tablename__ = "daily_stats"

    date = Column(DateTime, primary_key=True)  # day granularity
    total = Column(Integer, default=0)
    succeeded = Column(Integer, default=0)
    failed = Column(Integer, default=0)
    retried = Column(Integer, default=0)
    avg_runtime = Column(Float, nullable=True)


# ---------------------------------------------------------------------------
# Auto-migrations with Alembic (simplified inline)
# ---------------------------------------------------------------------------
def run_migrations():
    """Auto-create tables and apply Alembic migrations if available."""
    # For a production system, use Alembic with env.py, but for demo we just create all
    Base.metadata.create_all(bind=engine)
    logger.info("Database schema up-to-date.")


# ---------------------------------------------------------------------------
# Pydantic schemas for API
# ---------------------------------------------------------------------------
class TaskOut(BaseModel):
    id: str
    celery_id: str
    name: str
    status: TaskState
    worker: Optional[str] = None
    args: Optional[str] = None
    kwargs: Optional[str] = None
    result: Optional[str] = None
    traceback: Optional[str] = None
    retries: int
    queue: Optional[str] = None
    runtime: Optional[float] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    sent_at: Optional[datetime.datetime] = None
    started_at: Optional[datetime.datetime] = None
    succeeded_at: Optional[datetime.datetime] = None
    failed_at: Optional[datetime.datetime] = None
    eta: Optional[datetime.datetime] = None
    expires: Optional[datetime.datetime] = None

    class Config:
        from_attributes = True


class WorkerOut(BaseModel):
    hostname: str
    status: WorkerStatus
    last_heartbeat: Optional[datetime.datetime] = None
    active: int
    processed: int
    loadavg: Optional[str] = None
    sw_ident: Optional[str] = None
    sw_ver: Optional[str] = None
    sw_sys: Optional[str] = None

    class Config:
        from_attributes = True


class DailyStatsOut(BaseModel):
    date: datetime.datetime
    total: int
    succeeded: int
    failed: int
    retried: int
    avg_runtime: Optional[float] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# WebSocket manager for broadcasting task updates
# ---------------------------------------------------------------------------
class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.active_connections.discard(connection)


manager = ConnectionManager()


# ---------------------------------------------------------------------------
# Celery event monitor (runs in background thread)
# ---------------------------------------------------------------------------
class CeleryMonitor:
    """Real-time monitor that updates the database on Celery events."""

    def __init__(self, app: Celery, db_session_factory, loop: asyncio.AbstractEventLoop):
        self.app = app
        self.db_factory = db_session_factory
        self.loop = loop
        self.state = None
        if CeleryState:
            self.state = CeleryState()

    def _process_event(self, event: dict):
        """Handle a single Celery event and persist to DB."""
        event_type = event.get("type")
        uuid = event.get("uuid")
        if not uuid:
            return

        with self.db_factory() as session:
            task = session.query(Task).filter(Task.celery_id == uuid).first()
            if not task:
                # Create new task record
                task = Task(celery_id=uuid, name=event.get("name", "unknown"))
                session.add(task)
                session.flush()

            # Update fields based on event type
            task.name = event.get("name", task.name)
            task.worker = event.get("hostname", task.worker)
            task.queue = event.get("routing_key") or event.get("queue", task.queue)

            if event_type == "task-sent":
                task.status = TaskState.PENDING if task.status in (TaskState.PENDING, "RECEIVED") else task.status
                task.sent_at = datetime.datetime.utcnow()
            elif event_type == "task-received":
                task.status = TaskState.RECEIVED
            elif event_type == "task-started":
                task.status = TaskState.STARTED
                task.started_at = datetime.datetime.utcnow()
            elif event_type == "task-succeeded":
                task.status = TaskState.SUCCESS
                task.result = str(event.get("result", ""))[:1000]
                task.runtime = event.get("runtime")
                task.succeeded_at = datetime.datetime.utcnow()
                # Update daily stats
                self._update_daily_stats(session, task, TaskState.SUCCESS)
            elif event_type == "task-failed":
                task.status = TaskState.FAILURE
                task.traceback = event.get("exception", "")[:2000]
                task.runtime = event.get("runtime")
                task.failed_at = datetime.datetime.utcnow()
                self._update_daily_stats(session, task, TaskState.FAILURE)
            elif event_type == "task-retried":
                task.retries += 1
                task.status = TaskState.RETRY
                self._update_daily_stats(session, task, TaskState.RETRY)
            elif event_type == "task-revoked":
                task.status = TaskState.REVOKED

            # Worker related events
            if event_type in ("worker-online", "worker-offline", "worker-heartbeat"):
                hostname = event.get("hostname")
                if hostname:
                    worker = session.query(Worker).filter(Worker.hostname == hostname).first()
                    if not worker:
                        worker = Worker(hostname=hostname)
                        session.add(worker)
                    if event_type == "worker-online":
                        worker.status = WorkerStatus.ONLINE
                    elif event_type == "worker-offline":
                        worker.status = WorkerStatus.OFFLINE
                    worker.last_heartbeat = datetime.datetime.utcnow()
                    worker.processed = event.get("processed", worker.processed)
                    worker.active = event.get("active", worker.active)
                    worker.loadavg = str(event.get("loadavg", worker.loadavg))
                    sw = event.get("sw_ident")
                    if sw:
                        worker.sw_ident = sw
                    sw_ver = event.get("sw_ver")
                    if sw_ver:
                        worker.sw_ver = sw_ver
                    sw_sys = event.get("sw_sys")
                    if sw_sys:
                        worker.sw_sys = sw_sys

            session.commit()

            # Broadcast update via WebSocket
            task_data = {
                "id": str(task.id),
                "celery_id": task.celery_id,
                "name": task.name,
                "status": task.status,
                "worker": task.worker,
                "retries": task.retries,
                "runtime": task.runtime,
                "timestamp": datetime.datetime.utcnow().isoformat(),
            }
            asyncio.run_coroutine_threadsafe(manager.broadcast(task_data), self.loop)

    def _update_daily_stats(self, session: Session, task: Task, final_status: TaskState):
        """Aggregate daily statistics when a task reaches a terminal state."""
        day = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        stats = session.query(DailyStats).filter(DailyStats.date == day).first()
        if not stats:
            stats = DailyStats(date=day, total=0, succeeded=0, failed=0, retried=0)
            session.add(stats)
        stats.total += 1
        if final_status == TaskState.SUCCESS:
            stats.succeeded += 1
        elif final_status == TaskState.FAILURE:
            stats.failed += 1
        elif final_status == TaskState.RETRY:
            stats.retried += 1
        # Update average runtime if meaningful
        if task.runtime is not None:
            if stats.avg_runtime is None:
                stats.avg_runtime = task.runtime
            else:
                # naive incremental average
                n = stats.total - 1  # previous total (excluding current)
                stats.avg_runtime = (stats.avg_runtime * n + task.runtime) / stats.total

    def run(self):
        """Start listening to Celery events."""
        if not Celery:
            logger.error("Celery not installed. Event monitoring disabled.")
            return
        with self.app.connection() as connection:
            recv: EventReceiver = self.app.events.Receiver(
                connection,
                handlers={
                    "*": self._process_event
                }
            )
            logger.info("Celery event monitor started.")
            try:
                recv.capture(limit=None, timeout=None, wakeup=True)
            except KeyboardInterrupt:
                pass
            except Exception as e:
                logger.exception("Event monitor error")


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Run migrations
    run_migrations()
    # Try to create a Celery app if configuration provided (env variables fallback)
    broker_url = "redis://localhost:6379/0"  # example; can be overridden via env
    celery_app = None
    if Celery:
        celery_app = Celery("kanchi", broker=broker_url, backend=broker_url)
        # Disable the default Celery task sender to avoid interference
        celery_app.conf.task_always_eager = False
        celery_app.conf.task_ignore_result = False
        celery_app.conf.broker_connection_retry_on_startup = True
    if celery_app:
        monitor = CeleryMonitor(celery_app, SessionLocal, asyncio.get_running_loop())
        monitor_thread = threading.Thread(target=monitor.run, daemon=True)
        monitor_thread.start()
    yield
    # Cleanup resources if any

app = FastAPI(title="Kanchi", version="0.1.0", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helper function to get DB session
# ---------------------------------------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# REST Endpoints
# ---------------------------------------------------------------------------
@app.get("/tasks", response_model=List[TaskOut])
def list_tasks(
    status: Optional[List[TaskState]] = Query(None),
    name: Optional[str] = None,
    worker: Optional[str] = None,
    search: Optional[str] = None,
    start_date: Optional[datetime.datetime] = None,
    end_date: Optional[datetime.datetime] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    query = db.query(Task)
    if status:
        query = query.filter(Task.status.in_([s.value for s in status]))
    if name:
        query = query.filter(Task.name.ilike(f"%{name}%"))
    if worker:
        query = query.filter(Task.worker == worker)
    if search:
        # Full-text-like search across name, args, kwargs, result, traceback
        like = f"%{search}%"
        query = query.filter(
            or_(
                Task.name.ilike(like),
                Task.args.ilike(like),
                Task.kwargs.ilike(like),
                Task.result.ilike(like),
                Task.traceback.ilike(like),
            )
        )
    if start_date:
        query = query.filter(Task.created_at >= start_date)
    if end_date:
        query = query.filter(Task.created_at <= end_date)
    query = query.order_by(Task.updated_at.desc())
    tasks = query.offset(skip).limit(limit).all()
    return tasks


@app.get("/tasks/{task_id}", response_model=TaskOut)
def get_task(task_id: str, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.get("/workers", response_model=List[WorkerOut])
def list_workers(db: Session = Depends(get_db)):
    return db.query(Worker).all()


@app.get("/stats/daily", response_model=List[DailyStatsOut])
def daily_stats(
    start_date: Optional[datetime.datetime] = None,
    end_date: Optional[datetime.datetime] = None,
    db: Session = Depends(get_db),
):
    q = db.query(DailyStats)
    if start_date:
        q = q.filter(DailyStats.date >= start_date)
    if end_date:
        q = q.filter(DailyStats.date <= end_date)
    q = q.order_by(DailyStats.date.asc())
    return q.all()


@app.get("/orphans", response_model=List[TaskOut])
def detect_orphans(
    max_idle_minutes: int = 30,
    db: Session = Depends(get_db),
):
    """Return tasks that are STARTED but haven't updated for longer than max_idle_minutes."""
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(minutes=max_idle_minutes)
    orphaned = (
        db.query(Task)
        .filter(
            Task.status == TaskState.STARTED.value,
            Task.updated_at < cutoff,
        )
        .all()
    )
    return orphaned


# ---------------------------------------------------------------------------
# WebSocket endpoint for real-time updates
# ---------------------------------------------------------------------------
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ---------------------------------------------------------------------------
# Run the application with uvicorn if executed directly
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)