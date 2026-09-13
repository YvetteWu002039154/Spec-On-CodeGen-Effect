import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, JSON, Float, Date, Enum, ForeignKey
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from .database import Base
import enum

class TaskStatus(str, enum.Enum):
    PENDING = "PENDING"
    RECEIVED = "RECEIVED"
    STARTED = "STARTED"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    RETRY = "RETRY"
    REVOKED = "REVOKED"
    ORPHAN = "ORPHAN"

class WorkerStatus(str, enum.Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"

class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    args = Column(JSON, nullable=True)
    kwargs = Column(JSON, nullable=True)
    status = Column(String, default=TaskStatus.PENDING, index=True)
    worker = Column(String, nullable=True)
    retries = Column(Integer, default=0)
    parent_id = Column(String, nullable=True)  # not used for retries but can be set
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    result = Column(JSON, nullable=True)
    traceback = Column(String, nullable=True)
    exception = Column(String, nullable=True)

class Worker(Base):
    __tablename__ = "workers"

    hostname = Column(String, primary_key=True)
    status = Column(String, default=WorkerStatus.OFFLINE)
    last_heartbeat = Column(DateTime, nullable=True)
    concurrency = Column(Integer, nullable=True)
    queues = Column(JSON, nullable=True)
    # additional fields can be added

class DailyStats(Base):
    __tablename__ = "daily_stats"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    date = Column(Date, nullable=False, index=True)
    total_tasks = Column(Integer, default=0)
    succeeded = Column(Integer, default=0)
    failed = Column(Integer, default=0)
    retried = Column(Integer, default=0)
    avg_runtime = Column(Float, default=0.0)

