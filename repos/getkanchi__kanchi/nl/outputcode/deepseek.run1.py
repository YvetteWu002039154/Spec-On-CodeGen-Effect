import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Set
from uuid import uuid4

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import HTMLResponse
from sqlalchemy import (
    Column, Integer, String, DateTime, Float, Enum, ForeignKey, Text, Boolean,
    create_engine, select, func, and_, or_, text
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base, relationship, selectinload
import celery
from celery import Celery
from celery.events import EventReceiver
from celery.events.state import State
from kombu import Connection
import uvicorn

# ---------- Configuration ----------
DATABASE_URL = "sqlite+aiosqlite:///kanchi.db"
CELERY_BROKER_URL = "redis://localhost:6379/0"
CELERY_BACKEND_URL = "redis://localhost:6379/1"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("kanchi")

# ---------- Database Setup ----------
Base = declarative_base()

class TaskModel(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    uuid = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    state = Column(String, nullable=False, default="PENDING", index=True)
    received_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    succeeded_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    retried_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)
    runtime = Column(Float, nullable=True)
    exception = Column(Text, nullable=True)
    traceback = Column(Text, nullable=True)
    args = Column(Text, nullable=True)
    kwargs = Column(Text, nullable=True)
    result = Column(Text, nullable=True)
    worker = Column(String, nullable=True, index=True)
    retries = Column(Integer, default=0)
    parent_id = Column(String, ForeignKey("tasks.id"), nullable=True)
    root_id = Column(String, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # relationships
    parent = relationship("TaskModel", remote_side=[id], backref="children")
    events = relationship("TaskEventModel", back_populates="task", order_by="TaskEventModel.timestamp")

class WorkerModel(Base):
    __tablename__ = "workers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    hostname = Column(String, unique=True, nullable=False, index=True)
    pid = Column(Integer, nullable=True)
    last_heartbeat = Column(DateTime, nullable=True)
    online = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class TaskEventModel(Base):
    __tablename__ = "task_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String, ForeignKey("tasks.id"), nullable=False, index=True)
    type = Column(String, nullable=False)  # e.g., task-sent, task-received, task-started, task-succeeded, etc.
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    payload = Column(Text, nullable=True)  # JSON

    task = relationship("TaskModel", back_populates="events")

class DailyStatsModel(Base):
    __tablename__ = "daily_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False, index=True)
    total_tasks = Column(Integer, default=0)
    succeeded = Column(Integer, default=0)
    failed = Column(Integer, default=0)
    retried = Column(Integer, default=0)
    revoked = Column(Integer, default=0)
    avg_runtime = Column(Float, default=0.0)
    total_runtime = Column(Float, default=0.0)
    worker_count = Column(Integer, default=0)

    __table_args__ = (Index("ix_daily_stats_date", "date", unique=True),)

# Async engine and session
engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# ---------- Celery App ----------
celery_app = Celery("kanchi", broker=CELERY_BROKER_URL, backend=CELERY_BACKEND_URL)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)

# ---------- Event Monitor ----------
class CeleryEventMonitor:
    def __init__(self, celery_app: Celery, db_session_factory):
        self.celery_app = celery_app
        self.db_session_factory = db_session_factory
        self.state = State()
        self.connection = None
        self.receiver = None
        self._running = False
        self.websockets: Set[WebSocket] = set()

    async def start(self):
        if self._running:
            return
        self._running = True
        # Start capturing events in a background task
        asyncio.create_task(self._capture_events())

    async def stop(self):
        self._running = False
        if self.receiver:
            self.receiver.should_stop = True
        if self.connection:
            try:
                self.connection.release()
            except:
                pass

    async def _capture_events(self):
        conn = self.celery_app.connection().acquire(block=True)
        self.connection = conn
        self.receiver = EventReceiver(
            conn,
            handlers={
                "*": self._handle_event,
            },
            app=self.celery_app,
        )
        try:
            self.receiver.capture(limit=None, timeout=None, wakeup=True)
        except Exception as e:
            logger.error(f"Event capture failed: {e}")
        finally:
            self._running = False

    def _handle_event(self, event: Dict[str, Any]):
        """Handle raw event; dispatch to appropriate handler and persist to DB."""
        event_type = event.get("type", "")
        try:
            if event_type.startswith("task-"):
                self._handle_task_event(event)
            elif event_type.startswith("worker-"):
                self._handle_worker_event(event)
            # Also update in-memory state for quick queries
            self.state.event(event)
        except Exception as e:
            logger.exception(f"Error handling event {event_type}: {e}")

    def _handle_task_event(self, event: Dict[str, Any]):
        type_map = {
            "task-sent": self._task_sent,
            "task-received": self._task_received,
            "task-started": self._task_started,
            "task-succeeded": self._task_succeeded,
            "task-failed": self._task_failed,
            "task-retried": self._task_retried,
            "task-revoked": self._task_revoked,
            "task-rejected": self._task_rejected,
        }
        handler = type_map.get(event["type"])
        if handler:
            # We need async DB operation; schedule via asyncio.run_coroutine_threadsafe or queue
            # For simplicity, we spawn a new async task that writes to DB
            asyncio.create_task(self._async_persist(event, handler))

    def _handle_worker_event(self, event: Dict[str, Any]):
        handler_map = {
            "worker-online": self._worker_online,
            "worker-offline": self._worker_offline,
            "worker-heartbeat": self._worker_heartbeat,
        }
        handler = handler_map.get(event["type"])
        if handler:
            asyncio.create_task(self._async_persist(event, handler))

    async def _async_persist(self, event: Dict[str, Any], handler):
        async with self.db_session_factory() as session:
            try:
                await handler(session, event)
                await session.commit()
                # Broadcast updated data to websockets
                await self.broadcast(event)
            except Exception as e:
                logger.exception(f"Failed to persist event: {e}")
                await session.rollback()

    # ---- Task event handlers ----
    async def _task_sent(self, session: AsyncSession, event: Dict):
        uuid = event["uuid"]
        task = TaskModel(
            uuid=uuid,
            name=event.get("name", ""),
            state="SENT",
            args=event.get("args", ""),
            kwargs=event.get("kwargs", ""),
            root_id=event.get("root_id"),
            parent_id=event.get("parent_id"),
        )
        session.add(task)
        await self._add_event(session, task.id, event)

    async def _task_received(self, session: AsyncSession, event: Dict):
        task = await session.execute(select(TaskModel).where(TaskModel.uuid == event["uuid"]))
        task = task.scalar_one_or_none()
        if task:
            task.state = "RECEIVED"
            task.received_at = datetime.utcfromtimestamp(event["timestamp"])
            task.worker = event.get("hostname")
            await self._add_event(session, task.id, event)

    async def _task_started(self, session: AsyncSession, event: Dict):
        task = await session.execute(select(TaskModel).where(TaskModel.uuid == event["uuid"]))
        task = task.scalar_one_or_none()
        if task:
            task.state = "STARTED"
            task.started_at = datetime.utcfromtimestamp(event["timestamp"])
            task.worker = event.get("hostname")
            await self._add_event(session, task.id, event)

    async def _task_succeeded(self, session: AsyncSession, event: Dict):
        task = await session.execute(select(TaskModel).where(TaskModel.uuid == event["uuid"]))
        task = task.scalar_one_or_none()
        if task:
            task.state = "SUCCESS"
            task.succeeded_at = datetime.utcfromtimestamp(event["timestamp"])
            task.runtime = event.get("runtime")
            task.result = event.get("result")
            await self._add_event(session, task.id, event)

    async def _task_failed(self, session: AsyncSession, event: Dict):
        task = await session.execute(select(TaskModel).where(TaskModel.uuid == event["uuid"]))
        task = task.scalar_one_or_none()
        if task:
            task.state = "FAILURE"
            task.failed_at = datetime.utcfromtimestamp(event["timestamp"])
            task.exception = event.get("exception")
            task.traceback = event.get("traceback")
            await self._add_event(session, task.id, event)

    async def _task_retried(self, session: AsyncSession, event: Dict):
        task = await session.execute(select(TaskModel).where(TaskModel.uuid == event["uuid"]))
        task = task.scalar_one_or_none()
        if task:
            task.state = "RETRY"
            task.retried_at = datetime.utcfromtimestamp(event["timestamp"])
            task.retries += 1
            task.exception = event.get("exception")
            task.traceback = event.get("traceback")
            await self._add_event(session, task.id, event)

    async def _task_revoked(self, session: AsyncSession, event: Dict):
        task = await session.execute(select(TaskModel).where(TaskModel.uuid == event["uuid"]))
        task = task.scalar_one_or_none()
        if task:
            task.state = "REVOKED"
            task.revoked_at = datetime.utcfromtimestamp(event["timestamp"])
            await self._add_event(session, task.id, event)

    async def _task_rejected(self, session: AsyncSession, event: Dict):
        # treat as failed for simplicity
        await self._task_failed(session, event)

    # ---- Worker event handlers ----
    async def _worker_online(self, session: AsyncSession, event: Dict):
        hostname = event["hostname"]
        worker = await session.execute(select(WorkerModel).where(WorkerModel.hostname == hostname))
        worker = worker.scalar_one_or_none()
        if not worker:
            worker = WorkerModel(hostname=hostname, pid=event.get("pid"), online=True)
            session.add(worker)
        else:
            worker.online = True
            worker.pid = event.get("pid", worker.pid)
        worker.last_heartbeat = datetime.utcfromtimestamp(event["timestamp"])

    async def _worker_offline(self, session: AsyncSession, event: Dict):
        hostname = event["hostname"]
        worker = await session.execute(select(WorkerModel).where(WorkerModel.hostname == hostname))
        worker = worker.scalar_one_or_none()
        if worker:
            worker.online = False
            worker.last_heartbeat = datetime.utcfromtimestamp(event["timestamp"])

    async def _worker_heartbeat(self, session: AsyncSession, event: Dict):
        hostname = event["hostname"]
        worker = await session.execute(select(WorkerModel).where(WorkerModel.hostname == hostname))
        worker = worker.scalar_one_or_none()
        if worker:
            worker.last_heartbeat = datetime.utcfromtimestamp(event["timestamp"])
            worker.online = True

    async def _add_event(self, session: AsyncSession, task_id: str, event: Dict):
        event_obj = TaskEventModel(
            task_id=task_id,
            type=event["type"],
            timestamp=datetime.utcfromtimestamp(event["timestamp"]),
            payload=json.dumps(event, default=str),
        )
        session.add(event_obj)

    async def broadcast(self, event: Dict):
        """Send event to all connected websockets."""
        disconnected = set()
        for ws in self.websockets:
            try:
                await ws.send_json(event)
            except Exception:
                disconnected.add(ws)
        self.websockets -= disconnected

    def register_websocket(self, websocket: WebSocket):
        self.websockets.add(websocket)

    def unregister_websocket(self, websocket: WebSocket):
        self.websockets.discard(websocket)

# ---------- FastAPI App ----------
app = FastAPI(title="Kanchi", version="1.0.0")
monitor = None

@app.on_event("startup")
async def startup_event():
    global monitor
    await init_db()
    monitor = CeleryEventMonitor(celery_app, async_session)
    await monitor.start()

@app.on_event("shutdown")
async def shutdown_event():
    if monitor:
        await monitor.stop()

# ---------- WebSocket Endpoint ----------
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    monitor.register_websocket(websocket)
    try:
        while True:
            # Keep connection alive, can receive client filters later
            data = await websocket.receive_text()
            # For now, we ignore client messages
    except WebSocketDisconnect:
        monitor.unregister_websocket(websocket)

# ---------- REST API Endpoints ----------
@app.get("/tasks", response_model=List[Dict[str, Any]])
async def get_tasks(
    name: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    worker: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    async with async_session() as session:
        query = select(TaskModel)
        conditions = []
        if name:
            conditions.append(TaskModel.name == name)
        if state:
            conditions.append(TaskModel.state == state)
        if worker:
            conditions.append(TaskModel.worker == worker)
        if search:
            # full-text search on name, exception, traceback, args, kwargs
            search_filter = or_(
                TaskModel.name.ilike(f"%{search}%"),
                TaskModel.exception.ilike(f"%{search}%"),
                TaskModel.traceback.ilike(f"%{search}%"),
                TaskModel.args.ilike(f"%{search}%"),
                TaskModel.kwargs.ilike(f"%{search}%"),
            )
            conditions.append(search_filter)
        if start_date:
            conditions.append(TaskModel.created_at >= start_date)
        if end_date:
            conditions.append(TaskModel.created_at <= end_date)

        if conditions:
            query = query.where(and_(*conditions))
        query = query.order_by(TaskModel.created_at.desc())
        query = query.limit(limit).offset(offset)
        result = await session.execute(query)
        tasks = result.scalars().all()
        return [task_to_dict(t) for t in tasks]

@app.get("/tasks/{task_uuid}")
async def get_task(task_uuid: str):
    async with async_session() as session:
        result = await session.execute(
            select(TaskModel).where(TaskModel.uuid == task_uuid).options(selectinload(TaskModel.events))
        )
        task = result.scalar_one_or_none()
        if not task:
            return {"error": "Not found"}, 404
        return task_to_dict(task, include_events=True)

@app.get("/workers")
async def get_workers(online_only: bool = Query(False)):
    async with async_session() as session:
        query = select(WorkerModel)
        if online_only:
            query = query.where(WorkerModel.online == True)
        result = await session.execute(query)
        workers = result.scalars().all()
        return [worker_to_dict(w) for w in workers]

@app.get("/workers/{hostname}/health")
async def worker_health(hostname: str):
    async with async_session() as session:
        result = await session.execute(select(WorkerModel).where(WorkerModel.hostname == hostname))
        worker = result.scalar_one_or_none()
        if not worker:
            return {"error": "Not found"}, 404
        threshold = datetime.utcnow() - timedelta(seconds=30)
        healthy = worker.online and worker.last_heartbeat and worker.last_heartbeat > threshold
        return {
            "hostname": hostname,
            "online": worker.online,
            "last_heartbeat": worker.last_heartbeat.isoformat() if worker.last_heartbeat else None,
            "healthy": healthy,
        }

@app.get("/tasks/orphans")
async def orphan_tasks():
    """Detect tasks that are in non-terminal state but worker is offline or missing heartbeat."""
    async with async_session() as session:
        # Get workers considered offline (no heartbeat in 30 sec)
        threshold = datetime.utcnow() - timedelta(seconds=30)
        stale_workers_query = select(WorkerModel.hostname).where(
            WorkerModel.online == False
        ).union(
            select(WorkerModel).where(WorkerModel.last_heartbeat < threshold)
        )
        stale_hosts = (await session.execute(stale_workers_query)).scalars().all()
        stale_hosts = set(stale_hosts)

        # Tasks in non-terminal states with worker in stale_hosts or with no worker
        query = select(TaskModel).where(
            TaskModel.state.in_(["RECEIVED", "STARTED", "RETRY"]),
        )
        result = await session.execute(query)
        tasks = result.scalars().all()
        orphans = []
        for t in tasks:
            if t.worker in stale_hosts or t.worker is None:
                orphans.append(task_to_dict(t))
        return orphans

@app.get("/tasks/retries")
async def retried_tasks():
    """Return tasks with retries > 0"""
    async with async_session() as session:
        query = select(TaskModel).where(TaskModel.retries > 0).order_by(TaskModel.retries.desc())
        result = await session.execute(query)
        tasks = result.scalars().all()
        return [task_to_dict(t) for t in tasks]

@app.get("/stats/daily")
async def daily_stats(date: Optional[str] = Query(None, description="YYYY-MM-DD")):
    async with async_session() as session:
        if date:
            parsed_date = datetime.strptime(date, "%Y-%m-%d")
            result = await session.execute(
                select(DailyStatsModel).where(func.date(DailyStatsModel.date) == parsed_date.date())
            )
            stats = result.scalar_one_or_none()
        else:
            # Last 30 days
            result = await session.execute(
                select(DailyStatsModel).order_by(DailyStatsModel.date.desc()).limit(30)
            )
            stats = result.scalars().all()
        if not stats:
            return []
        if not isinstance(stats, list):
            stats = [stats]
        return [{
            "date": s.date.isoformat(),
            "total_tasks": s.total_tasks,
            "succeeded": s.succeeded,
            "failed": s.failed,
            "retried": s.retried,
            "revoked": s.revoked,
            "avg_runtime": s.avg_runtime,
            "total_runtime": s.total_runtime,
            "worker_count": s.worker_count,
        } for s in stats]

@app.post("/stats/daily/compute")
async def compute_daily_stats():
    """Force recompute daily stats for today."""
    today = datetime.utcnow().date()
    async with async_session() as session:
        await compute_daily_stats_for_date(session, today)
        await session.commit()
    return {"status": "ok", "date": str(today)}

async def compute_daily_stats_for_date(session: AsyncSession, date: datetime.date):
    start = datetime.combine(date, datetime.min.time())
    end = datetime.combine(date, datetime.max.time())
    # Aggregate from tasks
    stmt = select(
        func.count(TaskModel.id).label("total"),
        func.sum(case((TaskModel.state == "SUCCESS", 1), else_=0)).label("succeeded"),
        func.sum(case((TaskModel.state == "FAILURE", 1), else_=0)).label("failed"),
        func.sum(case((TaskModel.state == "RETRY", 1), else_=0)).label("retried"),
        func.sum(case((TaskModel.state == "REVOKED", 1), else_=0)).label("revoked"),
        func.avg(TaskModel.runtime).label("avg_runtime"),
        func.sum(TaskModel.runtime).label("total_runtime"),
    ).where(
        and_(TaskModel.created_at >= start, TaskModel.created_at <= end)
    )
    result = await session.execute(stmt)
    row = result.one_or_none()
    if not row or not row.total:
        return

    # Count workers active on that day (simplistic: workers that had any task)
    worker_count_query = select(func.count(func.distinct(WorkerModel.hostname))).where(
        WorkerModel.last_heartbeat >= start, WorkerModel.last_heartbeat <= end
    )
    worker_count = await session.execute(worker_count_query)
    workers = worker_count.scalar() or 0

    stats = DailyStatsModel(
        date=start,
        total_tasks=row.total,
        succeeded=row.succeeded or 0,
        failed=row.failed or 0,
        retried=row.retried or 0,
        revoked=row.revoked or 0,
        avg_runtime=row.avg_runtime or 0.0,
        total_runtime=row.total_runtime or 0.0,
        worker_count=workers,
    )
    session.merge(stats)

# ---------- Helper functions ----------
def task_to_dict(task: TaskModel, include_events=False) -> Dict[str, Any]:
    data = {
        "uuid": task.uuid,
        "name": task.name,
        "state": task.state,
        "received_at": task.received_at.isoformat() if task.received_at else None,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "succeeded_at": task.succeeded_at.isoformat() if task.succeeded_at else None,
        "failed_at": task.failed_at.isoformat() if task.failed_at else None,
        "retried_at": task.retried_at.isoformat() if task.retried_at else None,
        "revoked_at": task.revoked_at.isoformat() if task.revoked_at else None,
        "runtime": task.runtime,
        "worker": task.worker,
        "retries": task.retries,
        "exception": task.exception,
        "traceback": task.traceback,
        "args": task.args,
        "kwargs": task.kwargs,
        "result": task.result,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
    }
    if include_events:
        data["events"] = [{
            "type": e.type,
            "timestamp": e.timestamp.isoformat(),
            "payload": json.loads(e.payload) if e.payload else None,
        } for e in task.events]
    return data

def worker_to_dict(worker: WorkerModel) -> Dict[str, Any]:
    return {
        "hostname": worker.hostname,
        "pid": worker.pid,
        "last_heartbeat": worker.last_heartbeat.isoformat() if worker.last_heartbeat else None,
        "online": worker.online,
        "created_at": worker.created_at.isoformat() if worker.created_at else None,
    }

# ---------- Main entry point ----------
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)