import os
import sys
import asyncio
import json
import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

import celery
from celery import states
from celery.events.receiver import Receiver
from celery.events.state import Worker as CeleryWorker, Task as CeleryTask

import sqlalchemy as sa
from sqlalchemy import (Boolean, Column, Date, DateTime, ForeignKey, Integer,
                        String, Text, UniqueConstraint, create_engine, func)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session as SaSession

from fastapi import (FastAPI, HTTPException, WebSocket, WebSocketDisconnect,
                     Depends, Query)
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

import alembic.config
import alembic.command

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("kanchi")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./kanchi.db")
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class TaskModel(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, index=True)
    name = Column(String, index=True)
    args = Column(Text)
    kwargs = Column(Text)
    status = Column(String(20), index=True)
    worker_hostname = Column(String, index=True, nullable=True)
    worker_pid = Column(Integer, nullable=True)
    timestamp = Column(DateTime)
    result = Column(Text, nullable=True)
    traceback = Column(Text, nullable=True)
    retries = Column(Integer, default=0)
    root_id = Column(String(36), nullable=True, index=True)
    parent_id = Column(String(36), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    children = relationship("TaskModel", backref="parent", remote_side=[id])
    worker = relationship("WorkerModel", foreign_keys=[worker_hostname], backref="tasks")

class WorkerModel(Base):
    __tablename__ = "workers"

    hostname = Column(String, primary_key=True)
    pid = Column(Integer, primary_key=True)
    last_heartbeat = Column(DateTime)
    status = Column(String(20), default="offline")
    active_tasks = Column(Integer, default=0)
    processed = Column(Integer, default=0)
    queues = Column(Text, default="[]")

class DailyStatsModel(Base):
    __tablename__ = "daily_stats"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, unique=True, index=True)
    total = Column(Integer, default=0)
    success = Column(Integer, default=0)
    failure = Column(Integer, default=0)
    revoked = Column(Integer, default=0)
    retry = Column(Integer, default=0)

Base.metadata.create_all(bind=engine)

def run_alembic_migrations():
    alembic_ini = os.path.join(os.path.dirname(__file__), "alembic.ini")
    if not os.path.exists(alembic_ini):
        from textwrap import dedent
        ini_content = dedent("""\
        [alembic]
        script_location = alembic
        sqlalchemy.url = {db_url}
        """).format(db_url=DATABASE_URL)
        os.makedirs(os.path.dirname(alembic_ini), exist_ok=True)
        with open(alembic_ini, "w") as f:
            f.write(ini_content)

        alembic_dir = os.path.join(os.path.dirname(__file__), "alembic")
        os.makedirs(alembic_dir, exist_ok=True)
        env_py = os.path.join(alembic_dir, "env.py")
        with open(env_py, "w") as f:
            f.write(dedent("""\
            from logging.config import fileConfig
            from sqlalchemy import engine_from_config
            from sqlalchemy import pool
            from alembic import context
            from kanchi.models import Base

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
            """))

        script_template = os.path.join(alembic_dir, "script.py.mako")
        os.makedirs(os.path.dirname(script_template), exist_ok=True)
        with open(script_template, "w") as f:
            f.write("""\
""")

    alembic.config.main(argv=["upgrade", "head"])

class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast(self, message: Dict):
        if not self.active_connections:
            return
        payload = json.dumps(message)
        await asyncio.gather(*(ws.send_text(payload) for ws in self.active_connections), return_exceptions=True)

manager = ConnectionManager()

def find_orphans(session: SaSession, timeout_seconds: int = 120) -> List[TaskModel]:
    threshold = datetime.utcnow() - timedelta(seconds=timeout_seconds)
    non_terminal = [states.PENDING, states.RECEIVED, states.STARTED, states.RETRY]
    orphans = session.query(TaskModel).filter(
        TaskModel.status.in_(non_terminal),
        TaskModel.updated_at < threshold,
        ~TaskModel.worker_hostname.in_(
            session.query(WorkerModel.hostname).filter(WorkerModel.last_heartbeat >= threshold)
        )
    ).all()
    return orphans

def compute_daily_stats(session: SaSession, target_date: date):
    tasks = session.query(TaskModel).filter(sa.func.date(TaskModel.created_at) == target_date).all()
    total = len(tasks)
    success = sum(1 for t in tasks if t.status == states.SUCCESS)
    failure = sum(1 for t in tasks if t.status == states.FAILURE)
    revoked = sum(1 for t in tasks if t.status == states.REVOKED)
    retry = sum(1 for t in tasks if t.status == states.RETRY)
    existing = session.query(DailyStatsModel).filter(DailyStatsModel.date == target_date).first()
    if existing:
        existing.total, existing.success, existing.failure, existing.revoked, existing.retry = total, success, failure, revoked, retry
    else:
        session.add(DailyStatsModel(date=target_date, total=total, success=success, failure=failure, revoked=revoked, retry=retry))
    session.commit()

