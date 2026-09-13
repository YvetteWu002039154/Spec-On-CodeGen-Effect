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
            try:
                data["state"] = TaskState(data["state"])
            except ValueError:
                data["state"] = TaskState.PENDING
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)


@dataclass
class WorkerInfo:
    hostname: str
    status: str = "online"
    active_tasks: int = 0
    processed_tasks: int = 0
    failed_tasks: int = 0
    load_avg: Optional[List[float]] = None
    heartbeat_expires: Optional[float] = None
    last_heartbeat: Optional[datetime] = None
    queues: List[str] = field(default_factory=list)
    concurrency: Optional[int] = None
    pool: Optional[str] = None
    sw_ver: Optional[str] = None
    sw_sys: Optional[str] = None
    pid: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if d.get("last_heartbeat") and isinstance(d["last_heartbeat"], datetime):
            d["last_heartbeat"] = d["last_heartbeat"].isoformat()
        return d

    def is_alive(self) -> bool:
        if self.heartbeat_expires:
            return time.time() < self.heartbeat_expires
        if self.last_heartbeat:
            return (datetime.utcnow() - self.last_heartbeat).total_seconds() < 30
        return self.status == "online"


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


class TaskFilter:
    def __init__(
        self,
        state: Optional[str] = None,
        name: Optional[str] = None,
        worker: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        search: Optional[str] = None,
        task_id: Optional[str] = None,
        parent_id: Optional[str] = None,
        root_id: Optional[str] = None,
        queue: Optional[str] = None,
        has_retries: Optional[bool] = None,
        is_orphan: Optional[bool] = None,
    ):
        self.state = state
        self.name = name
        self.worker = worker
        self.date_from = date_from
        self.date_to = date_to
        self.search = search
        self.task_id = task_id
        self.parent_id = parent_id
        self.root_id = root_id
        self.queue = queue
        self.has_retries = has_retries
        self.is_orphan = is_orphan

    def matches(self, task: TaskResult) -> bool:
        if self.state and task.state.value != self.state:
            return False
        if self.name and self.name.lower() not in (task.name or "").lower():
            return False
        if self.worker and self.worker.lower() not in (task.worker or "").lower():
            return False
        if self.task_id and task.task_id != self.task_id:
            return False
        if self.parent_id and task.parent_id != self.parent_id:
            return False
        if self.root_id and task.root_id != self.root_id:
            return False
        if self.queue and task.queue != self.queue:
            return False
        if self.has_retries is not None:
            if self.has_retries and task.retries == 0:
                return False
            if not self.has_retries and task.retries > 0:
                return False
        task_time = task.received or task.timestamp
        if self.date_from and task_time:
            if task_time < self.date_from:
                return False
        if self.date_to and task_time:
            if task_time > self.date_to:
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


