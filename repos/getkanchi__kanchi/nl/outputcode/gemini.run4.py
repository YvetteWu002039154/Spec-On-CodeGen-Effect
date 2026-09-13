import datetime
import json
import asyncio
from typing import List, Optional, Any
from enum import Enum

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Boolean,
    Enum as SQLEnum,
    Date,
    or_
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from alembic.config import Config
from alembic import command

Base = declarative_base()


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    STARTED = "STARTED"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    RETRY = "RETRY"
    REVOKED = "REVOKED"
    ORPHAN = "ORPHAN"


class WorkerStatus(str, Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"


class Worker(Base):
    __tablename__ = 'workers'
    
    id = Column(String, primary_key=True)
    hostname = Column(String, nullable=False)
    status = Column(SQLEnum(WorkerStatus), default=WorkerStatus.ONLINE)
    last_heartbeat = Column(DateTime, default=datetime.datetime.utcnow)


class Task(Base):
    __tablename__ = 'tasks'
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.PENDING)
    worker_id = Column(String, ForeignKey('workers.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    retries = Column(Integer, default=0)
    is_orphan = Column(Boolean, default=False)
    result = Column(String, nullable=True)
    traceback = Column(String, nullable=True)


class TaskStatistic(Base):
    __tablename__ = 'task_statistics'
    
    date = Column(Date, primary_key=True)
    total_tasks = Column(Integer, default=0)
    successful_tasks = Column(Integer, default=0)
    failed_tasks = Column(Integer, default=0)
    retried_tasks = Column(Integer, default=0)


class DatabaseManager:
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)
        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)

    def run_auto_migrations(self, alembic_ini_path: str = "alembic.ini"):
        try:
            alembic_cfg = Config(alembic_ini_path)
            command.upgrade(alembic_cfg, "head")
        except Exception:
            Base.metadata.create_all(self.engine)

    def get_session(self) -> Session:
        return self.SessionLocal()


class WebSocketConnectionManager:
    def __init__(self):
        self.active_connections: List[Any] = []

    async def connect(self, websocket: Any):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: Any):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


class WorkerService:
    def __init__(self, db_session: Session):
        self.db = db_session
        self.offline_threshold = datetime.timedelta(minutes=5)

    def register_or_heartbeat(self, worker_id: str, hostname: str) -> Worker:
        worker = self.db.query(Worker).filter(Worker.id == worker_id).first()
        if not worker:
            worker = Worker(id=worker_id, hostname=hostname, status=WorkerStatus.ONLINE)
            self.db.add(worker)
        else:
            worker.status = WorkerStatus.ONLINE
            worker.last_heartbeat = datetime.datetime.utcnow()
        self.db.commit()
        return worker

    def monitor_health(self) -> List[Worker]:
        threshold_time = datetime.datetime.utcnow() - self.offline_threshold
        offline_workers = self.db.query(Worker).filter(
            Worker.status == WorkerStatus.ONLINE,
            Worker.last_heartbeat < threshold_time
        ).all()

        for worker in offline_workers:
            worker.status = WorkerStatus.OFFLINE
        
        if offline_workers:
            self.db.commit()
            
        return offline_workers


class StatisticsService:
    def __init__(self, db_session: Session):
        self.db = db_session

    def _get_or_create_today_stat(self) -> TaskStatistic:
        today = datetime.datetime.utcnow().date()
        stat = self.db.query(TaskStatistic).filter(TaskStatistic.date == today).first()
        if not stat:
            stat = TaskStatistic(date=today)
            self.db.add(stat)
            self.db.commit()
        return stat

    def record_task_created(self):
        stat = self._get_or_create_today_stat()
        stat.total_tasks += 1
        self.db.commit()

    def record_task_status_change(self, status: TaskStatus):
        stat = self._get_or_create_today_stat()
        if status == TaskStatus.SUCCESS:
            stat.successful_tasks += 1
        elif status == TaskStatus.FAILURE:
            stat.failed_tasks += 1
        elif status == TaskStatus.RETRY:
            stat.retried_tasks += 1
        self.db.commit()

    def get_history(self, start_date: datetime.date, end_date: datetime.date) -> List[TaskStatistic]:
        return self.db.query(TaskStatistic).filter(
            TaskStatistic.date >= start_date,
            TaskStatistic.date <= end_date
        ).order_by(TaskStatistic.date.desc()).all()


