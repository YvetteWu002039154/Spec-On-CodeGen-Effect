import asyncio
import json
import logging
import os
from datetime import date, datetime, timedelta
from threading import Thread
from typing import Any, Dict, List, Optional, Set

import uvicorn
from celery import Celery
from celery.events import EventReceiver
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, validator
from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Integer,
    String,
    Text,
    create_engine,
    func,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Database setup
# ---------------------------------------------------------------------------
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///kanchi.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class TaskEvent(Base):
    __tablename__ = "task_events"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), index=True, nullable=False, comment="Celery task UUID")
    name = Column(String, index=True, nullable=False)
    state = Column(String(20), index=True, nullable=False)
    args = Column(Text, default="")
    kwargs = Column(Text, default="")
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    runtime = Column(Integer, default=0, comment="Runtime in milliseconds (for success/failure)")
    worker = Column(String, index=True, nullable=True)
    queue = Column(String, default="celery")
    retries = Column(Integer, default=0)
    parent_task_id = Column(String(36), nullable=True, index=True)
    root_task_id = Column(String(36), nullable=True, index=True)
    exception = Column(Text, nullable=True)
    traceback = Column(Text, nullable=True)


class WorkerHeartbeat(Base):
    __tablename__ = "worker_heartbeats"

    id = Column(Integer, primary_key=True, index=True)
    hostname = Column(String, unique=True, index=True, nullable=False)
    status = Column(String(20), default="offline", comment="online/offline")
    last_heartbeat = Column(DateTime, default=datetime.utcnow)
    pid = Column(Integer, nullable=True)
    freq = Column(Integer, nullable=True)
    sw_ver = Column(String, nullable=True)
    sw_ident = Column(String, nullable=True)
    sw_sys = Column(String, nullable=True)
    clock = Column(Integer, nullable=True)


class DailyStatistics(Base):
    __tablename__ = "daily_statistics"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, unique=True, index=True, nullable=False)
    total_tasks = Column(Integer, default=0)
    succeeded = Column(Integer, default=0)
    failed = Column(Integer, default=0)
    retried = Column(Integer, default=0)
    total_runtime = Column(Integer, default=0, comment="Total runtime in milliseconds")


def init_db():
    Base.metadata.create_all(bind=engine)


# ---------------------------------------------------------------------------
# Alembic auto-migrations (simplified)
# ---------------------------------------------------------------------------
def run_alembic_migrations():
    try:
        import alembic.config
        from alembic import command

        alembic_cfg = alembic.config.Config()
        alembic_cfg.set_main_option("script_location", "alembic")
        alembic_cfg.set_main_option("sqlalchemy.url", DATABASE_URL)

        # Ensure the alembic directory exists with basic structure
        if not os.path.exists("alembic"):
            os.makedirs("alembic/versions", exist_ok=True)
            # Create minimal env.py and alembic.ini if not exists
            if not os.path.exists("alembic.ini"):
                with open("alembic.ini", "w") as f:
                    f.write("[alembic]\nscript_location = alembic\nsqlalchemy.url = {}\n".format(DATABASE_URL))
            if not os.path.exists("alembic/env.py"):
                with open("alembic/env.py", "w") as f:
                    f.write(
                        """from logging.config import fileConfig
        from sqlalchemy import engine_from_config
        from sqlalchemy import pool
        from alembic import context

        config = context.config
        fileConfig(config.config_file_name)

        target_metadata = None

        def run_migrations_offline():
            context.configure(
                url=config.get_main_option("sqlalchemy.url"),
                target_metadata=target_metadata,
                literal_binds=True,
                dialect_opts={"paramstyle": "named"},
            )
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
        """
                    )
            if not os.path.exists("alembic/script.py.mako"):
                with open("alembic/script.py.mako", "w") as f:
                    f.write(
                        """\"\"\"${message}

        Revision ID: ${up_revision}
        Revises: ${down_revision | comma,n}
        Create Date: ${create_date}
        \"\"\"
        from alembic import op
        import sqlalchemy as sa
        ${imports if imports else ""}

        revision = ${repr(up_revision)}
        down_revision = ${repr(down_revision)}
        branch_labels = ${repr(branch_labels)}
        depends_on = ${repr(depends_on)}


        def upgrade():
            ${upgrades if upgrades else "pass"}


        def downgrade():
            ${downgrades if downgrades else "pass"}
        """
                    )
        # Auto-generate migration if no versions exist
        if not os.listdir("alembic/versions"):
            command.revision(alembic_cfg, message="auto", autogenerate=True)
        command.upgrade(alembic_cfg, "head")
        logger.info("Alembic migrations applied successfully.")
    except Exception as e:
        logger.error(f"Alembic migration failed: {e}. Falling back to create_all.")
        init_db()
        logger.info("Database tables created via create_all.")


