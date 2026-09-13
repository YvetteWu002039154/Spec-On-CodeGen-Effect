import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import threading
import time
import hashlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TaskState(str, Enum):
    PENDING = "PENDING"
    RECEIVED = "RECEIVED"
    STARTED = "STARTED"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    REVOKED = "REVOKED"
    RETRY = "RETRY"
    IGNORED = "IGNORED"


@dataclass
class TaskEvent:
    task_id: str
    name: str
    state: TaskState
    worker: Optional[str] = None
    args: Optional[str] = None
    kwargs: Optional[str] = None
    result: Optional[str] = None
    traceback: Optional[str] = None
    received: Optional[datetime] = None
    started: Optional[datetime] = None
    succeeded: Optional[datetime] = None
    failed: Optional[datetime] = None
    retried: Optional[datetime] = None
    revoked: Optional[datetime] = None
    runtime: Optional[float] = None
    retries: int = 0
    parent_id: Optional[str] = None
    root_id: Optional[str] = None
    eta: Optional[datetime] = None
    expires: Optional[datetime] = None
    hostname: Optional[str] = None
    exchange: Optional[str] = None
    routing_key: Optional[str] = None
    clock: Optional[int] = None
    client: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        for key, value in d.items():
            if isinstance(value, datetime):
                d[key] = value.isoformat() if value else None
            elif isinstance(value, TaskState):
                d[key] = value.value
        return d


@dataclass
class WorkerInfo:
    hostname: str
    status: str = "online"
    active_tasks: int = 0
    processed_tasks: int = 0
    failed_tasks: int = 0
    last_heartbeat: Optional[datetime] = None
    software_identity: Optional[str] = None
    software_version: Optional[str] = None
    software_sys: Optional[str] = None
    loadavg: Optional[List[float]] = None
    pid: Optional[int] = None
    clock: Optional[str] = None
    uptime: Optional[int] = None
    queues: List[str] = field(default_factory=list)
    concurrency: Optional[int] = None
    pool: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if self.last_heartbeat:
            d['last_heartbeat'] = self.last_heartbeat.isoformat()
        return d

    def is_alive(self, timeout: int = 30) -> bool:
        if self.last_heartbeat is None:
            return False
        return (datetime.utcnow() - self.last_heartbeat).total_seconds() < timeout


@dataclass
class DailyStats:
    date: str
    total: int = 0
    succeeded: int = 0
    failed: int = 0
    retried: int = 0
    revoked: int = 0
    pending: int = 0
    started: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TaskFilter:
    def __init__(
        self,
        task_name: Optional[str] = None,
        state: Optional[TaskState] = None,
        worker: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        search_term: Optional[str] = None,
        task_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ):
        self.task_name = task_name
        self.state = state
        self.worker = worker
        self.date_from = date_from
        self.date_to = date_to
        self.search_term = search_term
        self.task_id = task_id
        self.limit = limit
        self.offset = offset

    def matches(self, task: TaskEvent) -> bool:
        if self.task_id and task.task_id != self.task_id:
            return False
        if self.task_name and self.task_name.lower() not in task.name.lower():
            return False
        if self.state and task.state != self.state:
            return False
        if self.worker and task.worker and self.worker.lower() not in task.worker.lower():
            return False
        if self.date_from and task.timestamp < self.date_from:
            return False
        if self.date_to and task.timestamp > self.date_to:
            return False
        if self.search_term:
            term = self.search_term.lower()
            searchable = " ".join(filter(None, [
                task.task_id,
                task.name,
                task.worker,
                task.args,
                task.kwargs,
                task.result,
                task.traceback,
            ])).lower()
            if term not in searchable:
                return False
        return True


