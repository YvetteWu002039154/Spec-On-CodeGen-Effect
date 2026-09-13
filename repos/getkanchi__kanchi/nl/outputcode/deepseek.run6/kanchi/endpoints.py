from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, datetime
from .database import get_db
from .models import Task, TaskStatus, Worker, DailyStats
from .schemas import TaskOut, WorkerOut, DailyStatsOut
from .websocket import manager
import asyncio

router = APIRouter()

@router.get("/tasks", response_model=List[TaskOut])
def list_tasks(
    status: Optional[str] = None,
    name: Optional[str] = None,
    worker: Optional[str] = None,
    search: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    query = db.query(Task)
    if status:
        query = query.filter(Task.status == status)
    if name:
        query = query.filter(Task.name.ilike(f"%{name}%"))
    if worker:
        query = query.filter(Task.worker == worker)
    if search:
        like = f"%{search}%"
        query = query.filter(
            (Task.name.ilike(like)) |
            (Task.task_id.ilike(like)) |
            (Task.worker.ilike(like)) |
            (Task.exception.ilike(like))
        )
    if date_from:
        query = query.filter(Task.created_at >= datetime(date_from.year, date_from.month, date_from.day))
    if date_to:
        query = query.filter(Task.created_at < datetime(date_to.year, date_to.month, date_to.day) + timedelta(days=1))
    tasks = query.order_by(Task.created_at.desc()).offset(skip).limit(limit).all()
    return tasks

@router.get("/tasks/{task_id}", response_model=TaskOut)
def get_task(task_id: str, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.get("/workers", response_model=List[WorkerOut])
def list_workers(db: Session = Depends(get_db)):
    return db.query(Worker).all()

@router.get("/stats/daily", response_model=List[DailyStatsOut])
def daily_stats(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: Session = Depends(get_db)
):
    query = db.query(DailyStats)
    if date_from:
        query = query.filter(DailyStats.date >= date_from)
    if date_to:
        query = query.filter(DailyStats.date <= date_to)
    return query.order_by(DailyStats.date).all()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # keep connection alive, all data sent via broadcast
            await asyncio.sleep(3600)  # just keep alive
    except WebSocketDisconnect:
        manager.disconnect(websocket)

