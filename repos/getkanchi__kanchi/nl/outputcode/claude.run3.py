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
    eta: Optional[datetime] = None
    expires: Optional[datetime] = None
    queue: Optional[str] = None
    exchange: Optional[str] = None
    routing_key: Optional[str] = None
    clock: Optional[int] = None
    client: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        for k, v in d.items():
            if isinstance(v, datetime):
                d[k] = v.isoformat() if v else None
            elif isinstance(v, TaskState):
                d[k] = v.value
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
    load_average: Optional[List[float]] = None
    heartbeat_expires: Optional[datetime] = None
    last_heartbeat: Optional[datetime] = None
    software_identity: Optional[str] = None
    software_version: Optional[str] = None
    software_sys: Optional[str] = None
    pid: Optional[int] = None
    clock: Optional[int] = None
    freq: Optional[float] = None
    queues: List[str] = field(default_factory=list)
    pool: Optional[Dict[str, Any]] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        for k, v in d.items():
            if isinstance(v, datetime):
                d[k] = v.isoformat() if v else None
        return d

    def is_alive(self) -> bool:
        if self.heartbeat_expires:
            return datetime.utcnow() < self.heartbeat_expires
        if self.last_heartbeat:
            return (datetime.utcnow() - self.last_heartbeat).total_seconds() < 30
        return self.status == "online"


