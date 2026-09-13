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
    load_average: Optional[List[float]] = None
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

    @property
    def is_alive(self) -> bool:
        if self.heartbeat_expires:
            return time.time() < self.heartbeat_expires
        if self.last_heartbeat:
            return (datetime.utcnow() - self.last_heartbeat).total_seconds() < 30
        return False


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
        state: Optional[TaskState] = None,
        name: Optional[str] = None,
        worker: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        search: Optional[str] = None,
        task_id: Optional[str] = None,
        parent_id: Optional[str] = None,
        root_id: Optional[str] = None,
        queue: Optional[str] = None,
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

    def matches(self, task: TaskResult) -> bool:
        if self.task_id and task.task_id != self.task_id:
            return False
        if self.state and task.state != self.state:
            return False
        if self.name and self.name.lower() not in (task.name or "").lower():
            return False
        if self.worker and self.worker.lower() not in (task.worker or "").lower():
            return False
        if self.parent_id and task.parent_id != self.parent_id:
            return False
        if self.root_id and task.root_id != self.root_id:
            return False
        if self.queue and task.queue != self.queue:
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
            is_new = task.task_id not in self._tasks
            self._tasks[task.task_id] = task
            if is_new:
                self._task_order.append(task.task_id)
                self._enforce_limit()
            self._update_daily_stats(task)

    def _enforce_limit(self) -> None:
        while len(self._task_order) > self._max_tasks:
            oldest_id = self._task_order.pop(0)
            self._tasks.pop(oldest_id, None)

    def _update_daily_stats(self, task: TaskResult) -> None:
        task_time = task.received or task.timestamp or datetime.utcnow()
        date_key = task_time.strftime("%Y-%m-%d")
        if date_key not in self._daily_stats:
            self._daily_stats[date_key] = DailyTaskStats(date=date_key)
        stats = self._daily_stats[date_key]
        if task.state == TaskState.SUCCESS:
            stats.succeeded = max(stats.succeeded, 1)
        elif task.state == TaskState.FAILURE:
            stats.failed = max(stats.failed, 1)
        elif task.state == TaskState.RETRY:
            stats.retried = max(stats.retried, 1)
        elif task.state == TaskState.REVOKED:
            stats.revoked = max(stats.revoked, 1)

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
                return datetime.min if not sort_desc else datetime.max
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

    def get_daily_stats(self, days: int = 30) -> List[DailyTaskStats]:
        with self._lock:
            result = []
            today = datetime.utcnow().date()
            for i in range(days - 1, -1, -1):
                date = today - timedelta(days=i)
                date_key = date.strftime("%Y-%m-%d")
                if date_key in self._daily_stats:
                    result.append(self._daily_stats[date_key])
                else:
                    result.append(DailyTaskStats(date=date_key))
            return result

    def get_task_count_by_state(self) -> Dict[str, int]:
        with self._lock:
            counts: Dict[str, int] = {}
            for task in self._tasks.values():
                state = task.state.value if isinstance(task.state, TaskState) else str(task.state)
                counts[state] = counts.get(state, 0) + 1
            return counts

    def find_orphan_tasks(self) -> List[TaskResult]:
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

    def get_task_history(self, name: str, limit: int = 50) -> List[TaskResult]:
        with self._lock:
            tasks = [t for t in self._tasks.values() if t.name == name]
            tasks.sort(key=lambda t: t.received or datetime.min, reverse=True)
            return tasks[:limit]

    @property
    def total_tasks(self) -> int:
        with self._lock:
            return len(self._tasks)


class WorkerRegistry:
    def __init__(self, heartbeat_timeout: float = 30.0):
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
            if not worker.heartbeat_expires:
                worker.heartbeat_expires = time.time() + self._heartbeat_timeout
            return worker

    def heartbeat(self, hostname: str, **kwargs) -> WorkerInfo:
        with self._lock:
            worker = self.update_worker(hostname, **kwargs)
            worker.heartbeat_expires = time.time() + self._heartbeat_timeout
            worker.status = "online"
            return worker

    def worker_offline(self, hostname: str) -> Optional[WorkerInfo]:
        with self._lock:
            if hostname in self._workers:
                self._workers[hostname].status = "offline"
                return self._workers[hostname]
            return None

    def get_worker(self, hostname: str) -> Optional[WorkerInfo]:
        with self._lock:
            return self._workers.get(hostname)

    def get_all_workers(self) -> List[WorkerInfo]:
        with self._lock:
            return list(self._workers.values())

    def get_online_workers(self) -> List[WorkerInfo]:
        with self._lock:
            return [w for w in self._workers.values() if w.is_alive]

    def remove_worker(self, hostname: str) -> bool:
        with self._lock:
            if hostname in self._workers:
                del self._workers[hostname]
                return True
            return False

    def check_heartbeats(self) -> List[str]:
        with self._lock:
            offline = []
            for hostname, worker in self._workers.items():
                if not worker.is_alive and worker.status == "online":
                    worker.status = "offline"
                    offline.append(hostname)
            return offline

    @property
    def worker_count(self) -> int:
        with self._lock:
            return len(self._workers)

    @property
    def online_worker_count(self) -> int:
        with self._lock:
            return sum(1 for w in self._workers.values() if w.is_alive)


