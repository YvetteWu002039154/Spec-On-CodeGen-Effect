import datetime
import enum
from typing import List, Optional, Dict, Any
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Enum, JSON, Boolean, or_
from sqlalchemy.orm import declarative_base, sessionmaker, Session

Base = declarative_base()

class TaskStatus(enum.Enum):
    PENDING = "PENDING"
    STARTED = "STARTED"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    RETRY = "RETRY"
    REVOKED = "REVOKED"
    ORPHAN = "ORPHAN"

class WorkerStatus(enum.Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"

class Task(Base):
    __tablename__ = 'tasks'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, index=True, nullable=False)
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING, index=True)
    worker_hostname = Column(String, index=True)
    args = Column(JSON, default=list)
    kwargs = Column(JSON, default=dict)
    result = Column(String, nullable=True)
    traceback = Column(String, nullable=True)
    retries = Column(Integer, default=0)
    is_orphan = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

class Worker(Base):
    __tablename__ = 'workers'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    hostname = Column(String, unique=True, index=True, nullable=False)
    status = Column(Enum(WorkerStatus), default=WorkerStatus.ONLINE)
    last_heartbeat = Column(DateTime, default=datetime.datetime.utcnow)
    concurrency = Column(Integer, default=1)

class TaskStatistic(Base):
    __tablename__ = 'task_statistics'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, unique=True, index=True, nullable=False)
    total_tasks = Column(Integer, default=0)
    successful_tasks = Column(Integer, default=0)
    failed_tasks = Column(Integer, default=0)
    retried_tasks = Column(Integer, default=0)

class WebSocketMock:
    async def accept(self):
        pass
    async def send_json(self, data: dict):
        pass

class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocketMock] = []

    async def connect(self, websocket: WebSocketMock):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocketMock):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

class TaskFilter:
    def __init__(
        self,
        start_date: Optional[datetime.datetime] = None,
        end_date: Optional[datetime.datetime] = None,
        status: Optional[TaskStatus] = None,
        name: Optional[str] = None,
        worker: Optional[str] = None,
        search_term: Optional[str] = None
    ):
        self.start_date = start_date
        self.end_date = end_date
        self.status = status
        self.name = name
        self.worker = worker
        self.search_term = search_term

class TaskManager:
    def __init__(self, session: Session, ws_manager: WebSocketManager):
        self.session = session
        self.ws_manager = ws_manager

    def create_task(self, task_id: str, name: str, worker_hostname: str, args: list = None, kwargs: dict = None) -> Task:
        task = Task(
            task_id=task_id,
            name=name,
            worker_hostname=worker_hostname,
            args=args or [],
            kwargs=kwargs or {}
        )
        self.session.add(task)
        self.session.commit()
        return task

    def update_task_status(self, task_id: str, status: TaskStatus, result: str = None, traceback: str = None) -> Optional[Task]:
        task = self.session.query(Task).filter(Task.task_id == task_id).first()
        if task:
            task.status = status
            if status == TaskStatus.STARTED:
                task.started_at = datetime.datetime.utcnow()
            elif status in [TaskStatus.SUCCESS, TaskStatus.FAILURE, TaskStatus.REVOKED]:
                task.completed_at = datetime.datetime.utcnow()
            
            if result:
                task.result = result
            if traceback:
                task.traceback = traceback
                
            self.session.commit()
        return task

    def track_retry(self, task_id: str) -> Optional[Task]:
        task = self.session.query(Task).filter(Task.task_id == task_id).first()
        if task:
            task.retries += 1
            task.status = TaskStatus.RETRY
            self.session.commit()
        return task

    def detect_orphans(self, timeout_minutes: int = 60) -> List[Task]:
        cutoff_time = datetime.datetime.utcnow() - datetime.timedelta(minutes=timeout_minutes)
        orphans = self.session.query(Task).filter(
            Task.status == TaskStatus.STARTED,
            Task.started_at < cutoff_time
        ).all()
        
        for task in orphans:
            task.status = TaskStatus.ORPHAN
            task.is_orphan = True
        
        if orphans:
            self.session.commit()
        return orphans

    def filter_tasks(self, filters: TaskFilter) -> List[Task]:
        query = self.session.query(Task)
        
        if filters.start_date:
            query = query.filter(Task.created_at >= filters.start_date)
        if filters.end_date:
            query = query.filter(Task.created_at <= filters.end_date)
        if filters.status:
            query = query.filter(Task.status == filters.status)
        if filters.name:
            query = query.filter(Task.name == filters.name)
        if filters.worker:
            query = query.filter(Task.worker_hostname == filters.worker)
        if filters.search_term:
            search = f"%{filters.search_term}%"
            query = query.filter(
                or_(
                    Task.name.ilike(search),
                    Task.task_id.ilike(search),
                    Task.result.ilike(search),
                    Task.traceback.ilike(search)
                )
            )
            
        return query.all()

