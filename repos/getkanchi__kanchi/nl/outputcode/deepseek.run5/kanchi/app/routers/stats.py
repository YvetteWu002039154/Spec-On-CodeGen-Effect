from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from ..database import get_session
from ..models import DailyTaskStatistic, Task, TaskStatus
from ..schemas import DailyStatResponse
from typing import List, Optional
from datetime import date, datetime, timedelta
import math

router = APIRouter(prefix="/api/stats", tags=["stats"])

@router.get("/daily", response_model=dict)
async def daily_stats(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    session: AsyncSession = Depends(get_session)
):
    query = select(DailyTaskStatistic).order_by(DailyTaskStatistic.date)
    if date_from:
        query = query.where(DailyTaskStatistic.date >= date_from)
    if date_to:
        query = query.where(DailyTaskStatistic.date <= date_to)
    result = await session.execute(query)
    stats = result.scalars().all()
    return {"data": [DailyStatResponse.from_orm(s) for s in stats]}

@router.post("/recalculate", response_model=dict)
async def recalculate_stats(session: AsyncSession = Depends(get_session)):
    # recalculate daily stats for all dates where tasks exist
    # truncate and recompute
    await session.execute("DELETE FROM daily_task_statistics")
    # group by date
    stmt = select(
        func.date(Task.created_at).label('day'),
        func.count(Task.id).label('total'),
        func.count(Task.id).filter(Task.status == TaskStatus.SUCCESS).label('succeeded'),
        func.count(Task.id).filter(Task.status == TaskStatus.FAILURE).label('failed'),
        func.count(Task.id).filter(Task.status == TaskStatus.RETRY).label('retried'),
        func.count(Task.id).filter(Task.status == TaskStatus.PENDING).label('pending'),
        func.count(Task.id).filter(Task.status == TaskStatus.REVOKED).label('revoked'),
        func.count(Task.id).filter(Task.status == TaskStatus.ORPHAN).label('orphan')
    ).group_by(func.date(Task.created_at))
    result = await session.execute(stmt)
    rows = result.fetchall()
    for row in rows:
        date_obj = row[0]
        stat = DailyTaskStatistic(
            date=date_obj,
            total=row[1] or 0,
            succeeded=row[2] or 0,
            failed=row[3] or 0,
            retried=row[4] or 0,
            pending=row[5] or 0,
            revoked=row[6] or 0,
            orphan=row[7] or 0
        )
        session.add(stat)
    await session.commit()
    return {"message": "Stats recalculated successfully"}