class WebSocketConnection:
    def __init__(self, connection_id: str, filters: Optional[Dict] = None):
        self.connection_id = connection_id
        self.filters = filters or {}
        self.connected_at = datetime.utcnow()
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
        self._lock = threading.RLock()

    def add_connection(self, connection: WebSocketConnection) -> None:
        with self._lock:
            self._connections[connection.connection_id] = connection
            logger.info(f"WebSocket connection added: {connection.connection_id}")

    def remove_connection(self, connection_id: str) -> None:
        with self._lock:
            if connection_id in self._connections:
                self._connections[connection_id].close()
                del self._connections[connection_id]
                logger.info(f"WebSocket connection removed: {connection_id}")

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
        with self._lock:
            conn = self._connections.get(connection_id)
        if conn and not conn.is_closed:
            await conn.send(message)
            return True
        return False

    def get_connection(self, connection_id: str) -> Optional[WebSocketConnection]:
        with self._lock:
            return self._connections.get(connection_id)

    @property
    def connection_count(self) -> int:
        with self._lock:
            return len(self._connections)


class EventProcessor:
    def __init__(
        self,
        task_storage: TaskStorage,
        worker_registry: WorkerRegistry,
        ws_manager: Optional[WebSocketManager] = None,
    ):
        self._storage = task_storage
        self._workers = worker_registry
        self._ws_manager = ws_manager
        self._event_handlers: Dict[str, List] = {}
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def register_handler(self, event_type: str, handler) -> None:
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)

    def process_event(self, event: Dict[str, Any]) -> Optional[TaskResult]:
        event_type = event.get("type", "")
        result = None

        if event_type.startswith("task-"):
            result = self._process_task_event(event_type, event)
        elif event_type.startswith("worker-"):
            self._process_worker_event(event_type, event)

        for handler in self._event_handlers.get(event_type, []):
            try:
                handler(event, result)
            except Exception as e:
                logger.error(f"Error in event handler for {event_type}: {e}")

        if self._ws_manager and self._loop and result:
            message = {
                "type": "task_update",
                "task": result.to_dict(),
                "event_type": event_type,
            }
            asyncio.run_coroutine_threadsafe(
                self._ws_manager.broadcast(message),
                self._loop
            )

        return result

    def _process_task_event(self, event_type: str, event: Dict[str, Any]) -> Optional[TaskResult]:
        task_id = event.get("uuid") or event.get("task_id")
        if not task_id:
            return None

        existing = self._storage.get_task(task_id)
        if existing:
            task = existing
        else:
            task = TaskResult(
                task_id=task_id,
                name=event.get("name", "unknown"),
                state=TaskState.PENDING,
            )

        now = datetime.utcnow()

        if event_type == "task-received":
            task.name = event.get("name", task.name)
            task.state = TaskState.RECEIVED
            task.received = now
            task.args = str(event.get("args", ""))
            task.kwargs = str(event.get("kwargs", ""))
            task.worker = event.get("hostname", task.worker)
            task.retries = event.get("retries", 0)
            task.parent_id = event.get("parent_id", task.parent_id)
            task.root_id = event.get("root_id", task.root_id)
            task.expires = self._parse_datetime(event.get("expires"))
            task.eta = self._parse_datetime(event.get("eta"))
            task.queue = event.get("queue", task.queue)
            task.exchange = event.get("exchange", task.exchange)
            task.routing_key = event.get("routing_key", task.routing_key)
            task.clock = event.get("clock", task.clock)
            task.client = event.get("client", task.client)
            task.timestamp = now

        elif event_type == "task-started":
            task.state = TaskState.STARTED
            task.started = now
            task.worker = event.get("hostname", task.worker)
            task.timestamp = now

        elif event_type == "task-succeeded":
            task.state = TaskState.SUCCESS
            task.succeeded = now
            task.result = str(event.get("result", ""))
            task.runtime = event.get("runtime", task.runtime)
            task.timestamp = now

        elif event_type == "task-failed":
            task.state = TaskState.FAILURE
            task.failed = now
            task.result = str(event.get("result", ""))
            task.traceback = event.get("traceback", task.traceback)
            task.timestamp = now

        elif event_type == "task-retried":
            task.state = TaskState.RETRY
            task.retried = now
            task.retries = (task.retries or 0) + 1
            task.traceback = event.get("traceback", task.traceback)
            task.timestamp = now

        elif event_type == "task-revoked":
            task.state = TaskState.REVOKED
            task.revoked = now
            task.timestamp = now

        self._storage.save_task(task)
        return task

    def _process_worker_event(self, event_type: str, event: Dict[str, Any]) -> None:
        hostname = event.get("hostname")
        if not hostname:
            return

        if event_type == "worker-online":
            self._workers.update_worker(
                hostname,
                status="online",
                sw_ident=event.get("sw_ident"),
                sw_ver=event.get("sw_ver"),
                sw_sys=event.get("sw_sys"),
                pid=event.get("pid"),
            )
        elif event_type == "worker-heartbeat":
            self._workers.heartbeat(
                hostname,
                active_tasks=event.get("active", 0),
                processed_tasks=event.get("processed", 0),
                load_average=event.get("loadavg"),
                heartbeat_expires=event.get("expires"),
            )
        elif event_type == "worker-offline":
            self._workers.worker_offline(hostname)

        if self._ws_manager and self._loop:
            worker = self._workers.get_worker(hostname)
            if worker:
                message = {
                    "type": "worker_update",
                    "worker": worker.to_dict(),
                    "event_type": event_type,
                }
                asyncio.run_coroutine_threadsafe(
                    self._ws_manager.broadcast(message),
                    self._loop
                )

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
                return None
        return None