class TaskStore:
    def __init__(self, max_tasks: int = 10000):
        self._tasks: Dict[str, TaskResult] = {}
        self._task_order: List[str] = []
        self._max_tasks = max_tasks
        self._lock = threading.RLock()
        self._daily_stats: Dict[str, DailyTaskStats] = {}
        self._retry_map: Dict[str, List[str]] = {}

    def add_or_update(self, task: TaskResult) -> None:
        with self._lock:
            is_new = task.task_id not in self._tasks
            self._tasks[task.task_id] = task
            if is_new:
                self._task_order.append(task.task_id)
                if len(self._task_order) > self._max_tasks:
                    oldest_id = self._task_order.pop(0)
                    self._tasks.pop(oldest_id, None)
            self._update_daily_stats(task)
            if task.parent_id:
                if task.parent_id not in self._retry_map:
                    self._retry_map[task.parent_id] = []
                if task.task_id not in self._retry_map[task.parent_id]:
                    self._retry_map[task.parent_id].append(task.task_id)

    def get(self, task_id: str) -> Optional[TaskResult]:
        with self._lock:
            return self._tasks.get(task_id)

    def get_all(self) -> List[TaskResult]:
        with self._lock:
            return [self._tasks[tid] for tid in reversed(self._task_order) if tid in self._tasks]

    def filter_tasks(
        self,
        task_filter: Optional[TaskFilter] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[TaskResult], int]:
        with self._lock:
            all_tasks = [self._tasks[tid] for tid in reversed(self._task_order) if tid in self._tasks]
            if task_filter:
                all_tasks = [t for t in all_tasks if task_filter.matches(t)]
            total = len(all_tasks)
            start = (page - 1) * page_size
            end = start + page_size
            return all_tasks[start:end], total

    def delete(self, task_id: str) -> bool:
        with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
                self._task_order.remove(task_id)
                return True
            return False

    def clear(self) -> None:
        with self._lock:
            self._tasks.clear()
            self._task_order.clear()

    def count(self) -> int:
        with self._lock:
            return len(self._tasks)

    def get_stats(self) -> Dict[str, int]:
        with self._lock:
            stats = {state.value: 0 for state in TaskState}
            for task in self._tasks.values():
                stats[task.state.value] = stats.get(task.state.value, 0) + 1
            stats["total"] = len(self._tasks)
            return stats

    def get_daily_stats(self, days: int = 7) -> List[DailyTaskStats]:
        with self._lock:
            result = []
            today = datetime.utcnow().date()
            for i in range(days - 1, -1, -1):
                date = today - timedelta(days=i)
                date_str = date.isoformat()
                if date_str in self._daily_stats:
                    result.append(self._daily_stats[date_str])
                else:
                    result.append(DailyTaskStats(date=date_str))
            return result

    def _update_daily_stats(self, task: TaskResult) -> None:
        task_time = task.succeeded or task.failed or task.received or task.timestamp
        if not task_time:
            task_time = datetime.utcnow()
        date_str = task_time.date().isoformat()
        if date_str not in self._daily_stats:
            self._daily_stats[date_str] = DailyTaskStats(date=date_str)
        stats = self._daily_stats[date_str]
        if task.state == TaskState.SUCCESS:
            stats.succeeded += 1
        elif task.state == TaskState.FAILURE:
            stats.failed += 1
        elif task.state == TaskState.RETRY:
            stats.retried += 1
        elif task.state == TaskState.REVOKED:
            stats.revoked += 1
        stats.total = stats.succeeded + stats.failed + stats.retried + stats.revoked

    def get_retries_for_task(self, task_id: str) -> List[TaskResult]:
        with self._lock:
            retry_ids = self._retry_map.get(task_id, [])
            return [self._tasks[tid] for tid in retry_ids if tid in self._tasks]

    def get_orphan_tasks(self) -> List[TaskResult]:
        with self._lock:
            orphans = []
            for task in self._tasks.values():
                if task.parent_id and task.parent_id not in self._tasks:
                    orphans.append(task)
            return orphans

    def get_task_names(self) -> List[str]:
        with self._lock:
            names = set()
            for task in self._tasks.values():
                if task.name:
                    names.add(task.name)
            return sorted(list(names))

    def get_queues(self) -> List[str]:
        with self._lock:
            queues = set()
            for task in self._tasks.values():
                if task.queue:
                    queues.add(task.queue)
            return sorted(list(queues))


class WorkerStore:
    def __init__(self):
        self._workers: Dict[str, WorkerInfo] = {}
        self._lock = threading.RLock()

    def add_or_update(self, worker: WorkerInfo) -> None:
        with self._lock:
            self._workers[worker.hostname] = worker

    def get(self, hostname: str) -> Optional[WorkerInfo]:
        with self._lock:
            return self._workers.get(hostname)

    def get_all(self) -> List[WorkerInfo]:
        with self._lock:
            return list(self._workers.values())

    def get_active_workers(self) -> List[WorkerInfo]:
        with self._lock:
            return [w for w in self._workers.values() if w.is_alive()]

    def update_heartbeat(self, hostname: str, expires: float) -> None:
        with self._lock:
            if hostname in self._workers:
                self._workers[hostname].heartbeat_expires = expires
                self._workers[hostname].last_heartbeat = datetime.utcnow()
                self._workers[hostname].status = "online"

    def mark_offline(self, hostname: str) -> None:
        with self._lock:
            if hostname in self._workers:
                self._workers[hostname].status = "offline"

    def remove(self, hostname: str) -> bool:
        with self._lock:
            if hostname in self._workers:
                del self._workers[hostname]
                return True
            return False

    def count(self) -> int:
        with self._lock:
            return len(self._workers)

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            active = sum(1 for w in self._workers.values() if w.is_alive())
            total_active_tasks = sum(w.active_tasks for w in self._workers.values())
            total_processed = sum(w.processed_tasks for w in self._workers.values())
            return {
                "total": len(self._workers),
                "active": active,
                "offline": len(self._workers) - active,
                "total_active_tasks": total_active_tasks,
                "total_processed": total_processed,
            }


