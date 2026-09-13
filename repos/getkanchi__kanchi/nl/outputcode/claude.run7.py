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
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


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
    sw_ident: Optional[str] = None
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
            return (datetime.utcnow() - self.last_heartbeat).total_seconds() < 60
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


class TaskFilter:
    def __init__(
        self,
        task_name: Optional[str] = None,
        state: Optional[TaskState] = None,
        worker: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        search_term: Optional[str] = None,
        queue: Optional[str] = None,
        parent_id: Optional[str] = None,
        root_id: Optional[str] = None,
    ):
        self.task_name = task_name
        self.state = state
        self.worker = worker
        self.date_from = date_from
        self.date_to = date_to
        self.search_term = search_term
        self.queue = queue
        self.parent_id = parent_id
        self.root_id = root_id

    def matches(self, task: TaskResult) -> bool:
        if self.task_name and self.task_name.lower() not in task.name.lower():
            return False
        if self.state and task.state != self.state:
            return False
        if self.worker and task.worker and self.worker.lower() not in task.worker.lower():
            return False
        if self.queue and task.queue and self.queue != task.queue:
            return False
        if self.parent_id and task.parent_id != self.parent_id:
            return False
        if self.root_id and task.root_id != self.root_id:
            return False

        task_time = task.received or task.timestamp or task.started
        if self.date_from and task_time and task_time < self.date_from:
            return False
        if self.date_to and task_time and task_time > self.date_to:
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
                task.queue,
            ])).lower()
            if term not in searchable:
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
                val = t.received or t.timestamp or datetime.min
            return val

        try:
            tasks.sort(key=sort_key, reverse=sort_desc)
        except TypeError:
            pass

        total = len(tasks)
        return tasks[offset:offset + limit], total

    def delete_task(self, task_id: str) -> bool:
        with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
                if task_id in self._task_order:
                    self._task_order.remove(task_id)
                return True
            return False

    def clear_tasks(self, task_filter: Optional[TaskFilter] = None) -> int:
        with self._lock:
            if task_filter is None:
                count = len(self._tasks)
                self._tasks.clear()
                self._task_order.clear()
                return count
            to_delete = [
                tid for tid, t in self._tasks.items()
                if task_filter.matches(t)
            ]
            for tid in to_delete:
                del self._tasks[tid]
                if tid in self._task_order:
                    self._task_order.remove(tid)
            return len(to_delete)

    def _update_daily_stats(self, task: TaskResult) -> None:
        task_time = task.succeeded or task.failed or task.received or task.timestamp
        if not task_time:
            return
        date_str = task_time.strftime("%Y-%m-%d")
        key = f"{date_str}:{task.name}"
        if key not in self._daily_stats:
            self._daily_stats[key] = DailyTaskStats(date=date_str, task_name=task.name)
        stats = self._daily_stats[key]
        stats.total = max(stats.total, 1)

        if task.state == TaskState.SUCCESS:
            stats.succeeded = max(stats.succeeded, 1)
            if task.runtime is not None:
                if stats.min_runtime is None or task.runtime < stats.min_runtime:
                    stats.min_runtime = task.runtime
                if stats.max_runtime is None or task.runtime > stats.max_runtime:
                    stats.max_runtime = task.runtime
        elif task.state == TaskState.FAILURE:
            stats.failed = max(stats.failed, 1)
        elif task.state == TaskState.RETRY:
            stats.retried = max(stats.retried, 1)
        elif task.state == TaskState.REVOKED:
            stats.revoked = max(stats.revoked, 1)

    def get_daily_stats(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        task_name: Optional[str] = None,
    ) -> List[DailyTaskStats]:
        with self._lock:
            stats = list(self._daily_stats.values())

        if date_from:
            date_from_str = date_from.strftime("%Y-%m-%d")
            stats = [s for s in stats if s.date >= date_from_str]
        if date_to:
            date_to_str = date_to.strftime("%Y-%m-%d")
            stats = [s for s in stats if s.date <= date_to_str]
        if task_name:
            stats = [s for s in stats if task_name.lower() in s.task_name.lower()]

        return sorted(stats, key=lambda s: (s.date, s.task_name))

    def get_task_count_by_state(self) -> Dict[str, int]:
        with self._lock:
            counts: Dict[str, int] = {}
            for task in self._tasks.values():
                state = task.state.value if isinstance(task.state, TaskState) else str(task.state)
                counts[state] = counts.get(state, 0) + 1
            return counts

    def get_orphan_tasks(self) -> List[TaskResult]:
        with self._lock:
            all_ids = set(self._tasks.keys())
            orphans = []
            for task in self._tasks.values():
                if task.parent_id and task.parent_id not in all_ids:
                    orphans.append(task)
            return orphans

    def get_retry_chain(self, task_id: str) -> List[TaskResult]:
        with self._lock:
            chain = []
            visited = set()
            current_id = task_id
            while current_id and current_id not in visited:
                visited.add(current_id)
                task = self._tasks.get(current_id)
                if task:
                    chain.append(task)
                    current_id = task.parent_id
                else:
                    break
            return chain

    def get_task_names(self) -> List[str]:
        with self._lock:
            return sorted(set(t.name for t in self._tasks.values()))

    def get_queues(self) -> List[str]:
        with self._lock:
            return sorted(set(t.queue for t in self._tasks.values() if t.queue))