class TaskManager:
    def __init__(
        self,
        task_storage: TaskStorage,
        worker_registry: WorkerRegistry,
        event_processor: EventProcessor,
    ):
        self._storage = task_storage
        self._workers = worker_registry
        self._processor = event_processor

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
        task_id: Optional[str] = None,
        parent_id: Optional[str] = None,
        root_id: Optional[str] = None,
        queue: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
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
            task_id=task_id,
            parent_id=parent_id,
            root_id=root_id,
            queue=queue,
        )
        return self._storage.get_tasks(
            task_filter=task_filter,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_desc=sort_desc,
        )

    def delete_task(self, task_id: str) -> bool:
        return self._storage.delete_task(task_id)

    def clear_tasks(
        self,
        state: Optional[str] = None,
        name: Optional[str] = None,
        worker: Optional[str] = None,
    ) -> int:
        task_filter = None
        if any([state, name, worker]):
            task_filter = TaskFilter(
                state=TaskState(state) if state else None,
                name=name,
                worker=worker,
            )
        return self._storage.clear_tasks(task_filter)

    def get_task_stats(self) -> Dict[str, Any]:
        state_counts = self._storage.get_task_count_by_state()
        total = self._storage.total_tasks
        return {
            "total": total,
            "by_state": state_counts,
            "workers": {
                "total": self._workers.worker_count,
                "online": self._workers.online_worker_count,
            }
        }

    def get_daily_stats(self, days: int = 30) -> List[Dict[str, Any]]:
        stats = self._storage.get_daily_stats(days)
        return [s.to_dict() for s in stats]

    def get_orphan_tasks(self) -> List[TaskResult]:
        return self._storage.find_orphan_tasks()

    def get_retry_chain(self, task_id: str) -> List[TaskResult]:
        return self._storage.get_retry_chain(task_id)

    def get_task_history(self, name: str, limit: int = 50) -> List[TaskResult]:
        return self._storage.get_task_history(name, limit)

    def get_workers(self) -> List[WorkerInfo]:
        return self._workers.get_all_workers()

    def get_worker(self, hostname: str) -> Optional[WorkerInfo]:
        return self._workers.get_worker(hostname)

    def process_event(self, event: Dict[str, Any]) -> Optional[TaskResult]:
        return self._processor.process_event(event)

    def get_task_names(self) -> List[str]:
        tasks, _ = self._storage.get_tasks(limit=self._storage.total_tasks)
        names = list(set(t.name for t in tasks if t.name))
        names.sort()
        return names

    def get_queues(self) -> List[str]:
        tasks, _ = self._storage.get_tasks(limit=self._storage.total_tasks)
        queues = list(set(t.queue for t in tasks if t.queue))
        queues.sort()
        return queues


