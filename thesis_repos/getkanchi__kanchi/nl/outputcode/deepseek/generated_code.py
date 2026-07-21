import asyncio
import datetime
import json
import logging
import os
import subprocess
import time  # FIX 1: missing import
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Set

import uvicorn
from celery import Celery
from celery.events import EventReceiver
from fastapi import Depends, FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from fastapi.responses import JSONResponse
from kombu import Connection
from pydantic import BaseModel  # FIX 2: schema classes need BaseModel, not SQLAlchemy Base
from pydantic_settings import BaseSettings, SettingsConfigDict  # FIX 3: pydantic v2 moved BaseSettings
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    func,
    select,  # FIX 4: select was missing from imports
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker

logger = logging.getLogger(__name__)  # FIX 5: logger was never defined
logging.basicConfig(level=logging.INFO)


# ---------- Settings ----------
class Settings(BaseSettings):  # FIX 3: now uses pydantic_settings.BaseSettings
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./kanchi.db"
    celery_broker_url: str = "redis://localhost:6379/0"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    alembic_ini_path: str = "./alembic.ini"
    orphan_threshold_seconds: int = 300


settings = Settings()


# ---------- Database ----------
# FIX 6: declarative_base() moved to ORM in SQLAlchemy 2.0
class Base(DeclarativeBase):
    pass


engine = create_async_engine(settings.database_url, future=True)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# ---------- ORM Models ----------
class WorkerModel(Base):
    __tablename__ = "workers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    hostname = Column(String(255), unique=True, nullable=False, index=True)
    pid = Column(Integer, nullable=True)
    status = Column(String(50), nullable=False, default="OFFLINE", index=True)
    last_heartbeat = Column(DateTime(timezone=True), nullable=True)
    queues = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    tasks = relationship("TaskModel", back_populates="worker")


class TaskModel(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=True, index=True)  # FIX 7: nullable=True so new tasks without name don't crash
    status = Column(String(50), nullable=False, default="PENDING", index=True)
    worker_id = Column(Integer, ForeignKey("workers.id", ondelete="SET NULL"), nullable=True, index=True)
    queue = Column(String(255), nullable=True, index=True)
    args = Column(Text, nullable=True)
    kwargs = Column(Text, nullable=True)
    result = Column(Text, nullable=True)
    exception = Column(Text, nullable=True)
    traceback = Column(Text, nullable=True)
    retries = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=True)
    runtime = Column(Float, nullable=True)
    time_start = Column(DateTime(timezone=True), nullable=True)
    time_end = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    worker = relationship("WorkerModel", back_populates="tasks")


class DailyStatsModel(Base):
    __tablename__ = "daily_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime(timezone=True), unique=True, index=True, nullable=False)
    total = Column(Integer, nullable=False, default=0)
    succeeded = Column(Integer, nullable=False, default=0)
    failed = Column(Integer, nullable=False, default=0)
    retried = Column(Integer, nullable=False, default=0)
    pending = Column(Integer, nullable=False, default=0)
    average_runtime = Column(Float, nullable=True)


# ---------- Pydantic Schemas ----------
# FIX 8: TaskOut/TaskFilter/WorkerOut/DailyStatsOut were inheriting from SQLAlchemy Base — wrong.
# They are API schemas and must inherit from pydantic BaseModel.
class TaskOut(BaseModel):
    model_config = {"from_attributes": True}


class TaskFilter(BaseModel):
    date_start: Optional[datetime.datetime] = None
    date_end: Optional[datetime.datetime] = None
    status: Optional[str] = None
    name: Optional[str] = None
    worker: Optional[str] = None
    queue: Optional[str] = None
    q: Optional[str] = None


class WorkerOut(BaseModel):
    model_config = {"from_attributes": True}


class DailyStatsOut(BaseModel):
    model_config = {"from_attributes": True}


# ---------- WebSocket Manager ----------
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in list(self.active_connections):  # iterate copy to allow removal
            try:
                await connection.send_text(message)
            except Exception:
                self.disconnect(connection)


manager = ConnectionManager()