# ---------------------------------------------------------------------------
# Event processing (Celery events → DB)
# ---------------------------------------------------------------------------
class KanchiEventProcessor:
    def __init__(self, session_factory):
        self.session_factory = session_factory
        self.event_queue = None  # will be set by FastAPI startup

    def process_event(self, event: Dict[str, Any]):
        event_type = event.get("type")
        try:
            if event_type == "worker-online":
                self._handle_worker_online(event)
            elif event_type == "worker-offline":
                self._handle_worker_offline(event)
            elif event_type == "worker-heartbeat":
                self._handle_worker_heartbeat(event)
            elif event_type in (
                "task-sent",
                "task-received",
                "task-started",
                "task-succeeded",
                "task-failed",
                "task-retried",
                "task-revoked",
            ):
                self._handle_task_event(event_type, event)
            # Ignore other events
        except Exception as e:
            logger.exception(f"Error processing event {event_type}: {e}")

    def _handle_task_event(self, event_type: str, event: Dict[str, Any]):
        db = self.session_factory()
        try:
            uuid = event["uuid"]
            state = event_type[len("task-") :]  # e.g., 'succeeded'
            timestamp = datetime.utcfromtimestamp(event.get("timestamp", 0))
            # For task events, we may have multiple events for same UUID (e.g., sent, received, started, succeeded)
            # We always create a new row for each event to keep full history, but we could update the last one.
            # Here we insert a new event record.
            name = event.get("name", "unknown")

            args_str = json.dumps(event.get("args", [])) if event.get("args") else ""
            kwargs_str = json.dumps(event.get("kwargs", {})) if event.get("kwargs") else ""
            worker = event.get("hostname")
            runtime = 0
            retries = 0
            parent_id = event.get("parent_id", None)
            root_id = event.get("root_id", None)
            exception = None
            traceback = None

            if state == "succeeded":
                runtime = event.get("runtime", 0)  # in seconds? Celery sends runtime in seconds
                runtime = int(runtime * 1000)  # convert to ms
            elif state == "failed":
                runtime = event.get("runtime", 0)
                runtime = int(runtime * 1000)
                exception = event.get("exception")
                traceback = event.get("traceback")
                retries = event.get("retries", 0)
            elif state == "retried":
                # event contains 'exception', 'traceback', and 'runtime'
                runtime = event.get("runtime", 0)
                runtime = int(runtime * 1000)
                retries = event.get("retries", 0)
                exception = event.get("exception")
                traceback = event.get("traceback")
            elif state in ("sent", "received", "started", "revoked"):
                pass

            # Determine root_task_id: for retried tasks, the root_id is often the original task uuid,
            # but Celery may provide 'root_id' field in newer versions.
            # If root_id not provided, use parent_id's root, or fallback to uuid.
            if not root_id:
                if parent_id:
                    # Lookup root_task_id of parent task (if exists)
                    parent_event = db.query(TaskEvent).filter(TaskEvent.uuid == parent_id).first()
                    root_id = parent_event.root_task_id if parent_event and parent_event.root_task_id else parent_id
                else:
                    root_id = uuid

            task_event = TaskEvent(
                uuid=uuid,
                name=name,
                state=state,
                args=args_str,
                kwargs=kwargs_str,
                timestamp=timestamp,
                runtime=runtime,
                worker=worker,
                queue=event.get("queue", "celery"),
                retries=retries,
                parent_task_id=parent_id,
                root_task_id=root_id,
                exception=exception,
                traceback=traceback,
            )
            db.add(task_event)
            db.commit()

            # Push to WebSocket queue if available
            if self.event_queue is not None:
                self.event_queue.put_nowait(json.dumps({
                    "event": "task_event",
                    "data": {
                        "uuid": uuid,
                        "name": name,
                        "state": state,
                        "timestamp": timestamp.isoformat(),
                        "worker": worker,
                        "root_task_id": root_id,
                    },
                }))
        except Exception as e:
            db.rollback()
            logger.exception(f"Error handling task event {uuid}: {e}")
        finally:
            db.close()

    def _handle_worker_online(self, event: Dict[str, Any]):
        db = self.session_factory()
        try:
            hostname = event["hostname"]
            now = datetime.utcfromtimestamp(event.get("timestamp", datetime.utcnow().timestamp()))
            worker = db.query(WorkerHeartbeat).filter(WorkerHeartbeat.hostname == hostname).first()
            if worker:
                worker.status = "online"
                worker.last_heartbeat = now
                worker.pid = event.get("pid")
                worker.freq = event.get("freq")
                worker.sw_ver = event.get("sw_ver")
                worker.sw_ident = event.get("sw_ident")
                worker.sw_sys = event.get("sw_sys")
                worker.clock = event.get("clock")
            else:
                worker = WorkerHeartbeat(
                    hostname=hostname,
                    status="online",
                    last_heartbeat=now,
                    pid=event.get("pid"),
                    freq=event.get("freq"),
                    sw_ver=event.get("sw_ver"),
                    sw_ident=event.get("sw_ident"),
                    sw_sys=event.get("sw_sys"),
                    clock=event.get("clock"),
                )
                db.add(worker)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.exception(f"Error handling worker-online for {event.get('hostname')}: {e}")
        finally:
            db.close()

    def _handle_worker_offline(self, event: Dict[str, Any]):
        db = self.session_factory()
        try:
            hostname = event["hostname"]
            worker = db.query(WorkerHeartbeat).filter(WorkerHeartbeat.hostname == hostname).first()
            if worker:
                worker.status = "offline"
                worker.last_heartbeat = datetime.utcfromtimestamp(
                    event.get("timestamp", datetime.utcnow().timestamp())
                )
                db.commit()
        except Exception as e:
            db.rollback()
            logger.exception(f"Error handling worker-offline for {hostname}: {e}")
        finally:
            db.close()

    def _handle_worker_heartbeat(self, event: Dict[str, Any]):
        db = self.session_factory()
        try:
            hostname = event["hostname"]
            now = datetime.utcfromtimestamp(event.get("timestamp", datetime.utcnow().timestamp()))
            worker = db.query(WorkerHeartbeat).filter(WorkerHeartbeat.hostname == hostname).first()
            if worker:
                worker.status = "online"  # heartbeat indicates online
                worker.last_heartbeat = now
                worker.clock = event.get("clock")
                worker.freq = event.get("freq")
            else:
                # unknown worker, register as online
                worker = WorkerHeartbeat(
                    hostname=hostname, status="online", last_heartbeat=now
                )
                db.add(worker)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.exception(f"Error handling worker-heartbeat for {hostname}: {e}")
        finally:
            db.close()