class WorkerManager:
    def __init__(self, session: Session):
        self.session = session

    def update_heartbeat(self, hostname: str, concurrency: int = 1) -> Worker:
        worker = self.session.query(Worker).filter(Worker.hostname == hostname).first()
        if not worker:
            worker = Worker(hostname=hostname, concurrency=concurrency)
            self.session.add(worker)
        
        worker.last_heartbeat = datetime.datetime.utcnow()
        worker.status = WorkerStatus.ONLINE
        worker.concurrency = concurrency
        self.session.commit()
        return worker

    def check_health(self, offline_timeout_seconds: int = 120) -> List[Worker]:
        cutoff_time = datetime.datetime.utcnow() - datetime.timedelta(seconds=offline_timeout_seconds)
        offline_workers = self.session.query(Worker).filter(
            Worker.status == WorkerStatus.ONLINE,
            Worker.last_heartbeat < cutoff_time
        ).all()
        
        for worker in offline_workers:
            worker.status = WorkerStatus.OFFLINE
            
        if offline_workers:
            self.session.commit()
        return offline_workers

class StatisticsManager:
    def __init__(self, session: Session):
        self.session = session

    def generate_daily_statistics(self, target_date: datetime.date) -> TaskStatistic:
        start_of_day = datetime.datetime.combine(target_date, datetime.time.min)
        end_of_day = datetime.datetime.combine(target_date, datetime.time.max)
        
        tasks = self.session.query(Task).filter(
            Task.created_at >= start_of_day,
            Task.created_at <= end_of_day
        ).all()
        
        total = len(tasks)
        successful = sum(1 for t in tasks if t.status == TaskStatus.SUCCESS)
        failed = sum(1 for t in tasks if t.status == TaskStatus.FAILURE)
        retried = sum(1 for t in tasks if t.retries > 0)
        
        stat = self.session.query(TaskStatistic).filter(
            TaskStatistic.date == start_of_day
        ).first()
        
        if not stat:
            stat = TaskStatistic(date=start_of_day)
            self.session.add(stat)
            
        stat.total_tasks = total
        stat.successful_tasks = successful
        stat.failed_tasks = failed
        stat.retried_tasks = retried
        
        self.session.commit()
        return stat

    def get_history(self, start_date: datetime.date, end_date: datetime.date) -> List[TaskStatistic]:
        start_dt = datetime.datetime.combine(start_date, datetime.time.min)
        end_dt = datetime.datetime.combine(end_date, datetime.time.max)
        
        return self.session.query(TaskStatistic).filter(
            TaskStatistic.date >= start_dt,
            TaskStatistic.date <= end_dt
        ).order_by(TaskStatistic.date.asc()).all()

class MigrationManager:
    @staticmethod
    def run_auto_migrations(engine):
        try:
            from alembic.config import Config
            from alembic import command
            alembic_cfg = Config("alembic.ini")
            command.upgrade(alembic_cfg, "head")
        except (ImportError, FileNotFoundError):
            Base.metadata.create_all(engine)

class KanchiSystem:
    def __init__(self, db_url: str = "sqlite:///:memory:"):
        self.engine = create_engine(db_url)
        MigrationManager.run_auto_migrations(self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.ws_manager = WebSocketManager()
        
    def get_session(self) -> Session:
        return self.SessionLocal()
        
    def get_task_manager(self, session: Session) -> TaskManager:
        return TaskManager(session, self.ws_manager)
        
    def get_worker_manager(self, session: Session) -> WorkerManager:
        return WorkerManager(session)
        
    def get_statistics_manager(self, session: Session) -> StatisticsManager:
        return StatisticsManager(session)