class WebSocketConnection:
    def __init__(self, connection_id: str, filters: Optional[Dict[str, Any]] = None):
        self.connection_id = connection_id
        self.filters = filters or {}
        self.created_at = datetime.utcnow()
        self._queue: asyncio.Queue = asyncio.Queue()
        self._closed = False

    async def send(self, message: Dict[str, Any]) -> None:
        if not self._closed:
            await self._queue.put(message)

    async def receive(self) -> Optional[Dict[str, Any]]:
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
        self._lock = asyncio.Lock()

    async def connect(self, connection_id: Optional[str] = None, filters: Optional[Dict[str, Any]] = None) -> WebSocketConnection:
        async with self._lock:
            if not connection_id:
                connection_id = str(uuid.uuid4())
            conn = WebSocketConnection(connection_id, filters)
            self._connections[connection_id] = conn
            logger.info(f"WebSocket connected: {connection_id}")
            return conn

    async def disconnect(self, connection_id: str) -> None:
        async with self._lock:
            if connection_id in self._connections:
                self._connections[connection_id].close()
                del self._connections[connection_id]
                logger.info(f"WebSocket disconnected: {connection_id}")

    async def broadcast(self, message: Dict[str, Any]) -> None:
        async with self._lock:
            connections = list(self._connections.values())
        for conn in connections:
            if not conn.is_closed:
                try:
                    await conn.send(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to {conn.connection_id}: {e}")

    async def send_to(self, connection_id: str, message: Dict[str, Any]) -> bool:
        async with self._lock:
            conn = self._connections.get(connection_id)
        if conn and not conn.is_closed:
            await conn.send(message)
            return True
        return False

    def count(self) -> int:
        return len(self._connections)


class CeleryEventHandler:
    def __init__(self, task_store: TaskStore, worker_store: WorkerStore):
        self._task_store = task_store
        self._worker_store = worker_store
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
        self._callbacks: List[Any] = []

    def add_callback(self, callback) -> None:
        self._callbacks.append(callback)

    def handle_event(self, event: Dict[str, Any]) -> Optional[TaskResult]:
        event_type = event.get("type", "")
        handler = self._event_handlers.get(event_type)
        if handler:
            return handler(event)
        return None

    def _get_or_create_task(self, task_id: str) -> TaskResult:
        task = self._task_store.get(task_id)
        if not task:
            task = TaskResult(
                task_id=task_id,
                name=task_id,
                state=TaskState.PENDING,
            )
        return task

    def _handle_task_sent(self, event: Dict[str, Any]) -> TaskResult:
        task_id = event.get("uuid", str(uuid.uuid4()))
        task = self._get_or_create_task(task_id)
        task.name = event.get("name", task.name)
        task.state = TaskState.PENDING
        task.args = str(event.get("args", ""))
        task.kwargs = str(event.get("kwargs", ""))
        task.queue = event.get("queue")
        task.exchange = event.get("exchange")
        task.routing_key = event.get("routing_key")
        task.parent_id = event.get("parent_id")
        task.root_id = event.get("root_id")
        task.expires = self._parse_datetime(event.get("expires"))
        task.eta = self._parse_datetime(event.get("eta"))
        task.timestamp = datetime.utcnow()
        self._task_store.add_or_update(task)
        self._notify_callbacks("task-sent", task)
        return task

    def _handle_task_received(self, event: Dict[str, Any]) -> TaskResult:
        task_id = event.get("uuid", str(uuid.uuid4()))
        task = self._get_or_create_task(task_id)
        task.name = event.get("name", task.name)
        task.state = TaskState.RECEIVED
        task.worker = event.get("hostname")
        task.args = str(event.get("args", task.args or ""))
        task.kwargs = str(event.get("kwargs", task.kwargs or ""))
        task.received = datetime.utcnow()
        task.retries = event.get("retries", task.retries)
        task.parent_id = event.get("parent_id", task.parent_id)
        task.root_id = event.get("root_id", task.root_id)
        task.eta = self._parse_datetime(event.get("eta")) or task.eta
        task.expires = self._parse_datetime(event.get("expires")) or task.expires
        task.clock = event.get("clock")
        self._task_store.add_or_update(task)
        self._notify_callbacks("task-received", task)
        return task

    def _handle_task_started(self, event: Dict[str, Any]) -> TaskResult:
        task_id = event.get("uuid", str(uuid.uuid4()))
        task = self._get_or_create_task(task_id)
        task.state = TaskState.STARTED
        task.worker = event.get("hostname", task.worker)
        task.started = datetime.utcnow()
        task.pid = event.get("pid")
        self._task_store.add_or_update(task)
        self._update_worker_active_tasks(task.worker, 1)
        self._notify_callbacks("task-started", task)
        return task

    def _handle_task_succeeded(self, event: Dict[str, Any]) -> TaskResult:
        task_id = event.get("uuid", str(uuid.uuid4()))
        task = self._get_or_create_task(task_id)
        task.state = TaskState.SUCCESS
        task.worker = event.get("hostname", task.worker)
        task.succeeded = datetime.utcnow()
        task.result = str(event.get("result", ""))
        task.runtime = event.get("runtime")
        self._task_store.add_or_update(task)
        self._update_worker_active_tasks(task.worker, -1)
        self._update_worker_processed(task.worker)
        self._notify_callbacks("task-succeeded", task)
        return task

    def _handle_task_failed(self, event: Dict[str, Any]) -> TaskResult:
        task_id = event.get("uuid", str(uuid.uuid4()))
        task = self._get_or_create_task(task_id)
        task.state = TaskState.FAILURE
        task.worker = event.get("hostname", task.worker)
        task.failed = datetime.utcnow()
        task.traceback = event.get("traceback", "")
        task.result = str(event.get("exception", ""))
        self._task_store.add_or_update(task)
        self._update_worker_active_tasks(task.worker, -1)
        self._update_worker_failed(task.worker)
        self._notify_callbacks("task-failed", task)
        return task

    def _handle_task_revoked(self, event: Dict[str, Any]) -> TaskResult:
        task_id = event.get("uuid", str(uuid.uuid4()))
        task = self._get_or_create_task(task_id)
        task.state = TaskState.REVOKED
        task.worker = event.get("hostname", task.worker)
        task.revoked = datetime.utcnow()
        task.result = event.get("terminated", "")
        self._task_store.add_or_update(task)
        self._notify_callbacks("task-revoked", task)
        return task

    def _handle_task_retried(self, event: Dict[str, Any]) -> TaskResult:
        task_id = event.get("uuid", str(uuid.uuid4()))
        task = self._get_or_create_task(task_id)
        task.state = TaskState.RETRY
        task.worker = event.get("hostname", task.worker)
        task.retried = datetime.utcnow()
        task.retries = task.retries + 1
        task.traceback = event.get("traceback", "")
        self._task_store.add_or_update(task)
        self._notify_callbacks("task-retried", task)
        return task

    def _handle_worker_online(self, event: Dict[str, Any]) -> WorkerInfo:
        hostname = event.get("hostname", "unknown")
        worker = self._worker_store.get(hostname) or WorkerInfo(hostname=hostname)
        worker.status = "online"
        worker.last_heartbeat = datetime.utcnow()
        worker.sw_ver = event.get("sw_ver")
        worker.sw_sys = event.get("sw_sys")
        self._worker_store.add_or_update(worker)
        self._notify_callbacks("worker-online", worker)
        return worker

    def _handle_worker_offline(self, event: Dict[str, Any]) -> WorkerInfo:
        hostname = event.get("hostname", "unknown")
        worker = self._worker_store.get(hostname) or WorkerInfo(hostname=hostname)
        worker.status = "offline"
        self._worker_store.add_or_update(worker)
        self._notify_callbacks("worker-offline", worker)
        return worker

    def _handle_worker_heartbeat(self, event: Dict[str, Any]) -> WorkerInfo:
        hostname = event.get("hostname", "unknown")
        worker = self._worker_store.get(hostname) or WorkerInfo(hostname=hostname)
        worker.status = "online"
        worker.last_heartbeat = datetime.utcnow()
        worker.heartbeat_expires = event.get("expires", time.time() + 30)
        worker.active_tasks = event.get("active", worker.active_tasks)
        worker.processed_tasks = event.get("processed", worker.processed_tasks)
        worker.load_avg = event.get("loadavg")
        worker.clock = event.get("clock")
        self._worker_store.add_or_update(worker)
        self._notify_callbacks("worker-heartbeat", worker)
        return worker

    def _update_worker_active_tasks(self, hostname: Optional[str], delta: int) -> None:
        if hostname:
            worker = self._worker_store.get(hostname)
            if worker:
                worker.active_tasks = max(0, worker.active_tasks + delta)
                self._worker_store.add_or_update(worker)

    def _update_worker_processed(self, hostname: Optional[str]) -> None:
        if hostname:
            worker = self._worker_store.get(hostname)
            if worker:
                worker.processed_tasks += 1
                self._worker_store.add_or_update(worker)

    def _update_worker_failed(self, hostname: Optional[str]) -> None:
        if hostname:
            worker = self._worker_store.get(hostname)
            if worker:
                worker.failed_tasks += 1
                self._worker_store.add_or_update(worker)

    def _notify_callbacks(self, event_type: str, data: Any) -> None:
        for callback in self._callbacks:
            try:
                callback(event_type, data)
            except Exception as e:
                logger.error(f"Error in event callback: {e}")

    @staticmethod
    def _parse_datetime(value: Any) -> Optional[datetime]:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, (int, float)):
            try:
                return datetime.utcfromtimestamp(value)
            except (ValueError, OSError):
                return None
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return None
        return None


