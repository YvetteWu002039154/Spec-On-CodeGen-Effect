import asyncio
import json
import logging
import os
import sys
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlparse

from celery import Celery
from celery.events import EventReceiver
from celery.events.state import State
from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn
from sqlalchemy import (
    Boolean,
    Column,
    create_engine,
    DateTime,
    Float,
    Integer,
    JSON,
    inspect,
    or_,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.sql import func

# ------------------------------------------------------------------------------
# Configuration (environment variables)
# ------------------------------------------------------------------------------

BROKER_URL = os.getenv("KANCHI_BROKER_URL", "redis://localhost:6379/0")
DATABASE_URL = os.getenv("KANCHI_DATABASE_URL", "sqlite:///kanchi.db")
AUTO_MIGRATE = os.getenv("KANCHI_AUTO_MIGRATE", "true").lower() == "true"
ALEMBIC_INI_PATH = os.getenv("KANCHI_ALEMBIC_INI", "alembic.ini")
ORPHAN_TIMEOUT_SECONDS = int(os.getenv("KANCHI_ORPHAN_TIMEOUT", "300"))
WEBSOCKET_BROADCAST_CHUNK = int(os.getenv("KANCHI_WS_CHUNK", "100"))

# ------------------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------------------

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger("kanchi")

# ------------------------------------------------------------------------------
# Database setup
# ------------------------------------------------------------------------------

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = scoped_session(sessionmaker(bind=engine))
Base = declarative_base()

class TaskEvent(Base):
    __tablename__ = "task_events"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String, unique=True, index=True)  # UUID from event
    timestamp = Column(DateTime, default=func.now(), index=True)
    state = Column(String(32), index=True)  # SENT, RECEIVED, STARTED, SUCCESS, FAILURE, RETRY
    task_id = Column(String(255), index=True)
    task_name = Column(String(255), index=True)
    worker = Column(String(255), nullable=True, index=True)
    args = Column(JSON, nullable=True)
    kwargs = Column(JSON, nullable=True)
    result = Column(Text, nullable=True)
    traceback = Column(Text, nullable=True)
    exception = Column(String, nullable=True)
    retries = Column(Integer, default=0)
    parent_id = Column(String(255), nullable=True, index=True)
    expires = Column(DateTime, nullable=True)
    eta = Column(DateTime, nullable=True)
    runtime = Column(Float, nullable=True)

    def __repr__(self):
        return f"<TaskEvent {self.task_id} {self.state}>"

class WorkerHeartbeat(Base):
    __tablename__ = "worker_heartbeats"

    id = Column(Integer, primary_key=True, index=True)
    hostname = Column(String(255), unique=True, index=True)
    last_heartbeat = Column(DateTime, default=func.now())
    status = Column(String(10), default="ONLINE")  # ONLINE/OFFLINE

class DailyTaskStats(Base):
    __tablename__ = "daily_task_stats"
    __table_args__ = (UniqueConstraint("date", "task_name", name="uq_daily_stats"),)

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, index=True)
    task_name = Column(String(255), index=True)
    total_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)
    retry_count = Column(Integer, default=0)
    total_runtime = Column(Float, default=0.0)
    avg_runtime = Column(Float, default=0.0)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ------------------------------------------------------------------------------
# WebSocket manager
# ------------------------------------------------------------------------------

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected, total: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        logger.info(f"WebSocket client disconnected, total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        async with self._lock:
            # Copy list to avoid mutation during iteration
            connections = self.active_connections.copy()
        if not connections:
            return
        payload = json.dumps(message, default=str)
        # Send to all; handle disconnections gracefully
        for ws in connections:
            try:
                await ws.send_text(payload)
            except Exception:
                # Remove in next cleanup or handle silently
                pass

manager = ConnectionManager()

# ------------------------------------------------------------------------------
# FastAPI app
# ------------------------------------------------------------------------------

app = FastAPI(title="Kanchi", description="Real-time Celery task monitoring (and management) system")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive by receiving messages (ping/pong)
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket)

# ------------------------------------------------------------------------------
# REST API Pydantic models
# ------------------------------------------------------------------------------

