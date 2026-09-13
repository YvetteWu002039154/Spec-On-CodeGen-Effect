import asyncio
import json
from datetime import datetime
from celery import Celery
from celery.events import EventReceiver
from kombu import Connection
from .config import settings
from .database import SessionLocal
from .models import Task, TaskStatus, Worker, WorkerStatus, DailyStats
from .websocket import manager
import logging

logger = logging.getLogger(__name__)

def process_event(event: dict, session):
    event_type = event['type']
    message = None

    if event_type.startswith('task-'):
        task_id = event['uuid']
        task = session.query(Task).filter(Task.task_id == task_id).first()
        if not task and event_type == 'task-sent':
            task = Task(task_id=task_id, name=event.get('name', ''), args=event.get('args'), kwargs=event.get('kwargs'),
                        status=TaskStatus.PENDING, created_at=datetime.utcnow())
            session.add(task)
            message = {'type': 'task_created', 'task': {'id': task.id, 'task_id': task_id, 'name': task.name}}
        elif task:
            if event_type == 'task-received':
                task.status = TaskStatus.RECEIVED
                task.worker = event.get('hostname')
                message = {'type': 'task_updated', 'task': {'id': task.id, 'status': task.status, 'worker': task.worker}}
            elif event_type == 'task-started':
                task.status = TaskStatus.STARTED
                task.started_at = datetime.utcnow()
                message = {'type': 'task_updated', 'task': {'id': task.id, 'status': task.status, 'started_at': task.started_at.isoformat()}}
            elif event_type == 'task-succeeded':
                task.status = TaskStatus.SUCCESS
                task.completed_at = datetime.utcnow()
                task.result = event.get('result')
                message = {'type': 'task_updated', 'task': {'id': task.id, 'status': task.status, 'completed_at': task.completed_at.isoformat()}}
            elif event_type == 'task-failed':
                task.status = TaskStatus.FAILURE
                task.completed_at = datetime.utcnow()
                task.exception = event.get('exception')
                task.traceback = event.get('traceback')
                message = {'type': 'task_updated', 'task': {'id': task.id, 'status': task.status, 'exception': task.exception}}
            elif event_type == 'task-retried':
                task.status = TaskStatus.RETRY
                task.retries = event.get('retries', 0)
                task.exception = event.get('exception')
                task.traceback = event.get('traceback')
                message = {'type': 'task_updated', 'task': {'id': task.id, 'status': task.status, 'retries': task.retries}}
            elif event_type == 'task-revoked':
                task.status = TaskStatus.REVOKED
                message = {'type': 'task_updated', 'task': {'id': task.id, 'status': task.status}}
        session.commit()

    elif event_type.startswith('worker-'):
        hostname = event['hostname']
        worker = session.query(Worker).filter(Worker.hostname == hostname).first()
        if event_type == 'worker-online':
            if not worker:
                worker = Worker(hostname=hostname, status=WorkerStatus.ONLINE, last_heartbeat=datetime.utcnow())
                session.add(worker)
            else:
                worker.status = WorkerStatus.ONLINE
                worker.last_heartbeat = datetime.utcnow()
            message = {'type': 'worker_update', 'worker': {'hostname': hostname, 'status': 'ONLINE'}}
        elif event_type == 'worker-offline':
            if worker:
                worker.status = WorkerStatus.OFFLINE
                message = {'type': 'worker_update', 'worker': {'hostname': hostname, 'status': 'OFFLINE'}}
        elif event_type == 'worker-heartbeat':
            if worker:
                worker.last_heartbeat = datetime.utcnow()
                if worker.status != WorkerStatus.ONLINE:
                    worker.status = WorkerStatus.ONLINE
                    message = {'type': 'worker_update', 'worker': {'hostname': hostname, 'status': 'ONLINE'}}
            else:
                worker = Worker(hostname=hostname, status=WorkerStatus.ONLINE, last_heartbeat=datetime.utcnow())
                session.add(worker)
                message = {'type': 'worker_update', 'worker': {'hostname': hostname, 'status': 'ONLINE'}}
        session.commit()

    if message:
        # push to websocket manager in main thread via asyncio loop
        loop = asyncio.get_event_loop()
        loop.call_soon_threadsafe(manager.broadcast, message)

def celery_events_listener(app: Celery, event_queue: asyncio.Queue):
    with app.connection() as connection:
        recv = EventReceiver(connection, handlers={
            'task-sent': lambda event: process_event_threadsafe(event, app),
            'task-received': lambda event: process_event_threadsafe(event, app),
            'task-started': lambda event: process_event_threadsafe(event, app),
            'task-succeeded': lambda event: process_event_threadsafe(event, app),
            'task-failed': lambda event: process_event_threadsafe(event, app),
            'task-retried': lambda event: process_event_threadsafe(event, app),
            'task-revoked': lambda event: process_event_threadsafe(event, app),
            'worker-online': lambda event: process_event_threadsafe(event, app),
            'worker-offline': lambda event: process_event_threadsafe(event, app),
            'worker-heartbeat': lambda event: process_event_threadsafe(event, app),
        })
        recv.capture(limit=None, timeout=None, wakeup=True)

def process_event_threadsafe(event, app):
    # create a new session for this thread
    session = SessionLocal()
    try:
        process_event(event, session)
    except Exception as e:
        logger.error(f"Error processing event: {e}", exc_info=True)
        session.rollback()
    finally:
        session.close()