class TaskSearchEngine:
    def __init__(self, task_store: TaskStore):
        self._task_store = task_store

    def search(
        self,
        query: Optional[str] = None,
        state: Optional[str] = None,
        name: Optional[str] = None,
        worker: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        queue: Optional[str] = None,
        has_retries: Optional[bool] = None,
        is_orphan: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[TaskResult], int]:
        task_filter = TaskFilter(
            state=state,
            name=name,
            worker=worker,
            date_from=date_from,
            date_to=date_to,
            search=query,
            queue=queue,
            has_retries=has_retries,
            is_orphan=is_orphan,
        )
        tasks, total = self._task_store.filter_tasks(task_filter, page, page_size)
        if is_orphan:
            orphan_ids = {t.task_id for t in self._task_store.get_orphan_tasks()}
            tasks = [t for t in tasks if t.task_id in orphan_ids]
            total = len(tasks)
        return tasks, total

    def get_task_detail(self, task_id: str) -> Optional[Dict[str, Any]]:
        task = self._task_store.get(task_id)
        if not task:
            return None
        detail = task.to_dict()
        retries = self._task_store.get_retries_for_task(task_id)
        detail["retry_tasks"] = [r.to_dict() for r in retries]
        detail["is_orphan"] = (
            task.parent_id is not None and
            self._task_store.get(task.parent_id) is None
        )
        return detail


