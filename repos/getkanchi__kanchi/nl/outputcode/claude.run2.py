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
class TaskResult:
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
    expires: Optional[datetime] = None
    eta: Optional[datetime] = None
    queue: Optional[str] = None
    exchange: Optional[str] = None
    routing_key: Optional[str] = None
    clock: Optional[int] = None
    client: Optional[str] = None
    timestamp: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        for key, value in d.items():
            if isinstance(value, datetime):
                d[key] = value.isoformat()
            elif isinstance(value, TaskState):
                d[key] = value.value
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskResult":
        datetime_fields = [
            "received", "started", "succeeded", "failed",
            "retried", "revoked", "expires", "eta", "timestamp"
        ]
        for f in datetime_fields:
            if data.get(f) and isinstance(data[f], str):
                try:
                    data[f] = datetime.fromisoformat(data[f])
                except (ValueError, TypeError):
                    data[f] = None
        if "state" in data and isinstance(data["state"], str):
            data["state"] = TaskState(data["state"])
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class WorkerInfo:
    hostname: str
    status: str = "online"
    active_tasks: int = 0
    processed_tasks: int = 0
    failed_tasks: int = 0
    last_heartbeat: Optional[datetime] = None
    queues: List[str] = field(default_factory=list)
    concurrency: int = 0
    prefetch_count: int = 0
    pid: Optional[int] = None
    sw_ver: Optional[str] = None
    sw_sys: Optional[str] = None
    loadavg: Optional[List[float]] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if d.get("last_heartbeat") and isinstance(d["last_heartbeat"], datetime):
            d["last_heartbeat"] = d["last_heartbeat"].isoformat()
        return d

    def is_alive(self, timeout_seconds: int = 30) -> bool:
        if self.last_heartbeat is None:
            return False
        return (datetime.utcnow() - self.last_heartbeat).total_seconds() < timeout_seconds


@dataclass
class DailyTaskStats:
    date: str
    succeeded: int = 0
    failed: int = 0
    retried: int = 0
    revoked: int = 0
    total: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TaskFilter:
    task_id: Optional[str] = None
    name: Optional[str] = None
    state: Optional[TaskState] = None
    worker: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    search: Optional[str] = None
    queue: Optional[str] = None
    page: int = 1
    page_size: int = 20

    def matches(self, task: TaskResult) -> bool:
        if self.task_id and self.task_id.lower() not in task.task_id.lower():
            return False
        if self.name and self.name.lower() not in (task.name or "").lower():
            return False
        if self.state and task.state != self.state:
            return False
        if self.worker and self.worker.lower() not in (task.worker or "").lower():
            return False
        if self.queue and self.queue.lower() not in (task.queue or "").lower():
            return False
        if self.date_from:
            task_time = task.received or task.timestamp
            if task_time and task_time < self.date_from:
                return False
        if self.date_to:
            task_time = task.received or task.timestamp
            if task_time and task_time > self.date_to:
                return False
        if self.search:
            search_lower = self.search.lower()
            searchable = " ".join(filter(None, [
                task.task_id,
                task.name,
                task.worker,
                task.args,
                task.kwargs,
                task.result,
                task.traceback,
            ])).lower()
            if search_lower not in searchable:
                return False
        return True


class TaskStorage:
    def __init__(self, max_tasks: int = 10000):
        self._tasks: Dict[str, TaskResult] = {}
        self._task_order: List[str] = []
        self._max_tasks = max_tasks
        self._lock = threading.RLock()
        self._daily_stats: Dict[str, DailyTaskStats] = {}

    def save_task(self, task: TaskResult) -> None:
        with self._lock:
            is_new = task.task_id not in self._tasks
            self._tasks[task.task_id] = task
            if is_new:
                self._task_order.append(task.task_id)
                if len(self._task_order) > self._max_tasks:
                    oldest_id = self._task_order.pop(0)
                    self._tasks.pop(oldest_id, None)
            self._update_daily_stats(task)

    def _update_daily_stats(self, task: TaskResult) -> None:
        task_time = task.received or task.timestamp or datetime.utcnow()
        date_key = task_time.strftime("%Y-%m-%d")
        if date_key not in self._daily_stats:
            self._daily_stats[date_key] = DailyTaskStats(date=date_key)
        stats = self._daily_stats[date_key]
        if task.state == TaskState.SUCCESS:
            stats.succeeded += 1
        elif task.state == TaskState.FAILURE:
            stats.failed += 1
        elif task.state == TaskState.RETRY:
            stats.retried += 1
        elif task.state == TaskState.REVOKED:
            stats.revoked += 1
        stats.total = stats.succeeded + stats.failed + stats.retried + stats.revoked

    def get_task(self, task_id: str) -> Optional[TaskResult]:
        with self._lock:
            return self._tasks.get(task_id)

    def get_all_tasks(self) -> List[TaskResult]:
        with self._lock:
            return [self._tasks[tid] for tid in reversed(self._task_order) if tid in self._tasks]

    def filter_tasks(self, task_filter: TaskFilter) -> Tuple[List[TaskResult], int]:
        with self._lock:
            all_tasks = [self._tasks[tid] for tid in reversed(self._task_order) if tid in self._tasks]
            filtered = [t for t in all_tasks if task_filter.matches(t)]
            total = len(filtered)
            start = (task_filter.page - 1) * task_filter.page_size
            end = start + task_filter.page_size
            return filtered[start:end], total

    def delete_task(self, task_id: str) -> bool:
        with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
                self._task_order.remove(task_id)
                return True
            return False

    def clear_tasks(self) -> int:
        with self._lock:
            count = len(self._tasks)
            self._tasks.clear()
            self._task_order.clear()
            return count

    def get_daily_stats(self, days: int = 30) -> List[DailyTaskStats]:
        with self._lock:
            result = []
            today = datetime.utcnow().date()
            for i in range(days - 1, -1, -1):
                date = today - timedelta(days=i)
                date_key = date.strftime("%Y-%m-%d")
                stats = self._daily_stats.get(date_key, DailyTaskStats(date=date_key))
                result.append(stats)
            return result

    def get_task_stats(self) -> Dict[str, Any]:
        with self._lock:
            stats = {state.value: 0 for state in TaskState}
            for task in self._tasks.values():
                stats[task.state.value] = stats.get(task.state.value, 0) + 1
            stats["total"] = len(self._tasks)
            return stats

    def find_orphan_tasks(self, workers: Dict[str, WorkerInfo]) -> List[TaskResult]:
        with self._lock:
            orphans = []
            active_worker_hostnames = set(workers.keys())
            for task in self._tasks.values():
                if task.state == TaskState.STARTED:
                    if task.worker and task.worker not in active_worker_hostnames:
                        orphans.append(task)
                    elif task.started:
                        elapsed = (datetime.utcnow() - task.started).total_seconds()
                        if elapsed > 3600:
                            orphans.append(task)
            return orphans

    def get_retry_chain(self, task_id: str) -> List[TaskResult]:
        with self._lock:
            chain = []
            task = self._tasks.get(task_id)
            if not task:
                return chain
            chain.append(task)
            for t in self._tasks.values():
                if t.parent_id == task_id and t.task_id != task_id:
                    chain.extend(self.get_retry_chain(t.task_id))
            return chain