class TaskEventOut(BaseModel):
    id: int
    event_id: str
    timestamp: datetime
    state: str
    task_id: str
    task_name: str
    worker: Optional[str]
    args: Optional[Any]
    kwargs: Optional[Any]
    result: Optional[str]
    traceback: Optional[str]
    exception: Optional[str]
    retries: int = 0
    parent_id: Optional[str]
    runtime: Optional[float]

    class Config:
        from_attributes = True

class WorkerOut(BaseModel):
    hostname: str
    last_heartbeat: datetime
    status: str

class DailyStatsOut(BaseModel):
    date: datetime
    task_name: str
    total_count: int
    success_count: int
    failure_count: int
    retry_count: int
    avg_runtime: float

# Helper to serialize event to dict for WebSocket broadcast
def event_to_payload(ev: TaskEvent) -> dict:
    return {
        "id": ev.id,
        "event_id": ev.event_id,
        "timestamp": ev.timestamp.isoformat() if ev.timestamp else None,
        "state": ev.state,
        "task_id": ev.task_id,
        "task_name": ev.task_name,
        "worker": ev.worker,
        "args": json.dumps(ev.args) if isinstance(ev.args, (dict, list)) else str(ev.args),
        "kwargs": json.dumps(ev.kwargs) if isinstance(ev.kwargs, (dict, list)) else str(ev.kwargs),
        "retries": ev.retries,
        "parent_id": ev.parent_id,
        "runtime": ev.runtime,
    }

# ------------------------------------------------------------------------------
# API Endpoints
# ------------------------------------------------------------------------------

@app.get("/api/tasks", response_model=List[TaskEventOut])
def list_tasks(
    search: Optional[str] = Query(None, description="Full-text search across task_name, task_id, worker"),
    status: Optional[str] = Query(None, description="Comma-separated states"),
    task_name: Optional[str] = Query(None),
    worker: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    limit: int = Query(100, ge=1, le=5000),
    offset: int = Query(0, ge=0),
    db: Session = None,
):
    if db is None:
        db = next(get_db())
    query = db.query(TaskEvent)

    if search:
        search_filter = or_(
            TaskEvent.task_name.ilike(f"%{search}%"),
            TaskEvent.task_id.ilike(f"%{search}%"),
            TaskEvent.worker.ilike(f"%{search}%"),
            TaskEvent.event_id.ilike(f"%{search}%"),
        )
        query = query.filter(search_filter)

    if status:
        states = [s.strip() for s in status.split(",") if s.strip()]
        if states:
            query = query.filter(TaskEvent.state.in_(states))

    if task_name:
        query = query.filter(TaskEvent.task_name == task_name)

    if worker:
        query = query.filter(TaskEvent.worker == worker)

    if date_from:
        query = query.filter(TaskEvent.timestamp >= date_from)
    if date_to:
        query = query.filter(TaskEvent.timestamp <= date_to)

    total = query.count()
    results = query.order_by(TaskEvent.timestamp.desc()).offset(offset).limit(limit).all()
    return results

@app.get("/api/tasks/daily-stats", response_model=List[DailyStatsOut])
def daily_stats(
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    task_name: Optional[str] = Query(None),
    db: Session = None,
):
    if db is None:
        db = next(get_db())
    query = db.query(DailyTaskStats)
    if date_from:
        query = query.filter(DailyTaskStats.date >= date_from)
    if date_to:
        query = query.filter(DailyTaskStats.date <= date_to)
    if task_name:
        query = query.filter(DailyTaskStats.task_name == task_name)
    return query.all()