# ---------- Celery Monitor ----------
class CeleryMonitor:
    def __init__(self):
        self._loop: Optional[asyncio.AbstractEventLoop] = None  # FIX 9: store loop for thread-safe dispatch
        self._stop_event = False
        try:
            self.celery_app = Celery(broker=settings.celery_broker_url)
            self.conn = Connection(settings.celery_broker_url)
            # FIX 10: all handler methods were referenced but never defined — add them below
            self.receiver = EventReceiver(self.conn, handlers={
                'task-sent': self.on_task_sent,
                'task-received': self.on_task_received,
                'task-started': self.on_task_started,
                'task-succeeded': self.on_task_succeeded,
                'task-failed': self.on_task_failed,
                'task-retried': self.on_task_retried,
                'worker-online': self.on_worker_online,
                'worker-offline': self.on_worker_offline,
                'worker-heartbeat': self.on_worker_heartbeat,
            })
        except Exception as e:
            logger.warning(f"Could not connect to broker: {e}. Monitor will be inactive.")
            self.receiver = None

    # FIX 10: define sync handler methods that dispatch to async process_event via the stored loop
    def _dispatch(self, event_type: str, event: Dict[str, Any]):
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self.process_event(event_type, event), self._loop)

    def on_task_sent(self, event): self._dispatch('task-sent', event)
    def on_task_received(self, event): self._dispatch('task-received', event)
    def on_task_started(self, event): self._dispatch('task-started', event)
    def on_task_succeeded(self, event): self._dispatch('task-succeeded', event)
    def on_task_failed(self, event): self._dispatch('task-failed', event)
    def on_task_retried(self, event): self._dispatch('task-retried', event)
    def on_worker_online(self, event): self._dispatch('worker-online', event)
    def on_worker_offline(self, event): self._dispatch('worker-offline', event)
    def on_worker_heartbeat(self, event): self._dispatch('worker-heartbeat', event)

    async def start(self):
        self._loop = asyncio.get_event_loop()  # FIX 9: capture loop for thread-safe dispatch
        if self.receiver is None:
            logger.warning("No broker receiver — Celery monitor inactive.")
            return
        try:
            while not self._stop_event:
                # FIX 11: capture() signature — use keyword args, not positional None,None,None
                await self._loop.run_in_executor(None, lambda: self.receiver.capture(limit=None, timeout=1.0, wakeup=True))
                await asyncio.sleep(0)
        except Exception as e:
            logger.error(f"Celery monitor error: {e}")

    def stop(self):
        self._stop_event = True
        if self.receiver:
            try:
                self.receiver.should_stop = True
            except Exception:
                pass

    async def process_event(self, event_type: str, event: Dict[str, Any]):
        async with async_session() as session:
            if event_type.startswith('task-'):
                await self.handle_task_event(session, event_type, event)
            elif event_type.startswith('worker-'):
                await self.handle_worker_event(session, event_type, event)
            await session.commit()

        message = json.dumps({"type": event_type, "data": event}, default=str)
        await manager.broadcast(message)

    async def handle_task_event(self, session: AsyncSession, event_type: str, event: Dict[str, Any]):
        task_id = event.get('uuid', '')
        if not task_id:
            return

        result = await session.execute(
            select(TaskModel).where(TaskModel.task_id == task_id)
        )
        task_obj = result.scalars().first()

        if task_obj is None:
            task_obj = TaskModel(task_id=task_id, status='PENDING')
            session.add(task_obj)

        task_obj.name = event.get('name', task_obj.name)
        task_obj.queue = event.get('queue', task_obj.queue)
        args = event.get('args')
        kwargs = event.get('kwargs')
        if args:
            task_obj.args = str(args)
        if kwargs:
            task_obj.kwargs = str(kwargs)
        task_obj.max_retries = event.get('retries')

        now = datetime.datetime.now(tz=datetime.timezone.utc)

        if event_type == 'task-sent':
            task_obj.status = 'PENDING'
            task_obj.time_start = None
            task_obj.time_end = None
            task_obj.retries = 0
            task_obj.worker_id = None
        elif event_type == 'task-received':
            task_obj.status = 'RECEIVED'
        elif event_type == 'task-started':
            task_obj.status = 'STARTED'
            task_obj.time_start = datetime.datetime.fromtimestamp(event.get('timestamp', time.time()), tz=datetime.timezone.utc)
            hostname = event.get('hostname')
            if hostname:
                worker_result = await session.execute(
                    select(WorkerModel).where(WorkerModel.hostname == hostname)
                )
                worker = worker_result.scalars().first()
                if worker:
                    task_obj.worker_id = worker.id
        elif event_type == 'task-succeeded':
            task_obj.status = 'SUCCESS'
            task_obj.time_end = datetime.datetime.fromtimestamp(event.get('timestamp', time.time()), tz=datetime.timezone.utc)
            task_obj.result = str(event.get('result', ''))
        elif event_type == 'task-failed':
            task_obj.status = 'FAILURE'
            task_obj.time_end = datetime.datetime.fromtimestamp(event.get('timestamp', time.time()), tz=datetime.timezone.utc)
            task_obj.exception = event.get('exception', '')
            task_obj.traceback = event.get('traceback', '')
            task_obj.retries = event.get('retries', task_obj.retries)
        elif event_type == 'task-retried':
            task_obj.status = 'RETRY'
            task_obj.retries = event.get('retries', task_obj.retries)
            task_obj.exception = event.get('exception', '')
            task_obj.traceback = event.get('traceback', '')

        # FIX 12: func.now() is a SQL expression — cannot assign to ORM attribute directly.
        # onupdate handles this automatically; just set a Python datetime for the ORM session.
        task_obj.updated_at = now
        await session.flush()
        await self.update_daily_stats(session, task_obj.status)

    async def handle_worker_event(self, session: AsyncSession, event_type: str, event: Dict[str, Any]):
        hostname = event.get('hostname')
        if not hostname:
            return
        worker_result = await session.execute(
            select(WorkerModel).where(WorkerModel.hostname == hostname)
        )
        worker = worker_result.scalars().first()
        if not worker:
            worker = WorkerModel(hostname=hostname)
            session.add(worker)

        now = datetime.datetime.now(tz=datetime.timezone.utc)

        if event_type == 'worker-online':
            worker.status = 'ONLINE'
            worker.last_heartbeat = datetime.datetime.fromtimestamp(event.get('timestamp', time.time()), tz=datetime.timezone.utc)
            worker.queues = ','.join(event.get('queues', []))
        elif event_type == 'worker-offline':
            worker.status = 'OFFLINE'
        elif event_type == 'worker-heartbeat':
            worker.status = 'ONLINE'
            worker.last_heartbeat = datetime.datetime.fromtimestamp(event.get('timestamp', time.time()), tz=datetime.timezone.utc)

        # FIX 12: same func.now() fix
        worker.updated_at = now
        await session.flush()

    async def update_daily_stats(self, session: AsyncSession, status: str):
        today = datetime.date.today()
        date_start = datetime.datetime(today.year, today.month, today.day, tzinfo=datetime.timezone.utc)
        date_end = date_start + datetime.timedelta(days=1)
        stats_result = await session.execute(
            select(DailyStatsModel).where(
                DailyStatsModel.date >= date_start,
                DailyStatsModel.date < date_end,
            )
        )
        stats = stats_result.scalars().first()
        if not stats:
            stats = DailyStatsModel(date=date_start)
            session.add(stats)

        stats.total += 1
        if status == 'SUCCESS':
            stats.succeeded += 1
        elif status == 'FAILURE':
            stats.failed += 1
        elif status == 'RETRY':
            stats.retried += 1
        elif status in ('PENDING', 'RECEIVED', 'STARTED'):
            stats.pending += 1
        await session.flush()


