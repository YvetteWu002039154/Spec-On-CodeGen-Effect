import asyncio
import json
import logging
import threading
from datetime import datetime, timedelta, date
from typing import List, Optional, Dict, Any, Union

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, Query, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Date, or_, and_
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from celery import Celery
from alembic.config import Config
from alembic import command

# --- Database Configuration ---
SQLALCHEMY_DATABASE_URL = "sqlite:///./kanchi.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- SQLAlchemy Models ---
class TaskModel(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, index=True, nullable=False)
    state = Column(String, index=True, nullable=False)
    worker = Column(String, index=True)
    args = Column(String, nullable=True)
    kwargs = Column(String, nullable=True)
    result = Column(String, nullable=True)
    traceback = Column(String, nullable=True)
    retries = Column(Integer, default=0, nullable=False)
    is_orphan = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

class WorkerModel(Base):
    __tablename__ = "workers"

    id = Column(Integer, primary_key=True, index=True)
    hostname = Column(String, unique=True, index=True, nullable=False)
    status = Column(String, nullable=False)  # ONLINE, OFFLINE
    last_heartbeat = Column(DateTime, default=datetime.utcnow, nullable=False)

class DailyStatisticModel(Base):
    __tablename__ = "daily_statistics"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, unique=True, index=True, nullable=False)
    total_tasks = Column(Integer, default=0, nullable=False)
    successful_tasks = Column(Integer, default=0, nullable=False)
    failed_tasks = Column(Integer, default=0, nullable=False)
    retried_tasks = Column(Integer, default=0, nullable=False)

# --- Pydantic Schemas ---
class TaskBase(BaseModel):
    task_id: str
    name: str
    state: str
    worker: Optional[str] = None
    retries: int = 0
    is_orphan: bool = False

class TaskDetail(TaskBase):
    id: int
    args: Optional[str] = None
    kwargs: Optional[str] = None
    result: Optional[str] = None
    traceback: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        orm_mode = True

class WorkerDetail(BaseModel):
    hostname: str
    status: str
    last_heartbeat: datetime

    class Config:
        orm_mode = True

class DailyStatisticDetail(BaseModel):
    date: date
    total_tasks: int
    successful_tasks: int
    failed_tasks: int
    retried_tasks: int

    class Config:
        orm_mode = True

# --- Alembic Auto-Migration ---
class AutoMigration:
    @staticmethod
    def run_migrations():
        try:
            alembic_cfg = Config()
            alembic_cfg.set_main_option("script_location", "alembic")
            alembic_cfg.set_main_option("sqlalchemy.url", SQLALCHEMY_DATABASE_URL)
            command.upgrade(alembic_cfg, "head")
            logging.info("Alembic auto-migrations completed successfully.")
        except Exception as e:
            logging.warning(f"Alembic migration skipped or failed (ensure alembic is initialized): {e}")
            Base.metadata.create_all(bind=engine)
            logging.info("Fallback: SQLAlchemy create_all executed.")

# --- WebSocket Manager ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)

ws_manager = ConnectionManager()

# --- Services ---
class StatsService:
    def __init__(self, db: Session):
        self.db = db

    def update_daily_stats(self, state: str):
        today = datetime.utcnow().date()
        stat = self.db.query(DailyStatisticModel).filter(DailyStatisticModel.date == today).first()
        
        if not stat:
            stat = DailyStatisticModel(date=today)
            self.db.add(stat)
        
        stat.total_tasks += 1
        if state == 'SUCCESS':
            stat.successful_tasks += 1
        elif state == 'FAILURE':
            stat.failed_tasks += 1
        elif state == 'RETRY':
            stat.retried_tasks += 1
            
        self.db.commit()

    def get_history(self, limit: int = 30) -> List[DailyStatisticModel]:
        return self.db.query(DailyStatisticModel).order_by(DailyStatisticModel.date.desc()).limit(limit).all()

class WorkerService:
    def __init__(self, db: Session):
        self.db = db

    def update_health(self, hostname: str, status: str):
        worker = self.db.query(WorkerModel).filter(WorkerModel.hostname == hostname).first()
        if not worker:
            worker = WorkerModel(hostname=hostname)
            self.db.add(worker)
        
        worker.status = status
        worker.last_heartbeat = datetime.utcnow()
        self.db.commit()

    def check_worker_health(self, timeout_minutes: int = 5):
        threshold = datetime.utcnow() - timedelta(minutes=timeout_minutes)
        offline_workers = self.db.query(WorkerModel).filter(
            WorkerModel.last_heartbeat < threshold,
            WorkerModel.status == 'ONLINE'
        ).all()
        
        for worker in offline_workers:
            worker.status = 'OFFLINE'
        
        if offline_workers:
            self.db.commit()

    def get_all_workers(self) -> List[WorkerModel]:
        return self.db.query(WorkerModel).all()

