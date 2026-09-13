import uuid
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, DateTime, Text, Date, ForeignKey, Enum, JSON, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .database import Base
import enum


class TaskStatus(str, enum.Enum):
    PENDING = "PENDING"
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

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), index=True)
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING, index=True)
    args = Column(JSON, nullable=True)
    kwargs = Column(JSON, nullable=True)
    result = Column(Text, nullable=True)
    traceback = Column(Text, nullable=True)
    worker = Column(String(255), nullable=True, index=True)
    date_done = Column(DateTime, nullable=True)
    retries = Column(Integer, default=0)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    children = relationship("Task", backref="parent", remote_side=[id])


class Worker(Base):
    __tablename__ = "workers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hostname = Column(String(255), unique=True, nullable=False, index=True)
    status = Column(Enum(WorkerStatus), default=WorkerStatus.ONLINE)
    last_heartbeat = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DailyTaskStatistic(Base):
    __tablename__ = "daily_task_statistics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    date = Column(Date, unique=True, nullable=False, index=True)
    total = Column(Integer, default=0)
    succeeded = Column(Integer, default=0)
    failed = Column(Integer, default=0)
    retried = Column(Integer, default=0)
    pending = Column(Integer, default=0)
    revoked = Column(Integer, default=0)
    orphan = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

