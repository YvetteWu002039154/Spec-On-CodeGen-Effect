import asyncio
import threading
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .celery_events import start_celery_event_listener
from .services.orphan_detector import orphan_detector_loop
from .database import engine, Base
import logging
import alembic.config
import alembic.command

logger = logging.getLogger(__name__)

def run_migrations():
    alembic_args = ['--raiseerr', 'upgrade', 'head']
    try:
        alembic.config.main(argv=alembic_args)
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise

@asynccontextmanager
async def lifespan(app: FastAPI):
    # run auto-migrations
    run_migrations()
    # create tables if not exists (in case alembic not set up)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # start celery event listener in a thread
    loop = asyncio.get_running_loop()
    start_celery_event_listener(loop)
    # start orphan detector background task
    asyncio.create_task(orphan_detector_loop())
    yield
    # shutdown

app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from .routers import tasks, workers, stats

app.include_router(tasks.router)
app.include_router(workers.router)
app.include_router(stats.router)