@app.get("/api/tasks/orphans", response_model=List[TaskEventOut])
def orphans(
    timeout_minutes: int = Query(ORPHAN_TIMEOUT_SECONDS // 60, ge=1),
    db: Session = None,
):
    if db is None:
        db = next(get_db())
    threshold = datetime.utcnow() - timedelta(minutes=timeout_minutes)
    # Find tasks that are in STARTED state with no later terminal event
    subquery = db.query(TaskEvent.task_id).filter(
        TaskEvent.state.in_(["SUCCESS", "FAILURE"]),
        TaskEvent.timestamp > threshold,
    ).subquery()

    orphans = db.query(TaskEvent).filter(
        TaskEvent.state == "STARTED",
        TaskEvent.timestamp < threshold,
        ~TaskEvent.task_id.in_(subquery),
    ).all()
    return orphans

@app.get("/api/tasks/{task_id}/retries", response_model=List[TaskEventOut])
def task_retries(task_id: str, db: Session = None):
    if db is None:
        db = next(get_db())
    retries = db.query(TaskEvent).filter(
        TaskEvent.task_id == task_id,
        TaskEvent.state == "RETRY",
    ).order_by(TaskEvent.timestamp).all()
    return retries

@app.get("/api/workers", response_model=List[WorkerOut])
def list_workers(db: Session = None):
    if db is None:
        db = next(get_db())
    now = datetime.utcnow()
    online_threshold = timedelta(minutes=2)  # workers that have sent heartbeat within 2 minutes are online
    workers = db.query(WorkerHeartbeat).all()
    result = []
    for w in workers:
        status = "ONLINE" if (now - w.last_heartbeat) < online_threshold else "OFFLINE"
        result.append(WorkerOut(hostname=w.hostname, last_heartbeat=w.last_heartbeat, status=status))
    return result

# ------------------------------------------------------------------------------
# Celery event monitor (background thread)
# ------------------------------------------------------------------------------

celery_app = Celery("kanchi_monitor", broker=BROKER_URL)

def create_event_receiver() -> EventReceiver:
    # Using a fresh connection
    connection = celery_app.connection()
    receiver = EventReceiver(connection, handlers={
        "task-sent": handle_task_event,
        "task-received": handle_task_event,
        "task-started": handle_task_event,
        "task-succeeded": handle_task_event,
        "task-failed": handle_task_event,
        "task-retried": handle_task_event,
        "worker-online": handle_worker_event,
        "worker-offline": handle_worker_event,
        "worker-heartbeat": handle_worker_event,
    })
    return receiver

def handle_task_event(event: dict):
    if not event:
        return
    # Map event type to state
    type_map = {
        "task-sent": "SENT",
        "task-received": "RECEIVED",
        "task-started": "STARTED",
        "task-succeeded": "SUCCESS",
        "task-failed": "FAILURE",
        "task-retried": "RETRY",
    }
    state_str = type_map.get(event["type"], event["type"])

    # Extract fields
    event_id = event.get("uuid", "")
    task_id = event.get("uuid", "")
    task_name = event.get("name", "")
    worker = event.get("hostname", None)
    args = event.get("args")
    kwargs = event.get("kwargs")
    result = event.get("result")
    traceback = event.get("traceback")
    exception = event.get("exception")
    retries = event.get("retries", 0)
    parent_id = event.get("parent_id")
    runtime = event.get("runtime")
    timestamp_val = event.get("timestamp")

    try:
        ev = TaskEvent(
            event_id=event_id,
            timestamp=timestamp_val,
            state=state_str,
            task_id=task_id,
            task_name=task_name,
            worker=worker,
            args=args,
            kwargs=kwargs,
            result=str(result) if result is not None else None,
            traceback=traceback,
            exception=repr(exception) if exception else None,
            retries=retries,
            parent_id=parent_id,
            runtime=float(runtime) if runtime else None,
        )
        db = SessionLocal()
        db.add(ev)
        db.commit()
        db.refresh(ev)

        # Update daily stats (simple)
        update_daily_stats(db, ev)

        # Broadcast via WebSocket (thread-safe)
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = app.state.asyncio_loop
        if loop:
            asyncio.run_coroutine_threadsafe(
                manager.broadcast(event_to_payload(ev)),
                loop,
            )
    except Exception as exc:
        logger.error(f"Failed to store event {event_id}: {exc}")
    finally:
        db.close()

def handle_worker_event(event: dict):
    hostname = event.get("hostname")
    if not hostname:
        return
    timestamp_val = event.get("timestamp")
    db = SessionLocal()
    try:
        worker_heartbeat = db.query(WorkerHeartbeat).filter_by(hostname=hostname).first()
        if not worker_heartbeat:
            worker_heartbeat = WorkerHeartbeat(hostname=hostname, last_heartbeat=timestamp_val, status="ONLINE")
            db.add(worker_heartbeat)
        else:
            worker_heartbeat.last_heartbeat = timestamp_val
            if event["type"] == "worker-online":
                worker_heartbeat.status = "ONLINE"
            elif event["type"] == "worker-offline":
                worker_heartbeat.status = "OFFLINE"
            else:
                # heartbeat: keep previous status or set to ONLINE if not offline
                if worker_heartbeat.status != "OFFLINE":
                    worker_heartbeat.status = "ONLINE"
        db.commit()
    except Exception as exc:
        logger.error(f"Failed to update worker {hostname}: {exc}")
    finally:
        db.close()

def update_daily_stats(db: Session, event: TaskEvent):
    try:
        date = event.timestamp.date() if event.timestamp else datetime.utcnow().date()
        state = event.state
        task_name = event.task_name
        stats = db.query(DailyTaskStats).filter_by(date=date, task_name=task_name).first()
        if not stats:
            stats = DailyTaskStats(date=date, task_name=task_name)
            db.add(stats)
        stats.total_count += 1
        if state == "SUCCESS":
            stats.success_count += 1
        elif state == "FAILURE":
            stats.failure_count += 1
        elif state == "RETRY":
            stats.retry_count += 1
        if event.runtime is not None and state in ("SUCCESS", "FAILURE"):
            if stats.total_runtime is None:
                stats.total_runtime = 0.0
            stats.total_runtime += event.runtime
            if stats.total_count > 0:
                stats.avg_runtime = stats.total_runtime / stats.total_count
        db.commit()
    except Exception as e:
        logger.warning(f"Failed to update daily stats: {e}")
        db.rollback()

def capture_events():
    """Run in a separate thread to capture celery events."""
    def run_capture(loop):
        # Store loop for later use in callbacks
        app.state.asyncio_loop = loop
        with celery_app.connection() as conn:
            receiver = celery_app.events.Receiver(conn, handlers={
                "task-sent": handle_task_event,
                "task-received": handle_task_event,
                "task-started": handle_task_event,
                "task-succeeded": handle_task_event,
                "task-failed": handle_task_event,
                "task-retried": handle_task_event,
                "worker-online": handle_worker_event,
                "worker-offline": handle_worker_event,
                "worker-heartbeat": handle_worker_event,
            })
            try:
                receiver.capture(limit=None, timeout=None, wakeup=True)
            except KeyboardInterrupt:
                pass
            except Exception:
                logger.exception("Event capture failed, restarting in 5s")
                time.sleep(5)
                # Restart recursively? For simplicity, just log and exit; could be handled by external orchestrator
    # We need to get the running event loop from the main thread.
    # This function will be called from startup, at which point the loop exists.
    loop = asyncio.get_event_loop()
    thread = threading.Thread(target=run_capture, args=(loop,), daemon=True)
    thread.start()
    logger.info("Celery event capture thread started")

# ------------------------------------------------------------------------------
# Alembic migrations (auto-migrate on startup)
# ------------------------------------------------------------------------------

def run_auto_migrations():
    """Run Alembic migrations if configured, otherwise fallback to create_all."""
    if not AUTO_MIGRATE:
        logger.info("Auto-migration disabled, using create_all")
        Base.metadata.create_all(bind=engine)
        return
    if not os.path.exists(ALEMBIC_INI_PATH):
        logger.warning(f"Alembic config not found at {ALEMBIC_INI_PATH}, falling back to create_all")
        Base.metadata.create_all(bind=engine)
    else:
        try:
            from alembic.config import Config
            from alembic import command
            alembic_cfg = Config(ALEMBIC_INI_PATH)
            # Ensure the database schema is up to date
            command.upgrade(alembic_cfg, "head")
            logger.info("Database migrations applied successfully")
        except Exception as exc:
            logger.error(f"Migration failed: {exc}, attempting create_all as fallback")
            Base.metadata.create_all(bind=engine)

# ------------------------------------------------------------------------------
# Startup event
# ------------------------------------------------------------------------------

@app.on_event("startup")
async def startup_event():
    run_auto_migrations()
    # Start event capture in a background thread
    capture_events()
    logger.info("Kanchi system started")

# ------------------------------------------------------------------------------
# Main entry point
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run("__main__:app", host="0.0.0.0", port=8000, reload=False)