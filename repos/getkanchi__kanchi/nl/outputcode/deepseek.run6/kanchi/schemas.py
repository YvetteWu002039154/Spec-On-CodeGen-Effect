from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime, date

class TaskOut(BaseModel):
    id: str
    task_id: str
    name: str
    args: Optional[Any]
    kwargs: Optional[Any]
    status: str
    worker: Optional[str]
    retries: int
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    result: Optional[Any]
    traceback: Optional[str]
    exception: Optional[str]

    class Config:
        orm_mode = True

class WorkerOut(BaseModel):
    hostname: str
    status: str
    last_heartbeat: Optional[datetime]
    concurrency: Optional[int]
    queues: Optional[Any]

    class Config:
        orm_mode = True

class DailyStatsOut(BaseModel):
    date: date
    total_tasks: int
    succeeded: int
    failed: int
    retried: int
    avg_runtime: float

    class Config:
        orm_mode = True