def handle_celery_event(event_name: str, event: Dict):
    db = SessionLocal()
    try:
        if event_name.startswith("task-"):
            handle_task_event(event_name, event, db)
        elif event_name.startswith("worker-"):
            handle_worker_event(event_name, event, db)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Error handling event {event_name}: {e}")
    finally:
        db.close()

def handle_task_event(event_name: str, event: Dict, db: SaSession):
    uuid = event["uuid"]
    task = db.query(TaskModel).filter(TaskModel.uuid == uuid).first()
    now = datetime.utcnow()
    if event_name == "task-sent":
        task = TaskModel(
            uuid=uuid,
            name=event["name"],
            args=event.get("args"),
            kwargs=event.get("kwargs"),
            status=states.PENDING,
            timestamp=datetime.fromtimestamp(event["timestamp"]),
            created_at=now,
            updated_at=now
        )
        db.add(task)
    elif event_name == "task-received":
        if not task:
            task = TaskModel(uuid=uuid, name=event["name"], args=event.get("args"), kwargs=event.get("kwargs"))
            db.add(task)
        task.status = states.RECEIVED
        task.timestamp = datetime.fromtimestamp(event["timestamp"])
        task.worker_hostname = event["hostname"]
        task.worker_pid = event["pid"]
        task.updated_at = now
    elif event_name == "task-started":
        if not task:
            task = TaskModel(uuid=uuid, name=event["name"], args=event.get("args"), kwargs=event.get("kwargs"))
            db.add(task)
        task.status = states.STARTED
        task.timestamp = datetime.fromtimestamp(event["timestamp"])
        task.worker_hostname = event["hostname"]
        task.worker_pid = event["pid"]
        task.updated_at = now
    elif event_name == "task-succeeded":
        if not task:
            task = TaskModel(uuid=uuid, name=event["name"], args=event.get("args"), kwargs=event.get("kwargs"))
            db.add(task)
        task.status = states.SUCCESS
        task.result = event.get("result")
        task.timestamp = datetime.fromtimestamp(event["timestamp"])
        task.updated_at = now
    elif event_name == "task-failed":
        if not task:
            task = TaskModel(uuid=uuid, name=event["name"], args=event.get("args"), kwargs=event.get("kwargs"))
            db.add(task)
        task.status = states.FAILURE
        task.traceback = event.get("traceback")
        task.timestamp = datetime.fromtimestamp(event["timestamp"])
        task.updated_at = now
    elif event_name == "task-retried":
        if not task:
            task = TaskModel(uuid=uuid, name=event["name"], args=event.get("args"), kwargs=event.get("kwargs"))
            db.add(task)
        task.status = states.RETRY
        task.traceback = event.get("traceback")
        task.timestamp = datetime.fromtimestamp(event["timestamp"])
        task.updated_at = now
        task.retries = event.get("retries", 0)
        request = event.get("request")
        if request and "root_id" in request:
            task.root_id = request["root_id"]
            orig = db.query(TaskModel).filter(TaskModel.uuid == request["root_id"]).first()
            if orig:
                orig.retries = task.retries
    elif event_name == "task-revoked":
        if not task:
            task = TaskModel(uuid=uuid, name=event["name"], args=event.get("args"), kwargs=event.get("kwargs"))
            db.add(task)
        task.status = states.REVOKED
        task.timestamp = datetime.fromtimestamp(event["timestamp"])
        task.updated_at = now
    db.flush()
    asyncio.run_coroutine_threadsafe(manager.broadcast({"type": "task_update", "uuid": uuid, "status": task.status}), loop)

def handle_worker_event(event_name: str, event: Dict, db: SaSession):
    hostname = event["hostname"]
    pid = event["pid"]
    worker = db.query(WorkerModel).filter(WorkerModel.hostname == hostname, WorkerModel.pid == pid).first()
    now = datetime.utcnow()
    if event_name == "worker-online":
        if not worker:
            worker = WorkerModel(hostname=hostname, pid=pid, last_heartbeat=now, status="online")
            db.add(worker)
        else:
            worker.status = "online"
            worker.last_heartbeat = now
    elif event_name == "worker-offline":
        if worker:
            worker.status = "offline"
            worker.last_heartbeat = now
    elif event_name == "worker-heartbeat":
        if not worker:
            worker = WorkerModel(hostname=hostname, pid=pid, last_heartbeat=now, status="online")
            db.add(worker)
        else:
            worker.last_heartbeat = now
            if worker.status == "offline":
                worker.status = "online"
        worker.active_tasks = event.get("active", 0)
        worker.processed = event.get("processed", event.get("total", 0))
        if "queues" in event:
            worker.queues = json.dumps(event["queues"])
    db.flush()
    asyncio.run_coroutine_threadsafe(manager.broadcast({"type": "worker_update", "hostname": hostname, "status": worker.status}), loop)

