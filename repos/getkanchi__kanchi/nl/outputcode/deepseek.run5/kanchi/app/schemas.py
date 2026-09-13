from pydantic import BaseModel, Field, validator
from typing import Optional, Any, List
from datetime import datetime, date
from uuid import UUID
from .models import TaskStatus, WorkerStatus


class TaskBase(BaseModel):
    task_id: str
    name: str
    status: TaskStatus = TaskStatus.PENDING
    args: Optional[Any] = None
    kwargs: Optional[Any] = None
    result: Optional[str] = None
    traceback: Optional[str] = None
    worker: Optional[str] = None
    date_done: Optional[datetime] = None
    retries: int = 0
    parent_id: Optional[UUID] = None


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    status: Optional[TaskStatus] = None
    result: Optional[str] = None
    traceback: Optional[str] = None
    worker: Optional[str] = None
    date_done: Optional[datetime] = None
    retries: Optional[int] = None
    parent_id: Optional[UUID] = None


class TaskResponse(TaskBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class TaskFilterParams(BaseModel):
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    status: Optional[TaskStatus] = None
    name: Optional[str] = None
    worker: Optional[str] = None
    search: Optional[str] = None
    page: int = Field(1, ge=1)
    page_size: int = Field(50, ge=1, le=200)


class WorkerBase(BaseModel):
    hostname: str
    status: WorkerStatus = WorkerStatus.ONLINE


class WorkerCreate(WorkerBase):
    pass


class WorkerUpdate(BaseModel):
    status: Optional[WorkerStatus] = None
    last_heartbeat: Optional[datetime] = None


class WorkerResponse(WorkerBase):
    id: UUID
    last_heartbeat: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class DailyStatResponse(BaseModel):
    id: UUID
    date: date
    total: int
    succeeded: int
    failed: int
    retried: int
    pending: int
    revoked: int
    orphan: int

    class Config:
        orm_mode = True


class WebSocketMessage(BaseModel):
    type: str
    payload: Any