class TaskStore:
    def __init__(self, max_tasks: int = 10000):
        self._tasks: Dict[str, TaskEvent] = {}
        self._task_order: List[str] = []
        self._max_tasks = max_tasks
        self._lock = threading.RLock()
        self._daily_stats: Dict[str, DailyStats] = {}

    def upsert_task(self, task: TaskEvent) -> None:
        with self._lock:
            if task.task_id not in self._tasks:
                self._task_order.append(task.task_id)
                if len(self._task_order) > self._max_tasks:
                    oldest_id = self._task_order.pop(0)
                    del self._tasks[oldest_id]
            self._tasks[task.task_id] = task
            self._update_daily_stats(task)

    def get_task(self, task_id: str) -> Optional[TaskEvent]:
        with self._lock:
            return self._tasks.get(task_id)

    def get_tasks(self, task_filter: Optional[TaskFilter] = None) -> Tuple[List[TaskEvent], int]:
        with self._lock:
            all_tasks = [self._tasks[tid] for tid in reversed(self._task_order) if tid in self._tasks]
            if task_filter is None:
                total = len(all_tasks)
                return all_tasks[:100], total
            filtered = [t for t in all_tasks if task_filter.matches(t)]
            total = len(filtered)
            start = task_filter.offset
            end = start + task_filter.limit
            return filtered[start:end], total

    def get_task_count(self) -> int:
        with self._lock:
            return len(self._tasks)

    def delete_task(self, task_id: str) -> bool:
        with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
                if task_id in self._task_order:
                    self._task_order.remove(task_id)
                return True
            return False

    def clear_tasks(self) -> int:
        with self._lock:
            count = len(self._tasks)
            self._tasks.clear()
            self._task_order.clear()
            return count

    def _update_daily_stats(self, task: TaskEvent) -> None:
        date_key = task.timestamp.strftime("%Y-%m-%d")
        if date_key not in self._daily_stats:
            self._daily_stats[date_key] = DailyStats(date=date_key)
        stats = self._daily_stats[date_key]
        stats.total = max(stats.total, 1)
        if task.state == TaskState.SUCCESS:
            stats.succeeded += 1
        elif task.state == TaskState.FAILURE:
            stats.failed += 1
        elif task.state == TaskState.RETRY:
            stats.retried += 1
        elif task.state == TaskState.REVOKED:
            stats.revoked += 1
        elif task.state == TaskState.PENDING:
            stats.pending += 1
        elif task.state == TaskState.STARTED:
            stats.started += 1

    def get_daily_stats(self, days: int = 7) -> List[DailyStats]:
        with self._lock:
            result = []
            for i in range(days - 1, -1, -1):
                date = (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d")
                if date in self._daily_stats:
                    result.append(self._daily_stats[date])
                else:
                    result.append(DailyStats(date=date))
            return result

    def get_state_counts(self) -> Dict[str, int]:
        with self._lock:
            counts = {state.value: 0 for state in TaskState}
            for task in self._tasks.values():
                counts[task.state.value] += 1
            return counts

    def find_orphans(self) -> List[TaskEvent]:
        with self._lock:
            orphans = []
            task_ids = set(self._tasks.keys())
            for task in self._tasks.values():
                if task.parent_id and task.parent_id not in task_ids:
                    orphans.append(task)
            return orphans

    def get_retried_tasks(self) -> List[TaskEvent]:
        with self._lock:
            return [t for t in self._tasks.values() if t.retries > 0 or t.state == TaskState.RETRY]

    def get_task_history(self, task_name: str, limit: int = 50) -> List[TaskEvent]:
        with self._lock:
            history = [
                t for t in self._tasks.values()
                if t.name == task_name
            ]
            history.sort(key=lambda x: x.timestamp, reverse=True)
            return history[:limit]


class WorkerStore:
    def __init__(self):
        self._workers: Dict[str, WorkerInfo] = {}
        self._lock = threading.RLock()

    def upsert_worker(self, worker: WorkerInfo) -> None:
        with self._lock:
            self._workers[worker.hostname] = worker

    def get_worker(self, hostname: str) -> Optional[WorkerInfo]:
        with self._lock:
            return self._workers.get(hostname)

    def get_all_workers(self) -> List[WorkerInfo]:
        with self._lock:
            return list(self._workers.values())

    def get_active_workers(self, timeout: int = 30) -> List[WorkerInfo]:
        with self._lock:
            return [w for w in self._workers.values() if w.is_alive(timeout)]

    def mark_worker_offline(self, hostname: str) -> None:
        with self._lock:
            if hostname in self._workers:
                self._workers[hostname].status = "offline"

    def update_heartbeat(self, hostname: str, timestamp: Optional[datetime] = None) -> None:
        with self._lock:
            if hostname in self._workers:
                self._workers[hostname].last_heartbeat = timestamp or datetime.utcnow()
                self._workers[hostname].status = "online"

    def get_worker_count(self) -> Dict[str, int]:
        with self._lock:
            total = len(self._workers)
            active = sum(1 for w in self._workers.values() if w.is_alive())
            offline = total - active
            return {"total": total, "active": active, "offline": offline}


class WebSocketClient:
    def __init__(self, client_id: str, subscriptions: Optional[List[str]] = None):
        self.client_id = client_id
        self.subscriptions = subscriptions or ["tasks", "workers", "stats"]
        self._queue: asyncio.Queue = asyncio.Queue()
        self.connected: bool = True
        self.connected_at: datetime = datetime.utcnow()

    async def send(self, message: Dict[str, Any]) -> None:
        if self.connected:
            await self._queue.put(message)

    async def receive(self) -> Optional[Dict[str, Any]]:
        try:
            return await asyncio.wait_for(self._queue.get(), timeout=1.0)
        except asyncio.TimeoutError:
            return None

    def disconnect(self) -> None:
        self.connected = False


class WebSocketManager:
    def __init__(self):
        self._clients: Dict[str, WebSocketClient] = {}
        self._lock = asyncio.Lock()

    async def connect(self, client_id: Optional[str] = None) -> WebSocketClient:
        async with self._lock:
            cid = client_id or str(uuid.uuid4())
            client = WebSocketClient(cid)
            self._clients[cid] = client
            logger.info(f"WebSocket client connected: {cid}")
            return client

    async def disconnect(self, client_id: str) -> None:
        async with self._lock:
            if client_id in self._clients:
                self._clients[client_id].disconnect()
                del self._clients[client_id]
                logger.info(f"WebSocket client disconnected: {client_id}")

    async def broadcast(self, message: Dict[str, Any], channel: str = "tasks") -> None:
        async with self._lock:
            clients = list(self._clients.values())
        for client in clients:
            if client.connected and channel in client.subscriptions:
                try:
                    await client.send(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to client {client.client_id}: {e}")

    async def send_to_client(self, client_id: str, message: Dict[str, Any]) -> bool:
        async with self._lock:
            client = self._clients.get(client_id)
        if client and client.connected:
            await client.send(message)
            return True
        return False

    def get_client_count(self) -> int:
        return len(self._clients)


class CeleryEventProcessor:
    def __init__(self, task_store: TaskStore, worker_store: WorkerStore):
        self.task_store = task_store
        self.worker_store = worker_store
        self._event_handlers = {
            "task-sent": self._handle_task_sent,
            "task-received": self._handle_task_received,
            "task-started": self._handle_task_started,
            "task-succeeded": self._handle_task_succeeded,
            "task-failed": self._handle_task_failed,
            "task-retried": self._handle_task_retried,
            "task-revoked": self._handle_task_revoked,
            "worker-online": self._handle_worker_online,
            "worker-offline": self._handle_worker_offline,
            "worker-heartbeat": self._handle_worker_heartbeat,
        }

    def process_event(self, event: Dict[str, Any]) -> Optional[TaskEvent]:
        event_type = event.get("type", "")
        handler = self._event_handlers.get(event_type)
        if handler:
            return handler(event)
        logger.debug(f"Unhandled event type: {event_type}")
        return None

    def _get_or_create_task(self, task_id: str, name: str = "unknown") -> TaskEvent:
        existing = self.task_store.get_task(task_id)
        if existing:
            return existing
        return TaskEvent(
            task_id=task_id,
            name=name,
            state=TaskState.PENDING,
        )

    def _handle_task_sent(self, event: Dict[str, Any]) -> TaskEvent:
        task_id = event.get("uuid", str(uuid.uuid4()))
        task = self._get_or_create_task(task_id, event.get("name", "unknown"))
        task.state = TaskState.PENDING
        task.name = event.get("name", task.name)
        task.args = str(event.get("args", ""))
        task.kwargs = str(event.get("kwargs", ""))
        task.eta = self._parse_datetime(event.get("eta"))
        task.expires = self._parse_datetime(event.get("expires"))
        task.parent_id = event.get("parent_id")
        task.root_id = event.get("root_id")
        task.exchange = event.get("exchange")
        task.routing_key = event.get("routing_key")
        task.timestamp = datetime.utcnow()
        self.task_store.upsert_task(task)
        return task

    def _handle_task_received(self, event: Dict[str, Any]) -> TaskEvent:
        task_id = event.get("uuid", str(uuid.uuid4()))
        task = self._get_or_create_task(task_id, event.get("name", "unknown"))
        task.state = TaskState.RECEIVED
        task.name = event.get("name", task.name)
        task.worker = event.get("hostname")
        task.hostname = event.get("hostname")
        task.args = str(event.get("args", task.args or ""))
        task.kwargs = str(event.get("kwargs", task.kwargs or ""))
        task.received = datetime.utcnow()
        task.retries = event.get("retries", 0)
        task.eta = self._parse_datetime(event.get("eta"))
        task.parent_id = event.get("parent_id", task.parent_id)
        task.root_id = event.get("root_id", task.root_id)
        task.clock = event.get("clock")
        task.timestamp = datetime.utcnow()
        self.task_store.upsert_task(task)
        return task

    def _handle_task_started(self, event: Dict[str, Any]) -> TaskEvent:
        task_id = event.get("uuid", str(uuid.uuid4()))
        task = self._get_or_create_task(task_id)
        task.state = TaskState.STARTED
        task.worker = event.get("hostname", task.worker)
        task.hostname = event.get("hostname", task.hostname)
        task.started = datetime.utcnow()
        task.pid = event.get("pid")
        task.clock = event.get("clock", task.clock)
        task.timestamp = datetime.utcnow()
        self.task_store.upsert_task(task)
        return task

    def _handle_task_succeeded(self, event: Dict[str, Any]) -> TaskEvent:
        task_id = event.get("uuid", str(uuid.uuid4()))
        task = self._get_or_create_task(task_id)
        task.state = TaskState.SUCCESS
        task.result = str(event.get("result", ""))
        task.runtime = event.get("runtime")
        task.succeeded = datetime.utcnow()
        task.worker = event.get("hostname", task.worker)
        task.clock = event.get("clock", task.clock)
        task.timestamp = datetime.utcnow()
        self.task_store.upsert_task(task)
        return task

    def _handle_task_failed(self, event: Dict[str, Any]) -> TaskEvent:
        task_id = event.get("uuid", str(uuid.uuid4()))
        task = self._get_or_create_task(task_id)
        task.state = TaskState.FAILURE
        task.traceback = event.get("traceback", "")
        task.exception = event.get("exception", "")
        task.failed = datetime.utcnow()
        task.worker = event.get("hostname", task.worker)
        task.clock = event.get("clock", task.clock)
        task.timestamp = datetime.utcnow()
        self.task_store.upsert_task(task)
        return task

    def _handle_task_retried(self, event: Dict[str, Any]) -> TaskEvent:
        task_id = event.get("uuid", str(uuid.uuid4()))
        task = self._get_or_create_task(task_id)
        task.state = TaskState.RETRY
        task.retries += 1
        task.traceback = event.get("traceback", task.traceback)
        task.exception = event.get("exception", "")
        task.retried = datetime.utcnow()
        task.worker = event.get("hostname", task.worker)
        task.eta = self._parse_datetime(event.get("eta"))
        task.clock = event.get("clock", task.clock)
        task.timestamp = datetime.utcnow()
        self.task_store.upsert_task(task)
        return task

    def _handle_task_revoked(self, event: Dict[str, Any]) -> TaskEvent:
        task_id = event.get("uuid", str(uuid.uuid4()))
        task = self._get_or_create_task(task_id)
        task.state = TaskState.REVOKED
        task.revoked = datetime.utcnow()
        task.worker = event.get("hostname", task.worker)
        task.terminated = event.get("terminated", False)
        task.signum = event.get("signum")
        task.expired = event.get("expired", False)
        task.clock = event.get("clock", task.clock)
        task.timestamp = datetime.utcnow()
        self.task_store.upsert_task(task)
        return task

    def _handle_worker_online(self, event: Dict[str, Any]) -> None:
        hostname = event.get("hostname", "unknown")
        worker = self.worker_store.get_worker(hostname) or WorkerInfo(hostname=hostname)
        worker.status = "online"
        worker.last_heartbeat = datetime.utcnow()
        worker.software_identity = event.get("sw_ident")
        worker.software_version = event.get("sw_ver")
        worker.software_sys = event.get("sw_sys")
        self.worker_store.upsert_worker(worker)
        logger.info(f"Worker online: {hostname}")

    def _handle_worker_offline(self, event: Dict[str, Any]) -> None:
        hostname = event.get("hostname", "unknown")
        self.worker_store.mark_worker_offline(hostname)
        logger.info(f"Worker offline: {hostname}")

    def _handle_worker_heartbeat(self, event: Dict[str, Any]) -> None:
        hostname = event.get("hostname", "unknown")
        worker = self.worker_store.get_worker(hostname) or WorkerInfo(hostname=hostname)
        worker.status = "online"
        worker.last_heartbeat = datetime.utcnow()
        worker.active_tasks = event.get("active", worker.active_tasks)
        worker.processed_tasks = event.get("processed", worker.processed_tasks)
        worker.loadavg = event.get("loadavg", worker.loadavg)
        worker.clock = str(event.get("clock", worker.clock))
        worker.uptime = event.get("uptime", worker.uptime)
        self.worker_store.upsert_worker(worker)

    def _parse_datetime(self, value: Any) -> Optional[datetime]:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                pass
        return None


class TaskManager:
    def __init__(self, task_store: TaskStore, worker_store: WorkerStore):
        self.task_store = task_store
        self.worker_store = worker_store

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        task = self.task_store.get_task(task_id)
        if task:
            return task.to_dict()
        return None

    def get_tasks(
        self,
        task_name: Optional[str] = None,
        state: Optional[str] = None,
        worker: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        search_term: Optional[str] = None,
        task_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        task_state = TaskState(state) if state else None
        task_filter = TaskFilter(
            task_name=task_name,
            state=task_state,
            worker=worker,
            date_from=date_from,
            date_to=date_to,
            search_term=search_term,
            task_id=task_id,
            limit=limit,
            offset=offset,
        )
        tasks, total = self.task_store.get_tasks(task_filter)
        return {
            "tasks": [t.to_dict() for t in tasks],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def delete_task(self, task_id: str) -> bool:
        return self.task_store.delete_task(task_id)

    def clear_tasks(self) -> Dict[str, int]:
        count = self.task_store.clear_tasks()
        return {"deleted": count}

    def get_task_stats(self) -> Dict[str, Any]:
        state_counts = self.task_store.get_state_counts()
        total = sum(state_counts.values())
        return {
            "total": total,
            "by_state": state_counts,
        }

    def get_daily_stats(self, days: int = 7) -> List[Dict[str, Any]]:
        stats = self.task_store.get_daily_stats(days)
        return [s.to_dict() for s in stats]

    def get_orphaned_tasks(self) -> List[Dict[str, Any]]:
        orphans = self.task_store.find_orphans()
        return [t.to_dict() for t in orphans]

    def get_retried_tasks(self) -> List[Dict[str, Any]]:
        retried = self.task_store.get_retried_tasks()
        return [t.to_dict() for t in retried]

    def get_task_history(self, task_name: str, limit: int = 50) -> List[Dict[str, Any]]:
        history = self.task_store.get_task_history(task_name, limit)
        return [t.to_dict() for t in history]

    def get_workers(self) -> List[Dict[str, Any]]:
        workers = self.worker_store.get_all_workers()
        return [w.to_dict() for w in workers]

    def get_worker(self, hostname: str) -> Optional[Dict[str, Any]]:
        worker = self.worker_store.get_worker(hostname)
        if worker:
            return worker.to_dict()
        return None

    def get_worker_stats(self) -> Dict[str, Any]:
        counts = self.worker_store.get_worker_count()
        workers = self.worker_store.get_all_workers()
        return {
            **counts,
            "workers": [w.to_dict() for w in workers],
        }


class MigrationManager:
    def __init__(self, db_url: str = "sqlite:///kanchi.db"):
        self.db_url = db_url
        self._migrations: List[Dict[str, Any]] = []
        self._applied: List[str] = []
        self._register_migrations()

    def _register_migrations(self) -> None:
        self._migrations = [
            {
                "id": "001_initial",
                "description": "Initial schema creation",
                "sql": """
                    CREATE TABLE IF NOT EXISTS tasks (
                        task_id VARCHAR(255) PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        state VARCHAR(50) NOT NULL,
                        worker VARCHAR(255),
                        args TEXT,
                        kwargs TEXT,
                        result TEXT,
                        traceback TEXT,
                        received TIMESTAMP,
                        started TIMESTAMP,
                        succeeded TIMESTAMP,
                        failed TIMESTAMP,
                        retried TIMESTAMP,
                        revoked TIMESTAMP,
                        runtime FLOAT,
                        retries INTEGER DEFAULT 0,
                        parent_id VARCHAR(255),
                        root_id VARCHAR(255),
                        eta TIMESTAMP,
                        expires TIMESTAMP,
                        hostname VARCHAR(255),
                        exchange VARCHAR(255),
                        routing_key VARCHAR(255),
                        clock INTEGER,
                        client VARCHAR(255),
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    CREATE TABLE IF NOT EXISTS workers (
                        hostname VARCHAR(255) PRIMARY KEY,
                        status VARCHAR(50) DEFAULT 'online',
                        active_tasks INTEGER DEFAULT 0,
                        processed_tasks INTEGER DEFAULT 0,
                        failed_tasks INTEGER DEFAULT 0,
                        last_heartbeat TIMESTAMP,
                        software_identity VARCHAR(255),
                        software_version VARCHAR(50),
                        software_sys VARCHAR(50),
                        pid INTEGER,
                        clock VARCHAR(50),
                        uptime INTEGER,
                        concurrency INTEGER,
                        pool VARCHAR(100)
                    );
                    CREATE TABLE IF NOT EXISTS daily_stats (
                        date VARCHAR(10) PRIMARY KEY,
                        total INTEGER DEFAULT 0,
                        succeeded INTEGER DEFAULT 0,
                        failed INTEGER DEFAULT 0,
                        retried INTEGER DEFAULT 0,
                        revoked INTEGER DEFAULT 0,
                        pending INTEGER DEFAULT 0,
                        started INTEGER DEFAULT 0
                    );
                """,
            },
            {
                "id": "002_add_indexes",
                "description": "Add indexes for performance",
                "sql": """
                    CREATE INDEX IF NOT EXISTS idx_tasks_state ON tasks(state);
                    CREATE INDEX IF NOT EXISTS idx_tasks_name ON tasks(name);
                    CREATE INDEX IF NOT EXISTS idx_tasks_worker ON tasks(worker);
                    CREATE INDEX IF NOT EXISTS idx_tasks_timestamp ON tasks(timestamp);
                    CREATE INDEX IF NOT EXISTS idx_tasks_parent_id ON tasks(parent_id);
                """,
            },
        ]

    def get_pending_migrations(self) -> List[Dict[str, Any]]:
        return [m for m in self._migrations if m["id"] not in self._applied]

    def apply_migration(self, migration_id: str) -> bool:
        migration = next((m for m in self._migrations if m["id"] == migration_id), None)
        if not migration:
            logger.error(f"Migration not found: {migration_id}")
            return False
        if migration_id in self._applied:
            logger.info(f"Migration already applied: {migration_id}")
            return True
        logger.info(f"Applying migration: {migration_id} - {migration['description']}")
        self._applied.append(migration_id)
        return True

    def run_migrations(self) -> Dict[str, Any]:
        pending = self.get_pending_migrations()
        applied = []
        failed = []
        for migration in pending:
            if self.apply_migration(migration["id"]):
                applied.append(migration["id"])
            else:
                failed.append(migration["id"])
        return {
            "applied": applied,
            "failed": failed,
            "total_applied": len(self._applied),
        }

    def get_migration_status(self) -> Dict[str, Any]:
        return {
            "total": len(self._migrations),
            "applied": len(self._applied),
            "pending": len(self.get_pending_migrations()),
            "applied_ids": self._applied,
            "pending_ids": [m["id"] for m in self.get_pending_migrations()],
        }


class KanchiMonitor:
    def __init__(
        self,
        max_tasks: int = 10000,
        db_url: str = "sqlite:///kanchi.db",
        worker_timeout: int = 30,
    ):
        self.task_store = TaskStore(max_tasks=max_tasks)
        self.worker_store = WorkerStore()
        self.ws_manager = WebSocketManager()
        self.event_processor = CeleryEventProcessor(self.task_store, self.worker_store)
        self.task_manager = TaskManager(self.task_store, self.worker_store)
        self.migration_manager = MigrationManager(db_url=db_url)
        self.worker_timeout = worker_timeout
        self._running = False
        self._event_callbacks: List[Any] = []
        self._lock = threading.RLock()

    def initialize(self) -> Dict[str, Any]:
        migration_result = self.migration_manager.run_migrations()
        logger.info(f"Migrations applied: {migration_result}")
        return migration_result

    def process_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        task = self.event_processor.process_event(event)
        if task:
            task_dict = task.to_dict()
            for callback in self._event_callbacks:
                try:
                    callback(task_dict)
                except Exception as e:
                    logger.error(f"Error in event callback: {e}")
            return task_dict
        return None

    def add_event_callback(self, callback: Any) -> None:
        self._event_callbacks.append(callback)

    def remove_event_callback(self, callback: Any) -> None:
        if callback in self._event_callbacks:
            self._event_callbacks.remove(callback)

    async def broadcast_task_update(self, task: Dict[str, Any]) -> None:
        message = {
            "type": "task_update",
            "data": task,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self.ws_manager.broadcast(message, channel="tasks")

    async def broadcast_worker_update(self, worker: Dict[str, Any]) -> None:
        message = {
            "type": "worker_update",
            "data": worker,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self.ws_manager.broadcast(message, channel="workers")

    async def broadcast_stats_update(self) -> None:
        stats = self.task_manager.get_task_stats()
        message = {
            "type": "stats_update",
            "data": stats,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self.ws_manager.broadcast(message, channel="stats")

    def get_dashboard_data(self) -> Dict[str, Any]:
        task_stats = self.task_manager.get_task_stats()
        worker_stats = self.task_manager.get_worker_stats()
        daily_stats = self.task_manager.get_daily_stats(days=7)
        recent_tasks_result = self.task_manager.get_tasks(limit=10)
        orphans = self.task_manager.get_orphaned_tasks()
        retried = self.task_manager.get_retried_tasks()
        return {
            "task_stats": task_stats,
            "worker_stats": worker_stats,
            "daily_stats": daily_stats,
            "recent_tasks": recent_tasks_result["tasks"],
            "orphaned_tasks_count": len(orphans),
            "retried_tasks_count": len(retried),
            "websocket_clients": self.ws_manager.get_client_count(),
            "timestamp": datetime.utcnow().isoformat(),
        }

    def search_tasks(
        self,
        query: str,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        return self.task_manager.get_tasks(
            search_term=query,
            limit=limit,
            offset=offset,
        )

    def filter_tasks(
        self,
        task_name: Optional[str] = None,
        state: Optional[str] = None,
        worker: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        return self.task_manager.get_tasks(
            task_name=task_name,
            state=state,
            worker=worker,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            offset=offset,
        )

    def get_health_status(self) -> Dict[str, Any]:
        active_workers = self.worker_store.get_active_workers(self.worker_timeout)
        all_workers = self.worker_store.get_all_workers()
        task_stats = self.task_manager.get_task_stats()
        is_healthy = len(active_workers) > 0
        return {
            "healthy": is_healthy,
            "active_workers": len(active_workers),
            "total_workers": len(all_workers),
            "total_tasks": task_stats["total"],
            "failed_tasks": task_stats["by_state"].get(TaskState.FAILURE.value, 0),
            "timestamp": datetime.utcnow().isoformat(),
        }

    def simulate_task_event(
        self,
        task_name: str,
        state: str = "SUCCESS",
        worker: str = "celery@worker1",
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        tid = task_id or str(uuid.uuid4())
        events = []
        if state in ["RECEIVED", "STARTED", "SUCCESS", "FAILURE", "RETRY", "REVOKED"]:
            events.append({
                "type": "task-received",
                "uuid": tid,
                "name": task_name,
                "hostname": worker,
                "args": "[]",
                "kwargs": "{}",
                "retries": 0,
            })
        if state in ["STARTED", "SUCCESS", "FAILURE"]:
            events.append({
                "type": "task-started",
                "uuid": tid,
                "hostname": worker,
            })
        if state == "SUCCESS":
            events.append({
                "type": "task-succeeded",
                "uuid": tid,
                "hostname": worker,
                "result": "null",
                "runtime": 0.1,
            })
        elif state == "FAILURE":
            events.append({
                "type": "task-failed",
                "uuid": tid,
                "hostname": worker,
                "exception": "Exception: Task failed",
                "traceback": "Traceback...",
            })
        elif state == "RETRY":
            events.append({
                "type": "task-retried",
                "uuid": tid,
                "hostname": worker,
                "exception": "Exception: Retrying",
                "traceback": "Traceback...",
            })
        elif state == "REVOKED":
            events.append({
                "type": "task-revoked",
                "uuid": tid,
                "hostname": worker,
                "terminated": False,
                "expired": False,
            })
        result = None
        for event in events:
            result = self.process_event(event)
        return result or {}


class KanchiAPI:
    def __init__(self, monitor: KanchiMonitor):
        self.monitor = monitor

    def get_tasks(
        self,
        task_name: Optional[str] = None,
        state: Optional[str] = None,
        worker: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        df = datetime.fromisoformat(date_from) if date_from else None
        dt = datetime.fromisoformat(date_to) if date_to else None
        return self.monitor.task_manager.get_tasks(
            task_name=task_name,
            state=state,
            worker=worker,
            date_from=df,
            date_to=dt,
            search_term=search,
            limit=limit,
            offset=offset,
        )

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self.monitor.task_manager.get_task(task_id)

    def delete_task(self, task_id: str) -> Dict[str, Any]:
        success = self.monitor.task_manager.delete_task(task_id)
        return {"success": success, "task_id": task_id}

    def clear_tasks(self) -> Dict[str, Any]:
        return self.monitor.task_manager.clear_tasks()

    def get_task_stats(self) -> Dict[str, Any]:
        return self.monitor.task_manager.get_task_stats()

    def get_daily_stats(self, days: int = 7) -> List[Dict[str, Any]]:
        return self.monitor.task_manager.get_daily_stats(days)

    def get_orphaned_tasks(self) -> List[Dict[str, Any]]:
        return self.monitor.task_manager.get_orphaned_tasks()

    def get_retried_tasks(self) -> List[Dict[str, Any]]:
        return self.monitor.task_manager.get_retried_tasks()

    def get_task_history(self, task_name: str, limit: int = 50) -> List[Dict[str, Any]]:
        return self.monitor.task_manager.get_task_history(task_name, limit)

    def get_workers(self) -> List[Dict[str, Any]]:
        return self.monitor.task_manager.get_workers()

    def get_worker(self, hostname: str) -> Optional[Dict[str, Any]]:
        return self.monitor.task_manager.get_worker(hostname)

    def get_worker_stats(self) -> Dict[str, Any]:
        return self.monitor.task_manager.get_worker_stats()

    def get_dashboard(self) -> Dict[str, Any]:
        return self.monitor.get_dashboard_data()

    def get_health(self) -> Dict[str, Any]:
        return self.monitor.get_health_status()

    def search_tasks(self, query: str, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        return self.monitor.search_tasks(query, limit, offset)

    def process_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return self.monitor.process_event(event)

    def get_migration_status(self) -> Dict[str, Any]:
        return self.monitor.migration_manager.get_migration_status()


def create_monitor(
    max_tasks: int = 10000,
    db_url: str = "sqlite:///kanchi.db",
    worker_timeout: int = 30,
) -> KanchiMonitor:
    monitor = KanchiMonitor(
        max_tasks=max_tasks,
        db_url=db_url,
        worker_timeout=worker_timeout,
    )
    monitor.initialize()
    return monitor


def create_api(monitor: Optional[KanchiMonitor] = None) -> KanchiAPI:
    if monitor is None:
        monitor = create_monitor()
    return KanchiAPI(monitor)


if __name__ == "__main__":
    monitor = create_monitor()
    api = create_api(monitor)

    print("=== Kanchi Task Monitor ===\n")

    monitor.process_event({
        "type": "worker-online",
        "hostname": "celery@worker1",
        "sw_ident": "py-celery",
        "sw_ver": "5.3.0",
        "sw_sys": "Linux",
    })

    monitor.process_event({
        "type": "worker-heartbeat",
        "hostname": "celery@worker1",
        "active": 2,
        "processed": 100,
        "loadavg": [0.1, 0.2, 0.3],
    })

    task1_id = str(uuid.uuid4())
    monitor.process_event({
        "type": "task-received",
        "uuid": task1_id,
        "name": "myapp.tasks.send_email",
        "hostname": "celery@worker1",
        "args": "['user@example.com']",
        "kwargs": "{'subject': 'Hello'}",
        "retries": 0,
    })
    monitor.process_event({
        "type": "task-started",
        "uuid": task1_id,
        "hostname": "celery@worker1",
    })
    monitor.process_event({
        "type": "task-succeeded",
        "uuid": task1_id,
        "hostname": "celery@worker1",
        "result": "True",
        "runtime": 0.5,
    })

    task2_id = str(uuid.uuid4())
    monitor.process_event({
        "type": "task-received",
        "uuid": task2_id,
        "name": "myapp.tasks.process_data",
        "hostname": "celery@worker1",
        "args": "[1, 2, 3]",
        "kwargs": "{}",
        "retries": 0,
    })
    monitor.process_event({
        "type": "task-started",
        "uuid": task2_id,
        "hostname": "celery@worker1",
    })
    monitor.process_event({
        "type": "task-failed",
        "uuid": task2_id,
        "hostname": "celery@worker1",
        "exception": "ValueError: Invalid data",
        "traceback": "Traceback (most recent call last):\n  ...\nValueError: Invalid data",
    })

    task3_id = str(uuid.uuid4())
    monitor.process_event({
        "type": "task-received",
        "uuid": task3_id,
        "name": "myapp.tasks.send_email",
        "hostname": "celery@worker1",
        "args": "['admin@example.com']",
        "kwargs": "{}",
        "retries": 1,
    })
    monitor.process_event({
        "type": "task-retried",
        "uuid": task3_id,
        "hostname": "celery@worker1",
        "exception": "ConnectionError: Timeout",
        "traceback": "...",
    })

    print("Dashboard:")
    dashboard = api.get_dashboard()
    print(f"  Total tasks: {dashboard['task_stats']['total']}")
    print(f"  Task states: {dashboard['task_stats']['by_state']}")
    print(f"  Active workers: {dashboard['worker_stats']['active']}")
    print(f"  Retried tasks: {dashboard['retried_tasks_count']}")

    print("\nAll Tasks:")
    tasks_result = api.get_tasks(limit=10)
    for task in tasks_result["tasks"]:
        print(f"  [{task['state']}] {task['name']} ({task['task_id'][:8]}...)")

    print("\nFailed Tasks:")
    failed_result = api.get_tasks(state="FAILURE")
    for task in failed_result["tasks"]:
        print(f"  {task['name']}: {task.get('traceback', 'N/A')[:50]}...")

    print("\nSearch for 'email':")
    search_result = api.search_tasks("email")
    print(f"  Found {search_result['total']} tasks")

    print("\nTask History for 'myapp.tasks.send_email':")
    history = api.get_task_history("myapp.tasks.send_email")
    print(f"  {len(history)} executions found")

    print("\nRetried Tasks:")
    retried = api.get_retried_tasks()
    print(f"  {len(retried)} retried tasks")

    print("\nWorkers:")
    workers = api.get_workers()
    for worker in workers:
        print(f"  {worker['hostname']}: {worker['status']}")

    print("\nHealth Status:")
    health = api.get_health()
    print(f"  Healthy: {health['healthy']}")
    print(f"  Active Workers: {health['active_workers']}")

    print("\nDaily Stats (last 7 days):")
    daily_stats = api.get_daily_stats(days=7)
    for stat in daily_stats:
        if stat['total'] > 0:
            print(f"  {stat['date']}: total={stat['total']}, succeeded={stat['succeeded']}, failed={stat['failed']}")

    print("\nMigration Status:")
    migration_status = api.get_migration_status()
    print(f"  Applied: {migration_status['applied']}/{migration_status['total']}")

    print("\nSimulating additional tasks...")
    for i in range(5):
        monitor.simulate_task_event(
            task_name=f"myapp.tasks.task_{i}",
            state=["SUCCESS", "FAILURE", "RETRY"][i % 3],
            worker="celery@worker1",
        )

    print("\nFinal Stats:")
    final_stats = api.get_task_stats()
    print(f"  Total: {final_stats['total']}")
    print(f"  By State: {final_stats['by_state']}")

    print("\nKanchi Monitor running successfully!")