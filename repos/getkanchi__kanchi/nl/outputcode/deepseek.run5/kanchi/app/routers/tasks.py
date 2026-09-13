from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, cast, String
from typing import List, Optional
from ..database import get_session
from ..models import Task, TaskStatus
from ..schemas import TaskResponse, TaskFilterParams, WebSocketMessage
from ..websocket_manager import manager
from datetime import date, datetime
import math

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

@router.get("/", response_model=dict)
async def list_tasks(
    status: Optional[TaskStatus] = None,
    name: Optional[str] = None,
    worker: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session)
):
    filters = []
    if status:
        filters.append(Task.status == status)
    if name:
        filters.append(Task.name.ilike(f"%{name}%"))
    if worker:
        filters.append(Task.worker.ilike(f"%{worker}%"))
    if date_from:
        filters.append(Task.created_at >= datetime(date_from.year, date_from.month, date_from.day))
    if date_to:
        filters.append(Task.created_at < datetime(date_to.year, date_to.month, date_to.day) + timedelta(days=1))
    if search:
        search_filter = or_(
            Task.name.ilike(f"%{search}%"),
            Task.task_id.ilike(f"%{search}%"),
            Task.worker.ilike(f"%{search}%"),
            cast(Task.args, String).ilike(f"%{search}%"),
            cast(Task.kwargs, String).ilike(f"%{search}%")
        )
        filters.append(search_filter)

    query = select(Task)
    if filters:
        query = query.where(and_(*filters))
    total_query = select(func.count(Task.id))
    if filters:
        total_query = total_query.where(and_(*filters))
    total = (await session.execute(total_query)).scalar()

    query = query.order_by(Task.created_at.desc()).offset((page-1)*page_size).limit(page_size)
    result = await session.execute(query)
    tasks = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": math.ceil(total / page_size) if total else 1,
        "data": [TaskResponse.from_orm(t) for t in tasks]
    }

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse.from_orm(task)

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # keep connection alive, receive messages if needed
            data = await websocket.receive_text()
            # client might send a filter update, but currently ignored
            pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)