# ---------- Orphan Detection ----------
async def orphan_detector():
    while True:
        await asyncio.sleep(60)
        async with async_session() as session:
            now = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
            threshold = now - datetime.timedelta(seconds=settings.orphan_threshold_seconds)
            stmt = select(TaskModel).join(WorkerModel, isouter=True).where(
                TaskModel.status == 'STARTED',
                (WorkerModel.status == 'OFFLINE') | (WorkerModel.last_heartbeat < threshold),
            )
            result = await session.execute(stmt)
            orphan_tasks = result.scalars().all()
            for task in orphan_tasks:
                task.status = 'ORPHAN'
                task.updated_at = now  # FIX 12: use Python datetime, not func.now()
            if orphan_tasks:
                await session.commit()
                for task in orphan_tasks:
                    message = json.dumps({"type": "task-updated", "data": {"task_id": task.task_id, "status": task.status}}, default=str)
                    await manager.broadcast(message)


# ---------- FastAPI App ----------
@asynccontextmanager
async def lifespan(app: FastAPI):
    if os.path.exists(settings.alembic_ini_path):
        try:
            subprocess.run(["alembic", "-c", settings.alembic_ini_path, "upgrade", "head"], check=True)
        except Exception as e:
            logger.error(f"Alembic migration failed: {e}")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    monitor = CeleryMonitor()
    asyncio.ensure_future(monitor.start())
    orphan_task = asyncio.create_task(orphan_detector())

    yield

    monitor.stop()
    orphan_task.cancel()
    try:
        await orphan_task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="Kanchi", lifespan=lifespan)


# ---------- DB Dependency ----------
# FIX 13: get_session was a sync def — must be async def to yield from async context manager
async def get_session():
    async with async_session() as session:
        yield session