@dataclass
class DailyTaskStats:
    date: str
    task_name: str
    succeeded: int = 0
    failed: int = 0
    retried: int = 0
    revoked: int = 0
    total: int = 0
    avg_runtime: Optional[float] = None
    min_runtime: Optional[float] = None
    max_runtime: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def update_runtime(self, runtime: float):
        if self.avg_runtime is None:
            self.avg_runtime = runtime
            self.min_runtime = runtime
            self.max_runtime = runtime
        else:
            count = self.succeeded
            if count > 0:
                self.avg_runtime = ((self.avg_runtime * (count - 1)) + runtime) / count
            self.min_runtime = min(self.min_runtime, runtime)
            self.max_runtime = max(self.max_runtime, runtime)


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
        parent_id: Optional[str] = None,
        root_id: Optional[str] = None,
        orphans_only: bool = False,
    ):
        self.state = state
        self.name = name
        self.worker = worker
        self.date_from = date_from
        self.date_to = date_to
        self.search = search
        self.queue = queue
        self.parent_id = parent_id
        self.root_id = root_id
        self.orphans_only = orphans_only

    def matches(self, task: TaskResult) -> bool:
        if self.state and task.state != self.state:
            return False
        if self.name and self.name.lower() not in (task.name or "").lower():
            return False
        if self.worker and self.worker.lower() not in (task.worker or "").lower():
            return False
        if self.date_from and task.received:
            if task.received < self.date_from:
                return False
        if self.date_to and task.received:
            if task.received > self.date_to:
                return False
        if self.queue and task.queue != self.queue:
            return False
        if self.parent_id and task.parent_id != self.parent_id:
            return False
        if self.root_id and task.root_id != self.root_id:
            return False
        if self.orphans_only and not task.is_orphan():
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
        self._lock = threading.RLock()
        self._max_tasks = max_tasks
        self._daily_stats: Dict[str, DailyTaskStats] = {}

    def save_task(self, task: TaskResult) -> TaskResult:
        with self._lock:
            task.updated_at = datetime.utcnow()
            self._tasks[task.task_id] = task
            self._update_daily_stats(task)
            self._enforce_limit()
            return task

    def get_task(self, task_id: str) -> Optional[TaskResult]:
        with self._lock:
            return self._tasks.get(task_id)

    def get_tasks(
        self,
        task_filter: Optional[TaskFilter] = None,
        limit: int = 100,
        offset: int = 0,
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
            return tasks[offset:offset + limit], total

    def delete_task(self, task_id: str) -> bool:
        with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
                return True
            return False

    def clear_tasks(self, task_filter: Optional[TaskFilter] = None) -> int:
        with self._lock:
            if task_filter is None:
                count = len(self._tasks)
                self._tasks.clear()
                return count
            to_delete = [
                tid for tid, t in self._tasks.items()
                if task_filter.matches(t)
            ]
            for tid in to_delete:
                del self._tasks[tid]
            return len(to_delete)

    def _enforce_limit(self):
        if len(self._tasks) > self._max_tasks:
            sorted_tasks = sorted(
                self._tasks.values(),
                key=lambda t: t.received or t.created_at
            )
            excess = len(self._tasks) - self._max_tasks
            for task in sorted_tasks[:excess]:
                del self._tasks[task.task_id]

    def _update_daily_stats(self, task: TaskResult):
        if not task.name:
            return
        
        date_str = (task.received or task.created_at).strftime("%Y-%m-%d")
        key = f"{date_str}:{task.name}"
        
        if key not in self._daily_stats:
            self._daily_stats[key] = DailyTaskStats(
                date=date_str,
                task_name=task.name
            )
        
        stats = self._daily_stats[key]
        
        if task.state == TaskState.SUCCESS:
            stats.succeeded += 1
            if task.runtime:
                stats.update_runtime(task.runtime)
        elif task.state == TaskState.FAILURE:
            stats.failed += 1
        elif task.state == TaskState.RETRY:
            stats.retried += 1
        elif task.state == TaskState.REVOKED:
            stats.revoked += 1
        
        stats.total = stats.succeeded + stats.failed + stats.retried + stats.revoked

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
            names = set(t.name for t in self._tasks.values() if t.name)
            return sorted(names)

    def get_queues(self) -> List[str]:
        with self._lock:
            queues = set(t.queue for t in self._tasks.values() if t.queue)
            return sorted(queues)

    def get_stats_summary(self) -> Dict[str, Any]:
        with self._lock:
            tasks = list(self._tasks.values())
            state_counts = {}
            for state in TaskState:
                state_counts[state.value] = sum(1 for t in tasks if t.state == state)
            
            runtimes = [t.runtime for t in tasks if t.runtime is not None]
            avg_runtime = sum(runtimes) / len(runtimes) if runtimes else None
            
            return {
                "total": len(tasks),
                "by_state": state_counts,
                "avg_runtime": avg_runtime,
                "task_names": self.get_task_names(),
                "queues": self.get_queues(),
            }


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
                for k, v in kwargs.items():
                    if hasattr(worker, k):
                        setattr(worker, k, v)
                worker.updated_at = datetime.utcnow()
            return worker

    def update_worker(self, hostname: str, **kwargs) -> Optional[WorkerInfo]:
        with self._lock:
            worker = self._workers.get(hostname)
            if worker:
                for k, v in kwargs.items():
                    if hasattr(worker, k):
                        setattr(worker, k, v)
                worker.updated_at = datetime.utcnow()
            return worker

    def heartbeat(self, hostname: str, **kwargs) -> WorkerInfo:
        with self._lock:
            worker = self._workers.get(hostname)
            if not worker:
                worker = WorkerInfo(hostname=hostname)
                self._workers[hostname] = worker
            
            worker.last_heartbeat = datetime.utcnow()
            worker.heartbeat_expires = datetime.utcnow() + timedelta(
                seconds=self._heartbeat_timeout
            )
            worker.status = "online"
            
            for k, v in kwargs.items():
                if hasattr(worker, k):
                    setattr(worker, k, v)
            
            worker.updated_at = datetime.utcnow()
            return worker

    def worker_offline(self, hostname: str) -> Optional[WorkerInfo]:
        with self._lock:
            worker = self._workers.get(hostname)
            if worker:
                worker.status = "offline"
                worker.updated_at = datetime.utcnow()
            return worker

    def get_worker(self, hostname: str) -> Optional[WorkerInfo]:
        with self._lock:
            return self._workers.get(hostname)

    def get_all_workers(self) -> List[WorkerInfo]:
        with self._lock:
            return list(self._workers.values())

    def get_active_workers(self) -> List[WorkerInfo]:
        with self._lock:
            return [w for w in self._workers.values() if w.is_alive()]

    def cleanup_stale_workers(self) -> List[str]:
        with self._lock:
            stale = []
            for hostname, worker in self._workers.items():
                if not worker.is_alive() and worker.status == "online":
                    worker.status = "offline"
                    stale.append(hostname)
            return stale

    def increment_active(self, hostname: str):
        with self._lock:
            worker = self._workers.get(hostname)
            if worker:
                worker.active_tasks = max(0, worker.active_tasks + 1)

    def decrement_active(self, hostname: str):
        with self._lock:
            worker = self._workers.get(hostname)
            if worker:
                worker.active_tasks = max(0, worker.active_tasks - 1)

    def increment_processed(self, hostname: str):
        with self._lock:
            worker = self._workers.get(hostname)
            if worker:
                worker.processed_tasks += 1

    def increment_failed(self, hostname: str):
        with self._lock:
            worker = self._workers.get(hostname)
            if worker:
                worker.failed_tasks += 1


class WebSocketConnection:
    def __init__(self, connection_id: str):
        self.connection_id = connection_id
        self.created_at = datetime.utcnow()
        self._queue: asyncio.Queue = asyncio.Queue()
        self._closed = False
        self.subscriptions: List[str] = []

    async def send(self, message: Dict[str, Any]):
        if not self._closed:
            await self._queue.put(message)

    async def receive(self) -> Optional[Dict[str, Any]]:
        if self._closed:
            return None
        try:
            return await asyncio.wait_for(self._queue.get(), timeout=1.0)
        except asyncio.TimeoutError:
            return None

    def close(self):
        self._closed = True

    @property
    def is_closed(self) -> bool:
        return self._closed


class WebSocketManager:
    def __init__(self):
        self._connections: Dict[str, WebSocketConnection] = {}
        self._lock = threading.RLock()

    def connect(self) -> WebSocketConnection:
        conn_id = str(uuid.uuid4())
        conn = WebSocketConnection(conn_id)
        with self._lock:
            self._connections[conn_id] = conn
        logger.info(f"WebSocket connected: {conn_id}")
        return conn

    def disconnect(self, connection_id: str):
        with self._lock:
            conn = self._connections.pop(connection_id, None)
            if conn:
                conn.close()
                logger.info(f"WebSocket disconnected: {connection_id}")

    async def broadcast(self, message: Dict[str, Any]):
        with self._lock:
            connections = list(self._connections.values())
        
        for conn in connections:
            if not conn.is_closed:
                try:
                    await conn.send(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to {conn.connection_id}: {e}")

    async def send_to(self, connection_id: str, message: Dict[str, Any]):
        with self._lock:
            conn = self._connections.get(connection_id)
        if conn and not conn.is_closed:
            await conn.send(message)

    def get_connection_count(self) -> int:
        with self._lock:
            return len(self._connections)

    def cleanup_closed(self):
        with self._lock:
            closed = [cid for cid, c in self._connections.items() if c.is_closed]
            for cid in closed:
                del self._connections[cid]


class EventProcessor:
    def __init__(
        self,
        task_storage: TaskStorage,
        worker_registry: WorkerRegistry,
        ws_manager: WebSocketManager,
    ):
        self._storage = task_storage
        self._workers = worker_registry
        self._ws = ws_manager
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

    async def process_event(self, event: Dict[str, Any]):
        event_type = event.get("type", "")
        handler = self._event_handlers.get(event_type)
        if handler:
            await handler(event)
        else:
            logger.debug(f"Unhandled event type: {event_type}")

    async def _handle_task_sent(self, event: Dict[str, Any]):
        task_id = event.get("uuid")
        if not task_id:
            return
        
        task = self._storage.get_task(task_id) or TaskResult(
            task_id=task_id,
            name=event.get("name", ""),
            state=TaskState.PENDING,
        )
        task.name = event.get("name", task.name)
        task.args = str(event.get("args", ""))
        task.kwargs = str(event.get("kwargs", ""))
        task.parent_id = event.get("parent_id")
        task.root_id = event.get("root_id")
        task.eta = self._parse_datetime(event.get("eta"))
        task.expires = self._parse_datetime(event.get("expires"))
        task.queue = event.get("queue")
        task.exchange = event.get("exchange")
        task.routing_key = event.get("routing_key")
        task.retries = event.get("retries", 0)
        task.state = TaskState.PENDING
        
        self._storage.save_task(task)
        await self._broadcast_task_update(task, "task-sent")

    async def _handle_task_received(self, event: Dict[str, Any]):
        task_id = event.get("uuid")
        if not task_id:
            return
        
        task = self._storage.get_task(task_id) or TaskResult(
            task_id=task_id,
            name=event.get("name", ""),
            state=TaskState.RECEIVED,
        )
        task.name = event.get("name", task.name)
        task.state = TaskState.RECEIVED
        task.received = self._parse_datetime(event.get("timestamp")) or datetime.utcnow()
        task.worker = event.get("hostname")
        task.args = str(event.get("args", task.args or ""))
        task.kwargs = str(event.get("kwargs", task.kwargs or ""))
        task.retries = event.get("retries", task.retries)
        task.eta = self._parse_datetime(event.get("eta")) or task.eta
        task.queue = event.get("queue", task.queue)
        task.clock = event.get("clock")
        
        self._storage.save_task(task)
        
        if task.worker:
            self._workers.register_worker(task.worker)
        
        await self._broadcast_task_update(task, "task-received")

    async def _handle_task_started(self, event: Dict[str, Any]):
        task_id = event.get("uuid")
        if not task_id:
            return
        
        task = self._storage.get_task(task_id) or TaskResult(
            task_id=task_id,
            name="",
            state=TaskState.STARTED,
        )
        task.state = TaskState.STARTED
        task.started = self._parse_datetime(event.get("timestamp")) or datetime.utcnow()
        task.worker = event.get("hostname", task.worker)
        task.pid = event.get("pid")
        task.clock = event.get("clock", task.clock)
        
        self._storage.save_task(task)
        
        if task.worker:
            self._workers.increment_active(task.worker)
        
        await self._broadcast_task_update(task, "task-started")

    async def _handle_task_succeeded(self, event: Dict[str, Any]):
        task_id = event.get("uuid")
        if not task_id:
            return
        
        task = self._storage.get_task(task_id) or TaskResult(
            task_id=task_id,
            name="",
            state=TaskState.SUCCESS,
        )
        task.state = TaskState.SUCCESS
        task.succeeded = self._parse_datetime(event.get("timestamp")) or datetime.utcnow()
        task.result = str(event.get("result", ""))
        task.runtime = event.get("runtime")
        task.worker = event.get("hostname", task.worker)
        task.clock = event.get("clock", task.clock)
        
        self._storage.save_task(task)
        
        if task.worker:
            self._workers.decrement_active(task.worker)
            self._workers.increment_processed(task.worker)
        
        await self._broadcast_task_update(task, "task-succeeded")

    async def _handle_task_failed(self, event: Dict[str, Any]):
        task_id = event.get("uuid")
        if not task_id:
            return
        
        task = self._storage.get_task(task_id) or TaskResult(
            task_id=task_id,
            name="",
            state=TaskState.FAILURE,
        )
        task.state = TaskState.FAILURE
        task.failed = self._parse_datetime(event.get("timestamp")) or datetime.utcnow()
        task.result = str(event.get("exception", ""))
        task.traceback = event.get("traceback")
        task.worker = event.get("hostname", task.worker)
        task.clock = event.get("clock", task.clock)
        
        self._storage.save_task(task)
        
        if task.worker:
            self._workers.decrement_active(task.worker)
            self._workers.increment_failed(task.worker)
        
        await self._broadcast_task_update(task, "task-failed")

    async def _handle_task_retried(self, event: Dict[str, Any]):
        task_id = event.get("uuid")
        if not task_id:
            return
        
        task = self._storage.get_task(task_id) or TaskResult(
            task_id=task_id,
            name="",
            state=TaskState.RETRY,
        )
        task.state = TaskState.RETRY
        task.retried = self._parse_datetime(event.get("timestamp")) or datetime.utcnow()
        task.result = str(event.get("exception", ""))
        task.traceback = event.get("traceback")
        task.worker = event.get("hostname", task.worker)
        task.retries = (task.retries or 0) + 1
        task.clock = event.get("clock", task.clock)
        
        self._storage.save_task(task)
        
        if task.worker:
            self._workers.decrement_active(task.worker)
        
        await self._broadcast_task_update(task, "task-retried")

    async def _handle_task_revoked(self, event: Dict[str, Any]):
        task_id = event.get("uuid")
        if not task_id:
            return
        
        task = self._storage.get_task(task_id) or TaskResult(
            task_id=task_id,
            name="",
            state=TaskState.REVOKED,
        )
        task.state = TaskState.REVOKED
        task.revoked = self._parse_datetime(event.get("timestamp")) or datetime.utcnow()
        task.worker = event.get("hostname", task.worker)
        task.terminated = event.get("terminated", False)
        task.signum = event.get("signum")
        task.expired = event.get("expired", False)
        task.clock = event.get("clock", task.clock)
        
        self._storage.save_task(task)
        
        if task.worker:
            self._workers.decrement_active(task.worker)
        
        await self._broadcast_task_update(task, "task-revoked")

    async def _handle_worker_online(self, event: Dict[str, Any]):
        hostname = event.get("hostname")
        if not hostname:
            return
        
        worker = self._workers.register_worker(
            hostname=hostname,
            status="online",
            software_identity=event.get("sw_ident"),
            software_version=event.get("sw_ver"),
            software_sys=event.get("sw_sys"),
            pid=event.get("pid"),
        )
        
        await self._broadcast_worker_update(worker, "worker-online")

    async def _handle_worker_offline(self, event: Dict[str, Any]):
        hostname = event.get("hostname")
        if not hostname:
            return
        
        worker = self._workers.worker_offline(hostname)
        if worker:
            await self._broadcast_worker_update(worker, "worker-offline")

    async def _handle_worker_heartbeat(self, event: Dict[str, Any]):
        hostname = event.get("hostname")
        if not hostname:
            return
        
        worker = self._workers.heartbeat(
            hostname=hostname,
            active_tasks=event.get("active", 0),
            processed_tasks=event.get("processed", 0),
            load_average=event.get("loadavg"),
            clock=event.get("clock"),
            freq=event.get("freq"),
            pid=event.get("pid"),
        )
        
        await self._broadcast_worker_update(worker, "worker-heartbeat")

    async def _broadcast_task_update(self, task: TaskResult, event_type: str):
        message = {
            "type": event_type,
            "data": task.to_dict(),
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self._ws.broadcast(message)

    async def _broadcast_worker_update(self, worker: WorkerInfo, event_type: str):
        message = {
            "type": event_type,
            "data": worker.to_dict(),
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self._ws.broadcast(message)

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
            for fmt in [
                "%Y-%m-%dT%H:%M:%S.%f",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M:%S.%f",
                "%Y-%m-%d %H:%M:%S",
            ]:
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue
        return None


class MigrationManager:
    def __init__(self, storage: TaskStorage, worker_registry: WorkerRegistry):
        self._storage = storage
        self._workers = worker_registry
        self._migrations: List[Dict[str, Any]] = []
        self._applied: List[str] = []
        self._register_migrations()

    def _register_migrations(self):
        self._migrations = [
            {
                "id": "001_initial",
                "description": "Initial schema setup",
                "up": self._migration_001_up,
                "down": self._migration_001_down,
            },
            {
                "id": "002_add_task_indices",
                "description": "Add task indices for performance",
                "up": self._migration_002_up,
                "down": self._migration_002_down,
            },
            {
                "id": "003_add_daily_stats",
                "description": "Add daily statistics tracking",
                "up": self._migration_003_up,
                "down": self._migration_003_down,
            },
        ]

    def run_migrations(self) -> List[str]:
        applied = []
        for migration in self._migrations:
            if migration["id"] not in self._applied:
                try:
                    migration["up"]()
                    self._applied.append(migration["id"])
                    applied.append(migration["id"])
                    logger.info(f"Applied migration: {migration['id']} - {migration['description']}")
                except Exception as e:
                    logger.error(f"Failed to apply migration {migration['id']}: {e}")
                    raise
        return applied

    def rollback_migration(self, migration_id: str) -> bool:
        migration = next((m for m in self._migrations if m["id"] == migration_id), None)
        if not migration:
            return False
        if migration_id not in self._applied:
            return False
        try:
            migration["down"]()
            self._applied.remove(migration_id)
            logger.info(f"Rolled back migration: {migration_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to rollback migration {migration_id}: {e}")
            return False

    def get_pending_migrations(self) -> List[str]:
        return [m["id"] for m in self._migrations if m["id"] not in self._applied]

    def get_applied_migrations(self) -> List[str]:
        return list(self._applied)

    def _migration_001_up(self):
        logger.debug("Migration 001: Setting up initial task storage")

    def _migration_001_down(self):
        logger.debug("Migration 001: Reverting initial task storage")

    def _migration_002_up(self):
        logger.debug("Migration 002: Adding task indices")

    def _migration_002_down(self):
        logger.debug("Migration 002: Removing task indices")

    def _migration_003_up(self):
        logger.debug("Migration 003: Setting up daily stats")

    def _migration_003_down(self):
        logger.debug("Migration 003: Removing daily stats")


class TaskRetryTracker:
    def __init__(self, storage: TaskStorage):
        self._storage = storage
        self._retry_chains: Dict[str, List[str]] = {}
        self._lock = threading.RLock()

    def track_retry(self, original_task_id: str, new_task_id: str):
        with self._lock:
            if original_task_id not in self._retry_chains:
                self._retry_chains[original_task_id] = []
            self._retry_chains[original_task_id].append(new_task_id)

    def get_retry_chain(self, task_id: str) -> List[str]:
        with self._lock:
            chain = [task_id]
            current = task_id
            visited = set()
            
            while current in self._retry_chains and current not in visited:
                visited.add(current)
                retries = self._retry_chains[current]
                if retries:
                    chain.extend(retries)
                    current = retries[-1]
                else:
                    break
            
            return chain

    def get_retry_count(self, task_id: str) -> int:
        with self._lock:
            return len(self._retry_chains.get(task_id, []))

    def find_orphans(self) -> List[TaskResult]:
        tasks, _ = self._storage.get_tasks(limit=10000)
        orphans = []
        for task in tasks:
            if task.is_orphan():
                orphans.append(task)
        return orphans


class OrphanDetector:
    def __init__(self, storage: TaskStorage):
        self._storage = storage

    def detect_orphans(self) -> List[TaskResult]:
        tasks, _ = self._storage.get_tasks(limit=10000)
        task_ids = {t.task_id for t in tasks}
        orphans = []
        
        for task in tasks:
            if task.parent_id and task.parent_id not in task_ids:
                if task.state in [TaskState.FAILURE, TaskState.REVOKED]:
                    orphans.append(task)
        
        return orphans

    def get_orphan_count(self) -> int:
        return len(self.detect_orphans())


class TaskSearchEngine:
    def __init__(self, storage: TaskStorage):
        self._storage = storage

    def search(
        self,
        query: str,
        state: Optional[TaskState] = None,
        worker: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[TaskResult], int]:
        task_filter = TaskFilter(
            state=state,
            worker=worker,
            date_from=date_from,
            date_to=date_to,
            search=query,
        )
        return self._storage.get_tasks(
            task_filter=task_filter,
            limit=limit,
            offset=offset,
        )

    def search_by_name(self, name: str, **kwargs) -> Tuple[List[TaskResult], int]:
        task_filter = TaskFilter(name=name, **{
            k: v for k, v in kwargs.items()
            if k in ["state", "worker", "date_from", "date_to"]
        })
        return self._storage.get_tasks(task_filter=task_filter)

    def search_by_worker(self, worker: str, **kwargs) -> Tuple[List[TaskResult], int]:
        task_filter = TaskFilter(worker=worker)
        return self._storage.get_tasks(task_filter=task_filter)

    def search_by_date_range(
        self,
        date_from: datetime,
        date_to: datetime,
        **kwargs
    ) -> Tuple[List[TaskResult], int]:
        task_filter = TaskFilter(date_from=date_from, date_to=date_to)
        return self._storage.get_tasks(task_filter=task_filter)


class HealthMonitor:
    def __init__(
        self,
        worker_registry: WorkerRegistry,
        check_interval: int = 10,
    ):
        self._workers = worker_registry
        self._check_interval = check_interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._health_callbacks: List[Any] = []

    def start(self):
        if not self._running:
            self._running = True
            self._thread = threading.Thread(
                target=self._monitor_loop,
                daemon=True,
                name="HealthMonitor"
            )
            self._thread.start()
            logger.info("Health monitor started")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Health monitor stopped")

    def _monitor_loop(self):
        while self._running:
            try:
                stale = self._workers.cleanup_stale_workers()
                if stale:
                    logger.warning(f"Workers went offline: {stale}")
                    for callback in self._health_callbacks:
                        try:
                            callback("workers_offline", stale)
                        except Exception as e:
                            logger.error(f"Health callback error: {e}")
            except Exception as e:
                logger.error(f"Health monitor error: {e}")
            time.sleep(self._check_interval)

    def add_callback(self, callback):
        self._health_callbacks.append(callback)

    def get_health_status(self) -> Dict[str, Any]:
        all_workers = self._workers.get_all_workers()
        active_workers = self._workers.get_active_workers()
        
        return {
            "total_workers": len(all_workers),
            "active_workers": len(active_workers),
            "offline_workers": len(all_workers) - len(active_workers),
            "workers": [w.to_dict() for w in all_workers],
            "checked_at": datetime.utcnow().isoformat(),
        }


class KanchiMonitor:
    def __init__(
        self,
        max_tasks: int = 10000,
        heartbeat_timeout: int = 30,
        health_check_interval: int = 10,
    ):
        self.task_storage = TaskStorage(max_tasks=max_tasks)
        self.worker_registry = WorkerRegistry(heartbeat_timeout=heartbeat_timeout)
        self.ws_manager = WebSocketManager()
        self.event_processor = EventProcessor(
            self.task_storage,
            self.worker_registry,
            self.ws_manager,
        )
        self.migration_manager = MigrationManager(
            self.task_storage,
            self.worker_registry,
        )
        self.retry_tracker = TaskRetryTracker(self.task_storage)
        self.orphan_detector = OrphanDetector(self.task_storage)
        self.search_engine = TaskSearchEngine(self.task_storage)
        self.health_monitor = HealthMonitor(
            self.worker_registry,
            check_interval=health_check_interval,
        )
        self._initialized = False

    def initialize(self):
        if not self._initialized:
            applied = self.migration_manager.run_migrations()
            if applied:
                logger.info(f"Applied migrations: {applied}")
            self.health_monitor.start()
            self._initialized = True
            logger.info("Kanchi monitor initialized")

    def shutdown(self):
        self.health_monitor.stop()
        logger.info("Kanchi monitor shut down")

    async def process_event(self, event: Dict[str, Any]):
        await self.event_processor.process_event(event)

    def get_tasks(
        self,
        state: Optional[str] = None,
        name: Optional[str] = None,
        worker: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        search: Optional[str] = None,
        queue: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        sort_by: str = "received",
        sort_desc: bool = True,
    ) -> Tuple[List[Dict[str, Any]], int]:
        task_filter = TaskFilter(
            state=TaskState(state) if state else None,
            name=name,
            worker=worker,
            date_from=date_from,
            date_to=date_to,
            search=search,
            queue=queue,
        )
        tasks, total = self.task_storage.get_tasks(
            task_filter=task_filter,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_desc=sort_desc,
        )
        return [t.to_dict() for t in tasks], total

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        task = self.task_storage.get_task(task_id)
        return task.to_dict() if task else None

    def get_workers(self) -> List[Dict[str, Any]]:
        return [w.to_dict() for w in self.worker_registry.get_all_workers()]

    def get_worker(self, hostname: str) -> Optional[Dict[str, Any]]:
        worker = self.worker_registry.get_worker(hostname)
        return worker.to_dict() if worker else None

    def get_stats(self) -> Dict[str, Any]:
        summary = self.task_storage.get_stats_summary()
        health = self.health_monitor.get_health_status()
        orphan_count = self.orphan_detector.get_orphan_count()
        
        return {
            "tasks": summary,
            "workers": health,
            "orphans": orphan_count,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def get_daily_stats(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        task_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        stats = self.task_storage.get_daily_stats(
            date_from=date_from,
            date_to=date_to,
            task_name=task_name,
        )
        return [s.to_dict() for s in stats]

    def get_orphans(self) -> List[Dict[str, Any]]:
        orphans = self.orphan_detector.detect_orphans()
        return [t.to_dict() for t in orphans]

    def connect_websocket(self) -> WebSocketConnection:
        return self.ws_manager.connect()

    def disconnect_websocket(self, connection_id: str):
        self.ws_manager.disconnect(connection_id)

    async def broadcast_message(self, message: Dict[str, Any]):
        await self.ws_manager.broadcast(message)

    def delete_task(self, task_id: str) -> bool:
        return self.task_storage.delete_task(task_id)

    def clear_tasks(
        self,
        state: Optional[str] = None,
        name: Optional[str] = None,
    ) -> int:
        task_filter = None
        if state or name:
            task_filter = TaskFilter(
                state=TaskState(state) if state else None,
                name=name,
            )
        return self.task_storage.clear_tasks(task_filter)

    def get_task_names(self) -> List[str]:
        return self.task_storage.get_task_names()

    def get_queues(self) -> List[str]:
        return self.task_storage.get_queues()

    def get_retry_chain(self, task_id: str) -> List[str]:
        return self.retry_tracker.get_retry_chain(task_id)

    def search_tasks(
        self,
        query: str,
        state: Optional[str] = None,
        worker: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        tasks, total = self.search_engine.search(
            query=query,
            state=TaskState(state) if state else None,
            worker=worker,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            offset=offset,
        )
        return [t.to_dict() for t in tasks], total


def create_monitor(
    max_tasks: int = 10000,
    heartbeat_timeout: int = 30,
    health_check_interval: int = 10,
) -> KanchiMonitor:
    monitor = KanchiMonitor(
        max_tasks=max_tasks,
        heartbeat_timeout=heartbeat_timeout,
        health_check_interval=health_check_interval,
    )
    monitor.initialize()
    return monitor


async def simulate_events(monitor: KanchiMonitor):
    events = [
        {
            "type": "worker-online",
            "hostname": "celery@worker1",
            "sw_ident": "py-celery",
            "sw_ver": "5.2.0",
            "sw_sys": "Linux",
            "pid": 12345,
        },
        {
            "type": "worker-heartbeat",
            "hostname": "celery@worker1",
            "active": 2,
            "processed": 100,
            "loadavg": [0.5, 0.3, 0.2],
            "clock": 1000,
            "freq": 2.0,
            "pid": 12345,
        },
        {
            "type": "task-received",
            "uuid": "task-001",
            "name": "myapp.tasks.send_email",
            "hostname": "celery@worker1",
            "timestamp": datetime.utcnow().timestamp(),
            "args": "['user@example.com']",
            "kwargs": "{}",
            "retries": 0,
            "queue": "default",
        },
        {
            "type": "task-started",
            "uuid": "task-001",
            "hostname": "celery@worker1",
            "timestamp": datetime.utcnow().timestamp(),
            "pid": 12346,
        },
        {
            "type": "task-succeeded",
            "uuid": "task-001",
            "hostname": "celery@worker1",
            "timestamp": datetime.utcnow().timestamp(),
            "result": "True",
            "runtime": 0.5,
        },
        {
            "type": "task-received",
            "uuid": "task-002",
            "name": "myapp.tasks.process_data",
            "hostname": "celery@worker1",
            "timestamp": datetime.utcnow().timestamp(),
            "args": "[1, 2, 3]",
            "kwargs": "{}",
            "retries": 0,
            "queue": "high_priority",
        },
        {
            "type": "task-started",
            "uuid": "task-002",
            "hostname": "celery@worker1",
            "timestamp": datetime.utcnow().timestamp(),
            "pid": 12347,
        },
        {
            "type": "task-failed",
            "uuid": "task-002",
            "hostname": "celery@worker1",
            "timestamp": datetime.utcnow().timestamp(),
            "exception": "ValueError: Invalid data",
            "traceback": "Traceback (most recent call last):\n  ...\nValueError: Invalid data",
        },
        {
            "type": "task-received",
            "uuid": "task-003",
            "name": "myapp.tasks.process_data",
            "hostname": "celery@worker1",
            "timestamp": datetime.utcnow().timestamp(),
            "args": "[1, 2, 3]",
            "kwargs": "{}",
            "retries": 1,
            "queue": "high_priority",
            "parent_id": "task-002",
            "root_id": "task-002",
        },
    ]
    
    for event in events:
        await monitor.process_event(event)
        await asyncio.sleep(0.01)


async def main():
    monitor = create_monitor()
    
    logger.info("Starting Kanchi Task Monitor simulation...")
    
    await simulate_events(monitor)
    
    stats = monitor.get_stats()
    logger.info(f"Stats: {json.dumps(stats, indent=2)}")
    
    tasks, total = monitor.get_tasks(limit=10)
    logger.info(f"Total tasks: {total}")
    for task in tasks:
        logger.info(f"  Task: {task['task_id']} - {task['name']} - {task['state']}")
    
    workers = monitor.get_workers()
    logger.info(f"Workers: {len(workers)}")
    for worker in workers:
        logger.info(f"  Worker: {worker['hostname']} - {worker['status']}")
    
    failed_tasks, failed_count = monitor.get_tasks(state="FAILURE")
    logger.info(f"Failed tasks: {failed_count}")
    
    search_results, search_count = monitor.search_tasks("process_data")
    logger.info(f"Search results for 'process_data': {search_count}")
    
    daily_stats = monitor.get_daily_stats()
    logger.info(f"Daily stats entries: {len(daily_stats)}")
    
    orphans = monitor.get_orphans()
    logger.info(f"Orphan tasks: {len(orphans)}")
    
    pending = monitor.migration_manager.get_pending_migrations()
    applied = monitor.migration_manager.get_applied_migrations()
    logger.info(f"Applied migrations: {applied}")
    logger.info(f"Pending migrations: {pending}")
    
    ws_conn = monitor.connect_websocket()
    logger.info(f"WebSocket connection: {ws_conn.connection_id}")
    
    await monitor.broadcast_message({
        "type": "system",
        "message": "Monitor is running",
        "timestamp": datetime.utcnow().isoformat(),
    })
    
    msg = await ws_conn.receive()
    if msg:
        logger.info(f"Received WebSocket message: {msg['type']}")
    
    monitor.disconnect_websocket(ws_conn.connection_id)
    
    monitor.shutdown()
    logger.info("Kanchi Monitor simulation complete")


if __name__ == "__main__":
    asyncio.run(main())