import asyncio
import datetime
import json
import logging
import os
import subprocess
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Set

import uvicorn
from celery import Celery
from celery.events import EventReceiver
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from fastapi.responses import JSONResponse
from pydantic import BaseSettings, Field
from kombu import Connection
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
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.orm.session import Session

# ---------- Settings ----------
class Settings(BaseSettings):
    database_url: str = Field("sqlite+aiosqlite:///./kanchi.db", env="DATABASE_URL")
    celery_broker_url: str = Field("redis://localhost:6379/0", env="CELERY_BROKER_URL")
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    alembic_ini_path: str = Field("./alembic.ini", env="ALEMBIC_INI_PATH")
    orphan_threshold_seconds: int = 300  # 5 minutes

    class Config:
        env_file = ".env"


settings = Settings()

# ---------- Database ----------
engine = create_async_engine(settings.database_url, future=True)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

# ---------- ORM Models ----------
class TaskModel(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False, index=True)
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

class WorkerModel(Base):
    __tablename__ = "workers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    hostname = Column(String(255), unique=True, nullable=False, index=True)
    pid = Column(Integer, nullable=True)
    status = Column(String(50), nullable=False, default="OFFLINE", index=True)  # ONLINE, OFFLINE
    last_heartbeat = Column(DateTime(timezone=True), nullable=True)
    queues = Column(Text, nullable=True)  # comma-separated
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    tasks = relationship("TaskModel", back_populates="worker")

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
class TaskOut(Base):
    class Config:
        orm_mode = True

class TaskFilter(Base):
    date_start: Optional[datetime.datetime] = None
    date_end: Optional[datetime.datetime] = None
    status: Optional[str] = None
    name: Optional[str] = None
    worker: Optional[str] = None
    queue: Optional[str] = None
    q: Optional[str] = None

class WorkerOut(Base):
    class Config:
        orm_mode = True

class DailyStatsOut(Base):
    class Config:
        orm_mode = True

# ---------- WebSocket Manager ----------
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                self.active_connections.remove(connection)

manager = ConnectionManager()

# ---------- FastAPI App ----------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run Alembic migrations if configured
    if os.path.exists(settings.alembic_ini_path):
        try:
            subprocess.run(["alembic", "-c", settings.alembic_ini_path, "upgrade", "head"], check=True)
        except Exception as e:
            logger.error(f"Alembic migration failed: {e}")

    # Create tables if not exist (fallback)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Start Celery monitor
    monitor = CeleryMonitor()
    asyncio.ensure_future(monitor.start())

    # Start orphan detector
    orphan_task = asyncio.create_task(orphan_detector())

    yield

    # Cleanup
    monitor.stop()
    orphan_task.cancel()
    try:
        await orphan_task
    except asyncio.CancelledError:
        pass

app = FastAPI(title="Kanchi", lifespan=lifespan)

