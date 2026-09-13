import asyncio
import json
import logging
import threading
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from alembic import command
from alembic.config import Config
from celery import Celery
from fastapi import Depends, FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Boolean, Column, Date, DateTime, Integer, String, Text, create_engine, or_
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# --- Database Configuration ---
SQLALCHEMY_DATABASE_URL = "sqlite:///./kanchi.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- SQLAlchemy Models ---
class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String, unique=True, index=True)
    name = Column(String, index=True, nullable=True)
    status = Column(String, index=True, default="PENDING")
    worker = Column(String, index=True, nullable=True)
    args = Column(Text, nullable=True)
    kwargs = Column(Text, nullable=True)
    result = Column(Text, nullable=True)
    traceback = Column(Text, nullable=True)
    retries = Column(Integer, default=0)
    is_orphan = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Worker(Base):
    __tablename__ = "workers"

    id = Column(Integer, primary_key=True, index=True)
    hostname = Column(String, unique=True, index=True)
    status = Column(String, default="OFFLINE")
    last_heartbeat = Column(DateTime, default=datetime.utcnow)

class DailyStatistic(Base):
    __tablename__ = "daily_statistics"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, unique=True, index=True, default=datetime.utcnow().date)
    total_tasks = Column(Integer, default=0)
    successful_tasks = Column(Integer, default=0)
    failed_tasks = Column(Integer, default=0)
    retried_tasks = Column(Integer, default=0)

# --- Alembic Auto-Migrations ---
def run_auto_migrations():
    try:
        alembic_cfg = Config()
        alembic_cfg.set_main_option("script_location", "alembic")
        alembic_cfg.set_main_option("sqlalchemy.url", SQLALCHEMY_DATABASE_URL)
        command.upgrade(alembic_cfg, "head")
    except Exception as e:
        logging.warning(f"Alembic migration failed or not initialized, falling back to create_all: {e}")
        Base.metadata.create_all(bind=engine)

# --- Pydantic Schemas ---
class TaskBase(BaseModel):
    task_id: str
    name: Optional[str] = None
    status: str
    worker: Optional[str] = None
    args: Optional[str] = None
    kwargs: Optional[str] = None
    result: Optional[str] = None
    traceback: Optional[str] = None
    retries: int
    is_orphan: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class WorkerBase(BaseModel):
    hostname: str
    status: str
    last_heartbeat: datetime

    model_config = ConfigDict(from_attributes=True)

class DailyStatisticBase(BaseModel):
    date: date
    total_tasks: int
    successful_tasks: int
    failed_tasks: int
    retried_tasks: int

    model_config = ConfigDict(from_attributes=True)

# --- Business Logic & Managers ---
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
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                self.disconnect(connection)

ws_manager = ConnectionManager()

class TaskManager:
    @staticmethod
    def get_tasks(
        db: Session,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status: Optional[str] = None,
        name: Optional[str] = None,
        worker: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Task]:
        query = db.query(Task)
        if start_date:
            query = query.filter(Task.created_at >= start_date)
        if end_date:
            query = query.filter(Task.created_at <= end_date)
        if status:
            query = query.filter(Task.status == status)
        if name:
            query = query.filter(Task.name == name)
        if worker:
            query = query.filter(Task.worker == worker)
        if search:
            search_filter = f"%{search}%"
            query = query.filter(
                or_(
                    Task.args.like(search_filter),
                    Task.kwargs.like(search_filter),
                    Task.result.like(search_filter),
                    Task.name.like(search_filter)
                )
            )
        return query.order_by(Task.created_at.desc()).offset(offset).limit(limit).all()

    @staticmethod
    def update_daily_stats(db: Session, status: str):
        today = datetime.utcnow().date()
        stat = db.query(DailyStatistic).filter(DailyStatistic.date == today).first()
        if not stat:
            stat = DailyStatistic(date=today)
            db.add(stat)
        
        stat.total_tasks += 1
        if status == "SUCCESS":
            stat.successful_tasks += 1
        elif status == "FAILURE":
            stat.failed_tasks += 1
        elif status == "RETRY":
            stat.retried_tasks += 1
        
        db.commit()

    @staticmethod
    def detect_orphans(db: Session, timeout_minutes: int = 5) -> int:
        cutoff_time = datetime.utcnow() - timedelta(minutes=timeout_minutes)
        offline_workers = db.query(Worker).filter(Worker.last_heartbeat < cutoff_time).all()
        
        orphan_count = 0
        for worker in offline_workers:
            worker.status = "OFFLINE"
            orphaned_tasks = db.query(Task).filter(
                Task.worker == worker.hostname,
                Task.status == "STARTED"
            ).all()
            
            for task in orphaned_tasks:
                task.is_orphan = True
                task.status = "ORPHANED"
                orphan_count += 1
                
        db.commit()
        return orphan_count