class WorkerRegistry:
    def __init__(self, heartbeat_timeout: int = 30):
        self._workers: Dict[str, WorkerInfo] = {}
        self._lock = threading.RLock()
        self._heartbeat_timeout = heartbeat_timeout

    def register_worker(self, hostname: str, **kwargs) -> WorkerInfo:
        with self._lock:
            if hostname not in self._workers:
                worker = WorkerInfo(hostname=hostname, **kwargs)
                self._workers[hostname] = worker
            else:
                worker = self._workers[hostname]
                for key, value in kwargs.items():
                    if hasattr(worker, key):
                        setattr(worker, key, value)
            worker.last_heartbeat = datetime.utcnow()
            worker.status = "online"
            return worker

    def update_heartbeat(self, hostname: str) -> Optional[WorkerInfo]:
        with self._lock:
            worker = self._workers.get(hostname)
            if worker:
                worker.last_heartbeat = datetime.utcnow()
                worker.status = "online"
            return worker

    def mark_offline(self, hostname: str) -> Optional[WorkerInfo]:
        with self._lock:
            worker = self._workers.get(hostname)
            if worker:
                worker.status = "offline"
            return worker

    def get_worker(self, hostname: str) -> Optional[WorkerInfo]:
        with self._lock:
            return self._workers.get(hostname)

    def get_all_workers(self) -> List[WorkerInfo]:
        with self._lock:
            return list(self._workers.values())

    def get_online_workers(self) -> List[WorkerInfo]:
        with self._lock:
            return [w for w in self._workers.values() if w.is_alive(self._heartbeat_timeout)]

    def check_worker_health(self) -> None:
        with self._lock:
            for worker in self._workers.values():
                if not worker.is_alive(self._heartbeat_timeout):
                    worker.status = "offline"

    def update_task_count(self, hostname: str, active_delta: int = 0,
                          processed_delta: int = 0, failed_delta: int = 0) -> None:
        with self._lock:
            worker = self._workers.get(hostname)
            if worker:
                worker.active_tasks = max(0, worker.active_tasks + active_delta)
                worker.processed_tasks += processed_delta
                worker.failed_tasks += failed_delta

    def remove_worker(self, hostname: str) -> bool:
        with self._lock:
            if hostname in self._workers:
                del self._workers[hostname]
                return True
            return False

    def get_worker_stats(self) -> Dict[str, Any]:
        with self._lock:
            online = sum(1 for w in self._workers.values() if w.is_alive(self._heartbeat_timeout))
            return {
                "total": len(self._workers),
                "online": online,
                "offline": len(self._workers) - online,
            }


class WebSocketConnection:
    def __init__(self, connection_id: str):
        self.connection_id = connection_id
        self.created_at = datetime.utcnow()
        self._queue: asyncio.Queue = asyncio.Queue()
        self._closed = False
        self.subscriptions: List[str] = []

    async def send(self, message: Dict[str, Any]) -> None:
        if not self._closed:
            await self._queue.put(json.dumps(message))

    async def receive(self) -> Optional[str]:
        if self._closed:
            return None
        try:
            return await asyncio.wait_for(self._queue.get(), timeout=1.0)
        except asyncio.TimeoutError:
            return None

    def close(self) -> None:
        self._closed = True

    @property
    def is_closed(self) -> bool:
        return self._closed