class CeleryEventMonitor(Thread):
    def __init__(self, celery_app: Celery, processor: KanchiEventProcessor):
        super().__init__(daemon=True)
        self.celery_app = celery_app
        self.processor = processor

    def run(self):
        with self.celery_app.connection() as conn:
            receiver = EventReceiver(conn, handlers={
                '*': self.processor.process_event,
            })
            receiver.capture(limit=None, timeout=None, wakeup=True)
            logger.info("Celery event monitor started.")


# ---------------------------------------------------------------------------
# FastAPI app and WebSocket manager
# ---------------------------------------------------------------------------
app = FastAPI(title="Kanchi", description="Celery task monitoring and management")

# Global event queue for WebSocket broadcasting (thread-safe)
event_queue = asyncio.Queue(maxsize=1000)
# WebSocket connections
active_connections: Set[WebSocket] = set()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.add(websocket)
    try:
        while True:
            # Keep connection alive and listen for incoming (ping/pong)
            data = await websocket.receive_text()
            # Could handle subscribe/unsubscribe, but for simplicity ignore
    except WebSocketDisconnect:
        active_connections.remove(websocket)


async def broadcast_event(message: str):
    for connection in active_connections:
        try:
            await connection.send_text(message)
        except Exception:
            active_connections.remove(connection)