class MigrationManager:
    def __init__(self, db_url: Optional[str] = None):
        self._db_url = db_url
        self._migrations: List[Dict[str, Any]] = []
        self._applied: List[str] = []

    def register_migration(self, version: str, description: str, up_fn, down_fn=None) -> None:
        migration = {
            "version": version,
            "description": description,
            "up": up_fn,
            "down": down_fn,
            "checksum": hashlib.md5(f"{version}{description}".encode()).hexdigest(),
        }
        self._migrations.append(migration)
        self._migrations.sort(key=lambda m: m["version"])

    def run_migrations(self) -> List[str]:
        applied = []
        for migration in self._migrations:
            if migration["version"] not in self._applied:
                try:
                    migration["up"]()
                    self._applied.append(migration["version"])
                    applied.append(migration["version"])
                    logger.info(f"Applied migration: {migration['version']} - {migration['description']}")
                except Exception as e:
                    logger.error(f"Failed to apply migration {migration['version']}: {e}")
                    raise
        return applied

    def rollback(self, target_version: Optional[str] = None) -> List[str]:
        rolled_back = []
        migrations_to_rollback = [
            m for m in reversed(self._migrations)
            if m["version"] in self._applied
        ]
        if target_version:
            migrations_to_rollback = [
                m for m in migrations_to_rollback
                if m["version"] > target_version
            ]
        for migration in migrations_to_rollback:
            if migration.get("down"):
                try:
                    migration["down"]()
                    self._applied.remove(migration["version"])
                    rolled_back.append(migration["version"])
                    logger.info(f"Rolled back migration: {migration['version']}")
                except Exception as e:
                    logger.error(f"Failed to rollback migration {migration['version']}: {e}")
                    raise
        return rolled_back

    def get_pending_migrations(self) -> List[Dict[str, Any]]:
        return [m for m in self._migrations if m["version"] not in self._applied]

    def get_applied_migrations(self) -> List[str]:
        return list(self._applied)


class KanchiMonitor:
    def __init__(
        self,
        max_tasks: int = 10000,
        heartbeat_timeout: float = 30.0,
        db_url: Optional[str] = None,
    ):
        self._task_storage = TaskStorage(max_tasks=max_tasks)
        self._worker_registry = WorkerRegistry(heartbeat_timeout=heartbeat_timeout)
        self._ws_manager = WebSocketManager()
        self._event_processor = EventProcessor(
            task_storage=self._task_storage,
            worker_registry=self._worker_registry,
            ws_manager=self._ws_manager,
        )
        self._task_manager = TaskManager(
            task_storage=self._task_storage,
            worker_registry=self._worker_registry,
            event_processor=self._event_processor,
        )
        self._migration_manager = MigrationManager(db_url=db_url)
        self._running = False
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    @property
    def task_manager(self) -> TaskManager:
        return self._task_manager

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
    def migration_manager(self) -> MigrationManager:
        return self._migration_manager

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop
        self._event_processor.set_event_loop(loop)

    def start(self) -> None:
        self._running = True
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_checker,
            daemon=True,
            name="kanchi-heartbeat"
        )
        self._heartbeat_thread.start()
        logger.info("Kanchi monitor started")

    def stop(self) -> None:
        self._running = False
        if self._heartbeat_thread:
            self._heartbeat_thread.join(timeout=5.0)
        logger.info("Kanchi monitor stopped")

    def _heartbeat_checker(self) -> None:
        while self._running:
            try:
                offline_workers = self._worker_registry.check_heartbeats()
                for hostname in offline_workers:
                    logger.warning(f"Worker went offline: {hostname}")
                    if self._ws_manager and self._loop:
                        worker = self._worker_registry.get_worker(hostname)
                        if worker:
                            message = {
                                "type": "worker_update",
                                "worker": worker.to_dict(),
                                "event_type": "worker-offline",
                            }
                            asyncio.run_coroutine_threadsafe(
                                self._ws_manager.broadcast(message),
                                self._loop
                            )
            except Exception as e:
                logger.error(f"Error in heartbeat checker: {e}")
            time.sleep(5.0)

    def process_event(self, event: Dict[str, Any]) -> Optional[TaskResult]:
        return self._event_processor.process_event(event)

    async def connect_websocket(self, connection_id: Optional[str] = None, filters: Optional[Dict] = None) -> WebSocketConnection:
        if not connection_id:
            connection_id = str(uuid.uuid4())
        conn = WebSocketConnection(connection_id=connection_id, filters=filters or {})
        self._ws_manager.add_connection(conn)
        initial_state = await self._get_initial_state()
        await conn.send({
            "type": "initial_state",
            "data": initial_state,
        })
        return conn

    def disconnect_websocket(self, connection_id: str) -> None:
        self._ws_manager.remove_connection(connection_id)

    async def _get_initial_state(self) -> Dict[str, Any]:
        tasks, total = self._task_storage.get_tasks(limit=100)
        workers = self._worker_registry.get_all_workers()
        stats = self._task_manager.get_task_stats()
        return {
            "tasks": [t.to_dict() for t in tasks],
            "total_tasks": total,
            "workers": [w.to_dict() for w in workers],
            "stats": stats,
        }

    def get_dashboard_data(self) -> Dict[str, Any]:
        stats = self._task_manager.get_task_stats()
        daily_stats = self._task_manager.get_daily_stats(days=7)
        workers = self._worker_registry.get_all_workers()
        recent_tasks, _ = self._task_storage.get_tasks(limit=10)
        orphans = self._task_storage.find_orphan_tasks()
        return {
            "stats": stats,
            "daily_stats": daily_stats,
            "workers": [w.to_dict() for w in workers],
            "recent_tasks": [t.to_dict() for t in recent_tasks],
            "orphan_count": len(orphans),
        }

    def run_migrations(self) -> List[str]:
        return self._migration_manager.run_migrations()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


