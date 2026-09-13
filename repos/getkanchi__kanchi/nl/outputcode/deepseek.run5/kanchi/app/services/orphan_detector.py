import asyncio
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from ..database import async_session
from ..models import Task, TaskStatus, Worker, WorkerStatus
from ..config import settings
import logging

logger = logging.getLogger(__name__)

async def detect_orphan_tasks():
    async with async_session() as session:
        cutoff = datetime.utcnow() - timedelta(seconds=settings.ORPHAN_TASK_TIMEOUT)
        # find tasks in STARTED state for longer than ORPHAN_TASK_TIMEOUT
        result = await session.execute(
            select(Task).where(
                Task.status == TaskStatus.STARTED,
                Task.updated_at < cutoff
            )
        )
        orphans = result.scalars().all()
        for task in orphans:
            # optionally check if worker is still online
            worker = await session.execute(
                select(Worker).where(Worker.hostname == task.worker)
            )
            worker_obj = worker.scalar_one_or_none()
            if worker_obj and worker_obj.status == WorkerStatus.ONLINE:
                # worker is online but task not updated, maybe still running, skip
                continue
            task.status = TaskStatus.ORPHAN
            task.updated_at = datetime.utcnow()
            logger.info(f"Orphan task detected: {task.task_id}")
        await session.commit()

async def orphan_detector_loop():
    while True:
        try:
            await detect_orphan_tasks()
        except Exception as e:
            logger.error(f"Orphan detection error: {e}")
        await asyncio.sleep(600)  # check every 10 minutes

