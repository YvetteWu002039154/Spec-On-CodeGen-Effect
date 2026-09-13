import asyncio
from fastapi import FastAPI
from celery import Celery
from .config import settings
from .database import engine, Base, SessionLocal
from .endpoints import router
from .tasks_monitor import celery_events_listener
from .websocket import manager
import threading

celery_app = Celery(broker=settings.CELERY_BROKER_URL)

def start_celery_listener(loop):
    # start background thread
    def run():
        celery_events_listener(celery_app, None)  # event queue not used in this version
    thread = threading.Thread(target=run, daemon=True)
    thread.start()

async def orphan_detection_loop():
    from .models import Task, TaskStatus, Worker
    from datetime import datetime, timedelta
    while True:
        await asyncio.sleep(settings.ORPHAN_TIMEOUT_SECONDS)
        try:
            db = SessionLocal()
            threshold = datetime.utcnow() - timedelta(seconds=settings.ORPHAN_TIMEOUT_SECONDS)
            stale_tasks = db.query(Task).filter(
                Task.status.in_([TaskStatus.STARTED, TaskStatus.RECEIVED])
            ).all()
            orphans = []
            for task in stale_tasks:
                if task.worker:
                    worker = db.query(Worker).filter(Worker.hostname == task.worker).first()
                    if not worker or (worker.last_heartbeat and worker.last_heartbeat < threshold):
                        task.status = TaskStatus.ORPHAN
                        orphans.append(task)
                else:
                    # no worker assigned yet, maybe still received but lost
                    if task.updated_at and task.updated_at < threshold:
                        task.status = TaskStatus.ORPHAN
                        orphans.append(task)
            if orphans:
                db.commit()
                for task in orphans:
                    await manager.broadcast({'type': 'task_updated', 'task': {'id': task.id, 'status': 'ORPHAN'}})
        except Exception as e:
            import logging
            logging.error(f"Orphan detection error: {e}", exc_info=True)
        finally:
            db.close()

app = FastAPI(title="Kanchi", version="0.1.0")
app.include_router(router)

@app.on_event("startup")
async def startup_event():
    # create tables if not exist (Alembic handles migrations otherwise)
    Base.metadata.create_all(bind=engine)
    loop = asyncio.get_running_loop()
    start_celery_listener(loop)
    asyncio.create_task(orphan_detection_loop())

