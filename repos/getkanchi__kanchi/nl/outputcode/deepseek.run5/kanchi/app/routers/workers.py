from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from ..database import get_session
from ..models import Worker, WorkerStatus
from ..schemas import WorkerResponse
from typing import List

router = APIRouter(prefix="/api/workers", tags=["workers"])

@router.get("/", response_model=List[WorkerResponse])
async def list_workers(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Worker).order_by(Worker.hostname))
    workers = result.scalars().all()
    return [WorkerResponse.from_orm(w) for w in workers]

@router.get("/{hostname}", response_model=WorkerResponse)
async def get_worker(hostname: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Worker).where(Worker.hostname == hostname))
    worker = result.scalar_one_or_none()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    return WorkerResponse.from_orm(worker)

