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

    def is_orphan(self) -> bool:
        if self.parent_id and self.root_id:
            return self.parent_id != self.root_id and self.state in [
                TaskState.FAILURE, TaskState.REVOKED
            ]
        return False


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
        if self.last_heartbeat:
            d['last_heartbeat'] = self.last_heartbeat.isoformat()
        return d

    def is_healthy(self) -> bool:
        if self.last_heartbeat is None:
            return False
        threshold = datetime.utcnow() - timedelta(seconds=30)
        return self.last_heartbeat > threshold and self.status == "online"


@dataclass
class DailyTaskStats:
    date: str
    task_name: str
    succeeded: int = 0
    failed: int = 0
    retried: int = 0
    revoked: int = 0
    total: int = 0
    avg_runtime: float = 0.0
    min_runtime: Optional[float] = None
    max_runtime: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def update(self, state: TaskState, runtime: Optional[float] = None):
        self.total += 1
        if state == TaskState.SUCCESS:
            self.succeeded += 1
        elif state == TaskState.FAILURE:
            self.failed += 1
        elif state == TaskState.RETRY:
            self.retried += 1
        elif state == TaskState.REVOKED:
            self.revoked += 1

        if runtime is not None:
            if self.min_runtime is None or runtime < self.min_runtime:
                self.min_runtime = runtime
            if self.max_runtime is None or runtime > self.max_runtime:
                self.max_runtime = runtime
            total_runtime = self.avg_runtime * (self.total - 1) + runtime
            self.avg_runtime = total_runtime / self.total


class TaskFilter:
    def __init__(
        self,
        state: Optional[TaskState] = None,
        name: Optional[str] = None,
        worker: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        search: Optional[str] = None,
        queue: Optional[str] = None,
        is_orphan: Optional[bool] = None,
        has_retries: Optional[bool] = None,
    ):
        self.state = state
        self.name = name
        self.worker = worker
        self.date_from = date_from
        self.date_to = date_to
        self.search = search
        self.queue = queue
        self.is_orphan = is_orphan
        self.has_retries = has_retries

    def matches(self, task: TaskResult) -> bool:
        if self.state and task.state != self.state:
            return False
        if self.name and self.name.lower() not in (task.name or "").lower():
            return False
        if self.worker and self.worker.lower() not in (task.worker or "").lower():
            return False
        if self.date_from and task.received and task.received < self.date_from:
            return False
        if self.date_to and task.received and task.received > self.date_to:
            return False
        if self.queue and self.queue.lower() not in (task.queue or "").lower():
            return False
        if self.is_orphan is not None and task.is_orphan() != self.is_orphan:
            return False
        if self.has_retries is not None:
            has_retries = task.retries > 0
            if has_retries != self.has_retries:
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
                task.queue,
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
            if task.task_id not in self._tasks:
                self._task_order.append(task.task_id)
                if len(self._task_order) > self._max_tasks:
                    oldest_id = self._task_order.pop(0)
                    self._tasks.pop(oldest_id, None)
            self._tasks[task.task_id] = task
            self._update_daily_stats(task)

    def get_task(self, task_id: str) -> Optional[TaskResult]:
        with self._lock:
            return self._tasks.get(task_id)

    def get_tasks(
        self,
        task_filter: Optional[TaskFilter] = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "received",
        sort_desc: bool = True,
    ) -> Tuple[List[TaskResult], int]:
        with self._lock:
            tasks = list(self._tasks.values())

        if task_filter:
            tasks = [t for t in tasks if task_filter.matches(t)]

        def sort_key(t: TaskResult):
            val = getattr(t, sort_by, None)
            if val is None:
                return datetime.min if sort_desc else datetime.max
            return val

        tasks.sort(key=sort_key, reverse=sort_desc)
        total = len(tasks)
        start = (page - 1) * page_size
        end = start + page_size
        return tasks[start:end], total

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

    def _update_daily_stats(self, task: TaskResult) -> None:
        if task.state not in [TaskState.SUCCESS, TaskState.FAILURE, TaskState.RETRY, TaskState.REVOKED]:
            return
        date_str = (task.received or datetime.utcnow()).strftime("%Y-%m-%d")
        key = f"{date_str}:{task.name}"
        if key not in self._daily_stats:
            self._daily_stats[key] = DailyTaskStats(date=date_str, task_name=task.name)
        self._daily_stats[key].update(task.state, task.runtime)

    def get_daily_stats(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        task_name: Optional[str] = None,
    ) -> List[DailyTaskStats]:
        with self._lock:
            stats = list(self._daily_stats.values())
        if date_from:
            stats = [s for s in stats if s.date >= date_from]
        if date_to:
            stats = [s for s in stats if s.date <= date_to]
        if task_name:
            stats = [s for s in stats if task_name.lower() in s.task_name.lower()]
        return sorted(stats, key=lambda s: (s.date, s.task_name))

    def get_task_names(self) -> List[str]:
        with self._lock:
            return sorted(set(t.name for t in self._tasks.values() if t.name))

    def get_worker_names(self) -> List[str]:
        with self._lock:
            return sorted(set(t.worker for t in self._tasks.values() if t.worker))

    def get_queue_names(self) -> List[str]:
        with self._lock:
            return sorted(set(t.queue for t in self._tasks.values() if t.queue))

    def get_stats_summary(self) -> Dict[str, Any]:
        with self._lock:
            tasks = list(self._tasks.values())
        total = len(tasks)
        by_state = {}
        for state in TaskState:
            by_state[state.value] = sum(1 for t in tasks if t.state == state)
        orphans = sum(1 for t in tasks if t.is_orphan())
        with_retries = sum(1 for t in tasks if t.retries > 0)
        runtimes = [t.runtime for t in tasks if t.runtime is not None]
        avg_runtime = sum(runtimes) / len(runtimes) if runtimes else 0.0
        return {
            "total": total,
            "by_state": by_state,
            "orphans": orphans,
            "with_retries": with_retries,
            "avg_runtime": avg_runtime,
        }


