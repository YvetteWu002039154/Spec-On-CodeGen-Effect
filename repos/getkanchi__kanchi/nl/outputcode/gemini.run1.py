import asyncio
import json
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from alembic import command
from alembic.config import Config
from celery import Celery
from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect
from sqlalchemy import Boolean, Column, DateTime, Integer, String, create_engine, func, or_
from sqlalchemy.orm import declarative_base, sessionmaker, Session

DATABASE_URL = "sqlite:///./kanchi.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String, unique=True, index=True)
    name = Column(String, index=True)
    status = Column(String, index=True)
    worker = Column(String, index=True)
    args = Column(String, nullable=True)
    kwargs = Column(String, nullable=True)
    result = Column(String, nullable=True)
    traceback = Column(String, nullable=True)
    retries = Column(Integer, default=0)
    is_orphan = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Worker(Base):
    __tablename__ = "workers"

    id = Column(Integer, primary_key=True, index=True)
    hostname = Column(String, unique=True, index=True)
    status = Column(String, index=True)
    last_heartbeat = Column(DateTime, default=datetime.utcnow)

class DailyStatistic(Base):
    __tablename__ = "daily_statistics"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, unique=True, index=True)
    total_tasks = Column(Integer, default=0)
    successful_tasks = Column(Integer, default=0)
    failed_tasks = Column(Integer, default=0)
    retried_tasks = Column(Integer, default=0)

def run_auto_migrations(connection_string: str) -> None:
    Base.metadata.create_all(bind=engine)
    alembic_cfg = Config()
    alembic_cfg.set_main_option("script_location", "alembic")
    alembic_cfg.set_main_option("sqlalchemy.url", connection_string)
    try:
        command.upgrade(alembic_cfg, "head")
    except Exception:
        pass

class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: Dict[str, Any]) -> None:
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

ws_manager = ConnectionManager()

class TaskService:
    def __init__(self, db: Session):
        self.db = db

    def filter_tasks(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status: Optional[str] = None,
        name: Optional[str] = None,
        worker: Optional[str] = None,
        search_text: Optional[str] = None
    ) -> List[Task]:
        query = self.db.query(Task)
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
        if search_text:
            query = query.filter(
                or_(
                    Task.name.ilike(f"%{search_text}%"),
                    Task.args.ilike(f"%{search_text}%"),
                    Task.kwargs.ilike(f"%{search_text}%"),
                    Task.task_id.ilike(f"%{search_text}%")
                )
            )
        return query.all()

    def track_retry(self, task_id: str) -> Optional[Task]:
        task = self.db.query(Task).filter(Task.task_id == task_id).first()
        if task:
            task.retries += 1
            task.status = "RETRY"
            self.db.commit()
            self.db.refresh(task)
        return task

    def detect_orphans(self, timeout_minutes: int = 15) -> List[Task]:
        timeout_threshold = datetime.utcnow() - timedelta(minutes=timeout_minutes)
        orphans = self.db.query(Task).filter(
            Task.status == "STARTED",
            Task.updated_at < timeout_threshold,
            Task.is_orphan == False
        ).all()
        
        for task in orphans:
            task.is_orphan = True
            task.status = "ORPHANED"
        
        if orphans:
            self.db.commit()
            
        return orphans

    def update_or_create_task(self, task_data: Dict[str, Any]) -> Task:
        task = self.db.query(Task).filter(Task.task_id == task_data["task_id"]).first()
        if not task:
            task = Task(**task_data)
            self.db.add(task)
        else:
            for key, value in task_data.items():
                setattr(task, key, value)
        self.db.commit()
        self.db.refresh(task)
        return task

class WorkerService:
    def __init__(self, db: Session):
        self.db = db

    def update_health(self, hostname: str, status: str) -> Worker:
        worker = self.db.query(Worker).filter(Worker.hostname == hostname).first()
        if not worker:
            worker = Worker(hostname=hostname, status=status)
            self.db.add(worker)
        else:
            worker.status = status
            worker.last_heartbeat = datetime.utcnow()
        self.db.commit()
        self.db.refresh(worker)
        return worker

    def check_health(self, timeout_minutes: int = 5) -> List[Worker]:
        timeout_threshold = datetime.utcnow() - timedelta(minutes=timeout_minutes)
        offline_workers = self.db.query(Worker).filter(
            Worker.last_heartbeat < timeout_threshold,
            Worker.status == "ONLINE"
        ).all()
        
        for worker in offline_workers:
            worker.status = "OFFLINE"
            
        if offline_workers:
            self.db.commit()
            
        return self.db.query(Worker).all()