class WorkerRegistry:
    def __init__(self, heartbeat_timeout: float = 60.0):
        self._workers: Dict[str, WorkerInfo] = {}
        self._lock = threading.RLock()
        self._heartbeat_timeout = heartbeat_timeout

    def register_worker(self, hostname: str, **kwargs) -> WorkerInfo:
        with self._lock:
            if hostname not in self._workers:
                self._workers[hostname] = WorkerInfo(hostname=hostname, **kwargs)
            else:
                worker = self._workers[hostname]
                for key, value in kwargs.items():
                    if hasattr(worker, key):
                        setattr(worker, key, value)
            return self._workers[hostname]

    def update_worker(self, hostname: str, **kwargs) -> Optional[WorkerInfo]:
        with self._lock:
            if hostname not in self._workers:
                return self.register_worker(hostname, **kwargs)
            worker = self._workers[hostname]
            for key, value in kwargs.items():
                if hasattr(worker, key):
                    setattr(worker, key, value)
            return worker

    def heartbeat(self, hostname: str, **kwargs) -> WorkerInfo:
        with self._lock:
            worker = self._workers.get(hostname)
            if not worker:
                worker = WorkerInfo(hostname=hostname)
                self._workers[hostname] = worker
            worker.last_heartbeat = datetime.utcnow()
            worker.heartbeat_expires = time.time() + self._heartbeat_timeout
            worker.status = "online"
            for key, value in kwargs.items():
                if hasattr(worker, key):
                    setattr(worker, key, value)
            return worker

    def worker_offline(self, hostname: str) -> Optional[WorkerInfo]:
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
            self._check_heartbeats()
            return list(self._workers.values())

    def get_online_workers(self) -> List[WorkerInfo]:
        with self._lock:
            self._check_heartbeats()
            return [w for w in self._workers.values() if w.is_alive()]

    def _check_heartbeats(self) -> None:
        now = time.time()
        for worker in self._workers.values():
            if worker.heartbeat_expires and now > worker.heartbeat_expires:
                worker.status = "offline"

    def remove_worker(self, hostname: str) -> bool:
        with self._lock:
            if hostname in self._workers:
                del self._workers[hostname]
                return True
            return False

    def get_worker_stats(self) -> Dict[str, Any]:
        with self._lock:
            self._check_heartbeats()
            total = len(self._workers)
            online = sum(1 for w in self._workers.values() if w.is_alive())
            return {
                "total": total,
                "online": online,
                "offline": total - online,
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

    def connect(self, filters: Optional[Dict[str, Any]] = None) -> WebSocketConnection:
        conn_id = str(uuid.uuid4())
        conn = WebSocketConnection(conn_id, filters)
        with self._lock:
            self._connections[conn_id] = conn
        logger.info(f"WebSocket connected: {conn_id}")
        return conn

    def disconnect(self, connection_id: str) -> None:
        with self._lock:
            conn = self._connections.pop(connection_id, None)
            if conn:
                conn.close()
        logger.info(f"WebSocket disconnected: {connection_id}")

    async def broadcast(self, message: Dict[str, Any]) -> None:
        with self._lock:
            connections = list(self._connections.values())
        for conn in connections:
            if not conn.is_closed:
                try:
                    await conn.send(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to {conn.connection_id}: {e}")

    async def broadcast_task_update(self, task: TaskResult) -> None:
        message = {
            "type": "task_update",
            "data": task.to_dict(),
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self.broadcast(message)

    async def broadcast_worker_update(self, worker: WorkerInfo) -> None:
        message = {
            "type": "worker_update",
            "data": worker.to_dict(),
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self.broadcast(message)

    def get_connection_count(self) -> int:
        with self._lock:
            return len(self._connections)

    def get_connections(self) -> List[WebSocketConnection]:
        with self._lock:
            return list(self._connections.values())


class CeleryEventHandler:
    def __init__(
        self,
        task_storage: TaskStorage,
        worker_registry: WorkerRegistry,
        ws_manager: WebSocketManager,
    ):
        self._task_storage = task_storage
        self._worker_registry = worker_registry
        self._ws_manager = ws_manager
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def _run_coroutine(self, coro) -> None:
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(coro, self._loop)

    def on_task_sent(self, event: Dict[str, Any]) -> None:
        task = self._get_or_create_task(event)
        task.state = TaskState.PENDING
        task.received = datetime.utcfromtimestamp(event.get("timestamp", time.time()))
        task.args = str(event.get("args", ""))
        task.kwargs = str(event.get("kwargs", ""))
        task.queue = event.get("queue")
        task.exchange = event.get("exchange")
        task.routing_key = event.get("routing_key")
        task.eta = self._parse_datetime(event.get("eta"))
        task.expires = self._parse_datetime(event.get("expires"))
        task.retries = event.get("retries", 0)
        task.parent_id = event.get("parent_id")
        task.root_id = event.get("root_id")
        self._task_storage.save_task(task)
        self._run_coroutine(self._ws_manager.broadcast_task_update(task))

    def on_task_received(self, event: Dict[str, Any]) -> None:
        task = self._get_or_create_task(event)
        task.state = TaskState.RECEIVED
        task.received = datetime.utcfromtimestamp(event.get("timestamp", time.time()))
        task.worker = event.get("hostname")
        task.args = str(event.get("args", ""))
        task.kwargs = str(event.get("kwargs", ""))
        task.retries = event.get("retries", 0)
        task.eta = self._parse_datetime(event.get("eta"))
        task.queue = event.get("queue")
        self._task_storage.save_task(task)
        self._run_coroutine(self._ws_manager.broadcast_task_update(task))

    def on_task_started(self, event: Dict[str, Any]) -> None:
        task = self._get_or_create_task(event)
        task.state = TaskState.STARTED
        task.started = datetime.utcfromtimestamp(event.get("timestamp", time.time()))
        task.worker = event.get("hostname")
        task.pid = event.get("pid")
        self._task_storage.save_task(task)
        self._run_coroutine(self._ws_manager.broadcast_task_update(task))

        worker_hostname = event.get("hostname")
        if worker_hostname:
            self._worker_registry.update_worker(
                worker_hostname,
                active_tasks=self._get_worker_active_count(worker_hostname) + 1
            )

    def on_task_succeeded(self, event: Dict[str, Any]) -> None:
        task = self._get_or_create_task(event)
        task.state = TaskState.SUCCESS
        task.succeeded = datetime.utcfromtimestamp(event.get("timestamp", time.time()))
        task.result = str(event.get("result", ""))
        task.runtime = event.get("runtime")
        self._task_storage.save_task(task)
        self._run_coroutine(self._ws_manager.broadcast_task_update(task))

        worker_hostname = event.get("hostname") or task.worker
        if worker_hostname:
            worker = self._worker_registry.get_worker(worker_hostname)
            if worker:
                worker.processed_tasks += 1
                active = max(0, worker.active_tasks - 1)
                self._worker_registry.update_worker(
                    worker_hostname,
                    active_tasks=active,
                    processed_tasks=worker.processed_tasks
                )

    def on_task_failed(self, event: Dict[str, Any]) -> None:
        task = self._get_or_create_task(event)
        task.state = TaskState.FAILURE
        task.failed = datetime.utcfromtimestamp(event.get("timestamp", time.time()))
        task.traceback = event.get("traceback", "")
        task.result = str(event.get("exception", ""))
        self._task_storage.save_task(task)
        self._run_coroutine(self._ws_manager.broadcast_task_update(task))

        worker_hostname = event.get("hostname") or task.worker
        if worker_hostname:
            worker = self._worker_registry.get_worker(worker_hostname)
            if worker:
                worker.failed_tasks += 1
                active = max(0, worker.active_tasks - 1)
                self._worker_registry.update_worker(
                    worker_hostname,
                    active_tasks=active,
                    failed_tasks=worker.failed_tasks
                )

    def on_task_retried(self, event: Dict[str, Any]) -> None:
        task = self._get_or_create_task(event)
        task.state = TaskState.RETRY
        task.retried = datetime.utcfromtimestamp(event.get("timestamp", time.time()))
        task.traceback = event.get("traceback", "")
        task.retries = task.retries + 1
        self._task_storage.save_task(task)
        self._run_coroutine(self._ws_manager.broadcast_task_update(task))

    def on_task_revoked(self, event: Dict[str, Any]) -> None:
        task = self._get_or_create_task(event)
        task.state = TaskState.REVOKED
        task.revoked = datetime.utcfromtimestamp(event.get("timestamp", time.time()))
        task.result = event.get("terminated", "")
        self._task_storage.save_task(task)
        self._run_coroutine(self._ws_manager.broadcast_task_update(task))

    def on_worker_online(self, event: Dict[str, Any]) -> None:
        hostname = event.get("hostname", "unknown")
        worker = self._worker_registry.heartbeat(
            hostname,
            status="online",
            sw_ident=event.get("sw_ident"),
            sw_ver=event.get("sw_ver"),
            sw_sys=event.get("sw_sys"),
        )
        self._run_coroutine(self._ws_manager.broadcast_worker_update(worker))

    def on_worker_offline(self, event: Dict[str, Any]) -> None:
        hostname = event.get("hostname", "unknown")
        worker = self._worker_registry.worker_offline(hostname)
        if worker:
            self._run_coroutine(self._ws_manager.broadcast_worker_update(worker))

    def on_worker_heartbeat(self, event: Dict[str, Any]) -> None:
        hostname = event.get("hostname", "unknown")
        worker = self._worker_registry.heartbeat(
            hostname,
            active_tasks=event.get("active", 0),
            processed_tasks=event.get("processed", 0),
            load_avg=event.get("loadavg"),
            clock=event.get("clock"),
        )
        self._run_coroutine(self._ws_manager.broadcast_worker_update(worker))

    def _get_or_create_task(self, event: Dict[str, Any]) -> TaskResult:
        task_id = event.get("uuid") or event.get("task_id") or str(uuid.uuid4())
        existing = self._task_storage.get_task(task_id)
        if existing:
            return existing
        return TaskResult(
            task_id=task_id,
            name=event.get("name", "unknown"),
            state=TaskState.PENDING,
            worker=event.get("hostname"),
            timestamp=datetime.utcnow(),
        )

    def _parse_datetime(self, value: Any) -> Optional[datetime]:
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

    def _get_worker_active_count(self, hostname: str) -> int:
        worker = self._worker_registry.get_worker(hostname)
        return worker.active_tasks if worker else 0


class TaskManager:
    def __init__(
        self,
        task_storage: TaskStorage,
        worker_registry: WorkerRegistry,
        ws_manager: WebSocketManager,
    ):
        self._task_storage = task_storage
        self._worker_registry = worker_registry
        self._ws_manager = ws_manager

    def get_tasks(
        self,
        task_name: Optional[str] = None,
        state: Optional[str] = None,
        worker: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        search_term: Optional[str] = None,
        queue: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        sort_by: str = "received",
        sort_desc: bool = True,
    ) -> Dict[str, Any]:
        task_state = None
        if state:
            try:
                task_state = TaskState(state.upper())
            except ValueError:
                pass

        task_filter = TaskFilter(
            task_name=task_name,
            state=task_state,
            worker=worker,
            date_from=date_from,
            date_to=date_to,
            search_term=search_term,
            queue=queue,
        )

        tasks, total = self._task_storage.get_tasks(
            task_filter=task_filter,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_desc=sort_desc,
        )

        return {
            "tasks": [t.to_dict() for t in tasks],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        task = self._task_storage.get_task(task_id)
        return task.to_dict() if task else None

    def get_task_retry_chain(self, task_id: str) -> List[Dict[str, Any]]:
        chain = self._task_storage.get_retry_chain(task_id)
        return [t.to_dict() for t in chain]

    def get_orphan_tasks(self) -> List[Dict[str, Any]]:
        orphans = self._task_storage.get_orphan_tasks()
        return [t.to_dict() for t in orphans]

    def delete_task(self, task_id: str) -> bool:
        return self._task_storage.delete_task(task_id)

    def clear_tasks(
        self,
        state: Optional[str] = None,
        task_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        task_filter = None
        if state or task_name:
            task_state = None
            if state:
                try:
                    task_state = TaskState(state.upper())
                except ValueError:
                    pass
            task_filter = TaskFilter(task_name=task_name, state=task_state)

        count = self._task_storage.clear_tasks(task_filter)
        return {"deleted": count}

    def get_task_statistics(self) -> Dict[str, Any]:
        state_counts = self._task_storage.get_task_count_by_state()
        total = sum(state_counts.values())
        return {
            "total": total,
            "by_state": state_counts,
            "task_names": self._task_storage.get_task_names(),
            "queues": self._task_storage.get_queues(),
        }

    def get_daily_stats(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        task_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        stats = self._task_storage.get_daily_stats(
            date_from=date_from,
            date_to=date_to,
            task_name=task_name,
        )
        return [s.to_dict() for s in stats]

    def get_workers(self) -> List[Dict[str, Any]]:
        workers = self._worker_registry.get_all_workers()
        return [w.to_dict() for w in workers]

    def get_worker(self, hostname: str) -> Optional[Dict[str, Any]]:
        worker = self._worker_registry.get_worker(hostname)
        return worker.to_dict() if worker else None

    def get_worker_stats(self) -> Dict[str, Any]:
        return self._worker_registry.get_worker_stats()


class MigrationManager:
    def __init__(self, db_url: Optional[str] = None):
        self._db_url = db_url
        self._migrations: List[Dict[str, Any]] = []
        self._applied: List[str] = []

    def register_migration(
        self,
        version: str,
        description: str,
        up_sql: str,
        down_sql: Optional[str] = None,
    ) -> None:
        migration = {
            "version": version,
            "description": description,
            "up_sql": up_sql,
            "down_sql": down_sql,
            "checksum": hashlib.md5(up_sql.encode()).hexdigest(),
        }
        self._migrations.append(migration)
        self._migrations.sort(key=lambda m: m["version"])

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
        migration = next((m for m in self._migrations if m["version"] == version), None)
        if migration and version in self._applied:
            if migration.get("down_sql"):
                logger.info(f"Rolling back migration {version}")
                self._applied.remove(version)
                return True
        return False

    def get_migration_history(self) -> List[str]:
        return list(self._applied)


class KanchiMonitor:
    def __init__(
        self,
        max_tasks: int = 10000,
        heartbeat_timeout: float = 60.0,
        db_url: Optional[str] = None,
    ):
        self._task_storage = TaskStorage(max_tasks=max_tasks)
        self._worker_registry = WorkerRegistry(heartbeat_timeout=heartbeat_timeout)
        self._ws_manager = WebSocketManager()
        self._event_handler = CeleryEventHandler(
            self._task_storage,
            self._worker_registry,
            self._ws_manager,
        )
        self._task_manager = TaskManager(
            self._task_storage,
            self._worker_registry,
            self._ws_manager,
        )
        self._migration_manager = MigrationManager(db_url=db_url)
        self._running = False
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None

        self._setup_default_migrations()

    def _setup_default_migrations(self) -> None:
        self._migration_manager.register_migration(
            version="001",
            description="Create tasks table",
            up_sql="""
                CREATE TABLE IF NOT EXISTS tasks (
                    id VARCHAR(36) PRIMARY KEY,
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
                    parent_id VARCHAR(36),
                    root_id VARCHAR(36),
                    queue VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """,
            down_sql="DROP TABLE IF EXISTS tasks",
        )
        self._migration_manager.register_migration(
            version="002",
            description="Create workers table",
            up_sql="""
                CREATE TABLE IF NOT EXISTS workers (
                    hostname VARCHAR(255) PRIMARY KEY,
                    status VARCHAR(50) NOT NULL DEFAULT 'offline',
                    active_tasks INTEGER DEFAULT 0,
                    processed_tasks INTEGER DEFAULT 0,
                    failed_tasks INTEGER DEFAULT 0,
                    last_heartbeat TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """,
            down_sql="DROP TABLE IF EXISTS workers",
        )
        self._migration_manager.register_migration(
            version="003",
            description="Create daily stats table",
            up_sql="""
                CREATE TABLE IF NOT EXISTS daily_task_stats (
                    id SERIAL PRIMARY KEY,
                    date DATE NOT NULL,
                    task_name VARCHAR(255) NOT NULL,
                    succeeded INTEGER DEFAULT 0,
                    failed INTEGER DEFAULT 0,
                    retried INTEGER DEFAULT 0,
                    revoked INTEGER DEFAULT 0,
                    total INTEGER DEFAULT 0,
                    avg_runtime FLOAT,
                    min_runtime FLOAT,
                    max_runtime FLOAT,
                    UNIQUE(date, task_name)
                )
            """,
            down_sql="DROP TABLE IF EXISTS daily_task_stats",
        )

    def run_migrations(self) -> List[str]:
        return self._migration_manager.apply_migrations()

    def start(self, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        if loop:
            self._event_loop = loop
        else:
            try:
                self._event_loop = asyncio.get_event_loop()
            except RuntimeError:
                self._event_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._event_loop)

        self._event_handler.set_event_loop(self._event_loop)
        self._running = True
        logger.info("Kanchi monitor started")

    def stop(self) -> None:
        self._running = False
        logger.info("Kanchi monitor stopped")

    def process_event(self, event_type: str, event_data: Dict[str, Any]) -> None:
        handlers = {
            "task-sent": self._event_handler.on_task_sent,
            "task-received": self._event_handler.on_task_received,
            "task-started": self._event_handler.on_task_started,
            "task-succeeded": self._event_handler.on_task_succeeded,
            "task-failed": self._event_handler.on_task_failed,
            "task-retried": self._event_handler.on_task_retried,
            "task-revoked": self._event_handler.on_task_revoked,
            "worker-online": self._event_handler.on_worker_online,
            "worker-offline": self._event_handler.on_worker_offline,
            "worker-heartbeat": self._event_handler.on_worker_heartbeat,
        }
        handler = handlers.get(event_type)
        if handler:
            handler(event_data)
        else:
            logger.warning(f"Unknown event type: {event_type}")

    @property
    def tasks(self) -> TaskManager:
        return self._task_manager

    @property
    def websocket(self) -> WebSocketManager:
        return self._ws_manager

    @property
    def storage(self) -> TaskStorage:
        return self._task_storage

    @property
    def workers(self) -> WorkerRegistry:
        return self._worker_registry

    @property
    def migrations(self) -> MigrationManager:
        return self._migration_manager

    def get_dashboard_data(self) -> Dict[str, Any]:
        task_stats = self._task_manager.get_task_statistics()
        worker_stats = self._task_manager.get_worker_stats()
        recent_tasks, _ = self._task_storage.get_tasks(limit=10, sort_desc=True)
        orphans = self._task_storage.get_orphan_tasks()

        return {
            "task_statistics": task_stats,
            "worker_statistics": worker_stats,
            "recent_tasks": [t.to_dict() for t in recent_tasks],
            "orphan_count": len(orphans),
            "websocket_connections": self._ws_manager.get_connection_count(),
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def handle_websocket(self, filters: Optional[Dict[str, Any]] = None):
        conn = self._ws_manager.connect(filters)
        try:
            initial_data = {
                "type": "initial",
                "data": self.get_dashboard_data(),
                "timestamp": datetime.utcnow().isoformat(),
            }
            await conn.send(initial_data)
            yield conn
        finally:
            self._ws_manager.disconnect(conn.connection_id)


class KanchiAPI:
    def __init__(self, monitor: KanchiMonitor):
        self._monitor = monitor

    def get_tasks(
        self,
        task_name: Optional[str] = None,
        state: Optional[str] = None,
        worker: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        search: Optional[str] = None,
        queue: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        sort_by: str = "received",
        sort_desc: bool = True,
    ) -> Dict[str, Any]:
        df = self._parse_date(date_from)
        dt = self._parse_date(date_to)
        return self._monitor.tasks.get_tasks(
            task_name=task_name,
            state=state,
            worker=worker,
            date_from=df,
            date_to=dt,
            search_term=search,
            queue=queue,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_desc=sort_desc,
        )

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self._monitor.tasks.get_task(task_id)

    def get_task_retry_chain(self, task_id: str) -> List[Dict[str, Any]]:
        return self._monitor.tasks.get_task_retry_chain(task_id)

    def get_orphan_tasks(self) -> List[Dict[str, Any]]:
        return self._monitor.tasks.get_orphan_tasks()

    def delete_task(self, task_id: str) -> Dict[str, Any]:
        success = self._monitor.tasks.delete_task(task_id)
        return {"success": success, "task_id": task_id}

    def clear_tasks(
        self,
        state: Optional[str] = None,
        task_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self._monitor.tasks.clear_tasks(state=state, task_name=task_name)

    def get_task_statistics(self) -> Dict[str, Any]:
        return self._monitor.tasks.get_task_statistics()

    def get_daily_stats(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        task_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        df = self._parse_date(date_from)
        dt = self._parse_date(date_to)
        return self._monitor.tasks.get_daily_stats(
            date_from=df,
            date_to=dt,
            task_name=task_name,
        )

    def get_workers(self) -> List[Dict[str, Any]]:
        return self._monitor.tasks.get_workers()

    def get_worker(self, hostname: str) -> Optional[Dict[str, Any]]:
        return self._monitor.tasks.get_worker(hostname)

    def get_worker_stats(self) -> Dict[str, Any]:
        return self._monitor.tasks.get_worker_stats()

    def get_dashboard(self) -> Dict[str, Any]:
        return self._monitor.get_dashboard_data()

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str)
        except (ValueError, TypeError):
            return None


def create_monitor(
    max_tasks: int = 10000,
    heartbeat_timeout: float = 60.0,
    db_url: Optional[str] = None,
    auto_migrate: bool = True,
) -> KanchiMonitor:
    monitor = KanchiMonitor(
        max_tasks=max_tasks,
        heartbeat_timeout=heartbeat_timeout,
        db_url=db_url,
    )
    if auto_migrate:
        applied = monitor.run_migrations()
        if applied:
            logger.info(f"Applied migrations: {applied}")
    return monitor


def create_api(monitor: Optional[KanchiMonitor] = None) -> KanchiAPI:
    if monitor is None:
        monitor = create_monitor()
    return KanchiAPI(monitor)


if __name__ == "__main__":
    monitor = create_monitor(max_tasks=5000)
    monitor.start()

    monitor.process_event("worker-online", {
        "hostname": "celery@worker1",
        "sw_ident": "py-celery",
        "sw_ver": "5.3.0",
        "sw_sys": "Linux",
        "timestamp": time.time(),
    })

    task_id_1 = str(uuid.uuid4())
    monitor.process_event("task-received", {
        "uuid": task_id_1,
        "name": "myapp.tasks.send_email",
        "hostname": "celery@worker1",
        "args": "['user@example.com']",
        "kwargs": "{'subject': 'Hello'}",
        "timestamp": time.time(),
        "queue": "default",
    })

    monitor.process_event("task-started", {
        "uuid": task_id_1,
        "name": "myapp.tasks.send_email",
        "hostname": "celery@worker1",
        "timestamp": time.time(),
        "pid": 12345,
    })

    monitor.process_event("task-succeeded", {
        "uuid": task_id_1,
        "name": "myapp.tasks.send_email",
        "hostname": "celery@worker1",
        "result": "True",
        "runtime": 0.523,
        "timestamp": time.time(),
    })

    task_id_2 = str(uuid.uuid4())
    monitor.process_event("task-received", {
        "uuid": task_id_2,
        "name": "myapp.tasks.process_data",
        "hostname": "celery@worker1",
        "args": "[1, 2, 3]",
        "kwargs": "{}",
        "timestamp": time.time(),
        "queue": "high_priority",
    })

    monitor.process_event("task-started", {
        "uuid": task_id_2,
        "name": "myapp.tasks.process_data",
        "hostname": "celery@worker1",
        "timestamp": time.time(),
    })

    monitor.process_event("task-failed", {
        "uuid": task_id_2,
        "name": "myapp.tasks.process_data",
        "hostname": "celery@worker1",
        "traceback": "Traceback (most recent call last):\n  ...\nValueError: Invalid data",
        "exception": "ValueError('Invalid data')",
        "timestamp": time.time(),
    })

    api = create_api(monitor)

    print("\n=== Dashboard ===")
    dashboard = api.get_dashboard()
    print(json.dumps(dashboard, indent=2, default=str))

    print("\n=== All Tasks ===")
    tasks = api.get_tasks(limit=10)
    print(json.dumps(tasks, indent=2, default=str))

    print("\n=== Failed Tasks ===")
    failed_tasks = api.get_tasks(state="FAILURE")
    print(json.dumps(failed_tasks, indent=2, default=str))

    print("\n=== Workers ===")
    workers = api.get_workers()
    print(json.dumps(workers, indent=2, default=str))

    print("\n=== Task Statistics ===")
    stats = api.get_task_statistics()
    print(json.dumps(stats, indent=2, default=str))

    print("\n=== Search Tasks ===")
    search_results = api.get_tasks(search="send_email")
    print(json.dumps(search_results, indent=2, default=str))

    print("\n=== Orphan Tasks ===")
    orphans = api.get_orphan_tasks()
    print(json.dumps(orphans, indent=2, default=str))

    print("\n=== Daily Stats ===")
    daily = api.get_daily_stats()
    print(json.dumps(daily, indent=2, default=str))

    monitor.stop()
    print("\nKanchi monitor stopped successfully.")