class TaskService:
    def __init__(self, db: Session):
        self.db = db
        self.stats_service = StatsService(db)

    def process_event(self, event: dict):
        task_id = event.get('uuid')
        if not task_id:
            return

        task = self.db.query(TaskModel).filter(TaskModel.task_id == task_id).first()
        state = event.get('type', '').replace('task-', '').upper()

        if not task:
            task = TaskModel(
                task_id=task_id,
                name=event.get('name', 'unknown'),
                state=state,
                worker=event.get('hostname'),
                args=event.get('args'),
                kwargs=event.get('kwargs')
            )
            self.db.add(task)
        else:
            task.state = state
            if state == 'STARTED':
                task.started_at = datetime.utcnow()
            elif state in ['SUCCEEDED', 'FAILED']:
                task.completed_at = datetime.utcnow()
                task.result = event.get('result')
                task.traceback = event.get('traceback')
            elif state == 'RETRIED':
                task.retries += 1

        self.db.commit()
        self.stats_service.update_daily_stats(state)
        
        # Broadcast update via WebSocket
        asyncio.run(ws_manager.broadcast({
            "type": "task_update",
            "task_id": task.task_id,
            "state": task.state,
            "worker": task.worker
        }))

    def filter_tasks(
        self, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status: Optional[str] = None,
        name: Optional[str] = None,
        worker: Optional[str] = None,
        search_text: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[TaskModel]:
        query = self.db.query(TaskModel)

        if start_date:
            query = query.filter(TaskModel.created_at >= start_date)
        if end_date:
            query = query.filter(TaskModel.created_at <= end_date)
        if status:
            query = query.filter(TaskModel.state == status)
        if name:
            query = query.filter(TaskModel.name.ilike(f"%{name}%"))
        if worker:
            query = query.filter(TaskModel.worker == worker)
        if search_text:
            query = query.filter(
                or_(
                    TaskModel.args.ilike(f"%{search_text}%"),
                    TaskModel.kwargs.ilike(f"%{search_text}%"),
                    TaskModel.result.ilike(f"%{search_text}%"),
                    TaskModel.traceback.ilike(f"%{search_text}%")
                )
            )

        return query.order_by(TaskModel.created_at.desc()).offset(skip).limit(limit).all()

    def detect_orphans(self, timeout_hours: int = 1):
        threshold = datetime.utcnow() - timedelta(hours=timeout_hours)
        orphans = self.db.query(TaskModel).filter(
            TaskModel.state.in_(['STARTED', 'RECEIVED']),
            TaskModel.created_at < threshold,
            TaskModel.is_orphan == False
        ).all()

        for task in orphans:
            task.is_orphan = True
            task.state = 'ORPHANED'
        
        if orphans:
            self.db.commit()

# --- Celery Event Monitor ---
class CeleryMonitor:
    def __init__(self, broker_url: str = 'redis://localhost:6379/0'):
        self.app = Celery('kanchi_monitor', broker=broker_url)
        self.thread = threading.Thread(target=self._run_monitor, daemon=True)

    def start(self):
        self.thread.start()

    def _run_monitor(self):
        def on_task_event(event):
            with SessionLocal() as db:
                task_service = TaskService(db)
                task_service.process_event(event)

        def on_worker_event(event):
            with SessionLocal() as db:
                worker_service = WorkerService(db)
                hostname = event.get('hostname')
                event_type = event.get('type')
                if hostname:
                    status = 'ONLINE' if event_type in ['worker-online', 'worker-heartbeat'] else 'OFFLINE'
                    worker_service.update_health(hostname, status)

        while True:
            try:
                with self.app.connection() as connection:
                    recv = self.app.events.Receiver(connection, handlers={
                        'task-sent': on_task_event,
                        'task-received': on_task_event,
                        'task-started': on_task_event,
                        'task-succeeded': on_task_event,
                        'task-failed': on_task_event,
                        'task-retried': on_task_event,
                        'worker-online': on_worker_event,
                        'worker-heartbeat': on_worker_event,
                        'worker-offline': on_worker_event,
                    })
                    recv.capture(limit=None, timeout=None, wakeup=True)
            except Exception as e:
                logging.error(f"Celery monitor connection lost: {e}. Retrying in 5 seconds...")
                import time
                time.sleep(5)

# --- Background Tasks ---
def background_health_and_orphan_checks():
    while True:
        try:
            with SessionLocal() as db:
                worker_service = WorkerService(db)
                worker_service.check_worker_health()
                
                task_service = TaskService(db)
                task_service.detect_orphans()
        except Exception as e:
            logging.error(f"Background check error: {e}")
        
        import time
        time.sleep(60)

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
    AutoMigration.run_migrations()
    
    celery_monitor = CeleryMonitor()
    celery_monitor.start()
    
    bg_thread = threading.Thread(target=background_health_and_orphan_checks, daemon=True)
    bg_thread.start()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)

@app.get("/api/tasks", response_model=List[TaskDetail])
def get_tasks(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    status: Optional[str] = None,
    name: Optional[str] = None,
    worker: Optional[str] = None,
    search_text: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    task_service = TaskService(db)
    return task_service.filter_tasks(
        start_date=start_date,
        end_date=end_date,
        status=status,
        name=name,
        worker=worker,
        search_text=search_text,
        skip=skip,
        limit=limit
    )

@app.get("/api/workers", response_model=List[WorkerDetail])
def get_workers(db: Session = Depends(get_db)):
    worker_service = WorkerService(db)
    return worker_service.get_all_workers()

@app.get("/api/statistics/daily", response_model=List[DailyStatisticDetail])
def get_daily_statistics(limit: int = Query(30, ge=1, le=365), db: Session = Depends(get_db)):
    stats_service = StatsService(db)
    return stats_service.get_history(limit=limit)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)