# ---------- Celery Monitor ----------
class CeleryMonitor:
    def __init__(self):
        self.celery_app = Celery(broker=settings.celery_broker_url)
        self.conn = Connection(settings.celery_broker_url)
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
        self._stop_event = False

    async def start(self):
        loop = asyncio.get_event_loop()
        try:
            while not self._stop_event:
                # EventReceiver.capture runs in a blocking manner; run in executor
                await loop.run_in_executor(None, self.receiver.capture, None, None, None)
                await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Celery monitor error: {e}")

    def stop(self):
        self._stop_event = True
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
        task_id = event['uuid']
        task_obj = await session.get(TaskModel, {"task_id": task_id})  # use session.execute
        # Actually, use query
        result = await session.execute(
            select(TaskModel).where(TaskModel.task_id == task_id)
        )
        task_obj = result.scalars().first()

        if task_obj is None:
            task_obj = TaskModel(task_id=task_id)
            session.add(task_obj)

        task_obj.name = event.get('name', task_obj.name)
        task_obj.queue = event.get('queue', task_obj.queue)
        args = event.get('args', None)
        kwargs = event.get('kwargs', None)
        if args:
            task_obj.args = str(args)
        if kwargs:
            task_obj.kwargs = str(kwargs)
        task_obj.max_retries = event.get('retries', None)  # 'retries' = max retries in some events

        if event_type == 'task-sent':
            task_obj.status = 'PENDING'
            task_obj.args = str(event.get('args', ''))
            task_obj.kwargs = str(event.get('kwargs', ''))
            task_obj.time_start = None
            task_obj.time_end = None
            task_obj.retries = 0
            task_obj.worker_id = None
        elif event_type == 'task-received':
            task_obj.status = 'RECEIVED'
            task_obj.worker_id = None  # not yet assigned
        elif event_type == 'task-started':
            task_obj.status = 'STARTED'
            task_obj.time_start = datetime.datetime.fromtimestamp(event.get('timestamp', time.time()), tz=datetime.timezone.utc)
            # attempt to set worker
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
            # retries count might be in event
            task_obj.retries = event.get('retries', task_obj.retries)
        elif event_type == 'task-retried':
            task_obj.status = 'RETRY'
            task_obj.retries = event.get('retries', task_obj.retries)
            task_obj.exception = event.get('exception', '')
            task_obj.traceback = event.get('traceback', '')
            # After retry, the task gets a new execution, so we should not set time_end.

        task_obj.updated_at = func.now()
        await session.flush()

        # Update daily stats (incrementally)
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

        if event_type == 'worker-online':
            worker.status = 'ONLINE'
            worker.last_heartbeat = datetime.datetime.fromtimestamp(event.get('timestamp', time.time()), tz=datetime.timezone.utc)
            worker.queues = ','.join(event.get('queues', []))
        elif event_type == 'worker-offline':
            worker.status = 'OFFLINE'
        elif event_type == 'worker-heartbeat':
            worker.status = 'ONLINE'  # ensure online
            worker.last_heartbeat = datetime.datetime.fromtimestamp(event.get('timestamp', time.time()), tz=datetime.timezone.utc)

        worker.updated_at = func.now()
        await session.flush()

    async def update_daily_stats(self, session: AsyncSession, status: str):
        today = datetime.date.today()
        date_start = datetime.datetime(today.year, today.month, today.day, tzinfo=datetime.timezone.utc)
        date_end = date_start + datetime.timedelta(days=1)
        stats_result = await session.execute(
            select(DailyStatsModel).where(
                DailyStatsModel.date >= date_start,
                DailyStatsModel.date < date_end
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
        # avg runtime update later via batch; skip for now.
        await session.flush()

# ---------- Orphan Detection ----------
async def orphan_detector():
    while True:
        await asyncio.sleep(60)  # Run every minute
        async with async_session() as session:
            now = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
            threshold = now - datetime.timedelta(seconds=settings.orphan_threshold_seconds)

            # Find tasks that are STARTED but worker offline or last heartbeat too old
            stmt = select(TaskModel).join(WorkerModel, isouter=True).where(
                TaskModel.status == 'STARTED',
                (WorkerModel.status == 'OFFLINE') | (WorkerModel.last_heartbeat < threshold)
            )
            result = await session.execute(stmt)
            orphan_tasks = result.scalars().all()
            for task in orphan_tasks:
                task.status = 'ORPHAN'
                task.updated_at = func.now()
            if orphan_tasks:
                await session.commit()
                for task in orphan_tasks:
                    message = json.dumps({"type": "task-updated", "data": {"task_id": task.task_id, "status": task.status}}, default=str)
                    await manager.broadcast(message)

# ---------- API Routers ----------
def get_session():
    async with async_session() as session:
        yield session

from fastapi import Depends

# Helper to convert ORM to dict
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
        # Could filter by worker hostname
        subq = select(WorkerModel.id).where(WorkerModel.hostname.ilike(f"%{worker}%"))
        filters.append(TaskModel.worker_id.in_(subq))
    if queue:
        filters.append(TaskModel.queue.ilike(f"%{queue}%"))
    if q:
        # Full-text search across name, args, kwargs, exception, traceback
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
    result = await session.execute(
        select(TaskModel).where(TaskModel.task_id == task_id)
    )
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
    result = await session.execute(
        select(WorkerModel).where(WorkerModel.hostname == hostname)
    )
    worker = result.scalars().first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    return worker_to_dict(worker)

@app.get("/stats/daily", response_model=List[Dict])
async def get_daily_stats(
    start: Optional[datetime.date] = Query(None, alias="start"),
    end: Optional[datetime.date] = Query(None, alias="end"),
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
            data = await websocket.receive_text()
            # Client can send filter options, but for simplicity we ignore
            pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# ---------- Static files for UI? Not implemented, just API.

if __name__ == "__main__":
    uvicorn.run("__main__:app", host=settings.api_host, port=settings.api_port, reload=True)