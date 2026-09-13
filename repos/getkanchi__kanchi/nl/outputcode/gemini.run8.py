import datetime
import os
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Date, ForeignKey, or_
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship
from fastapi import WebSocket
from alembic.config import Config
from alembic import command

Base = declarative_base()

class Worker(Base):
    __tablename__ = 'kanchi_workers'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    hostname = Column(String, unique=True, index=True, nullable=False)
    is_online = Column(Boolean, default=True, nullable=False)
    last_heartbeat = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    
    tasks = relationship("Task", back_populates="worker")


class Task(Base):
    __tablename__ = 'kanchi_tasks'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, index=True, nullable=False)
    status = Column(String, index=True, nullable=False)
    worker_hostname = Column(String, ForeignKey('kanchi_workers.hostname'), nullable=True)
    retries = Column(Integer, default=0, nullable=False)
    is_orphan = Column(Boolean, default=False, nullable=False)
    full_text_data = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)

    worker = relationship("Worker", back_populates="tasks")


class DailyStatistic(Base):
    __tablename__ = 'kanchi_daily_statistics'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, unique=True, index=True, nullable=False)
    total_tasks = Column(Integer, default=0, nullable=False)
    successful_tasks = Column(Integer, default=0, nullable=False)
    failed_tasks = Column(Integer, default=0, nullable=False)
    retried_tasks = Column(Integer, default=0, nullable=False)


@dataclass
class TaskFilter:
    start_date: Optional[datetime.datetime] = None
    end_date: Optional[datetime.datetime] = None
    status: Optional[str] = None
    name: Optional[str] = None
    worker_hostname: Optional[str] = None
    search_query: Optional[str] = None


class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_task_update(self, task_data: Dict[str, Any]):
        for connection in self.active_connections:
            try:
                await connection.send_json(task_data)
            except Exception:
                self.disconnect(connection)


class KanchiSystem:
    def __init__(self, db_session: Session, ws_manager: WebSocketManager):
        self.db = db_session
        self.ws = ws_manager

    def filter_tasks(self, filters: TaskFilter) -> List[Task]:
        query = self.db.query(Task)
        
        if filters.start_date:
            query = query.filter(Task.created_at >= filters.start_date)
        if filters.end_date:
            query = query.filter(Task.created_at <= filters.end_date)
        if filters.status:
            query = query.filter(Task.status == filters.status)
        if filters.name:
            query = query.filter(Task.name.ilike(f"%{filters.name}%"))
        if filters.worker_hostname:
            query = query.filter(Task.worker_hostname == filters.worker_hostname)
        if filters.search_query:
            query = query.filter(
                or_(
                    Task.name.ilike(f"%{filters.search_query}%"),
                    Task.full_text_data.ilike(f"%{filters.search_query}%"),
                    Task.task_id.ilike(f"%{filters.search_query}%")
                )
            )
            
        return query.all()

    async def track_task_event(self, task_id: str, name: str, status: str, worker_hostname: str, full_text_data: str = ""):
        task = self.db.query(Task).filter(Task.task_id == task_id).first()
        
        if not task:
            task = Task(
                task_id=task_id, 
                name=name, 
                status=status, 
                worker_hostname=worker_hostname, 
                full_text_data=full_text_data
            )
            self.db.add(task)
        else:
            if status == "RETRY":
                task.retries += 1
            task.status = status
            task.worker_hostname = worker_hostname
            if full_text_data:
                task.full_text_data = full_text_data

        self.db.commit()
        self.db.refresh(task)
        
        self._update_daily_stats(status)
        
        await self.ws.broadcast_task_update({
            "task_id": task.task_id,
            "name": task.name,
            "status": task.status,
            "worker_hostname": task.worker_hostname,
            "retries": task.retries,
            "is_orphan": task.is_orphan,
            "updated_at": task.updated_at.isoformat()
        })

    def _update_daily_stats(self, status: str):
        today = datetime.date.today()
        stats = self.db.query(DailyStatistic).filter(DailyStatistic.date == today).first()
        
        if not stats:
            stats = DailyStatistic(date=today)
            self.db.add(stats)
        
        stats.total_tasks += 1
        if status == "SUCCESS":
            stats.successful_tasks += 1
        elif status == "FAILURE":
            stats.failed_tasks += 1
        elif status == "RETRY":
            stats.retried_tasks += 1
            
        self.db.commit()

    def get_daily_statistics(self, start_date: datetime.date, end_date: datetime.date) -> List[DailyStatistic]:
        return self.db.query(DailyStatistic).filter(
            DailyStatistic.date >= start_date,
            DailyStatistic.date <= end_date
        ).order_by(DailyStatistic.date.asc()).all()

    def update_worker_health(self, hostname: str):
        worker = self.db.query(Worker).filter(Worker.hostname == hostname).first()
        if not worker:
            worker = Worker(hostname=hostname)
            self.db.add(worker)
        else:
            worker.last_heartbeat = datetime.datetime.utcnow()
            worker.is_online = True
        self.db.commit()

    def check_worker_health(self, timeout_seconds: int = 60):
        cutoff = datetime.datetime.utcnow() - datetime.timedelta(seconds=timeout_seconds)
        offline_workers = self.db.query(Worker).filter(
            Worker.last_heartbeat < cutoff, 
            Worker.is_online == True
        ).all()
        
        for worker in offline_workers:
            worker.is_online = False
            
        self.db.commit()

    def detect_orphans(self):
        offline_workers_subquery = self.db.query(Worker.hostname).filter(Worker.is_online == False).subquery()
        
        orphans = self.db.query(Task).filter(
            Task.status.in_(["STARTED", "RECEIVED", "PENDING"]),
            Task.worker_hostname.in_(offline_workers_subquery),
            Task.is_orphan == False
        ).all()
        
        for task in orphans:
            task.is_orphan = True
            task.status = "ORPHANED"
            
        self.db.commit()


def run_auto_migrations(engine):
    try:
        alembic_cfg = Config()
        alembic_cfg.set_main_option("script_location", "alembic")
        alembic_cfg.set_main_option("sqlalchemy.url", str(engine.url))
        
        if os.path.exists("alembic") and os.path.exists(os.path.join("alembic", "env.py")):
            command.upgrade(alembic_cfg, "head")
        else:
            Base.metadata.create_all(engine)
    except Exception:
        Base.metadata.create_all(engine)


if __name__ == "__main__":
    engine = create_engine("sqlite:///:memory:", echo=False)
    run_auto_migrations(engine)
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    ws_manager = WebSocketManager()
    kanchi = KanchiSystem(db_session=db, ws_manager=ws_manager)
    
    kanchi.update_worker_health("worker-node-1")
    
    import asyncio
    asyncio.run(kanchi.track_task_event(
        task_id="123e4567-e89b-12d3-a456-426614174000",
        name="send_email_task",
        status="STARTED",
        worker_hostname="worker-node-1",
        full_text_data="user@example.com welcome email"
    ))
    
    filters = TaskFilter(status="STARTED")
    tasks = kanchi.filter_tasks(filters)
    
    kanchi.check_worker_health(timeout_seconds=0) 
    kanchi.detect_orphans()
    
    db.close()