class StatsService:
    def __init__(self, db: Session):
        self.db = db

    def update_daily_stats(self, status: str) -> DailyStatistic:
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        stat = self.db.query(DailyStatistic).filter(DailyStatistic.date == today).first()
        
        if not stat:
            stat = DailyStatistic(date=today)
            self.db.add(stat)
            
        stat.total_tasks += 1
        if status == "SUCCESS":
            stat.successful_tasks += 1
        elif status == "FAILURE":
            stat.failed_tasks += 1
        elif status == "RETRY":
            stat.retried_tasks += 1
            
        self.db.commit()
        self.db.refresh(stat)
        return stat

    def get_history(self, days: int = 30) -> List[DailyStatistic]:
        start_date = datetime.utcnow() - timedelta(days=days)
        return self.db.query(DailyStatistic).filter(DailyStatistic.date >= start_date).order_by(DailyStatistic.date.desc()).all()

def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI(title="Kanchi - Celery Task Monitoring")

@app.on_event("startup")
def on_startup() -> None:
    run_auto_migrations(DATABASE_URL)
    celery_app = Celery("kanchi_monitor", broker="amqp://guest@localhost//")
    monitor_thread = threading.Thread(target=start_celery_monitor, args=(celery_app,), daemon=True)
    monitor_thread.start()

@app.websocket("/ws/monitor")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)

@app.get("/api/tasks")
def get_tasks(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    status: Optional[str] = None,
    name: Optional[str] = None,
    worker: Optional[str] = None,
    search_text: Optional[str] = None,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    task_service = TaskService(db)
    tasks = task_service.filter_tasks(start_date, end_date, status, name, worker, search_text)
    return {"tasks": [task.__dict__ for task in tasks]}

@app.get("/api/workers")
def get_workers(db: Session = Depends(get_db)) -> Dict[str, Any]:
    worker_service = WorkerService(db)
    workers = worker_service.check_health()
    return {"workers": [worker.__dict__ for worker in workers]}

@app.get("/api/statistics")
def get_statistics(days: int = 30, db: Session = Depends(get_db)) -> Dict[str, Any]:
    stats_service = StatsService(db)
    history = stats_service.get_history(days)
    return {"statistics": [stat.__dict__ for stat in history]}

@app.post("/api/tasks/detect-orphans")
def trigger_orphan_detection(db: Session = Depends(get_db)) -> Dict[str, Any]:
    task_service = TaskService(db)
    orphans = task_service.detect_orphans()
    return {"orphaned_tasks_detected": len(orphans)}

def start_celery_monitor(celery_app: Celery) -> None:
    def on_task_event(event: Dict[str, Any]) -> None:
        db = SessionLocal()
        try:
            task_service = TaskService(db)
            stats_service = StatsService(db)
            
            event_type = event.get("type", "")
            task_id = event.get("uuid")
            
            if not task_id:
                return

            status_map = {
                "task-sent": "PENDING",
                "task-received": "RECEIVED",
                "task-started": "STARTED",
                "task-succeeded": "SUCCESS",
                "task-failed": "FAILURE",
                "task-retried": "RETRY"
            }

            status = status_map.get(event_type)
            if not status:
                return

            task_data = {
                "task_id": task_id,
                "name": event.get("name"),
                "status": status,
                "worker": event.get("hostname"),
                "args": event.get("args"),
                "kwargs": event.get("kwargs"),
                "result": event.get("result"),
                "traceback": event.get("traceback")
            }
            
            task_data = {k: v for k, v in task_data.items() if v is not None}
            
            if status == "RETRY":
                task_service.track_retry(task_id)
            else:
                task_service.update_or_create_task(task_data)

            if status in ["SUCCESS", "FAILURE", "RETRY"]:
                stats_service.update_daily_stats(status)

            asyncio.run(ws_manager.broadcast({
                "type": "task_update",
                "data": task_data
            }))
            
        finally:
            db.close()

    def on_worker_event(event: Dict[str, Any]) -> None:
        db = SessionLocal()
        try:
            worker_service = WorkerService(db)
            event_type = event.get("type", "")
            hostname = event.get("hostname")
            
            if not hostname:
                return

            status = "ONLINE" if event_type in ["worker-online", "worker-heartbeat"] else "OFFLINE"
            worker_service.update_health(hostname, status)

            asyncio.run(ws_manager.broadcast({
                "type": "worker_update",
                "data": {"hostname": hostname, "status": status}
            }))
        finally:
            db.close()

    with celery_app.connection() as connection:
        recv = celery_app.events.Receiver(connection, handlers={
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)