class WorkerRegistry:
    def __init__(self, heartbeat_timeout: int = 30):
        self._workers: Dict[str, WorkerInfo] = {}
        self._lock = threading.RLock()
        self._heartbeat_timeout = heartbeat_timeout

    def update_worker(self, hostname: str, **kwargs) -> WorkerInfo:
        with self._lock:
            if hostname not in self._workers:
                self._workers[hostname] = WorkerInfo(hostname=hostname)
            worker = self._workers[hostname]
            for key, value in kwargs.items():
                if hasattr(worker, key):
                    setattr(worker, key, value)
            worker.last_heartbeat = datetime.utcnow()
            return worker

    def get_worker(self, hostname: str) -> Optional[WorkerInfo]:
        with self._lock:
            return self._workers.get(hostname)

    def get_all_workers(self) -> List[WorkerInfo]:
        with self._lock:
            return list(self._workers.values())

    def get_healthy_workers(self) -> List[WorkerInfo]:
        return [w for w in self.get_all_workers() if w.is_healthy()]

    def mark_worker_offline(self, hostname: str) -> None:
        with self._lock:
            if hostname in self._workers:
                self._workers[hostname].status = "offline"

    def remove_worker(self, hostname: str) -> bool:
        with self._lock:
            if hostname in self._workers:
                del self._workers[hostname]
                return True
            return False

    def check_heartbeats(self) -> List[str]:
        offline = []
        threshold = datetime.utcnow() - timedelta(seconds=self._heartbeat_timeout)
        with self._lock:
            for hostname, worker in self._workers.items():
                if worker.status == "online" and (
                    worker.last_heartbeat is None or worker.last_heartbeat < threshold
                ):
                    worker.status = "offline"
                    offline.append(hostname)
        return offline

    def get_summary(self) -> Dict[str, Any]:
        workers = self.get_all_workers()
        healthy = [w for w in workers if w.is_healthy()]
        return {
            "total": len(workers),
            "online": len(healthy),
            "offline": len(workers) - len(healthy),
            "workers": [w.to_dict() for w in workers],
        }


class WebSocketConnection:
    def __init__(self, connection_id: str):
        self.connection_id = connection_id
        self.subscriptions: List[str] = []
        self.filters: Optional[TaskFilter] = None
        self.created_at = datetime.utcnow()
        self._queue: asyncio.Queue = asyncio.Queue()
        self._closed = False

    async def send(self, message: Dict[str, Any]) -> None:
        if not self._closed:
            await self._queue.put(message)

    async def receive(self) -> Optional[Dict[str, Any]]:
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

    def remove_connection(self, connection_id: str) -> None:
        with self._lock:
            self._connections.pop(connection_id, None)

    def get_connection(self, connection_id: str) -> Optional[WebSocketConnection]:
        with self._lock:
            return self._connections.get(connection_id)

    def get_all_connections(self) -> List[WebSocketConnection]:
        with self._lock:
            return [c for c in self._connections.values() if not c.is_closed]

    async def broadcast(self, message: Dict[str, Any], event_type: str = "update") -> None:
        message_with_type = {"type": event_type, "data": message}
        connections = self.get_all_connections()
        tasks = [conn.send(message_with_type) for conn in connections]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def broadcast_task_update(self, task: TaskResult) -> None:
        await self.broadcast(task.to_dict(), event_type="task_update")

    async def broadcast_worker_update(self, worker: WorkerInfo) -> None:
        await self.broadcast(worker.to_dict(), event_type="worker_update")

    def connection_count(self) -> int:
        return len(self.get_all_connections())