class CeleryEventReceiver:
    def __init__(self, monitor: KanchiMonitor):
        self._monitor = monitor
        self._running = False

    def process_celery_event(self, event: Dict[str, Any]) -> Optional[TaskResult]:
        return self._monitor.process_event(event)

    def simulate_task_lifecycle(self, task_name: str, worker: str = "worker@localhost") -> str:
        task_id = str(uuid.uuid4())
        now = datetime.utcnow()

        self._monitor.process_event({
            "type": "task-received",
            "uuid": task_id,
            "name": task_name,
            "hostname": worker,
            "args": "[]",
            "kwargs": "{}",
            "retries": 0,
            "timestamp": now.timestamp(),
        })

        self._monitor.process_event({
            "type": "task-started",
            "uuid": task_id,
            "hostname": worker,
            "timestamp": (now + timedelta(seconds=0.1)).timestamp(),
        })

        self._monitor.process_event({
            "type": "task-succeeded",
            "uuid": task_id,
            "hostname": worker,
            "result": "null",
            "runtime": 0.5,
            "timestamp": (now + timedelta(seconds=0.6)).timestamp(),
        })

        return task_id


class TaskSearchEngine:
    def __init__(self, task_storage: TaskStorage):
        self._storage = task_storage

    def search(
        self,
        query: str,
        state: Optional[str] = None,
        name: Optional[str] = None,
        worker: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[TaskResult], int]:
        task_filter = TaskFilter(
            state=TaskState(state) if state else None,
            name=name,
            worker=worker,
            date_from=date_from,
            date_to=date_to,
            search=query if query else None,
        )
        return self._storage.get_tasks(
            task_filter=task_filter,
            limit=limit,
            offset=offset,
        )

    def get_task_names(self) -> List[str]:
        tasks, _ = self._storage.get_tasks(limit=self._storage.total_tasks)
        return sorted(set(t.name for t in tasks if t.name))

    def get_workers(self) -> List[str]:
        tasks, _ = self._storage.get_tasks(limit=self._storage.total_tasks)
        return sorted(set(t.worker for t in tasks if t.worker))

    def get_queues(self) -> List[str]:
        tasks, _ = self._storage.get_tasks(limit=self._storage.total_tasks)
        return sorted(set(t.queue for t in tasks if t.queue))