# --- Celery Event Monitor ---
class CeleryMonitorThread(threading.Thread):
    def __init__(self, broker_url: str, loop: asyncio.AbstractEventLoop):
        super().__init__()
        self.app = Celery("kanchi", broker=broker_url)
        self.loop = loop
        self.daemon = True

    def run(self):
        while True:
            try:
                with self.app.connection() as connection:
                    recv = self.app.events.Receiver(connection, handlers={
                        "task-sent": self.handle_task_event,
                        "task-received": self.handle_task_event,
                        "task-started": self.handle_task_event,
                        "task-succeeded": self.handle_task_event,
                        "task-failed": self.handle_task_event,
                        "task-retried": self.handle_task_event,
                        "worker-heartbeat": self.handle_worker_event,
                        "worker-online": self.handle_worker_event,
                        "worker-offline": self.handle_worker_event,
                    })
                    recv.capture(limit=None, timeout=None, wakeup=True)
            except Exception as e:
                logging.error(f"Celery monitor error: {e}")
                threading.Event().wait(5)

    def handle_task_event(self, event: Dict[str, Any]):
        db = SessionLocal()
        try:
            task_id = event.get("uuid")
            if not task_id:
                return

            task = db.query(Task).filter(Task.task_id == task_id).first()
            if not task:
                task = Task(task_id=task_id)
                db.add(task)

            if "name" in event:
                task.name = event["name"]
            if "hostname" in event:
                task.worker = event["hostname"]
            if "args" in event:
                task.args = str(event["args"])
            if "kwargs" in event:
                task.kwargs = str(event["kwargs"])
            if "result" in event:
                task.result = str(event["result"])
            if "traceback" in event:
                task.traceback = str(event["traceback"])

            event_type = event.get("type")
            if event_type == "task-started":
                task.status = "STARTED"
            elif event_type == "task-succeeded":
                task.status = "SUCCESS"
                TaskManager.update_daily_stats(db, "SUCCESS")
            elif event_type == "task-failed":
                task.status = "FAILURE"
                TaskManager.update_daily_stats(db, "FAILURE")
            elif event_type == "task-retried":
                task.status = "RETRY"
                task.retries += 1
                TaskManager.update_daily_stats(db, "RETRY")

            db.commit()
            
            asyncio.run_coroutine_threadsafe(
                ws_manager.broadcast(json.dumps({"type": "task_update", "data": event})),
                self.loop
            )
        finally:
            db.close()

    def handle_worker_event(self, event: Dict[str, Any]):
        db = SessionLocal()
        try:
            hostname = event.get("hostname")
            if not hostname:
                return

            worker = db.query(Worker).filter(Worker.hostname == hostname).first()
            if not worker:
                worker = Worker(hostname=hostname)
                db.add(worker)

            event_type = event.get("type")
            if event_type in ("worker-online", "worker-heartbeat"):
                worker.status = "ONLINE"
                worker.last_heartbeat = datetime.utcnow()
            elif event_type == "worker-offline":
                worker.status = "OFFLINE"

            db.commit()
            
            asyncio.run_coroutine_threadsafe(
                ws_manager.broadcast(json.dumps({"type": "worker_update", "data": event})),
                self.loop
            )
        finally:
            db.close()

# --- FastAPI Application ---
app = FastAPI(title="Kanchi - Celery Task Monitoring")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.on_event("startup")
def on_startup():
    run_auto_migrations()
    loop = asyncio.get_running_loop()
    monitor_thread = CeleryMonitorThread(broker_url="amqp://guest:guest@localhost:5672//", loop=loop)
    monitor_thread.start()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)

@app.get("/tasks", response_model=List[TaskBase])
def read_tasks(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    status: Optional[str] = None,
    name: Optional[str] = None,
    worker: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    return TaskManager.get_tasks(db, start_date, end_date, status, name, worker, search, limit, offset)

@app.get("/tasks/{task_id}", response_model=TaskBase)
def read_task(task_id: str, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@app.post("/tasks/detect-orphans")
def trigger_orphan_detection(timeout_minutes: int = 5, db: Session = Depends(get_db)):
    orphans_found = TaskManager.detect_orphans(db, timeout_minutes)
    return {"message": f"Orphan detection completed. {orphans_found} orphans found and updated."}

@app.get("/workers", response_model=List[WorkerBase])
def read_workers(db: Session = Depends(get_db)):
    return db.query(Worker).all()

@app.get("/statistics", response_model=List[DailyStatisticBase])
def read_statistics(limit: int = 30, db: Session = Depends(get_db)):
    return db.query(DailyStatistic).order_by(DailyStatistic.date.desc()).limit(limit).all()