class CeleryEventProcessor:
    def __init__(self, storage: TaskStorage, worker_registry: WorkerRegistry):
        self._storage = storage
        self._worker_registry = worker_registry
        self._event_handlers: Dict[str, Any] = {}
        self._callbacks: List[Any] = []
        self._setup_handlers()

    def _setup_handlers(self) -> None:
        self._event_handlers = {
            "task-sent": self._handle_task_sent,
            "task-received": self._handle_task_received,
            "task-started": self._handle_task_started,
            "task-succeeded": self._handle_task_succeeded,
            "task-failed": self._handle_task_failed,
            "task-rejected": self._handle_task_failed,
            "task-revoked": self._handle_task_revoked,
            "task-retried": self._handle_task_retried,
            "worker-online": self._handle_worker_online,
            "worker-offline": self._handle_worker_offline,
            "worker-heartbeat": self._handle_worker_heartbeat,
        }

    def add_callback(self, callback) -> None:
        self._callbacks.append(callback)

    def _notify_callbacks(self, event_type: str, data: Any) -> None:
        for callback in self._callbacks:
            try:
                callback(event_type, data)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    def process_event(self, event: Dict[str, Any]) -> Optional[Any]:
        event_type = event.get("type", "")
        handler = self._event_handlers.get(event_type)
        if handler:
            return handler(event)
        return None

    def _get_or_create_task(self, task_id: str, name: str = "") -> TaskResult:
        task = self._storage.get_task(task_id)
        if task is None:
            task = TaskResult(task_id=task_id, name=name, state=TaskState.PENDING)
        return task

    def _handle_task_sent(self, event: Dict[str, Any]) -> TaskResult:
        task_id = event.get("uuid", str(uuid.uuid4()))
        task = self._get_or_create_task(task_id, event.get("name", ""))
        task.name = event.get("name", task.name)
        task.state = TaskState.PENDING
        task.args = str(event.get("args", ""))
        task.kwargs = str(event.get("kwargs", ""))
        task.eta = self._parse_datetime(event.get("eta"))
        task.expires = self._parse_datetime(event.get("expires"))
        task.queue = event.get("queue")
        task.exchange = event.get("exchange")
        task.routing_key = event.get("routing_key")
        task.parent_id = event.get("parent_id")
        task.root_id = event.get("root_id")
        task.retries = event.get("retries", 0)
        task.timestamp = datetime.utcnow()
        self._storage.save_task(task)
        self._notify_callbacks("task_update", task)
        return task

    def _handle_task_received(self, event: Dict[str, Any]) -> TaskResult:
        task_id = event.get("uuid", str(uuid.uuid4()))
        task = self._get_or_create_task(task_id, event.get("name", ""))
        task.name = event.get("name", task.name)
        task.state = TaskState.RECEIVED
        task.received = datetime.utcnow()
        task.worker = event.get("hostname")
        task.args = str(event.get("args", task.args or ""))
        task.kwargs = str(event.get("kwargs", task.kwargs or ""))
        task.eta = self._parse_datetime(event.get("eta"))
        task.expires = self._parse_datetime(event.get("expires"))
        task.queue = event.get("queue", task.queue)
        task.retries = event.get("retries", task.retries)
        task.parent_id = event.get("parent_id", task.parent_id)
        task.root_id = event.get("root_id", task.root_id)
        task.clock = event.get("clock")
        task.timestamp = datetime.utcnow()
        self._storage.save_task(task)
        self._notify_callbacks("task_update", task)
        return task

    def _handle_task_started(self, event: Dict[str, Any]) -> TaskResult:
        task_id = event.get("uuid", str(uuid.uuid4()))
        task = self._get_or_create_task(task_id)
        task.state = TaskState.STARTED
        task.started = datetime.utcnow()
        task.worker = event.get("hostname", task.worker)
        task.pid = event.get("pid")
        task.clock = event.get("clock", task.clock)
        task.timestamp = datetime.utcnow()
        self._storage.save_task(task)
        if task.worker:
            worker = self._worker_registry.get_worker(task.worker)
            if worker:
                worker.active_tasks += 1
        self._notify_callbacks("task_update", task)
        return task

    def _handle_task_succeeded(self, event: Dict[str, Any]) -> TaskResult:
        task_id = event.get("uuid", str(uuid.uuid4()))
        task = self._get_or_create_task(task_id)
        task.state = TaskState.SUCCESS
        task.succeeded = datetime.utcnow()
        task.result = str(event.get("result", ""))
        task.runtime = event.get("runtime")
        task.worker = event.get("hostname", task.worker)
        task.clock = event.get("clock", task.clock)
        task.timestamp = datetime.utcnow()
        self._storage.save_task(task)
        if task.worker:
            worker = self._worker_registry.get_worker(task.worker)
            if worker:
                worker.active_tasks = max(0, worker.active_tasks - 1)
                worker.processed_tasks += 1
        self._notify_callbacks("task_update", task)
        return task

    def _handle_task_failed(self, event: Dict[str, Any]) -> TaskResult:
        task_id = event.get("uuid", str(uuid.uuid4()))
        task = self._get_or_create_task(task_id)
        task.state = TaskState.FAILURE
        task.failed = datetime.utcnow()
        task.result = str(event.get("exception", ""))
        task.traceback = event.get("traceback", "")
        task.worker = event.get("hostname", task.worker)
        task.clock = event.get("clock", task.clock)
        task.timestamp = datetime.utcnow()
        self._storage.save_task(task)
        if task.worker:
            worker = self._worker_registry.get_worker(task.worker)
            if worker:
                worker.active_tasks = max(0, worker.active_tasks - 1)
                worker.failed_tasks += 1
        self._notify_callbacks("task_update", task)
        return task

    def _handle_task_revoked(self, event: Dict[str, Any]) -> TaskResult:
        task_id = event.get("uuid", str(uuid.uuid4()))
        task = self._get_or_create_task(task_id)
        task.state = TaskState.REVOKED
        task.revoked = datetime.utcnow()
        task.worker = event.get("hostname", task.worker)
        task.result = str(event.get("terminated", ""))
        task.clock = event.get("clock", task.clock)
        task.timestamp = datetime.utcnow()
        self._storage.save_task(task)
        if task.worker:
            worker = self._worker_registry.get_worker(task.worker)
            if worker:
                worker.active_tasks = max(0, worker.active_tasks - 1)
        self._notify_callbacks("task_update", task)
        return task

    def _handle_task_retried(self, event: Dict[str, Any]) -> TaskResult:
        task_id = event.get("uuid", str(uuid.uuid4()))
        task = self._get_or_create_task(task_id)
        task.state = TaskState.RETRY
        task.retried = datetime.utcnow()
        task.retries += 1
        task.result = str(event.get("exception", ""))
        task.traceback = event.get("traceback", "")
        task.worker = event.get("hostname", task.worker)
        task.clock = event.get("clock", task.clock)
        task.timestamp = datetime.utcnow()
        self._storage.save_task(task)
        self._notify_callbacks("task_update", task)
        return task

    def _handle_worker_online(self, event: Dict[str, Any]) -> WorkerInfo:
        hostname = event.get("hostname", "unknown")
        worker = self._worker_registry.update_worker(
            hostname,
            status="online",
            sw_ver=event.get("sw_ver"),
            sw_sys=event.get("sw_sys"),
            pid=event.get("pid"),
        )
        self._notify_callbacks("worker_update", worker)
        return worker

    def _handle_worker_offline(self, event: Dict[str, Any]) -> WorkerInfo:
        hostname = event.get("hostname", "unknown")
        self._worker_registry.mark_worker_offline(hostname)
        worker = self._worker_registry.get_worker(hostname)
        if worker:
            self._notify_callbacks("worker_update", worker)
            return worker
        return WorkerInfo(hostname=hostname, status="offline")

    def _handle_worker_heartbeat(self, event: Dict[str, Any]) -> WorkerInfo:
        hostname = event.get("hostname", "unknown")
        worker = self._worker_registry.update_worker(
            hostname,
            status="online",
            active_tasks=event.get("active", 0),
            processed_tasks=event.get("processed", 0),
            loadavg=event.get("loadavg"),
            clock=event.get("clock"),
        )
        self._notify_callbacks("worker_update", worker)
        return worker

    @staticmethod
    def _parse_datetime(value: Any) -> Optional[datetime]:
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
    def __init__(self, storage: TaskStorage, worker_registry: WorkerRegistry):
        self._storage = storage
        self._worker_registry = worker_registry

    def get_task(self, task_id: str) -> Optional[TaskResult]:
        return self._storage.get_task(task_id)

    def get_tasks(
        self,
        state: Optional[str] = None,
        name: Optional[str] = None,
        worker: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        search: Optional[str] = None,
        queue: Optional[str] = None,
        is_orphan: Optional[bool] = None,
        has_retries: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "received",
        sort_desc: bool = True,
    ) -> Tuple[List[TaskResult], int]:
        task_filter = TaskFilter(
            state=TaskState(state) if state else None,
            name=name,
            worker=worker,
            date_from=date_from,
            date_to=date_to,
            search=search,
            queue=queue,
            is_orphan=is_orphan,
            has_retries=has_retries,
        )
        return self._storage.get_tasks(
            task_filter=task_filter,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_desc=sort_desc,
        )

    def delete_task(self, task_id: str) -> bool:
        return self._storage.delete_task(task_id)

    def clear_tasks(self) -> int:
        return self._storage.clear_tasks()

    def get_stats(self) -> Dict[str, Any]:
        return self._storage.get_stats_summary()

    def get_daily_stats(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        task_name: Optional[str] = None,
    ) -> List[DailyTaskStats]:
        return self._storage.get_daily_stats(date_from, date_to, task_name)

    def get_task_names(self) -> List[str]:
        return self._storage.get_task_names()

    def get_worker_names(self) -> List[str]:
        return self._storage.get_worker_names()

    def get_queue_names(self) -> List[str]:
        return self._storage.get_queue_names()

    def get_orphan_tasks(self, page: int = 1, page_size: int = 20) -> Tuple[List[TaskResult], int]:
        return self.get_tasks(is_orphan=True, page=page, page_size=page_size)

    def get_retry_tasks(self, page: int = 1, page_size: int = 20) -> Tuple[List[TaskResult], int]:
        return self.get_tasks(has_retries=True, page=page, page_size=page_size)


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
            queues TEXT,
            concurrency INTEGER DEFAULT 0,
            prefetch_count INTEGER DEFAULT 0,
            pid INTEGER,
            sw_ver VARCHAR(50),
            sw_sys VARCHAR(50),
            loadavg TEXT
        )
        """

    def _migration_002_down(self) -> str:
        return "DROP TABLE IF EXISTS workers"

    def _migration_003_up(self) -> str:
        return """
        CREATE TABLE IF NOT EXISTS daily_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date VARCHAR(10),
            task_name VARCHAR(255),
            succeeded INTEGER DEFAULT 0,
            failed INTEGER DEFAULT 0,
            retried INTEGER DEFAULT 0,
            revoked INTEGER DEFAULT 0,
            total INTEGER DEFAULT 0,
            avg_runtime FLOAT DEFAULT 0.0,
            min_runtime FLOAT,
            max_runtime FLOAT,
            UNIQUE(date, task_name)
        )
        """

    def _migration_003_down(self) -> str:
        return "DROP TABLE IF EXISTS daily_stats"

    def _migration_004_up(self) -> str:
        return """
        CREATE INDEX IF NOT EXISTS idx_tasks_state ON tasks(state);
        CREATE INDEX IF NOT EXISTS idx_tasks_name ON tasks(name);
        CREATE INDEX IF NOT EXISTS idx_tasks_worker ON tasks(worker);
        CREATE INDEX IF NOT EXISTS idx_tasks_received ON tasks(received);
        CREATE INDEX IF NOT EXISTS idx_tasks_queue ON tasks(queue);
        """

    def _migration_004_down(self) -> str:
        return """
        DROP INDEX IF EXISTS idx_tasks_state;
        DROP INDEX IF EXISTS idx_tasks_name;
        DROP INDEX IF EXISTS idx_tasks_worker;
        DROP INDEX IF EXISTS idx_tasks_received;
        DROP INDEX IF EXISTS idx_tasks_queue;
        """

    def get_pending_migrations(self) -> List[Dict[str, Any]]:
        return [m for m in self._migrations if m["version"] not in self._applied]

    def apply_migration(self, migration: Dict[str, Any]) -> bool:
        try:
            sql = migration["up"]()
            logger.info(f"Applied migration {migration['version']}: {migration['description']}")
            self._applied.append(migration["version"])
            return True
        except Exception as e:
            logger.error(f"Failed to apply migration {migration['version']}: {e}")
            return False

    def run_migrations(self) -> int:
        pending = self.get_pending_migrations()
        applied_count = 0
        for migration in pending:
            if self.apply_migration(migration):
                applied_count += 1
        logger.info(f"Applied {applied_count} migrations")
        return applied_count

    def rollback_migration(self, version: str) -> bool:
        migration = next((m for m in self._migrations if m["version"] == version), None)
        if not migration:
            return False
        try:
            sql = migration["down"]()
            if version in self._applied:
                self._applied.remove(version)
            logger.info(f"Rolled back migration {version}")
            return True
        except Exception as e:
            logger.error(f"Failed to rollback migration {version}: {e}")
            return False


class KanchiMonitor:
    def __init__(
        self,
        max_tasks: int = 10000,
        heartbeat_timeout: int = 30,
        db_url: str = "sqlite:///kanchi.db",
    ):
        self._storage = TaskStorage(max_tasks=max_tasks)
        self._worker_registry = WorkerRegistry(heartbeat_timeout=heartbeat_timeout)
        self._ws_manager = WebSocketManager()
        self._event_processor = CeleryEventProcessor(self._storage, self._worker_registry)
        self._task_manager = TaskManager(self._storage, self._worker_registry)
        self._migration_manager = MigrationManager(db_url=db_url)
        self._running = False
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._setup_callbacks()

    def _setup_callbacks(self) -> None:
        self._event_processor.add_callback(self._on_event)

    def _on_event(self, event_type: str, data: Any) -> None:
        loop = None
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            pass
        if loop and loop.is_running():
            if event_type == "task_update" and isinstance(data, TaskResult):
                asyncio.ensure_future(self._ws_manager.broadcast_task_update(data))
            elif event_type == "worker_update" and isinstance(data, WorkerInfo):
                asyncio.ensure_future(self._ws_manager.broadcast_worker_update(data))

    def start(self) -> None:
        self._running = True
        self._migration_manager.run_migrations()
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_checker, daemon=True
        )
        self._heartbeat_thread.start()
        logger.info("Kanchi monitor started")

    def stop(self) -> None:
        self._running = False
        if self._heartbeat_thread:
            self._heartbeat_thread.join(timeout=5)
        logger.info("Kanchi monitor stopped")

    def _heartbeat_checker(self) -> None:
        while self._running:
            offline_workers = self._worker_registry.check_heartbeats()
            for hostname in offline_workers:
                logger.warning(f"Worker {hostname} went offline (heartbeat timeout)")
            time.sleep(10)

    def process_event(self, event: Dict[str, Any]) -> Optional[Any]:
        return self._event_processor.process_event(event)

    def get_task(self, task_id: str) -> Optional[TaskResult]:
        return self._task_manager.get_task(task_id)

    def get_tasks(self, **kwargs) -> Tuple[List[TaskResult], int]:
        return self._task_manager.get_tasks(**kwargs)

    def delete_task(self, task_id: str) -> bool:
        return self._task_manager.delete_task(task_id)

    def clear_tasks(self) -> int:
        return self._task_manager.clear_tasks()

    def get_stats(self) -> Dict[str, Any]:
        stats = self._task_manager.get_stats()
        stats["workers"] = self._worker_registry.get_summary()
        return stats

    def get_daily_stats(self, **kwargs) -> List[DailyTaskStats]:
        return self._task_manager.get_daily_stats(**kwargs)

    def get_workers(self) -> List[WorkerInfo]:
        return self._worker_registry.get_all_workers()

    def get_worker(self, hostname: str) -> Optional[WorkerInfo]:
        return self._worker_registry.get_worker(hostname)

    def get_task_names(self) -> List[str]:
        return self._task_manager.get_task_names()

    def get_worker_names(self) -> List[str]:
        return self._task_manager.get_worker_names()

    def get_queue_names(self) -> List[str]:
        return self._task_manager.get_queue_names()

    def get_orphan_tasks(self, **kwargs) -> Tuple[List[TaskResult], int]:
        return self._task_manager.get_orphan_tasks(**kwargs)

    def get_retry_tasks(self, **kwargs) -> Tuple[List[TaskResult], int]:
        return self._task_manager.get_retry_tasks(**kwargs)

    def create_websocket_connection(self) -> WebSocketConnection:
        connection_id = str(uuid.uuid4())
        connection = WebSocketConnection(connection_id)
        self._ws_manager.add_connection(connection)
        return connection

    def close_websocket_connection(self, connection_id: str) -> None:
        connection = self._ws_manager.get_connection(connection_id)
        if connection:
            connection.close()
        self._ws_manager.remove_connection(connection_id)

    async def handle_websocket_message(
        self, connection_id: str, message: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        connection = self._ws_manager.get_connection(connection_id)
        if not connection:
            return None

        msg_type = message.get("type", "")

        if msg_type == "subscribe":
            topics = message.get("topics", [])
            connection.subscriptions = topics
            return {"type": "subscribed", "topics": topics}

        elif msg_type == "filter":
            filter_data = message.get("filter", {})
            connection.filters = TaskFilter(
                state=TaskState(filter_data["state"]) if filter_data.get("state") else None,
                name=filter_data.get("name"),
                worker=filter_data.get("worker"),
                search=filter_data.get("search"),
                queue=filter_data.get("queue"),
            )
            return {"type": "filter_applied"}

        elif msg_type == "get_tasks":
            tasks, total = self.get_tasks(
                page=message.get("page", 1),
                page_size=message.get("page_size", 20),
            )
            return {
                "type": "tasks",
                "data": [t.to_dict() for t in tasks],
                "total": total,
            }

        elif msg_type == "get_stats":
            return {"type": "stats", "data": self.get_stats()}

        elif msg_type == "get_workers":
            workers = self.get_workers()
            return {
                "type": "workers",
                "data": [w.to_dict() for w in workers],
            }

        elif msg_type == "ping":
            return {"type": "pong", "timestamp": datetime.utcnow().isoformat()}

        return {"type": "error", "message": f"Unknown message type: {msg_type}"}

    @property
    def storage(self) -> TaskStorage:
        return self._storage

    @property
    def worker_registry(self) -> WorkerRegistry:
        return self._worker_registry

    @property
    def ws_manager(self) -> WebSocketManager:
        return self._ws_manager

    @property
    def task_manager(self) -> TaskManager:
        return self._task_manager

    @property
    def migration_manager(self) -> MigrationManager:
        return self._migration_manager


class TaskHistoryTracker:
    def __init__(self, storage: TaskStorage):
        self._storage = storage
        self._history: Dict[str, List[Dict[str, Any]]] = {}
        self._lock = threading.RLock()

    def record_state_change(self, task_id: str, old_state: Optional[TaskState], new_state: TaskState) -> None:
        with self._lock:
            if task_id not in self._history:
                self._history[task_id] = []
            self._history[task_id].append({
                "timestamp": datetime.utcnow().isoformat(),
                "old_state": old_state.value if old_state else None,
                "new_state": new_state.value,
            })

    def get_task_history(self, task_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            return self._history.get(task_id, []).copy()

    def clear_history(self, task_id: str) -> None:
        with self._lock:
            self._history.pop(task_id, None)


class RetryTracker:
    def __init__(self):
        self._retry_chains: Dict[str, List[str]] = {}
        self._lock = threading.RLock()

    def record_retry(self, original_task_id: str, retry_task_id: str) -> None:
        with self._lock:
            if original_task_id not in self._retry_chains:
                self._retry_chains[original_task_id] = []
            self._retry_chains[original_task_id].append(retry_task_id)

    def get_retry_chain(self, task_id: str) -> List[str]:
        with self._lock:
            return self._retry_chains.get(task_id, []).copy()

    def get_retry_count(self, task_id: str) -> int:
        with self._lock:
            return len(self._retry_chains.get(task_id, []))

    def find_original_task(self, retry_task_id: str) -> Optional[str]:
        with self._lock:
            for original_id, retries in self._retry_chains.items():
                if retry_task_id in retries:
                    return original_id
            return None


class OrphanDetector:
    def __init__(self, storage: TaskStorage):
        self._storage = storage

    def detect_orphans(self) -> List[TaskResult]:
        tasks, _ = self._storage.get_tasks(page_size=10000)
        task_ids = {t.task_id for t in tasks}
        orphans = []
        for task in tasks:
            if task.parent_id and task.parent_id not in task_ids:
                if task.state in [TaskState.FAILURE, TaskState.REVOKED]:
                    orphans.append(task)
        return orphans

    def is_orphan(self, task: TaskResult) -> bool:
        if not task.parent_id:
            return False
        parent = self._storage.get_task(task.parent_id)
        return parent is None and task.state in [TaskState.FAILURE, TaskState.REVOKED]


class SearchEngine:
    def __init__(self, storage: TaskStorage):
        self._storage = storage

    def full_text_search(self, query: str, page: int = 1, page_size: int = 20) -> Tuple[List[TaskResult], int]:
        task_filter = TaskFilter(search=query)
        return self._storage.get_tasks(task_filter=task_filter, page=page, page_size=page_size)

    def search_by_date_range(
        self,
        date_from: datetime,
        date_to: datetime,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[TaskResult], int]:
        task_filter = TaskFilter(date_from=date_from, date_to=date_to)
        return self._storage.get_tasks(task_filter=task_filter, page=page, page_size=page_size)

    def search_by_state(self, state: TaskState, page: int = 1, page_size: int = 20) -> Tuple[List[TaskResult], int]:
        task_filter = TaskFilter(state=state)
        return self._storage.get_tasks(task_filter=task_filter, page=page, page_size=page_size)

    def advanced_search(
        self,
        query: Optional[str] = None,
        state: Optional[TaskState] = None,
        name: Optional[str] = None,
        worker: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        queue: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[TaskResult], int]:
        task_filter = TaskFilter(
            search=query,
            state=state,
            name=name,
            worker=worker,
            date_from=date_from,
            date_to=date_to,
            queue=queue,
        )
        return self._storage.get_tasks(task_filter=task_filter, page=page, page_size=page_size)


def create_monitor(
    max_tasks: int = 10000,
    heartbeat_timeout: int = 30,
    db_url: str = "sqlite:///kanchi.db",
) -> KanchiMonitor:
    monitor = KanchiMonitor(
        max_tasks=max_tasks,
        heartbeat_timeout=heartbeat_timeout,
        db_url=db_url,
    )
    return monitor


def simulate_celery_events(monitor: KanchiMonitor, num_tasks: int = 5) -> None:
    workers = ["worker1@host1", "worker2@host2", "worker3@host3"]
    task_names = [
        "myapp.tasks.send_email",
        "myapp.tasks.process_payment",
        "myapp.tasks.generate_report",
        "myapp.tasks.sync_data",
        "myapp.tasks.cleanup",
    ]
    queues = ["default", "high_priority", "low_priority"]

    for worker in workers:
        monitor.process_event({
            "type": "worker-online",
            "hostname": worker,
            "sw_ver": "5.2.0",
            "sw_sys": "Linux",
            "pid": 12345,
        })

    for i in range(num_tasks):
        task_id = str(uuid.uuid4())
        worker = workers[i % len(workers)]
        task_name = task_names[i % len(task_names)]
        queue = queues[i % len(queues)]

        monitor.process_event({
            "type": "task-received",
            "uuid": task_id,
            "name": task_name,
            "hostname": worker,
            "args": f"[{i}]",
            "kwargs": "{}",
            "queue": queue,
            "retries": 0,
        })

        monitor.process_event({
            "type": "task-started",
            "uuid": task_id,
            "hostname": worker,
        })

        if i % 4 == 0:
            monitor.process_event({
                "type": "task-failed",
                "uuid": task_id,
                "hostname": worker,
                "exception": "ValueError: Something went wrong",
                "traceback": "Traceback (most recent call last):\n  ...\nValueError: Something went wrong",
            })
        elif i % 5 == 0:
            monitor.process_event({
                "type": "task-retried",
                "uuid": task_id,
                "hostname": worker,
                "exception": "ConnectionError: Temporary failure",
            })
        else:
            monitor.process_event({
                "type": "task-succeeded",
                "uuid": task_id,
                "hostname": worker,
                "result": f"Result for task {i}",
                "runtime": 0.5 + (i * 0.1),
            })

    for worker in workers:
        monitor.process_event({
            "type": "worker-heartbeat",
            "hostname": worker,
            "active": 2,
            "processed": 100 + workers.index(worker) * 50,
            "loadavg": [0.5, 0.3, 0.2],
        })


if __name__ == "__main__":
    monitor = create_monitor(max_tasks=1000)
    monitor.start()

    print("Simulating Celery events...")
    simulate_celery_events(monitor, num_tasks=20)

    print("\n=== Task Statistics ===")
    stats = monitor.get_stats()
    print(json.dumps(stats, indent=2, default=str))

    print("\n=== Recent Tasks ===")
    tasks, total = monitor.get_tasks(page=1, page_size=5)
    print(f"Total tasks: {total}")
    for task in tasks:
        print(f"  [{task.state.value}] {task.name} ({task.task_id[:8]}...) - Worker: {task.worker}")

    print("\n=== Workers ===")
    workers = monitor.get_workers()
    for worker in workers:
        print(f"  {worker.hostname}: {worker.status} (active: {worker.active_tasks}, processed: {worker.processed_tasks})")

    print("\n=== Daily Stats ===")
    daily_stats = monitor.get_daily_stats()
    for stat in daily_stats[:5]:
        print(f"  {stat.date} - {stat.task_name}: succeeded={stat.succeeded}, failed={stat.failed}")

    print("\n=== Failed Tasks ===")
    failed_tasks, failed_total = monitor.get_tasks(state="FAILURE")
    print(f"Total failed tasks: {failed_total}")
    for task in failed_tasks:
        print(f"  {task.name}: {task.result}")

    print("\n=== Search Results ===")
    search_engine = SearchEngine(monitor.storage)
    results, count = search_engine.full_text_search("email")
    print(f"Tasks matching 'email': {count}")

    print("\n=== Task Names ===")
    task_names = monitor.get_task_names()
    print(f"Unique task names: {task_names}")

    print("\n=== Queue Names ===")
    queue_names = monitor.get_queue_names()
    print(f"Queues: {queue_names}")

    print("\n=== Retry Tasks ===")
    retry_tasks, retry_total = monitor.get_retry_tasks()
    print(f"Tasks with retries: {retry_total}")

    print("\n=== Migration Status ===")
    pending = monitor.migration_manager.get_pending_migrations()
    print(f"Pending migrations: {len(pending)}")
    applied = monitor.migration_manager._applied
    print(f"Applied migrations: {applied}")

    monitor.stop()
    print("\nKanchi monitor stopped.")