class MigrationManager:
    def __init__(self, db_url: Optional[str] = None):
        self._db_url = db_url
        self._migrations: List[Dict[str, Any]] = []
        self._applied: List[str] = []

    def register_migration(self, version: str, description: str, up_sql: str, down_sql: str) -> None:
        self._migrations.append({
            "version": version,
            "description": description,
            "up_sql": up_sql,
            "down_sql": down_sql,
        })

    def get_pending_migrations(self) -> List[Dict[str, Any]]:
        return [m for m in self._migrations if m["version"] not in self._applied]

    def apply_migrations(self) -> List[str]:
        applied = []
        for migration in self.get_pending_migrations():
            logger.info(f"Applying migration {migration['version']}: {migration['description']}")
            self._applied.append(migration["version"])
            applied.append(migration["version"])
        return applied

    def rollback_migration(self, version: str) -> bool:
        if version in self._applied:
            self._applied.remove(version)
            logger.info(f"Rolled back migration {version}")
            return True
        return False

    def get_current_version(self) -> Optional[str]:
        if self._applied:
            return self._applied[-1]
        return None


class KanchiMonitor:
    def __init__(
        self,
        max_tasks: int = 10000,
        db_url: Optional[str] = None,
    ):
        self._task_store = TaskStore(max_tasks=max_tasks)
        self._worker_store = WorkerStore()
        self._event_handler = CeleryEventHandler(self._task_store, self._worker_store)
        self._ws_manager = WebSocketManager()
        self._search_engine = TaskSearchEngine(self._task_store)
        self._migration_manager = MigrationManager(db_url)
        self._running = False
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None
        self._setup_event_callbacks()
        self._setup_default_migrations()

    def _setup_event_callbacks(self) -> None:
        self._event_handler.add_callback(self._on_event)

    def _on_event(self, event_type: str, data: Any) -> None:
        if self._event_loop and self._event_loop.is_running():
            if isinstance(data, TaskResult):
                message = {
                    "type": event_type,
                    "task": data.to_dict(),
                    "timestamp": datetime.utcnow().isoformat(),
                }
            elif isinstance(data, WorkerInfo):
                message = {
                    "type": event_type,
                    "worker": data.to_dict(),
                    "timestamp": datetime.utcnow().isoformat(),
                }
            else:
                message = {
                    "type": event_type,
                    "data": str(data),
                    "timestamp": datetime.utcnow().isoformat(),
                }
            asyncio.run_coroutine_threadsafe(
                self._ws_manager.broadcast(message),
                self._event_loop
            )

    def _setup_default_migrations(self) -> None:
        self._migration_manager.register_migration(
            "001",
            "Create tasks table",
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id VARCHAR(255) PRIMARY KEY,
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
            """,
            "DROP TABLE IF EXISTS tasks",
        )
        self._migration_manager.register_migration(
            "002",
            "Create workers table",
            """
            CREATE TABLE IF NOT EXISTS workers (
                hostname VARCHAR(255) PRIMARY KEY,
                status VARCHAR(50),
                active_tasks INTEGER DEFAULT 0,
                processed_tasks INTEGER DEFAULT 0,
                failed_tasks INTEGER DEFAULT 0,
                last_heartbeat TIMESTAMP,
                concurrency INTEGER,
                pool VARCHAR(255),
                sw_ver VARCHAR(50),
                sw_sys VARCHAR(50),
                pid INTEGER
            )
            """,
            "DROP TABLE IF EXISTS workers",
        )
        self._migration_manager.register_migration(
            "003",
            "Create daily stats table",
            """
            CREATE TABLE IF NOT EXISTS daily_stats (
                date DATE PRIMARY KEY,
                succeeded INTEGER DEFAULT 0,
                failed INTEGER DEFAULT 0,
                retried INTEGER DEFAULT 0,
                revoked INTEGER DEFAULT 0,
                total INTEGER DEFAULT 0
            )
            """,
            "DROP TABLE IF EXISTS daily_stats",
        )

    def process_event(self, event: Dict[str, Any]) -> Optional[Any]:
        return self._event_handler.handle_event(event)

    def get_tasks(
        self,
        page: int = 1,
        page_size: int = 20,
        state: Optional[str] = None,
        name: Optional[str] = None,
        worker: Optional[str] = None,
        search: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        queue: Optional[str] = None,
        has_retries: Optional[bool] = None,
        is_orphan: Optional[bool] = None,
    ) -> Dict[str, Any]:
        tasks, total = self._search_engine.search(
            query=search,
            state=state,
            name=name,
            worker=worker,
            date_from=date_from,
            date_to=date_to,
            queue=queue,
            has_retries=has_retries,
            is_orphan=is_orphan,
            page=page,
            page_size=page_size,
        )
        return {
            "tasks": [t.to_dict() for t in tasks],
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": (total + page_size - 1) // page_size if page_size > 0 else 0,
        }

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self._search_engine.get_task_detail(task_id)

    def get_workers(self) -> List[Dict[str, Any]]:
        return [w.to_dict() for w in self._worker_store.get_all()]

    def get_worker(self, hostname: str) -> Optional[Dict[str, Any]]:
        worker = self._worker_store.get(hostname)
        if worker:
            return worker.to_dict()
        return None

    def get_stats(self) -> Dict[str, Any]:
        task_stats = self._task_store.get_stats()
        worker_stats = self._worker_store.get_stats()
        return {
            "tasks": task_stats,
            "workers": worker_stats,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def get_daily_stats(self, days: int = 7) -> List[Dict[str, Any]]:
        return [s.to_dict() for s in self._task_store.get_daily_stats(days)]

    def get_task_names(self) -> List[str]:
        return self._task_store.get_task_names()

    def get_queues(self) -> List[str]:
        return self._task_store.get_queues()

    def get_orphan_tasks(self) -> List[Dict[str, Any]]:
        return [t.to_dict() for t in self._task_store.get_orphan_tasks()]

    def delete_task(self, task_id: str) -> bool:
        return self._task_store.delete(task_id)

    def clear_tasks(self) -> None:
        self._task_store.clear()

    def run_migrations(self) -> List[str]:
        return self._migration_manager.apply_migrations()

    def get_migration_status(self) -> Dict[str, Any]:
        return {
            "current_version": self._migration_manager.get_current_version(),
            "pending": [m["version"] for m in self._migration_manager.get_pending_migrations()],
            "applied": self._migration_manager._applied,
        }

    async def start_websocket_server(self) -> None:
        self._event_loop = asyncio.get_event_loop()
        self._running = True
        logger.info("WebSocket server started")

    async def stop_websocket_server(self) -> None:
        self._running = False
        logger.info("WebSocket server stopped")

    async def connect_websocket(
        self,
        connection_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> WebSocketConnection:
        self._event_loop = asyncio.get_event_loop()
        conn = await self._ws_manager.connect(connection_id, filters)
        initial_message = {
            "type": "connected",
            "connection_id": conn.connection_id,
            "stats": self.get_stats(),
            "timestamp": datetime.utcnow().isoformat(),
        }
        await conn.send(initial_message)
        return conn

    async def disconnect_websocket(self, connection_id: str) -> None:
        await self._ws_manager.disconnect(connection_id)

    async def broadcast_message(self, message: Dict[str, Any]) -> None:
        await self._ws_manager.broadcast(message)

    def get_websocket_count(self) -> int:
        return self._ws_manager.count()

    @property
    def task_store(self) -> TaskStore:
        return self._task_store

    @property
    def worker_store(self) -> WorkerStore:
        return self._worker_store

    @property
    def event_handler(self) -> CeleryEventHandler:
        return self._event_handler

    @property
    def ws_manager(self) -> WebSocketManager:
        return self._ws_manager


class CeleryEventReceiver:
    def __init__(self, monitor: KanchiMonitor):
        self._monitor = monitor
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self, celery_app=None) -> None:
        self._running = True
        if celery_app:
            self._thread = threading.Thread(
                target=self._receive_events,
                args=(celery_app,),
                daemon=True,
            )
            self._thread.start()
            logger.info("Celery event receiver started")
        else:
            logger.warning("No Celery app provided, event receiver not started")

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Celery event receiver stopped")

    def _receive_events(self, celery_app) -> None:
        try:
            with celery_app.connection() as conn:
                recv = celery_app.events.Receiver(
                    conn,
                    handlers={"*": self._process_event},
                )
                recv.capture(limit=None, timeout=None, wakeup=True)
        except Exception as e:
            logger.error(f"Error receiving Celery events: {e}")

    def _process_event(self, event: Dict[str, Any]) -> None:
        try:
            self._monitor.process_event(event)
        except Exception as e:
            logger.error(f"Error processing event: {e}")

    def simulate_event(self, event: Dict[str, Any]) -> None:
        self._process_event(event)


class KanchiAPI:
    def __init__(self, monitor: KanchiMonitor):
        self._monitor = monitor

    def get_tasks(self, params: Dict[str, Any]) -> Dict[str, Any]:
        page = int(params.get("page", 1))
        page_size = int(params.get("page_size", 20))
        state = params.get("state")
        name = params.get("name")
        worker = params.get("worker")
        search = params.get("search")
        queue = params.get("queue")
        has_retries = params.get("has_retries")
        is_orphan = params.get("is_orphan")
        date_from = None
        date_to = None
        if params.get("date_from"):
            try:
                date_from = datetime.fromisoformat(params["date_from"])
            except ValueError:
                pass
        if params.get("date_to"):
            try:
                date_to = datetime.fromisoformat(params["date_to"])
            except ValueError:
                pass
        if has_retries is not None:
            has_retries = str(has_retries).lower() in ("true", "1", "yes")
        if is_orphan is not None:
            is_orphan = str(is_orphan).lower() in ("true", "1", "yes")
        return self._monitor.get_tasks(
            page=page,
            page_size=page_size,
            state=state,
            name=name,
            worker=worker,
            search=search,
            date_from=date_from,
            date_to=date_to,
            queue=queue,
            has_retries=has_retries,
            is_orphan=is_orphan,
        )

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self._monitor.get_task(task_id)

    def delete_task(self, task_id: str) -> Dict[str, Any]:
        success = self._monitor.delete_task(task_id)
        return {"success": success, "task_id": task_id}

    def get_workers(self) -> List[Dict[str, Any]]:
        return self._monitor.get_workers()

    def get_worker(self, hostname: str) -> Optional[Dict[str, Any]]:
        return self._monitor.get_worker(hostname)

    def get_stats(self) -> Dict[str, Any]:
        return self._monitor.get_stats()

    def get_daily_stats(self, days: int = 7) -> List[Dict[str, Any]]:
        return self._monitor.get_daily_stats(days)

    def get_task_names(self) -> List[str]:
        return self._monitor.get_task_names()

    def get_queues(self) -> List[str]:
        return self._monitor.get_queues()

    def get_orphan_tasks(self) -> List[Dict[str, Any]]:
        return self._monitor.get_orphan_tasks()

    def run_migrations(self) -> Dict[str, Any]:
        applied = self._monitor.run_migrations()
        return {"applied": applied, "count": len(applied)}

    def get_migration_status(self) -> Dict[str, Any]:
        return self._monitor.get_migration_status()


def create_monitor(max_tasks: int = 10000, db_url: Optional[str] = None) -> KanchiMonitor:
    monitor = KanchiMonitor(max_tasks=max_tasks, db_url=db_url)
    monitor.run_migrations()
    return monitor


def create_api(monitor: Optional[KanchiMonitor] = None) -> KanchiAPI:
    if monitor is None:
        monitor = create_monitor()
    return KanchiAPI(monitor)


if __name__ == "__main__":
    monitor = create_monitor()
    api = create_api(monitor)

    receiver = CeleryEventReceiver(monitor)

    test_events = [
        {
            "type": "worker-online",
            "hostname": "celery@worker1",
            "sw_ver": "5.2.0",
            "sw_sys": "Linux",
        },
        {
            "type": "worker-online",
            "hostname": "celery@worker2",
            "sw_ver": "5.2.0",
            "sw_sys": "Linux",
        },
        {
            "type": "task-received",
            "uuid": "task-001",
            "name": "myapp.tasks.send_email",
            "hostname": "celery@worker1",
            "args": "['user@example.com']",
            "kwargs": "{'subject': 'Hello'}",
            "retries": 0,
        },
        {
            "type": "task-started",
            "uuid": "task-001",
            "hostname": "celery@worker1",
        },
        {
            "type": "task-succeeded",
            "uuid": "task-001",
            "hostname": "celery@worker1",
            "result": "True",
            "runtime": 0.5,
        },
        {
            "type": "task-received",
            "uuid": "task-002",
            "name": "myapp.tasks.process_data",
            "hostname": "celery@worker2",
            "args": "[1, 2, 3]",
            "kwargs": "{}",
            "retries": 0,
        },
        {
            "type": "task-started",
            "uuid": "task-002",
            "hostname": "celery@worker2",
        },
        {
            "type": "task-failed",
            "uuid": "task-002",
            "hostname": "celery@worker2",
            "exception": "ValueError: Invalid data",
            "traceback": "Traceback (most recent call last):\n  ...\nValueError: Invalid data",
        },
        {
            "type": "task-received",
            "uuid": "task-003",
            "name": "myapp.tasks.process_data",
            "hostname": "celery@worker1",
            "args": "[1, 2, 3]",
            "kwargs": "{}",
            "retries": 1,
            "parent_id": "task-002",
        },
        {
            "type": "task-started",
            "uuid": "task-003",
            "hostname": "celery@worker1",
        },
        {
            "type": "task-succeeded",
            "uuid": "task-003",
            "hostname": "celery@worker1",
            "result": "processed",
            "runtime": 1.2,
        },
        {
            "type": "worker-heartbeat",
            "hostname": "celery@worker1",
            "active": 0,
            "processed": 2,
            "loadavg": [0.1, 0.2, 0.3],
            "expires": time.time() + 30,
        },
    ]

    print("Processing test events...")
    for event in test_events:
        receiver.simulate_event(event)

    print("\n=== Task Statistics ===")
    stats = api.get_stats()
    print(json.dumps(stats, indent=2))

    print("\n=== All Tasks ===")
    tasks = api.get_tasks({})
    print(f"Total tasks: {tasks['total']}")
    for task in tasks["tasks"]:
        print(f"  - {task['task_id']}: {task['name']} [{task['state']}]")

    print("\n=== Workers ===")
    workers = api.get_workers()
    for worker in workers:
        print(f"  - {worker['hostname']}: {worker['status']} (active: {worker['active_tasks']}, processed: {worker['processed_tasks']})")

    print("\n=== Daily Stats ===")
    daily_stats = api.get_daily_stats(7)
    for stat in daily_stats:
        if stat["total"] > 0:
            print(f"  {stat['date']}: succeeded={stat['succeeded']}, failed={stat['failed']}, total={stat['total']}")

    print("\n=== Task Detail (task-002) ===")
    task_detail = api.get_task("task-002")
    if task_detail:
        print(f"  Name: {task_detail['name']}")
        print(f"  State: {task_detail['state']}")
        print(f"  Retry tasks: {len(task_detail.get('retry_tasks', []))}")

    print("\n=== Filtering: Failed Tasks ===")
    failed_tasks = api.get_tasks({"state": "FAILURE"})
    print(f"Failed tasks: {failed_tasks['total']}")

    print("\n=== Filtering: Tasks with Retries ===")
    retry_tasks = api.get_tasks({"has_retries": "true"})
    print(f"Tasks with retries: {retry_tasks['total']}")

    print("\n=== Orphan Tasks ===")
    orphans = api.get_orphan_tasks()
    print(f"Orphan tasks: {len(orphans)}")

    print("\n=== Task Names ===")
    names = api.get_task_names()
    print(f"Unique task names: {names}")

    print("\n=== Migration Status ===")
    migration_status = api.get_migration_status()
    print(json.dumps(migration_status, indent=2))

    print("\n=== Search: 'email' ===")
    search_results = api.get_tasks({"search": "email"})
    print(f"Search results: {search_results['total']}")

    print("\nKanchi Monitor demo completed successfully!")