class TaskService:
    def __init__(self, db_session: Session, ws_manager: WebSocketConnectionManager):
        self.db = db_session
        self.ws_manager = ws_manager
        self.stats_service = StatisticsService(db_session)

    async def create_task(self, task_id: str, name: str, worker_id: Optional[str] = None) -> Task:
        task = Task(id=task_id, name=name, status=TaskStatus.PENDING, worker_id=worker_id)
        self.db.add(task)
        self.db.commit()
        
        self.stats_service.record_task_created()
        
        await self.ws_manager.broadcast(json.dumps({
            "event": "task_created", 
            "task_id": task.id, 
            "name": task.name
        }))
        return task

    async def update_task_status(self, 
                                 task_id: str, 
                                 status: TaskStatus, 
                                 worker_id: Optional[str] = None, 
                                 result: Optional[str] = None, 
                                 traceback: Optional[str] = None) -> Task:
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        task.status = status
        task.updated_at = datetime.datetime.utcnow()
        
        if worker_id:
            task.worker_id = worker_id
        if result:
            task.result = result
        if traceback:
            task.traceback = traceback
            
        if status == TaskStatus.RETRY:
            task.retries += 1
            
        self.db.commit()
        self.stats_service.record_task_status_change(status)
        
        await self.ws_manager.broadcast(json.dumps({
            "event": "task_update", 
            "task_id": task.id, 
            "status": task.status.value
        }))
        return task

    def detect_orphans(self) -> List[Task]:
        offline_workers_subquery = self.db.query(Worker.id).filter(Worker.status == WorkerStatus.OFFLINE).subquery()
        
        orphans = self.db.query(Task).filter(
            Task.status == TaskStatus.STARTED,
            Task.worker_id.in_(offline_workers_subquery)
        ).all()
        
        for task in orphans:
            task.status = TaskStatus.ORPHAN
            task.is_orphan = True
            
        if orphans:
            self.db.commit()
            
        return orphans

    def search_tasks(self, 
                     start_date: Optional[datetime.datetime] = None,
                     end_date: Optional[datetime.datetime] = None,
                     status: Optional[TaskStatus] = None,
                     name: Optional[str] = None,
                     worker_id: Optional[str] = None,
                     full_text: Optional[str] = None) -> List[Task]:
        query = self.db.query(Task)
        
        if start_date:
            query = query.filter(Task.created_at >= start_date)
        if end_date:
            query = query.filter(Task.created_at <= end_date)
        if status:
            query = query.filter(Task.status == status)
        if name:
            query = query.filter(Task.name.ilike(f"%{name}%"))
        if worker_id:
            query = query.filter(Task.worker_id == worker_id)
        if full_text:
            query = query.filter(
                or_(
                    Task.name.ilike(f"%{full_text}%"),
                    Task.result.ilike(f"%{full_text}%"),
                    Task.traceback.ilike(f"%{full_text}%")
                )
            )
            
        return query.all()


class KanchiSystem:
    def __init__(self, db_url: str):
        self.db_manager = DatabaseManager(db_url)
        self.ws_manager = WebSocketConnectionManager()
        
    def initialize(self):
        self.db_manager.run_auto_migrations()
        
    def get_worker_service(self) -> WorkerService:
        return WorkerService(self.db_manager.get_session())
        
    def get_task_service(self) -> TaskService:
        return TaskService(self.db_manager.get_session(), self.ws_manager)
        
    def get_statistics_service(self) -> StatisticsService:
        return StatisticsService(self.db_manager.get_session())