class TaskStatisticsCalculator:
    def __init__(self, task_storage: TaskStorage):
        self._storage = task_storage

    def calculate_success_rate(self, hours: int = 24) -> float:
        since = datetime.utcnow() - timedelta(hours=hours)
        task_filter = TaskFilter(date_from=since)
        tasks, total = self._storage.get_tasks(task_filter=task_filter, limit=total if (total := self._storage.total_tasks) else 1)
        if not tasks:
            return 0.0
        succeeded = sum(1 for t in tasks if t.state == TaskState.SUCCESS)
        return (succeeded / len(tasks)) * 100 if tasks else 0.0

    def calculate_average_runtime(self, name: Optional[str] = None) -> Optional[float]:
        task_filter = TaskFilter(
            state=TaskState.SUCCESS,
            name=name,
        )
        tasks, _ = self._storage.get_tasks(task_filter=task_filter, limit=1000)
        runtimes = [t.runtime for t in tasks if t.runtime is not None]
        if not runtimes:
            return None
        return sum(runtimes) / len(runtimes)

    def get_throughput(self, hours: int = 1) -> Dict[str, float]:
        since = datetime.utcnow() - timedelta(hours=hours)
        task_filter = TaskFilter(date_from=since)
        tasks, total = self._storage.get_tasks(
            task_filter=task_filter,
            limit=self._storage.total_tasks or 1
        )
        succeeded = sum(1 for t in tasks if t.state == TaskState.SUCCESS)
        failed = sum(1 for t in tasks if t.state == TaskState.FAILURE)
        return {
            "total_per_hour": len(tasks) / hours,
            "succeeded_per_hour": succeeded / hours,
            "failed_per_hour": failed / hours,
        }

    def get_failure_analysis(self) -> Dict[str, Any]:
        task_filter = TaskFilter(state=TaskState.FAILURE)
        tasks, total = self._storage.get_tasks(
            task_filter=task_filter,
            limit=self._storage.total_tasks or 1
        )
        by_name: Dict[str, int] = {}
        by_worker: Dict[str, int] = {}
        for task in tasks:
            if task.name:
                by_name[task.name] = by_name.get(task.name, 0) + 1
            if task.worker:
                by_worker[task.worker] = by_worker.get(task.worker, 0) + 1
        return {
            "total_failures": total,
            "by_task_name": by_name,
            "by_worker": by_worker,
        }


def create_monitor(
    max_tasks: int = 10000,
    heartbeat_timeout: float = 30.0,
    db_url: Optional[str] = None,
) -> KanchiMonitor:
    monitor = KanchiMonitor(
        max_tasks=max_tasks,
        heartbeat_timeout=heartbeat_timeout,
        db_url=db_url,
    )
    return monitor


async def run_websocket_demo(monitor: KanchiMonitor) -> None:
    loop = asyncio.get_event_loop()
    monitor.set_event_loop(loop)

    conn = await monitor.connect_websocket()
    logger.info(f"WebSocket connected: {conn.connection_id}")

    receiver = CeleryEventReceiver(monitor)
    task_id = receiver.simulate_task_lifecycle("myapp.tasks.process_data")
    logger.info(f"Simulated task: {task_id}")

    await asyncio.sleep(0.1)

    msg = await conn.receive()
    if msg:
        logger.info(f"Received WebSocket message: {msg.get('type')}")

    monitor.disconnect_websocket(conn.connection_id)


def main():
    monitor = create_monitor(max_tasks=5000)
    monitor.start()

    receiver = CeleryEventReceiver(monitor)

    task_ids = []
    for i in range(5):
        task_id = receiver.simulate_task_lifecycle(
            f"myapp.tasks.task_{i % 3}",
            worker=f"worker{i % 2}@localhost"
        )
        task_ids.append(task_id)

    monitor.process_event({
        "type": "worker-heartbeat",
        "hostname": "worker0@localhost",
        "active": 2,
        "processed": 10,
        "loadavg": [0.5, 0.3, 0.2],
    })

    monitor.process_event({
        "type": "worker-online",
        "hostname": "worker1@localhost",
        "sw_ident": "celery",
        "sw_ver": "5.3.0",
        "sw_sys": "Linux",
        "pid": 12345,
    })

    dashboard = monitor.get_dashboard_data()
    logger.info(f"Dashboard stats: {json.dumps(dashboard['stats'], indent=2)}")

    tm = monitor.task_manager
    tasks, total = tm.get_tasks(limit=10)
    logger.info(f"Total tasks: {total}, Retrieved: {len(tasks)}")

    workers = tm.get_workers()
    logger.info(f"Workers: {[w.hostname for w in workers]}")

    stats_calc = TaskStatisticsCalculator(monitor._task_storage)
    avg_runtime = stats_calc.calculate_average_runtime()
    logger.info(f"Average runtime: {avg_runtime}")

    search_engine = TaskSearchEngine(monitor._task_storage)
    names = search_engine.get_task_names()
    logger.info(f"Task names: {names}")

    asyncio.run(run_websocket_demo(monitor))

    monitor.stop()
    logger.info("Kanchi monitor demo completed")


if __name__ == "__main__":
    main()