async def event_consumer():
    """Coroutine that reads from event_queue and broadcasts."""
    while True:
        msg = await event_queue.get()
        await broadcast_event(msg)


@app.on_event("startup")
async def startup_event():
    # Run Alembic migrations
    run_alembic_migrations()
    # Start event consumer background task
    asyncio.create_task(event_consumer())

    # Set up event processor and queue
    processor = KanchiEventProcessor(SessionLocal)
    # Link the event queue to the processor
    processor.event_queue = event_queue

    # Get celery broker URL from env or default
    broker_url = os.environ.get("CELERY_BROKER_URL", "pyamqp://guest@localhost//")
    celery_app = Celery("kanchi", broker=broker_url)
    # Start event monitor thread
    monitor = CeleryEventMonitor(celery_app, processor)
    monitor.start()


# ---------------------------------------------------------------------------
# Pydantic models for API responses
# ---------------------------------------------------------------------------
class TaskEventOut(BaseModel):
    id: int
    uuid: str
    name: str
    state: str
    args: str = ""
    kwargs: str = ""
    timestamp: datetime
    runtime: int
    worker: Optional[str]
    queue: Optional[str]
    retries: int
    parent_task_id: Optional[str]
    root_task_id: Optional[str]

    class Config:
        orm_mode = True


class WorkerOut(BaseModel):
    hostname: str
    status: str
    last_heartbeat: datetime
    pid: Optional[int]

    class Config:
        orm_mode = True


class DailyStatsOut(BaseModel):
    date: date
    total_tasks: int
    succeeded: int
    failed: int
    retried: int
    total_runtime: int

    class Config:
        orm_mode = True


