import asyncio
import datetime
import json
import logging
import random
import uuid
from typing import Optional, List, Dict, Any, Set
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.exceptions import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import (
    create_engine,
    Column,
    String,
    DateTime,
    Integer,
    Text,
    Boolean,
    Float,
    ForeignKey,
    func,
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.ext.declarative import declarative_base
import threading
import time

# ===================== Configuration =====================

DATABASE_URL = "sqlite:///kanchi.db"
CELERY_BROKER_URL = "redis://localhost:6379/0"  # not used directly in the mock

# ===================== Logging =====================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("kanchi")

# ===================== Database Setup =====================
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ===================== SQLAlchemy Models =====================

class WorkerModel(Base):
    __tablename__ = "workers"
    hostname = Column(String(255), primary_key=True, index=True)
    status = Column(String(50), default="online")  # online/offline
    last_heartbeat = Column(DateTime, default=datetime.datetime.utcnow)
    pid = Column(Integer, nullable=True)
    cpu_usage = Column(Float, nullable=True)  # optional monitoring
    memory_usage = Column(Float, nullable=True)
    tasks_processed = Column(Integer, default=0)

    tasks = relationship("TaskModel", back_populates="worker", foreign_keys="TaskModel.worker_hostname")

class TaskModel(Base):
    __tablename__ = "tasks"
    uuid = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), index=True)
    status = Column(String(50), index=True)  # PENDING, STARTED, SUCCESS, FAILURE, RETRY, REVOKED
    args = Column(JSON, default=list)
    kwargs = Column(JSON, default=dict)
    result = Column(JSON, nullable=True)
    traceback = Column(Text, nullable=True)
    worker_hostname = Column(String(255), ForeignKey("workers.hostname"), nullable=True, index=True)
    parent_id = Column(String(36), ForeignKey("tasks.uuid"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    date_done = Column(DateTime, nullable=True)
    retry_count = Column(Integer, default=0)
    expires = Column(DateTime, nullable=True)
    eta = Column(DateTime, nullable=True)
    priority = Column(Integer, nullable=True)
    correlation_id = Column(String(255), nullable=True, index=True)  # for grouping

    worker = relationship("WorkerModel", back_populates="tasks", foreign_keys=[worker_hostname])
    parent = relationship("TaskModel", remote_side=[uuid], backref="children")
    retries = relationship("TaskRetryModel", back_populates="task", order_by="TaskRetryModel.retry_at")

class TaskRetryModel(Base):
    __tablename__ = "task_retries"
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_uuid = Column(String(36), ForeignKey("tasks.uuid"), nullable=False)
    attempt = Column(Integer, nullable=False)
    reason = Column(Text, nullable=True)
    retry_at = Column(DateTime, default=datetime.datetime.utcnow)
    scheduled_at = Column(DateTime, nullable=True)  # when the retry is scheduled

    task = relationship("TaskModel", back_populates="retries")

class DailyStatsModel(Base):
    __tablename__ = "daily_stats"
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, index=True, unique=True)  # naive date
    total_tasks = Column(Integer, default=0)
    success_tasks = Column(Integer, default=0)
    failure_tasks = Column(Integer, default=0)
    retry_tasks = Column(Integer, default=0)
    revoked_tasks = Column(Integer, default=0)
    avg_runtime = Column(Float, nullable=True)  # seconds
    total_runtime = Column(Float, nullable=True)

# Create tables (in production use Alembic migrations)
Base.metadata.create_all(bind=engine)

# ===================== Pydantic Schemas =====================

class TaskFilter(BaseModel):
    date_from: Optional[datetime.datetime] = None
    date_to: Optional[datetime.datetime] = None
    status: Optional[str] = None
    name: Optional[str] = None
    worker: Optional[str] = None
    full_text: Optional[str] = None

class TaskOut(BaseModel):
    uuid: str
    name: str
    status: str
    args: Any
    kwargs: Any
    result: Optional[Any]
    traceback: Optional[str]
    worker_hostname: Optional[str]
    parent_id: Optional[str]
    created_at: datetime.datetime
    updated_at: datetime.datetime
    date_done: Optional[datetime.datetime]
    retry_count: int

    class Config:
        orm_mode = True

class WorkerOut(BaseModel):
    hostname: str
    status: str
    last_heartbeat: datetime.datetime
    pid: Optional[int]
    cpu_usage: Optional[float]
    memory_usage: Optional[float]
    tasks_processed: int

    class Config:
        orm_mode = True

class DailyStatsOut(BaseModel):
    date: datetime.datetime
    total_tasks: int
    success_tasks: int
    failure_tasks: int
    retry_tasks: int
    revoked_tasks: int
    avg_runtime: Optional[float]
    total_runtime: Optional[float]

    class Config:
        orm_mode = True

# ===================== Service Layer =====================

class TaskService:
    """Contains business logic for tasks, statistics, orphan detection, etc."""

    @staticmethod
    def matches_filter(task: TaskModel, filt: TaskFilter) -> bool:
        if filt.date_from and task.created_at < filt.date_from:
            return False
        if filt.date_to and task.created_at > filt.date_to:
            return False
        if filt.status and task.status != filt.status:
            return False
        if filt.name and filt.name not in task.name:  # partial match
            return False
        if filt.worker and task.worker_hostname and filt.worker not in task.worker_hostname:
            return False
        if filt.full_text:
            search = filt.full_text.lower()
            fields = [
                task.name,
                json.dumps(task.args),
                json.dumps(task.kwargs),
                json.dumps(task.result),
                task.traceback or "",
                task.status,
            ]
            if not any(search in str(field).lower() for field in fields):
                return False
        return True

    @staticmethod
    def detect_orphans(db: Session) -> List[TaskModel]:
        """Detect tasks that are stuck in non-terminal state without a parent or worker heartbeat."""
        cutoff = datetime.datetime.utcnow() - datetime.timedelta(minutes=5)
        orphans = db.query(TaskModel).filter(
            TaskModel.status.in_(["PENDING", "STARTED", "RETRY"]),
            TaskModel.created_at < cutoff,
            TaskModel.worker_hostname == None,  # no worker assigned
        ).all()
        # also consider tasks without parent and no recent worker heartbeat?
        return orphans

    @staticmethod
    def compute_daily_stats(db: Session, target_date: datetime.date):
        """Aggregate tasks for a specific date and update daily_stats table."""
        start = datetime.datetime.combine(target_date, datetime.time.min)
        end = datetime.datetime.combine(target_date, datetime.time.max)
        tasks = db.query(TaskModel).filter(
            TaskModel.created_at >= start,
            TaskModel.created_at <= end,
        ).all()

        total = len(tasks)
        success = sum(1 for t in tasks if t.status == "SUCCESS")
        failure = sum(1 for t in tasks if t.status == "FAILURE")
        retry = sum(1 for t in tasks if t.status == "RETRY")
        revoked = sum(1 for t in tasks if t.status == "REVOKED")

        # runtime calculations (approximate)
        runtimes = []
        for t in tasks:
            if t.date_done and t.created_at:
                runtimes.append((t.date_done - t.created_at).total_seconds())
        avg_runtime = sum(runtimes) / len(runtimes) if runtimes else None
        total_runtime = sum(runtimes) if runtimes else None

        stats = db.query(DailyStatsModel).filter(func.date(DailyStatsModel.date) == target_date).first()
        if not stats:
            stats = DailyStatsModel(date=start)
            db.add(stats)
        stats.total_tasks = total
        stats.success_tasks = success
        stats.failure_tasks = failure
        stats.retry_tasks = retry
        stats.revoked_tasks = revoked
        stats.avg_runtime = avg_runtime
        stats.total_runtime = total_runtime
        db.commit()
        return stats

# ===================== WebSocket Manager =====================

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[WebSocket, TaskFilter] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[websocket] = TaskFilter()  # default empty filter

    def disconnect(self, websocket: WebSocket):
        self.active_connections.pop(websocket, None)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast_task_update(self, task: TaskModel):
        """Send task update to all connections whose filter matches."""
        for ws, filt in self.active_connections.items():
            try:
                if TaskService.matches_filter(task, filt):
                    task_out = TaskOut.from_orm(task)
                    await ws.send_json(task_out.dict())
            except Exception:
                self.disconnect(ws)

    def update_filter(self, websocket: WebSocket, filt: TaskFilter):
        self.active_connections[websocket] = filt

manager = ConnectionManager()

# ===================== Celery Event Monitor (Mock) =====================
# In a real implementation, this would connect to Celery events via celery.events.Receiver.
# We simulate random task updates for demonstration.

class MockCeleryMonitor(threading.Thread):
    """Generates synthetic task events to simulate Celery activity."""

    def __init__(self, db_session_factory):
        super().__init__(daemon=True)
        self.db_factory = db_session_factory
        self._stop_event = threading.Event()
        # Pre-populate workers
        with self.db_factory() as db:
            if not db.query(WorkerModel).first():
                workers = [
                    WorkerModel(hostname="worker1@host", pid=1001, cpu_usage=23.5, memory_usage=120.3),
                    WorkerModel(hostname="worker2@host", pid=1002, cpu_usage=45.2, memory_usage=89.7),
                ]
                db.add_all(workers)
                db.commit()

    def run(self):
        while not self._stop_event.is_set():
            time.sleep(random.uniform(1, 3))
            with self.db_factory() as db:
                self._generate_event(db)

    def stop(self):
        self._stop_event.set()

    def _generate_event(self, db: Session):
        # Choose a random action
        action = random.choice(["new_task", "update_status", "worker_heartbeat", "worker_fail", "retry"])
        if action == "new_task":
            task = TaskModel(
                uuid=str(uuid.uuid4()),
                name=f"tasks.demo{random.randint(1,5)}",
                status="PENDING",
                args=[random.randint(1,100)],
                kwargs={"debug": random.choice([True, False])},
                created_at=datetime.datetime.utcnow(),
                worker_hostname=None,
            )
            db.add(task)
            db.commit()
            # Broadcast
            asyncio.run(manager.broadcast_task_update(task))
            logger.info(f"New task {task.uuid}")

        elif action == "update_status":
            task = db.query(TaskModel).filter(TaskModel.status != "SUCCESS").order_by(func.random()).first()
            if not task:
                return
            old_status = task.status
            if old_status == "PENDING":
                # Assign worker and start
                worker = db.query(WorkerModel).filter(WorkerModel.status == "online").order_by(func.random()).first()
                if worker:
                    task.worker_hostname = worker.hostname
                    task.status = "STARTED"
                    task.updated_at = datetime.datetime.utcnow()
            elif old_status == "STARTED":
                # Complete or fail
                if random.random() < 0.3:
                    task.status = "FAILURE"
                    task.traceback = "Simulated error"
                    task.date_done = datetime.datetime.utcnow()
                else:
                    task.status = "SUCCESS"
                    task.result = {"output": random.randint(1, 1000)}
                    task.date_done = datetime.datetime.utcnow()
            elif old_status == "RETRY":
                # Might eventually succeed or fail
                if random.random() < 0.5:
                    task.status = "STARTED"
                    task.worker_hostname = None  # reassign later
                else:
                    task.status = "FAILURE"
                    task.traceback = "Retry exhausted"
                    task.date_done = datetime.datetime.utcnow()
            elif old_status == "REVOKED":
                pass  # already final
            task.updated_at = datetime.datetime.utcnow()
            db.commit()
            asyncio.run(manager.broadcast_task_update(task))
            logger.info(f"Task {task.uuid} from {old_status} to {task.status}")

        elif action == "worker_heartbeat":
            # Update a random worker's heartbeat
            worker = db.query(WorkerModel).filter(WorkerModel.status == "online").order_by(func.random()).first()
            if worker:
                worker.last_heartbeat = datetime.datetime.utcnow()
                worker.cpu_usage = random.uniform(10, 70)
                worker.memory_usage = random.uniform(50, 200)
                worker.tasks_processed += random.randint(0, 5)
                db.commit()
                logger.info(f"Worker {worker.hostname} heartbeat")

        elif action == "worker_fail":
            worker = db.query(WorkerModel).filter(WorkerModel.status == "online").order_by(func.random()).first()
            if worker:
                worker.status = "offline"
                db.commit()
                logger.info(f"Worker {worker.hostname} offline")
                # Mark tasks on this worker as failed?
                # In real system, would need to handle.

        elif action == "retry":
            task = db.query(TaskModel).filter(TaskModel.status.in_(["FAILURE", "RETRY"])).order_by(func.random()).first()
            if not task:
                return
            retry = TaskRetryModel(
                task_uuid=task.uuid,
                attempt=task.retry_count + 1,
                reason="Simulated retry",
                retry_at=datetime.datetime.utcnow(),
                scheduled_at=datetime.datetime.utcnow() + datetime.timedelta(seconds=30),
            )
            task.retry_count += 1
            task.status = "RETRY"
            task.updated_at = datetime.datetime.utcnow()
            db.add(retry)
            db.commit()
            asyncio.run(manager.broadcast_task_update(task))
            logger.info(f"Retry scheduled for task {task.uuid} attempt {retry.attempt}")

# ===================== FastAPI Application =====================

app = FastAPI(title="Kanchi - Celery Task Monitor")

# ===================== REST Endpoints =====================

@app.get("/tasks/", response_model=List[TaskOut])
def list_tasks(
    date_from: Optional[datetime.datetime] = Query(None),
    date_to: Optional[datetime.datetime] = Query(None),
    status: Optional[str] = Query(None),
    name: Optional[str] = Query(None),
    worker: Optional[str] = Query(None),
    full_text: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(TaskModel)
    if date_from:
        query = query.filter(TaskModel.created_at >= date_from)
    if date_to:
        query = query.filter(TaskModel.created_at <= date_to)
    if status:
        query = query.filter(TaskModel.status == status)
    if name:
        query = query.filter(TaskModel.name.contains(name))
    if worker:
        query = query.filter(TaskModel.worker_hostname.contains(worker))
    if full_text:
        # simple full-text search across multiple fields
        search = f"%{full_text}%"
        query = query.filter(
            TaskModel.name.ilike(search) |
            TaskModel.args.cast(String).ilike(search) |
            TaskModel.kwargs.cast(String).ilike(search) |
            TaskModel.result.cast(String).ilike(search) |
            TaskModel.traceback.ilike(search)
        )
    return query.order_by(TaskModel.created_at.desc()).all()

@app.get("/tasks/orphans", response_model=List[TaskOut])
def list_orphans(db: Session = Depends(get_db)):
    orphans = TaskService.detect_orphans(db)
    return orphans

@app.get("/workers/", response_model=List[WorkerOut])
def list_workers(db: Session = Depends(get_db)):
    return db.query(WorkerModel).all()

@app.get("/stats/daily", response_model=List[DailyStatsOut])
def get_daily_stats(
    date_from: Optional[datetime.date] = Query(None),
    date_to: Optional[datetime.date] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(DailyStatsModel)
    if date_from:
        query = query.filter(func.date(DailyStatsModel.date) >= date_from)
    if date_to:
        query = query.filter(func.date(DailyStatsModel.date) <= date_to)
    return query.order_by(DailyStatsModel.date.desc()).all()

@app.post("/stats/compute")
def compute_stats(
    target_date: Optional[datetime.date] = Query(default_factory=datetime.date.today),
    db: Session = Depends(get_db),
):
    stats = TaskService.compute_daily_stats(db, target_date)
    return {"message": f"Stats computed for {target_date}", "date": target_date, "total": stats.total_tasks}

# ===================== WebSocket Endpoint =====================

@app.websocket("/ws/tasks")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Expect JSON with filter parameters
            try:
                filt_data = json.loads(data)
                filt = TaskFilter(**filt_data)
                manager.update_filter(websocket, filt)
                # Optionally, send initial tasks matching filter
                with SessionLocal() as db:
                    matching = db.query(TaskModel).filter(
                        # We can't reuse matches_filter directly on SQL, but we can fetch recent and filter in code.
                        TaskModel.created_at >= datetime.datetime.utcnow() - datetime.timedelta(hours=1)
                    ).all()
                    matching = [t for t in matching if TaskService.matches_filter(t, filt)]
                    for task in matching[:50]:  # limit
                        task_out = TaskOut.from_orm(task)
                        await websocket.send_json(task_out.dict())
            except Exception as e:
                await websocket.send_text(f"Error: {str(e)}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# ===================== Database Dependency =====================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ===================== Startup Events =====================

@app.on_event("startup")
def startup_event():
    # Attempt to run Alembic migrations if available; otherwise create tables
    try:
        import alembic.config
        import alembic.command
        alembic_cfg = alembic.config.Config("alembic.ini")
        alembic.command.upgrade(alembic_cfg, "head")
    except Exception as e:
        logger.warning(f"Alembic migration failed (or not configured): {e}. Falling back to create_all.")
        Base.metadata.create_all(bind=engine)

    # Start the mock Celery monitor
    monitor_thread = MockCeleryMonitor(SessionLocal)
    monitor_thread.start()
    app.state.monitor = monitor_thread

@app.on_event("shutdown")
def shutdown_event():
    monitor: MockCeleryMonitor = app.state.monitor
    if monitor:
        monitor.stop()

# ===================== Main =====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")