# ---------- Serializers ----------
def task_to_dict(task: TaskModel) -> dict:
    return {
        "id": task.id,
        "task_id": task.task_id,
        "name": task.name,
        "status": task.status,
        "worker_id": task.worker_id,
        "queue": task.queue,
        "args": task.args,
        "kwargs": task.kwargs,
        "result": task.result,
        "exception": task.exception,
        "traceback": task.traceback,
        "retries": task.retries,
        "max_retries": task.max_retries,
        "runtime": task.runtime,
        "time_start": task.time_start.isoformat() if task.time_start else None,
        "time_end": task.time_end.isoformat() if task.time_end else None,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
    }


def worker_to_dict(worker: WorkerModel) -> dict:
    return {
        "id": worker.id,
        "hostname": worker.hostname,
        "pid": worker.pid,
        "status": worker.status,
        "last_heartbeat": worker.last_heartbeat.isoformat() if worker.last_heartbeat else None,
        "queues": worker.queues,
        "created_at": worker.created_at.isoformat() if worker.created_at else None,
        "updated_at": worker.updated_at.isoformat() if worker.updated_at else None,
    }


def daily_stats_to_dict(stats: DailyStatsModel) -> dict:
    return {
        "id": stats.id,
        "date": stats.date.isoformat() if stats.date else None,
        "total": stats.total,
        "succeeded": stats.succeeded,
        "failed": stats.failed,
        "retried": stats.retried,
        "pending": stats.pending,
        "average_runtime": stats.average_runtime,
    }


# ---------- API Routes ----------
@app.get("/tasks", response_model=List[Dict])
async def get_tasks(
    date_start: Optional[datetime.datetime] = Query(None),
    date_end: Optional[datetime.datetime] = Query(None),
    status: Optional[str] = Query(None),
    name: Optional[str] = Query(None),
    worker: Optional[str] = Query(None),
    queue: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session),
):
    query = select(TaskModel)
    filters = []
    if date_start:
        filters.append(TaskModel.created_at >= date_start)
    if date_end:
        filters.append(TaskModel.created_at <= date_end)
    if status:
        filters.append(TaskModel.status == status.upper())
    if name:
        filters.append(TaskModel.name.ilike(f"%{name}%"))
    if worker:
        subq = select(WorkerModel.id).where(WorkerModel.hostname.ilike(f"%{worker}%"))
        filters.append(TaskModel.worker_id.in_(subq))
    if queue:
        filters.append(TaskModel.queue.ilike(f"%{queue}%"))
    if q:
        filters.append(
            TaskModel.name.ilike(f"%{q}%") |
            TaskModel.args.ilike(f"%{q}%") |
            TaskModel.kwargs.ilike(f"%{q}%") |
            TaskModel.exception.ilike(f"%{q}%") |
            TaskModel.traceback.ilike(f"%{q}%")
        )
    for f in filters:
        query = query.where(f)
    result = await session.execute(query.order_by(TaskModel.created_at.desc()))
    tasks = result.scalars().all()
    return [task_to_dict(t) for t in tasks]


@app.get("/tasks/{task_id}", response_model=Dict)
async def get_task(task_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(TaskModel).where(TaskModel.task_id == task_id))
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task_to_dict(task)


@app.get("/workers", response_model=List[Dict])
async def get_workers(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(WorkerModel))
    workers = result.scalars().all()
    return [worker_to_dict(w) for w in workers]


@app.get("/workers/{hostname}", response_model=Dict)
async def get_worker(hostname: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(WorkerModel).where(WorkerModel.hostname == hostname))
    worker = result.scalars().first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    return worker_to_dict(worker)


@app.get("/stats/daily", response_model=List[Dict])
async def get_daily_stats(
    start: Optional[datetime.date] = Query(None),
    end: Optional[datetime.date] = Query(None),
    session: AsyncSession = Depends(get_session),
):
    query = select(DailyStatsModel)
    if start:
        query = query.where(DailyStatsModel.date >= datetime.datetime(start.year, start.month, start.day, tzinfo=datetime.timezone.utc))
    if end:
        query = query.where(DailyStatsModel.date <= datetime.datetime(end.year, end.month, end.day, tzinfo=datetime.timezone.utc))
    result = await session.execute(query.order_by(DailyStatsModel.date.desc()))
    stats = result.scalars().all()
    return [daily_stats_to_dict(s) for s in stats]


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


if __name__ == "__main__":
    uvicorn.run(app, host=settings.api_host, port=settings.api_port, reload=False)