class OrphanTask(BaseModel):
    uuid: str
    name: str
    state: str
    worker: Optional[str]
    started_at: datetime
    last_event_at: datetime


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/api/tasks", response_model=List[TaskEventOut])
def list_tasks(
    start_date: Optional[datetime] = Query(None, description="Start date filter (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="End date filter (ISO format)"),
    status: Optional[str] = Query(None, description="Task state (e.g., succeeded, failed, started)"),
    name: Optional[str] = Query(None, description="Task name filter (partial match)"),
    worker: Optional[str] = Query(None, description="Worker hostname"),
    search: Optional[str] = Query(None, description="Full-text search in name/args/kwargs"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(TaskEvent)
    if start_date:
        query = query.filter(TaskEvent.timestamp >= start_date)
    if end_date:
        query = query.filter(TaskEvent.timestamp <= end_date)
    if status:
        query = query.filter(TaskEvent.state == status)
    if name:
        query = query.filter(TaskEvent.name.ilike(f"%{name}%"))
    if worker:
        query = query.filter(TaskEvent.worker == worker)
    if search:
        # Simple full-text search across name, args, kwargs
        search_pattern = f"%{search}%"
        query = query.filter(
            (TaskEvent.name.ilike(search_pattern)) |
            (TaskEvent.args.ilike(search_pattern)) |
            (TaskEvent.kwargs.ilike(search_pattern))
        )
    # Order by newest first
    query = query.order_by(TaskEvent.timestamp.desc())
    tasks = query.offset(offset).limit(limit).all()
    return tasks


@app.get("/api/tasks/{task_id}", response_model=TaskEventOut)
def get_task(task_id: str, db: Session = Depends(get_db)):
    task = db.query(TaskEvent).filter(TaskEvent.uuid == task_id).order_by(TaskEvent.timestamp.desc()).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.get("/api/workers", response_model=List[WorkerOut])
def list_workers(db: Session = Depends(get_db)):
    workers = db.query(WorkerHeartbeat).all()
    return workers


@app.get("/api/stats/daily", response_model=DailyStatsOut)
def get_daily_stats(
    target_date: date = Query(None, description="Date in YYYY-MM-DD format; defaults to today"),
    db: Session = Depends(get_db),
):
    if target_date is None:
        target_date = date.today()
    # Try to find existing stats; if not compute on-the-fly
    stats = db.query(DailyStatistics).filter(DailyStatistics.date == target_date).first()
    if stats:
        return stats

    # Compute from task events
    start = datetime.combine(target_date, datetime.min.time())
    end = datetime.combine(target_date, datetime.max.time())

    base_query = db.query(TaskEvent).filter(
        TaskEvent.timestamp >= start,
        TaskEvent.timestamp < end + timedelta(days=1),
    )
    total = base_query.count()
    succeeded = base_query.filter(TaskEvent.state == "succeeded").count()
    failed = base_query.filter(TaskEvent.state == "failed").count()
    retried = base_query.filter(TaskEvent.state == "retried").count()
    # sum runtime (only from succeeded/failed that have runtime)
    runtime_result = (
        base_query.filter(TaskEvent.state.in_(["succeeded", "failed"]))
        .with_entities(func.sum(TaskEvent.runtime))
        .scalar()
    )
    total_runtime = runtime_result if runtime_result else 0

    # Optionally persist the computed stats (but don't commit here to keep endpoint read-only)
    # We could return and cache later.
    return DailyStatsOut(
        date=target_date,
        total_tasks=total,
        succeeded=succeeded,
        failed=failed,
        retried=retried,
        total_runtime=total_runtime,
    )


@app.get("/api/orphans", response_model=List[OrphanTask])
def list_orphan_tasks(
    db: Session = Depends(get_db),
    stale_minutes: int = Query(60, description="Consider task orphan if started and no completion event for this many minutes"),
):
    threshold = datetime.utcnow() - timedelta(minutes=stale_minutes)
    # Find tasks that are in 'started' state with no subsequent success/failure/retried/revoked
    # We need tasks whose latest event is a 'started' and timestamp older than threshold.
    # Subquery: max timestamp per task_uuid where state is started and not followed by a termination event.
    started_sub = (
        db.query(
            TaskEvent.uuid,
            func.max(TaskEvent.timestamp).label("max_ts"),
        )
        .filter(TaskEvent.state == "started")
        .group_by(TaskEvent.uuid)
        .subquery()
    )
    termination_states = ("succeeded", "failed", "retried", "revoked")
    # Check that no termination event exists for that uuid after the started event
    orphan_candidates = (
        db.query(
            TaskEvent.uuid,
            TaskEvent.name,
            TaskEvent.worker,
            started_sub.c.max_ts.label("started_at"),
            func.max(TaskEvent.timestamp).label("last_event_at"),
        )
        .join(started_sub, TaskEvent.uuid == started_sub.c.uuid)
        .filter(TaskEvent.timestamp == started_sub.c.max_ts)  # get the started row
        .group_by(TaskEvent.uuid)
        .having(
            # ensure no termination event exists after started
            func.sum(
                func.if_(
                    TaskEvent.state.in_(termination_states),
                    1,
                    0,
                )
            ) == 0,
        )
        .all()
    )

    # Further filter by worker offline? Not required; optional.
    orphans = []
    for row in orphan_candidates:
        # Check if worker is offline (optional)
        worker_offline = True
        if row.worker:
            worker_info = db.query(WorkerHeartbeat).filter(WorkerHeartbeat.hostname == row.worker).first()
            if worker_info and worker_info.status == "online":
                worker_offline = False
        # If worker is still online but task hasn't completed after threshold, still orphan.
        # We'll include all, but we could add additional check: task not completed for more than stale_minutes.
        if row.started_at < threshold:
            orphans.append(OrphanTask(
                uuid=row.uuid,
                name=row.name,
                state="started",
                worker=row.worker,
                started_at=row.started_at,
                last_event_at=row.last_event_at,
            ))
    return orphans


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Run the app with uvicorn
    uvicorn.run("__main__:app", host="0.0.0.0", port=8000, reload=False)