def celery_monitor():
    app = celery.Celery(broker=CELERY_BROKER_URL)
    state = State()
    with app.connection() as connection:
        receiver = Receiver(connection)
        state.event_count = 0
        for event_name, event in receiver.itercapture():
            handle_celery_event(event_name, event)

loop = None

def start_monitor():
    global loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    import threading
    t = threading.Thread(target=celery_monitor, daemon=True)
    t.start()
    loop.run_forever()

app = FastAPI(title="Kanchi")

@app.on_event("startup")
async def startup():
    run_alembic_migrations()
    global loop
    loop = asyncio.get_event_loop()
    import threading as _threading
    _threading.Thread(target=celery_monitor, daemon=True).start()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

class TaskFilterParams(BaseModel):
    date_from: Optional[date] = Query(None)
    date_to: Optional[date] = Query(None)
    status: Optional[str] = Query(None)
    name: Optional[str] = Query(None)
    worker: Optional[str] = Query(None)
    search: Optional[str] = Query(None)

class TaskOut(BaseModel):
    id: int
    uuid: str
    name: str
    args: Optional[str]
    kwargs: Optional[str]
    status: str
    worker_hostname: Optional[str]
    timestamp: datetime
    retries: int
    root_id: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class WorkerOut(BaseModel):
    hostname: str
    pid: int
    last_heartbeat: datetime
    status: str
    active_tasks: int
    processed: int
    queues: Optional[List[str]] = []

    class Config:
        orm_mode = True

class DailyStatsOut(BaseModel):
    date: date
    total: int
    success: int
    failure: int
    revoked: int
    retry: int

    class Config:
        orm_mode = True

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/tasks", response_model=List[TaskOut])
def list_tasks(filters: TaskFilterParams = Depends(), db: SaSession = Depends(get_db)):
    query = db.query(TaskModel)
    if filters.date_from:
        query = query.filter(func.date(TaskModel.created_at) >= filters.date_from)
    if filters.date_to:
        query = query.filter(func.date(TaskModel.created_at) <= filters.date_to)
    if filters.status:
        query = query.filter(TaskModel.status == filters.status)
    if filters.name:
        query = query.filter(TaskModel.name.ilike(f"%{filters.name}%"))
    if filters.worker:
        query = query.filter(TaskModel.worker_hostname.ilike(f"%{filters.worker}%"))
    if filters.search:
        search_term = f"%{filters.search}%"
        query = query.filter(
            TaskModel.name.ilike(search_term) |
            TaskModel.args.ilike(search_term) |
            TaskModel.kwargs.ilike(search_term) |
            TaskModel.result.ilike(search_term) |
            TaskModel.traceback.ilike(search_term)
        )
    tasks = query.order_by(TaskModel.created_at.desc()).limit(200).all()
    return tasks

@app.get("/tasks/{task_id}", response_model=TaskOut)
def get_task(task_id: int, db: SaSession = Depends(get_db)):
    task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@app.get("/workers", response_model=List[WorkerOut])
def list_workers(db: SaSession = Depends(get_db)):
    workers = db.query(WorkerModel).all()
    return workers

@app.get("/workers/{hostname}", response_model=WorkerOut)
def get_worker(hostname: str, db: SaSession = Depends(get_db)):
    worker = db.query(WorkerModel).filter(WorkerModel.hostname == hostname).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    return worker

@app.get("/stats/daily", response_model=DailyStatsOut)
def daily_stats(date_param: date = Query(..., alias="date"), db: SaSession = Depends(get_db)):
    compute_daily_stats(db, date_param)
    stat = db.query(DailyStatsModel).filter(DailyStatsModel.date == date_param).first()
    if not stat:
        raise HTTPException(status_code=404, detail="No stats for that date")
    return stat

@app.get("/orphans", response_model=List[TaskOut])
def orphans(timeout: int = Query(120), db: SaSession = Depends(get_db)):
    orphan_tasks = find_orphans(db, timeout)
    return orphan_tasks

@app.get("/")
def root():
    return {"service": "Kanchi Task Monitor"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)