class WebSocketManager:
    def __init__(self):
        self._connections: Dict[str, WebSocketConnection] = {}
        self._lock = threading.RLock()

    def add_connection(self, connection: WebSocketConnection) -> None:
        with self._lock:
            self._connections[connection.connection_id] = connection
            logger.info(f"WebSocket connection added: {connection.connection_id}")

    def remove_connection(self, connection_id: str) -> None:
        with self._lock:
            conn = self._connections.pop(connection_id, None)
            if conn:
                conn.close()
                logger.info(f"WebSocket connection removed: {connection_id}")

    def get_connection(self, connection_id: str) -> Optional[WebSocketConnection]:
        with self._lock:
            return self._connections.get(connection_id)

    async def broadcast(self, message: Dict[str, Any]) -> None:
        with self._lock:
            connections = list(self._connections.values())
        for conn in connections:
            if not conn.is_closed:
                try:
                    await conn.send(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to {conn.connection_id}: {e}")

    async def send_to(self, connection_id: str, message: Dict[str, Any]) -> bool:
        conn = self.get_connection(connection_id)
        if conn and not conn.is_closed:
            await conn.send(message)
            return True
        return False

    def get_connection_count(self) -> int:
        with self._lock:
            return len(self._connections)

    def cleanup_closed(self) -> int:
        with self._lock:
            closed = [cid for cid, conn in self._connections.items() if conn.is_closed]
            for cid in closed:
                del self._connections[cid]
            return len(closed)


class EventProcessor:
    def __init__(self, task_storage: TaskStorage, worker_registry: WorkerRegistry,
                 ws_manager: WebSocketManager):
        self._task_storage = task_storage
        self._worker_registry = worker_registry
        self._ws_manager = ws_manager
        self._event_handlers = {
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

    async def process_event(self, event: Dict[str, Any]) -> None:
        event_type = event.get("type", "")
        handler = self._event_handlers.get(event_type)
        if handler:
            await handler(event)
        else:
            logger.debug(f"Unhandled event type: {event_type}")

    async def _handle_task_received(self, event: Dict[str, Any]) -> None:
        task_id = event.get("uuid") or event.get("task_id", str(uuid.uuid4()))
        task = self._task_storage.get_task(task_id) or TaskResult(
            task_id=task_id,
            name=event.get("name", "unknown"),
            state=TaskState.RECEIVED,
        )
        task.state = TaskState.RECEIVED
        task.name = event.get("name", task.name)
        task.worker = event.get("hostname", task.worker)
        task.args = str(event.get("args", task.args))
        task.kwargs = str(event.get("kwargs", task.kwargs))
        task.received = datetime.utcfromtimestamp(event.get("timestamp", time.time()))
        task.retries = event.get("retries", task.retries)
        task.eta = self._parse_datetime(event.get("eta"))
        task.expires = self._parse_datetime(event.get("expires"))
        task.queue = event.get("queue", task.queue)
        task.exchange = event.get("exchange", task.exchange)
        task.routing_key = event.get("routing_key", task.routing_key)
        task.root_id = event.get("root_id", task.root_id)
        task.parent_id = event.get("parent_id", task.parent_id)
        task.clock = event.get("clock", task.clock)
        task.client = event.get("client", task.client)
        self._task_storage.save_task(task)
        await self._broadcast_task_update(task)

    async def _handle_task_started(self, event: Dict[str, Any]) -> None:
        task_id = event.get("uuid") or event.get("task_id", "")
        task = self._task_storage.get_task(task_id)
        if not task:
            task = TaskResult(
                task_id=task_id,
                name=event.get("name", "unknown"),
                state=TaskState.STARTED,
            )
        task.state = TaskState.STARTED
        task.worker = event.get("hostname", task.worker)
        task.started = datetime.utcfromtimestamp(event.get("timestamp", time.time()))
        task.pid = event.get("pid")
        self._task_storage.save_task(task)
        if task.worker:
            self._worker_registry.update_task_count(task.worker, active_delta=1)
        await self._broadcast_task_update(task)

    async def _handle_task_succeeded(self, event: Dict[str, Any]) -> None:
        task_id = event.get("uuid") or event.get("task_id", "")
        task = self._task_storage.get_task(task_id)
        if not task:
            task = TaskResult(
                task_id=task_id,
                name=event.get("name", "unknown"),
                state=TaskState.SUCCESS,
            )
        task.state = TaskState.SUCCESS
        task.worker = event.get("hostname", task.worker)
        task.succeeded = datetime.utcfromtimestamp(event.get("timestamp", time.time()))
        task.result = str(event.get("result", ""))
        task.runtime = event.get("runtime", task.runtime)
        self._task_storage.save_task(task)
        if task.worker:
            self._worker_registry.update_task_count(task.worker, active_delta=-1, processed_delta=1)
        await self._broadcast_task_update(task)

    async def _handle_task_failed(self, event: Dict[str, Any]) -> None:
        task_id = event.get("uuid") or event.get("task_id", "")
        task = self._task_storage.get_task(task_id)
        if not task:
            task = TaskResult(
                task_id=task_id,
                name=event.get("name", "unknown"),
                state=TaskState.FAILURE,
            )
        task.state = TaskState.FAILURE
        task.worker = event.get("hostname", task.worker)
        task.failed = datetime.utcfromtimestamp(event.get("timestamp", time.time()))
        task.traceback = event.get("traceback", task.traceback)
        task.result = str(event.get("exception", ""))
        self._task_storage.save_task(task)
        if task.worker:
            self._worker_registry.update_task_count(task.worker, active_delta=-1, failed_delta=1)
        await self._broadcast_task_update(task)

    async def _handle_task_retried(self, event: Dict[str, Any]) -> None:
        task_id = event.get("uuid") or event.get("task_id", "")
        task = self._task_storage.get_task(task_id)
        if not task:
            task = TaskResult(
                task_id=task_id,
                name=event.get("name", "unknown"),
                state=TaskState.RETRY,
            )
        task.state = TaskState.RETRY
        task.worker = event.get("hostname", task.worker)
        task.retried = datetime.utcfromtimestamp(event.get("timestamp", time.time()))
        task.retries = event.get("retries", task.retries + 1)
        task.traceback = event.get("traceback", task.traceback)
        self._task_storage.save_task(task)
        await self._broadcast_task_update(task)

    async def _handle_task_revoked(self, event: Dict[str, Any]) -> None:
        task_id = event.get("uuid") or event.get("task_id", "")
        task = self._task_storage.get_task(task_id)
        if not task:
            task = TaskResult(
                task_id=task_id,
                name=event.get("name", "unknown"),
                state=TaskState.REVOKED,
            )
        task.state = TaskState.REVOKED
        task.worker = event.get("hostname", task.worker)
        task.revoked = datetime.utcfromtimestamp(event.get("timestamp", time.time()))
        self._task_storage.save_task(task)
        if task.worker:
            self._worker_registry.update_task_count(task.worker, active_delta=-1)
        await self._broadcast_task_update(task)

    async def _handle_worker_online(self, event: Dict[str, Any]) -> None:
        hostname = event.get("hostname", "unknown")
        worker = self._worker_registry.register_worker(
            hostname=hostname,
            pid=event.get("pid"),
            sw_ver=event.get("sw_ver"),
            sw_sys=event.get("sw_sys"),
            concurrency=event.get("concurrency", 0),
            queues=[q.get("name", q) if isinstance(q, dict) else q
                    for q in event.get("queues", [])],
        )
        await self._broadcast_worker_update(worker)

    async def _handle_worker_offline(self, event: Dict[str, Any]) -> None:
        hostname = event.get("hostname", "unknown")
        worker = self._worker_registry.mark_offline(hostname)
        if worker:
            await self._broadcast_worker_update(worker)

    async def _handle_worker_heartbeat(self, event: Dict[str, Any]) -> None:
        hostname = event.get("hostname", "unknown")
        worker = self._worker_registry.update_heartbeat(hostname)
        if not worker:
            worker = self._worker_registry.register_worker(hostname=hostname)
        worker.active_tasks = event.get("active", worker.active_tasks)
        worker.processed_tasks = event.get("processed", worker.processed_tasks)
        worker.loadavg = event.get("loadavg", worker.loadavg)
        await self._broadcast_worker_update(worker)

    async def _broadcast_task_update(self, task: TaskResult) -> None:
        message = {
            "type": "task_update",
            "data": task.to_dict(),
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self._ws_manager.broadcast(message)

    async def _broadcast_worker_update(self, worker: WorkerInfo) -> None:
        message = {
            "type": "worker_update",
            "data": worker.to_dict(),
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self._ws_manager.broadcast(message)

    @staticmethod
    def _parse_datetime(value: Any) -> Optional[datetime]:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, (int, float)):
            return datetime.utcfromtimestamp(value)
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                pass
        return None


class MigrationManager:
    def __init__(self, db_url: str = "sqlite:///kanchi.db"):
        self._db_url = db_url
        self._migrations: List[Dict[str, Any]] = []
        self._applied: List[str] = []
        self._register_migrations()

    def _register_migrations(self) -> None:
        self._migrations = [
            {
                "version": "001",
                "description": "Create tasks table",
                "up": self._migration_001_up,
                "down": self._migration_001_down,
            },
            {
                "version": "002",
                "description": "Create workers table",
                "up": self._migration_002_up,
                "down": self._migration_002_down,
            },
            {
                "version": "003",
                "description": "Create daily stats table",
                "up": self._migration_003_up,
                "down": self._migration_003_down,
            },
            {
                "version": "004",
                "description": "Add indexes for task filtering",
                "up": self._migration_004_up,
                "down": self._migration_004_down,
            },
        ]

    def _migration_001_up(self) -> str:
        return """
        CREATE TABLE IF NOT EXISTS tasks (
            task_id VARCHAR(255) PRIMARY KEY,
            name VARCHAR(255),
            state VARCHAR(50),
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
            expires TIMESTAMP,
            eta TIMESTAMP,
            queue VARCHAR(255),
            exchange VARCHAR(255),
            routing_key VARCHAR(255),
            clock INTEGER,
            client VARCHAR(255),
            timestamp TIMESTAMP
        )
        """

    def _migration_001_down(self) -> str:
        return "DROP TABLE IF EXISTS tasks"

    def _migration_002_up(self) -> str:
        return """
        CREATE TABLE IF NOT EXISTS workers (
            hostname VARCHAR(255) PRIMARY KEY,
            status VARCHAR(50),
            active_tasks INTEGER DEFAULT 0,
            processed_tasks INTEGER DEFAULT 0,
            failed_tasks INTEGER DEFAULT 0,
            last_heartbeat TIMESTAMP,
            concurrency INTEGER DEFAULT 0,
            prefetch_count INTEGER DEFAULT 0,
            pid INTEGER,
            sw_ver VARCHAR(50),
            sw_sys VARCHAR(50)
        )
        """

    def _migration_002_down(self) -> str:
        return "DROP TABLE IF EXISTS workers"

    def _migration_003_up(self) -> str:
        return """
        CREATE TABLE IF NOT EXISTS daily_stats (
            date VARCHAR(10) PRIMARY KEY,
            succeeded INTEGER DEFAULT 0,
            failed INTEGER DEFAULT 0,
            retried INTEGER DEFAULT 0,
            revoked INTEGER DEFAULT 0,
            total INTEGER DEFAULT 0
        )
        """

    def _migration_003_down(self) -> str:
        return "DROP TABLE IF EXISTS daily_stats"

    def _migration_004_up(self) -> str:
        return """
        CREATE INDEX IF NOT EXISTS idx_tasks_state ON tasks(state);
        CREATE INDEX IF NOT EXISTS idx_tasks_worker ON tasks(worker);
        CREATE INDEX IF NOT EXISTS idx_tasks_name ON tasks(name);
        CREATE INDEX IF NOT EXISTS idx_tasks_received ON tasks(received);
        """

    def _migration_004_down(self) -> str:
        return """
        DROP INDEX IF EXISTS idx_tasks_state;
        DROP INDEX IF EXISTS idx_tasks_worker;
        DROP INDEX IF EXISTS idx_tasks_name;
        DROP INDEX IF EXISTS idx_tasks_received;
        """

    def get_pending_migrations(self) -> List[Dict[str, Any]]:
        return [m for m in self._migrations if m["version"] not in self._applied]

    def apply_migration(self, version: str) -> bool:
        migration = next((m for m in self._migrations if m["version"] == version), None)
        if not migration:
            logger.error(f"Migration {version} not found")
            return False
        if version in self._applied:
            logger.info(f"Migration {version} already applied")
            return True
        try:
            sql = migration["up"]()
            logger.info(f"Applied migration {version}: {migration['description']}")
            self._applied.append(version)
            return True
        except Exception as e:
            logger.error(f"Failed to apply migration {version}: {e}")
            return False

    def run_migrations(self) -> int:
        pending = self.get_pending_migrations()
        applied_count = 0
        for migration in pending:
            if self.apply_migration(migration["version"]):
                applied_count += 1
        logger.info(f"Applied {applied_count} migrations")
        return applied_count

    def rollback_migration(self, version: str) -> bool:
        migration = next((m for m in self._migrations if m["version"] == version), None)
        if not migration:
            return False
        if version not in self._applied:
            return False
        try:
            sql = migration["down"]()
            self._applied.remove(version)
            logger.info(f"Rolled back migration {version}")
            return True
        except Exception as e:
            logger.error(f"Failed to rollback migration {version}: {e}")
            return False


class TaskMonitor:
    def __init__(self, task_storage: TaskStorage, worker_registry: WorkerRegistry,
                 ws_manager: WebSocketManager, event_processor: EventProcessor):
        self._task_storage = task_storage
        self._worker_registry = worker_registry
        self._ws_manager = ws_manager
        self._event_processor = event_processor
        self._running = False
        self._health_check_interval = 30

    async def start(self) -> None:
        self._running = True
        logger.info("Task monitor started")
        asyncio.create_task(self._health_check_loop())

    async def stop(self) -> None:
        self._running = False
        logger.info("Task monitor stopped")

    async def _health_check_loop(self) -> None:
        while self._running:
            await asyncio.sleep(self._health_check_interval)
            self._worker_registry.check_worker_health()
            orphans = self._task_storage.find_orphan_tasks(
                {w.hostname: w for w in self._worker_registry.get_all_workers()}
            )
            if orphans:
                logger.warning(f"Found {len(orphans)} orphan tasks")
                await self._ws_manager.broadcast({
                    "type": "orphan_tasks",
                    "data": [t.to_dict() for t in orphans],
                    "timestamp": datetime.utcnow().isoformat(),
                })
            self._ws_manager.cleanup_closed()

    async def process_event(self, event: Dict[str, Any]) -> None:
        await self._event_processor.process_event(event)

    def get_task(self, task_id: str) -> Optional[TaskResult]:
        return self._task_storage.get_task(task_id)

    def filter_tasks(self, task_filter: TaskFilter) -> Tuple[List[TaskResult], int]:
        return self._task_storage.filter_tasks(task_filter)

    def get_task_stats(self) -> Dict[str, Any]:
        return self._task_storage.get_task_stats()

    def get_daily_stats(self, days: int = 30) -> List[DailyTaskStats]:
        return self._task_storage.get_daily_stats(days)

    def get_workers(self) -> List[WorkerInfo]:
        return self._worker_registry.get_all_workers()

    def get_worker_stats(self) -> Dict[str, Any]:
        return self._worker_registry.get_worker_stats()

    def get_retry_chain(self, task_id: str) -> List[TaskResult]:
        return self._task_storage.get_retry_chain(task_id)

    def find_orphan_tasks(self) -> List[TaskResult]:
        workers = {w.hostname: w for w in self._worker_registry.get_all_workers()}
        return self._task_storage.find_orphan_tasks(workers)

    def delete_task(self, task_id: str) -> bool:
        return self._task_storage.delete_task(task_id)

    def clear_tasks(self) -> int:
        return self._task_storage.clear_tasks()

    def get_websocket_count(self) -> int:
        return self._ws_manager.get_connection_count()


class KanchiApp:
    def __init__(self, max_tasks: int = 10000, heartbeat_timeout: int = 30):
        self._task_storage = TaskStorage(max_tasks=max_tasks)
        self._worker_registry = WorkerRegistry(heartbeat_timeout=heartbeat_timeout)
        self._ws_manager = WebSocketManager()
        self._event_processor = EventProcessor(
            self._task_storage, self._worker_registry, self._ws_manager
        )
        self._monitor = TaskMonitor(
            self._task_storage, self._worker_registry,
            self._ws_manager, self._event_processor
        )
        self._migration_manager = MigrationManager()
        self._started = False

    async def start(self) -> None:
        if not self._started:
            self._migration_manager.run_migrations()
            await self._monitor.start()
            self._started = True
            logger.info("Kanchi application started")

    async def stop(self) -> None:
        if self._started:
            await self._monitor.stop()
            self._started = False
            logger.info("Kanchi application stopped")

    async def process_event(self, event: Dict[str, Any]) -> None:
        await self._monitor.process_event(event)

    def get_task(self, task_id: str) -> Optional[TaskResult]:
        return self._monitor.get_task(task_id)

    def filter_tasks(self, **kwargs) -> Tuple[List[TaskResult], int]:
        task_filter = TaskFilter(**{k: v for k, v in kwargs.items()
                                    if k in TaskFilter.__dataclass_fields__})
        return self._monitor.filter_tasks(task_filter)

    def get_task_stats(self) -> Dict[str, Any]:
        return self._monitor.get_task_stats()

    def get_daily_stats(self, days: int = 30) -> List[Dict[str, Any]]:
        return [s.to_dict() for s in self._monitor.get_daily_stats(days)]

    def get_workers(self) -> List[Dict[str, Any]]:
        return [w.to_dict() for w in self._monitor.get_workers()]

    def get_worker_stats(self) -> Dict[str, Any]:
        return self._monitor.get_worker_stats()

    def get_retry_chain(self, task_id: str) -> List[Dict[str, Any]]:
        return [t.to_dict() for t in self._monitor.get_retry_chain(task_id)]

    def find_orphan_tasks(self) -> List[Dict[str, Any]]:
        return [t.to_dict() for t in self._monitor.find_orphan_tasks()]

    def delete_task(self, task_id: str) -> bool:
        return self._monitor.delete_task(task_id)

    def clear_tasks(self) -> int:
        return self._monitor.clear_tasks()

    async def connect_websocket(self) -> WebSocketConnection:
        conn = WebSocketConnection(connection_id=str(uuid.uuid4()))
        self._ws_manager.add_connection(conn)
        await conn.send({
            "type": "connected",
            "connection_id": conn.connection_id,
            "timestamp": datetime.utcnow().isoformat(),
        })
        return conn

    def disconnect_websocket(self, connection_id: str) -> None:
        self._ws_manager.remove_connection(connection_id)

    async def broadcast(self, message: Dict[str, Any]) -> None:
        await self._ws_manager.broadcast(message)

    def get_websocket_count(self) -> int:
        return self._monitor.get_websocket_count()

    @property
    def task_storage(self) -> TaskStorage:
        return self._task_storage

    @property
    def worker_registry(self) -> WorkerRegistry:
        return self._worker_registry

    @property
    def ws_manager(self) -> WebSocketManager:
        return self._ws_manager

    @property
    def event_processor(self) -> EventProcessor:
        return self._event_processor

    @property
    def monitor(self) -> TaskMonitor:
        return self._monitor

    @property
    def migration_manager(self) -> MigrationManager:
        return self._migration_manager


class CeleryEventReceiver:
    def __init__(self, app: KanchiApp, celery_app=None):
        self._kanchi_app = app
        self._celery_app = celery_app
        self._running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def on_event(self, event: Dict[str, Any]) -> None:
        if self._loop and not self._loop.is_closed():
            asyncio.run_coroutine_threadsafe(
                self._kanchi_app.process_event(event),
                self._loop
            )

    def start_receiving(self) -> None:
        if self._celery_app is None:
            logger.warning("No Celery app configured, using mock event generation")
            self._running = True
            return
        self._running = True
        try:
            with self._celery_app.connection() as conn:
                recv = self._celery_app.events.Receiver(
                    conn,
                    handlers={"*": self.on_event}
                )
                recv.capture(limit=None, timeout=None, wakeup=True)
        except Exception as e:
            logger.error(f"Error receiving Celery events: {e}")

    def stop_receiving(self) -> None:
        self._running = False


class TaskSearchEngine:
    def __init__(self, task_storage: TaskStorage):
        self._task_storage = task_storage

    def search(self, query: str, page: int = 1, page_size: int = 20) -> Tuple[List[TaskResult], int]:
        task_filter = TaskFilter(search=query, page=page, page_size=page_size)
        return self._task_storage.filter_tasks(task_filter)

    def search_by_date_range(self, date_from: datetime, date_to: datetime,
                              page: int = 1, page_size: int = 20) -> Tuple[List[TaskResult], int]:
        task_filter = TaskFilter(date_from=date_from, date_to=date_to, page=page, page_size=page_size)
        return self._task_storage.filter_tasks(task_filter)

    def search_by_state(self, state: TaskState, page: int = 1,
                         page_size: int = 20) -> Tuple[List[TaskResult], int]:
        task_filter = TaskFilter(state=state, page=page, page_size=page_size)
        return self._task_storage.filter_tasks(task_filter)

    def search_by_worker(self, worker: str, page: int = 1,
                          page_size: int = 20) -> Tuple[List[TaskResult], int]:
        task_filter = TaskFilter(worker=worker, page=page, page_size=page_size)
        return self._task_storage.filter_tasks(task_filter)

    def search_by_name(self, name: str, page: int = 1,
                        page_size: int = 20) -> Tuple[List[TaskResult], int]:
        task_filter = TaskFilter(name=name, page=page, page_size=page_size)
        return self._task_storage.filter_tasks(task_filter)

    def advanced_search(self, task_filter: TaskFilter) -> Tuple[List[TaskResult], int]:
        return self._task_storage.filter_tasks(task_filter)


class RetryTracker:
    def __init__(self, task_storage: TaskStorage):
        self._task_storage = task_storage

    def get_retry_chain(self, task_id: str) -> List[TaskResult]:
        return self._task_storage.get_retry_chain(task_id)

    def get_tasks_with_retries(self) -> List[TaskResult]:
        all_tasks = self._task_storage.get_all_tasks()
        return [t for t in all_tasks if t.retries > 0]

    def get_retry_stats(self) -> Dict[str, Any]:
        all_tasks = self._task_storage.get_all_tasks()
        tasks_with_retries = [t for t in all_tasks if t.retries > 0]
        total_retries = sum(t.retries for t in all_tasks)
        max_retries = max((t.retries for t in all_tasks), default=0)
        return {
            "tasks_with_retries": len(tasks_with_retries),
            "total_retries": total_retries,
            "max_retries_single_task": max_retries,
            "average_retries": total_retries / len(all_tasks) if all_tasks else 0,
        }


class OrphanDetector:
    def __init__(self, task_storage: TaskStorage, worker_registry: WorkerRegistry):
        self._task_storage = task_storage
        self._worker_registry = worker_registry

    def find_orphans(self) -> List[TaskResult]:
        workers = {w.hostname: w for w in self._worker_registry.get_all_workers()}
        return self._task_storage.find_orphan_tasks(workers)

    def mark_orphan_as_failed(self, task_id: str) -> Optional[TaskResult]:
        task = self._task_storage.get_task(task_id)
        if task and task.state == TaskState.STARTED:
            task.state = TaskState.FAILURE
            task.failed = datetime.utcnow()
            task.traceback = "Task marked as failed: worker went offline (orphan detection)"
            self._task_storage.save_task(task)
            return task
        return None

    def cleanup_orphans(self) -> int:
        orphans = self.find_orphans()
        count = 0
        for task in orphans:
            if self.mark_orphan_as_failed(task.task_id):
                count += 1
        return count


class HealthChecker:
    def __init__(self, worker_registry: WorkerRegistry, task_storage: TaskStorage):
        self._worker_registry = worker_registry
        self._task_storage = task_storage

    def get_system_health(self) -> Dict[str, Any]:
        worker_stats = self._worker_registry.get_worker_stats()
        task_stats = self._task_storage.get_task_stats()
        workers = self._worker_registry.get_all_workers()
        online_workers = [w for w in workers if w.is_alive()]
        total_active = sum(w.active_tasks for w in online_workers)
        return {
            "status": "healthy" if worker_stats["online"] > 0 else "degraded",
            "workers": worker_stats,
            "tasks": task_stats,
            "active_tasks": total_active,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def get_worker_health(self, hostname: str) -> Optional[Dict[str, Any]]:
        worker = self._worker_registry.get_worker(hostname)
        if not worker:
            return None
        is_alive = worker.is_alive()
        return {
            "hostname": worker.hostname,
            "status": worker.status,
            "is_alive": is_alive,
            "last_heartbeat": worker.last_heartbeat.isoformat() if worker.last_heartbeat else None,
            "active_tasks": worker.active_tasks,
            "processed_tasks": worker.processed_tasks,
            "failed_tasks": worker.failed_tasks,
        }


def create_app(max_tasks: int = 10000, heartbeat_timeout: int = 30) -> KanchiApp:
    return KanchiApp(max_tasks=max_tasks, heartbeat_timeout=heartbeat_timeout)


async def main():
    app = create_app()
    await app.start()

    logger.info("Simulating Celery events...")

    events = [
        {
            "type": "worker-online",
            "hostname": "celery@worker1",
            "pid": 12345,
            "sw_ver": "5.2.0",
            "sw_sys": "Linux",
            "concurrency": 4,
            "queues": ["default", "high_priority"],
            "timestamp": time.time(),
        },
        {
            "type": "worker-online",
            "hostname": "celery@worker2",
            "pid": 12346,
            "sw_ver": "5.2.0",
            "sw_sys": "Linux",
            "concurrency": 2,
            "queues": ["default"],
            "timestamp": time.time(),
        },
        {
            "type": "task-received",
            "uuid": "task-001",
            "name": "myapp.tasks.send_email",
            "hostname": "celery@worker1",
            "args": "['user@example.com']",
            "kwargs": "{'subject': 'Hello'}",
            "queue": "default",
            "timestamp": time.time(),
        },
        {
            "type": "task-started",
            "uuid": "task-001",
            "hostname": "celery@worker1",
            "timestamp": time.time(),
        },
        {
            "type": "task-succeeded",
            "uuid": "task-001",
            "hostname": "celery@worker1",
            "result": "True",
            "runtime": 0.5,
            "timestamp": time.time(),
        },
        {
            "type": "task-received",
            "uuid": "task-002",
            "name": "myapp.tasks.process_data",
            "hostname": "celery@worker2",
            "args": "[42]",
            "kwargs": "{}",
            "queue": "high_priority",
            "timestamp": time.time(),
        },
        {
            "type": "task-started",
            "uuid": "task-002",
            "hostname": "celery@worker2",
            "timestamp": time.time(),
        },
        {
            "type": "task-failed",
            "uuid": "task-002",
            "hostname": "celery@worker2",
            "exception": "ValueError: Invalid data",
            "traceback": "Traceback (most recent call last):\n  ...\nValueError: Invalid data",
            "timestamp": time.time(),
        },
        {
            "type": "task-received",
            "uuid": "task-003",
            "name": "myapp.tasks.send_email",
            "hostname": "celery@worker1",
            "args": "['admin@example.com']",
            "kwargs": "{'subject': 'Report'}",
            "queue": "default",
            "retries": 1,
            "parent_id": "task-001",
            "timestamp": time.time(),
        },
        {
            "type": "task-retried",
            "uuid": "task-003",
            "hostname": "celery@worker1",
            "retries": 1,
            "timestamp": time.time(),
        },
        {
            "type": "worker-heartbeat",
            "hostname": "celery@worker1",
            "active": 0,
            "processed": 2,
            "loadavg": [0.5, 0.3, 0.2],
            "timestamp": time.time(),
        },
    ]

    for event in events:
        await app.process_event(event)
        await asyncio.sleep(0.01)

    logger.info("\n=== Task Statistics ===")
    stats = app.get_task_stats()
    for key, value in stats.items():
        logger.info(f"  {key}: {value}")

    logger.info("\n=== Worker Statistics ===")
    worker_stats = app.get_worker_stats()
    for key, value in worker_stats.items():
        logger.info(f"  {key}: {value}")

    logger.info("\n=== Workers ===")
    workers = app.get_workers()
    for worker in workers:
        logger.info(f"  {worker['hostname']}: {worker['status']}")

    logger.info("\n=== All Tasks ===")
    tasks, total = app.filter_tasks(page=1, page_size=10)
    logger.info(f"  Total tasks: {total}")
    for task in tasks:
        logger.info(f"  [{task['state']}] {task['name']} ({task['task_id']})")

    logger.info("\n=== Failed Tasks ===")
    failed_tasks, failed_total = app.filter_tasks(state=TaskState.FAILURE)
    logger.info(f"  Total failed: {failed_total}")
    for task in failed_tasks:
        logger.info(f"  {task['name']}: {task['result']}")

    logger.info("\n=== Daily Stats (last 7 days) ===")
    daily_stats = app.get_daily_stats(days=7)
    for stat in daily_stats:
        if stat["total"] > 0:
            logger.info(f"  {stat['date']}: {stat}")

    logger.info("\n=== Retry Chain for task-003 ===")
    retry_chain = app.get_retry_chain("task-003")
    for task in retry_chain:
        logger.info(f"  {task['task_id']}: retries={task['retries']}, state={task['state']}")

    logger.info("\n=== Search: 'email' ===")
    search_results, search_total = app.filter_tasks(search="email")
    logger.info(f"  Found {search_total} tasks")
    for task in search_results:
        logger.info(f"  {task['name']}")

    logger.info("\n=== WebSocket Test ===")
    conn = await app.connect_websocket()
    logger.info(f"  Connected: {conn.connection_id}")
    msg = await conn.receive()
    if msg:
        data = json.loads(msg)
        logger.info(f"  Received: {data['type']}")

    await app.process_event({
        "type": "task-received",
        "uuid": "task-ws-test",
        "name": "myapp.tasks.websocket_test",
        "hostname": "celery@worker1",
        "timestamp": time.time(),
    })

    msg = await conn.receive()
    if msg:
        data = json.loads(msg)
        logger.info(f"  Received update: {data['type']} - {data['data'].get('name', '')}")

    app.disconnect_websocket(conn.connection_id)
    logger.info(f"  Disconnected")

    logger.info("\n=== Health Check ===")
    health_checker = HealthChecker(app.worker_registry, app.task_storage)
    health = health_checker.get_system_health()
    logger.info(f"  System status: {health['status']}")
    logger.info(f"  Active tasks: {health['active_tasks']}")

    logger.info("\n=== Orphan Detection ===")
    orphan_detector = OrphanDetector(app.task_storage, app.worker_registry)
    orphans = orphan_detector.find_orphans()
    logger.info(f"  Orphan tasks found: {len(orphans)}")

    logger.info("\n=== Retry Tracker ===")
    retry_tracker = RetryTracker(app.task_storage)
    retry_stats = retry_tracker.get_retry_stats()
    logger.info(f"  Retry stats: {retry_stats}")

    logger.info("\n=== Migration Manager ===")
    migration_manager = app.migration_manager
    logger.info(f"  Applied migrations: {migration_manager._applied}")

    await app.stop()
    logger.info("\nKanchi application stopped successfully")


if __name__ == "__main__":
    asyncio.run(main())