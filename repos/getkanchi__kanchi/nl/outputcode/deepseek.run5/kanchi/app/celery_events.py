import threading
import asyncio
import json
import time
from datetime import datetime
from celery import Celery
from celery.events import EventReceiver
from celery.events.state import State
from .config import settings
from .models import Task, TaskStatus, Worker, WorkerStatus
from .database import async_session
from .websocket_manager import manager
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import logging

logger = logging.getLogger(__name__)

celery_app = Celery('kanchi', broker=settings.CELERY_BROKER_URL, backend=settings.CELERY_RESULT_BACKEND)
celery_app.conf.update(
    task_track_started=True,
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
)

async def process_task_event(event: dict, session: AsyncSession):
    try:
        event_type = event['type']
        task_uuid = event['uuid']
        task_name = event.get('name', 'unknown')
        hostname = event.get('hostname', 'unknown')
        timestamp = datetime.fromtimestamp(event.get('timestamp', time.time()))
        args = event.get('args')
        kwargs = event.get('kwargs')
        result = event.get('result')
        traceback = event.get('traceback')
        retries = event.get('retries', 0)
        parent_id_raw = event.get('parent_id')

        if event_type in ('task-sent', 'task-received', 'task-started', 'task-succeeded', 'task-failed', 'task-retried', 'task-revoked'):
            # Map to our statuses
            status_map = {
                'task-sent': TaskStatus.PENDING,
                'task-received': TaskStatus.PENDING,
                'task-started': TaskStatus.STARTED,
                'task-succeeded': TaskStatus.SUCCESS,
                'task-failed': TaskStatus.FAILURE,
                'task-retried': TaskStatus.RETRY,
                'task-revoked': TaskStatus.REVOKED,
            }
            new_status = status_map.get(event_type, TaskStatus.PENDING)

            # Check if task exists
            result = await session.execute(select(Task).where(Task.task_id == task_uuid))
            task = result.scalar_one_or_none()
            if task:
                # update
                task.status = new_status if new_status != TaskStatus.RETRY else TaskStatus.FAILURE  # retry is intermediate
                if event_type == 'task-retried':
                    task.retries = retries
                if event_type == 'task-started':
                    task.worker = hostname
                if event_type in ('task-succeeded', 'task-failed', 'task-retried', 'task-revoked'):
                    task.date_done = timestamp
                    task.result = str(result) if result else None
                    task.traceback = traceback
                if parent_id_raw:
                    parent_result = await session.execute(select(Task).where(Task.task_id == parent_id_raw))
                    parent_task = parent_result.scalar_one_or_none()
                    if parent_task:
                        task.parent_id = parent_task.id
                task.updated_at = timestamp
            else:
                # create new
                new_task = Task(
                    task_id=task_uuid,
                    name=task_name,
                    status=new_status if event_type != 'task-retried' else TaskStatus.FAILURE,
                    args=args,
                    kwargs=kwargs,
                    worker=hostname if event_type == 'task-started' else None,
                    date_done=timestamp if event_type in ('task-succeeded', 'task-failed', 'task-raised') else None,
                    retries=retries if event_type == 'task-retried' else 0,
                    created_at=timestamp,
                    updated_at=timestamp
                )
                session.add(new_task)
            await session.commit()

            # broadcast via websocket
            msg = {
                "type": event_type,
                "payload": {
                    "task_id": task_uuid,
                    "name": task_name,
                    "status": new_status.value if event_type != 'task-retried' else 'RETRY',
                    "worker": hostname,
                    "timestamp": timestamp.isoformat()
                }
            }
            asyncio.ensure_future(manager.broadcast(msg))

        # worker events
        elif event_type in ('worker-online', 'worker-offline', 'worker-heartbeat'):
            hostname = event.get('hostname')
            if not hostname:
                return
            result = await session.execute(select(Worker).where(Worker.hostname == hostname))
            worker = result.scalar_one_or_none()
            if event_type == 'worker-online':
                if not worker:
                    worker = Worker(hostname=hostname, status=WorkerStatus.ONLINE, last_heartbeat=timestamp)
                    session.add(worker)
                else:
                    worker.status = WorkerStatus.ONLINE
                    worker.last_heartbeat = timestamp
            elif event_type == 'worker-offline':
                if worker:
                    worker.status = WorkerStatus.OFFLINE
                    worker.last_heartbeat = timestamp
            elif event_type == 'worker-heartbeat':
                if worker:
                    worker.last_heartbeat = timestamp
                    worker.status = WorkerStatus.ONLINE
                else:
                    worker = Worker(hostname=hostname, status=WorkerStatus.ONLINE, last_heartbeat=timestamp)
                    session.add(worker)
            await session.commit()
    except Exception as e:
        logger.error(f"Error processing event: {e}")
        await session.rollback()
        raise


def start_celery_event_listener(loop):
    """Run in a separate thread."""
    async def event_loop():
        async with async_session() as session:
            state = State()
            receiver = celery_app.events.Receiver(connection, handlers={
                '*': state.event,
            })
            await receiver.capture(limit=None, timeout=None, wakeup=True)

    def run():
        with celery_app.connection_for_read() as connection:
            while True:
                try:
                    state = State()
                    def on_event(event):
                        asyncio.run_coroutine_threadsafe(
                            process_task_event(event, async_session()),
                            loop
                        )
                    with celery_app.connection_for_read() as conn:
                        recv = EventReceiver(conn, handlers={"*": on_event})
                        recv.capture(limit=None, timeout=None, wakeup=True)
                except Exception as e:
                    logger.error(f"EventListener error: {e}, restarting in 5s")
                    time.sleep(5)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()

