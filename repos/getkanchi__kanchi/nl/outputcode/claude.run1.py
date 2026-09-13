import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
import threading
import time
import re
from collections import defaultdict

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
    UNKNOWN = "UNKNOWN"


class WorkerState(str, Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    HEARTBEAT = "HEARTBEAT"


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
    hostname: Optional[str] = None
    clock: Optional[int] = None
    timestamp: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        for key, value in d.items():
            if isinstance(value, datetime):
                d[key] = value.isoformat() if value else None
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
    state: WorkerState
    pid: Optional[int] = None
    software_identity: Optional[str] = None
    software_version: Optional[str] = None
    software_sys: Optional[str] = None
    loadavg: Optional[List[float]] = None
    processed: int = 0
    active: int = 0
    last_heartbeat: Optional[datetime] = None
    registered_tasks: List[str] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        for key, value in d.items():
            if isinstance(value, datetime):
                d[key] = value.isoformat() if value else None
            elif isinstance(value, WorkerState):
                d[key] = value.value
        return d

    def is_healthy(self, timeout_seconds: int = 30) -> bool:
        if self.last_heartbeat is None:
            return False
        elapsed = (datetime.utcnow() - self.last_heartbeat).total_seconds()
        return elapsed < timeout_seconds


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
    max_runtime: float = 0.0
    min_runtime: float = 0.0
    total_runtime: float = 0.0
    runtime_samples: List[float] = field(default_factory=list)

    def update_runtime(self, runtime: float):
        self.runtime_samples.append(runtime)
        self.total_runtime += runtime
        self.avg_runtime = self.total_runtime / len(self.runtime_samples)
        self.max_runtime = max(self.runtime_samples)
        self.min_runtime = min(self.runtime_samples)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d.pop('runtime_samples', None)
        return d


@dataclass
class TaskFilter:
    task_id: Optional[str] = None
    name: Optional[str] = None
    state: Optional[TaskState] = None
    worker: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    search_text: Optional[str] = None
    parent_id: Optional[str] = None
    root_id: Optional[str] = None
    queue: Optional[str] = None
    orphans_only: bool = False
    limit: int = 100
    offset: int = 0


class TaskStore:
    def __init__(self):
        self._tasks: Dict[str, TaskResult] = {}
        self._lock = threading.RLock()
        self._daily_stats: Dict[str, DailyTaskStats] = {}

    def save_task(self, task: TaskResult) -> TaskResult:
        with self._lock:
            task.updated_at = datetime.utcnow()
            self._tasks[task.task_id] = task
            self._update_daily_stats(task)
            return task

    def get_task(self, task_id: str) -> Optional[TaskResult]:
        with self._lock:
            return self._tasks.get(task_id)

    def get_tasks(self, task_filter: Optional[TaskFilter] = None) -> List[TaskResult]:
        with self._lock:
            tasks = list(self._tasks.values())

        if task_filter is None:
            return tasks

        filtered = []
        for task in tasks:
            if not self._matches_filter(task, task_filter):
                continue
            filtered.append(task)

        filtered.sort(key=lambda t: t.created_at, reverse=True)

        start = task_filter.offset
        end = start + task_filter.limit
        return filtered[start:end]

    def count_tasks(self, task_filter: Optional[TaskFilter] = None) -> int:
        if task_filter is None:
            with self._lock:
                return len(self._tasks)
        filter_copy = TaskFilter(**asdict(task_filter)) if task_filter else TaskFilter()
        filter_copy.limit = 999999
        filter_copy.offset = 0
        return len(self.get_tasks(filter_copy))

    def _matches_filter(self, task: TaskResult, f: TaskFilter) -> bool:
        if f.task_id and task.task_id != f.task_id:
            return False
        if f.name and f.name.lower() not in (task.name or "").lower():
            return False
        if f.state and task.state != f.state:
            return False
        if f.worker and f.worker.lower() not in (task.worker or "").lower():
            return False
        if f.queue and task.queue != f.queue:
            return False
        if f.parent_id and task.parent_id != f.parent_id:
            return False
        if f.root_id and task.root_id != f.root_id:
            return False
        if f.date_from and task.created_at < f.date_from:
            return False
        if f.date_to and task.created_at > f.date_to:
            return False
        if f.orphans_only and not task.is_orphan():
            return False
        if f.search_text:
            search = f.search_text.lower()
            searchable = " ".join(filter(None, [
                task.task_id,
                task.name,
                task.worker,
                task.args,
                task.kwargs,
                task.result,
                task.traceback,
            ])).lower()
            if search not in searchable:
                return False
        return True

    def delete_task(self, task_id: str) -> bool:
        with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
                return True
            return False

    def clear_tasks(self):
        with self._lock:
            self._tasks.clear()

    def _update_daily_stats(self, task: TaskResult):
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        key = f"{date_str}:{task.name}"

        if key not in self._daily_stats:
            self._daily_stats[key] = DailyTaskStats(
                date=date_str,
                task_name=task.name
            )

        stats = self._daily_stats[key]

        if task.state == TaskState.SUCCESS:
            stats.succeeded += 1
            if task.runtime is not None:
                stats.update_runtime(task.runtime)
        elif task.state == TaskState.FAILURE:
            stats.failed += 1
        elif task.state == TaskState.RETRY:
            stats.retried += 1
        elif task.state == TaskState.REVOKED:
            stats.revoked += 1

        stats.total = stats.succeeded + stats.failed + stats.retried + stats.revoked

    def get_daily_stats(self, date: Optional[str] = None, task_name: Optional[str] = None) -> List[DailyTaskStats]:
        with self._lock:
            stats = list(self._daily_stats.values())

        if date:
            stats = [s for s in stats if s.date == date]
        if task_name:
            stats = [s for s in stats if task_name.lower() in s.task_name.lower()]

        return stats

    def get_task_history(self, task_name: str, days: int = 7) -> List[DailyTaskStats]:
        cutoff = datetime.utcnow() - timedelta(days=days)
        result = []
        with self._lock:
            for stats in self._daily_stats.values():
                if stats.task_name == task_name:
                    try:
                        stat_date = datetime.strptime(stats.date, "%Y-%m-%d")
                        if stat_date >= cutoff:
                            result.append(stats)
                    except ValueError:
                        pass
        result.sort(key=lambda s: s.date)
        return result

    def get_state_counts(self) -> Dict[str, int]:
        with self._lock:
            counts = defaultdict(int)
            for task in self._tasks.values():
                counts[task.state.value] += 1
            return dict(counts)

    def get_orphan_tasks(self) -> List[TaskResult]:
        with self._lock:
            return [t for t in self._tasks.values() if t.is_orphan()]


class WorkerStore:
    def __init__(self):
        self._workers: Dict[str, WorkerInfo] = {}
        self._lock = threading.RLock()

    def save_worker(self, worker: WorkerInfo) -> WorkerInfo:
        with self._lock:
            worker.updated_at = datetime.utcnow()
            self._workers[worker.hostname] = worker
            return worker

    def get_worker(self, hostname: str) -> Optional[WorkerInfo]:
        with self._lock:
            return self._workers.get(hostname)

    def get_workers(self) -> List[WorkerInfo]:
        with self._lock:
            return list(self._workers.values())

    def get_healthy_workers(self, timeout_seconds: int = 30) -> List[WorkerInfo]:
        with self._lock:
            return [w for w in self._workers.values() if w.is_healthy(timeout_seconds)]

    def get_unhealthy_workers(self, timeout_seconds: int = 30) -> List[WorkerInfo]:
        with self._lock:
            return [w for w in self._workers.values() if not w.is_healthy(timeout_seconds)]

    def update_heartbeat(self, hostname: str, data: Dict[str, Any]) -> Optional[WorkerInfo]:
        with self._lock:
            worker = self._workers.get(hostname)
            if worker is None:
                worker = WorkerInfo(
                    hostname=hostname,
                    state=WorkerState.HEARTBEAT
                )
            worker.last_heartbeat = datetime.utcnow()
            worker.state = WorkerState.HEARTBEAT
            if 'processed' in data:
                worker.processed = data['processed']
            if 'active' in data:
                worker.active = data['active']
            if 'loadavg' in data:
                worker.loadavg = data['loadavg']
            if 'pid' in data:
                worker.pid = data['pid']
            worker.updated_at = datetime.utcnow()
            self._workers[hostname] = worker
            return worker

    def mark_offline(self, hostname: str) -> Optional[WorkerInfo]:
        with self._lock:
            worker = self._workers.get(hostname)
            if worker:
                worker.state = WorkerState.OFFLINE
                worker.updated_at = datetime.utcnow()
            return worker

    def delete_worker(self, hostname: str) -> bool:
        with self._lock:
            if hostname in self._workers:
                del self._workers[hostname]
                return True
            return False


class WebSocketConnection:
    def __init__(self, connection_id: str):
        self.connection_id = connection_id
        self.subscriptions: Set[str] = set()
        self.created_at = datetime.utcnow()
        self._queue: asyncio.Queue = asyncio.Queue()
        self._closed = False

    async def send(self, message: Dict[str, Any]):
        if not self._closed:
            await self._queue.put(message)

    async def receive(self) -> Optional[Dict[str, Any]]:
        try:
            return await asyncio.wait_for(self._queue.get(), timeout=1.0)
        except asyncio.TimeoutError:
            return None

    def close(self):
        self._closed = True

    def is_closed(self) -> bool:
        return self._closed

    def subscribe(self, channel: str):
        self.subscriptions.add(channel)

    def unsubscribe(self, channel: str):
        self.subscriptions.discard(channel)


class WebSocketManager:
    def __init__(self):
        self._connections: Dict[str, WebSocketConnection] = {}
        self._lock = threading.RLock()

    def add_connection(self, connection: WebSocketConnection):
        with self._lock:
            self._connections[connection.connection_id] = connection
            logger.info(f"WebSocket connection added: {connection.connection_id}")

    def remove_connection(self, connection_id: str):
        with self._lock:
            conn = self._connections.pop(connection_id, None)
            if conn:
                conn.close()
                logger.info(f"WebSocket connection removed: {connection_id}")

    def get_connection(self, connection_id: str) -> Optional[WebSocketConnection]:
        with self._lock:
            return self._connections.get(connection_id)

    def get_all_connections(self) -> List[WebSocketConnection]:
        with self._lock:
            return list(self._connections.values())

    async def broadcast(self, message: Dict[str, Any], channel: Optional[str] = None):
        with self._lock:
            connections = list(self._connections.values())

        for conn in connections:
            if conn.is_closed():
                continue
            if channel is None or channel in conn.subscriptions:
                try:
                    await conn.send(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to {conn.connection_id}: {e}")

    async def send_to(self, connection_id: str, message: Dict[str, Any]):
        conn = self.get_connection(connection_id)
        if conn and not conn.is_closed():
            await conn.send(message)

    def connection_count(self) -> int:
        with self._lock:
            return len(self._connections)


class EventProcessor:
    def __init__(self, task_store: TaskStore, worker_store: WorkerStore, ws_manager: WebSocketManager):
        self.task_store = task_store
        self.worker_store = worker_store
        self.ws_manager = ws_manager
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
            try:
                await handler(event)
            except Exception as e:
                logger.error(f"Error processing event {event_type}: {e}")
        else:
            logger.debug(f"No handler for event type: {event_type}")

    async def _handle_task_sent(self, event: Dict[str, Any]):
        task_id = event.get("uuid") or event.get("task_id")
        if not task_id:
            return

        task = self.task_store.get_task(task_id) or TaskResult(
            task_id=task_id,
            name=event.get("name", "unknown"),
            state=TaskState.PENDING
        )
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
        task.timestamp = datetime.utcnow()

        self.task_store.save_task(task)
        await self._broadcast_task_update(task, "task-sent")

    async def _handle_task_received(self, event: Dict[str, Any]):
        task_id = event.get("uuid") or event.get("task_id")
        if not task_id:
            return

        task = self.task_store.get_task(task_id) or TaskResult(
            task_id=task_id,
            name=event.get("name", "unknown"),
            state=TaskState.RECEIVED
        )
        task.state = TaskState.RECEIVED
        task.received = datetime.utcnow()
        task.worker = event.get("hostname")
        task.name = event.get("name", task.name)
        task.args = str(event.get("args", task.args or ""))
        task.kwargs = str(event.get("kwargs", task.kwargs or ""))
        task.retries = event.get("retries", task.retries)
        task.eta = self._parse_datetime(event.get("eta")) or task.eta
        task.hostname = event.get("hostname")
        task.timestamp = datetime.utcnow()

        self.task_store.save_task(task)
        await self._broadcast_task_update(task, "task-received")

    async def _handle_task_started(self, event: Dict[str, Any]):
        task_id = event.get("uuid") or event.get("task_id")
        if not task_id:
            return

        task = self.task_store.get_task(task_id) or TaskResult(
            task_id=task_id,
            name=event.get("name", "unknown"),
            state=TaskState.STARTED
        )
        task.state = TaskState.STARTED
        task.started = datetime.utcnow()
        task.worker = event.get("hostname", task.worker)
        task.hostname = event.get("hostname", task.hostname)
        task.pid = event.get("pid")
        task.timestamp = datetime.utcnow()

        self.task_store.save_task(task)
        await self._broadcast_task_update(task, "task-started")

    async def _handle_task_succeeded(self, event: Dict[str, Any]):
        task_id = event.get("uuid") or event.get("task_id")
        if not task_id:
            return

        task = self.task_store.get_task(task_id) or TaskResult(
            task_id=task_id,
            name=event.get("name", "unknown"),
            state=TaskState.SUCCESS
        )
        task.state = TaskState.SUCCESS
        task.succeeded = datetime.utcnow()
        task.result = str(event.get("result", ""))
        task.runtime = event.get("runtime")
        task.worker = event.get("hostname", task.worker)
        task.timestamp = datetime.utcnow()

        self.task_store.save_task(task)
        await self._broadcast_task_update(task, "task-succeeded")

    async def _handle_task_failed(self, event: Dict[str, Any]):
        task_id = event.get("uuid") or event.get("task_id")
        if not task_id:
            return

        task = self.task_store.get_task(task_id) or TaskResult(
            task_id=task_id,
            name=event.get("name", "unknown"),
            state=TaskState.FAILURE
        )
        task.state = TaskState.FAILURE
        task.failed = datetime.utcnow()
        task.result = str(event.get("exception", ""))
        task.traceback = event.get("traceback")
        task.worker = event.get("hostname", task.worker)
        task.timestamp = datetime.utcnow()

        self.task_store.save_task(task)
        await self._broadcast_task_update(task, "task-failed")

    async def _handle_task_retried(self, event: Dict[str, Any]):
        task_id = event.get("uuid") or event.get("task_id")
        if not task_id:
            return

        task = self.task_store.get_task(task_id) or TaskResult(
            task_id=task_id,
            name=event.get("name", "unknown"),
            state=TaskState.RETRY
        )
        task.state = TaskState.RETRY
        task.retried = datetime.utcnow()
        task.retries = task.retries + 1
        task.result = str(event.get("exception", ""))
        task.traceback = event.get("traceback")
        task.worker = event.get("hostname", task.worker)
        task.timestamp = datetime.utcnow()

        self.task_store.save_task(task)
        await self._broadcast_task_update(task, "task-retried")

    async def _handle_task_revoked(self, event: Dict[str, Any]):
        task_id = event.get("uuid") or event.get("task_id")
        if not task_id:
            return

        task = self.task_store.get_task(task_id) or TaskResult(
            task_id=task_id,
            name=event.get("name", "unknown"),
            state=TaskState.REVOKED
        )
        task.state = TaskState.REVOKED
        task.revoked = datetime.utcnow()
        task.worker = event.get("hostname", task.worker)
        task.timestamp = datetime.utcnow()

        self.task_store.save_task(task)
        await self._broadcast_task_update(task, "task-revoked")

    async def _handle_worker_online(self, event: Dict[str, Any]):
        hostname = event.get("hostname")
        if not hostname:
            return

        worker = self.worker_store.get_worker(hostname) or WorkerInfo(
            hostname=hostname,
            state=WorkerState.ONLINE
        )
        worker.state = WorkerState.ONLINE
        worker.pid = event.get("pid")
        worker.software_identity = event.get("sw_ident")
        worker.software_version = event.get("sw_ver")
        worker.software_sys = event.get("sw_sys")
        worker.last_heartbeat = datetime.utcnow()

        self.worker_store.save_worker(worker)
        await self._broadcast_worker_update(worker, "worker-online")

    async def _handle_worker_offline(self, event: Dict[str, Any]):
        hostname = event.get("hostname")
        if not hostname:
            return

        worker = self.worker_store.mark_offline(hostname)
        if worker is None:
            worker = WorkerInfo(hostname=hostname, state=WorkerState.OFFLINE)
            self.worker_store.save_worker(worker)

        await self._broadcast_worker_update(worker, "worker-offline")

    async def _handle_worker_heartbeat(self, event: Dict[str, Any]):
        hostname = event.get("hostname")
        if not hostname:
            return

        worker = self.worker_store.update_heartbeat(hostname, event)
        if worker:
            await self._broadcast_worker_update(worker, "worker-heartbeat")

    async def _broadcast_task_update(self, task: TaskResult, event_type: str):
        message = {
            "type": event_type,
            "task": task.to_dict(),
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.ws_manager.broadcast(message, channel="tasks")

    async def _broadcast_worker_update(self, worker: WorkerInfo, event_type: str):
        message = {
            "type": event_type,
            "worker": worker.to_dict(),
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.ws_manager.broadcast(message, channel="workers")

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
    def __init__(self, task_store: TaskStore, worker_store: WorkerStore, ws_manager: WebSocketManager):
        self.task_store = task_store
        self.worker_store = worker_store
        self.ws_manager = ws_manager
        self.event_processor = EventProcessor(task_store, worker_store, ws_manager)

    def get_task(self, task_id: str) -> Optional[TaskResult]:
        return self.task_store.get_task(task_id)

    def get_tasks(self, task_filter: Optional[TaskFilter] = None) -> List[TaskResult]:
        return self.task_store.get_tasks(task_filter)

    def count_tasks(self, task_filter: Optional[TaskFilter] = None) -> int:
        return self.task_store.count_tasks(task_filter)

    def delete_task(self, task_id: str) -> bool:
        return self.task_store.delete_task(task_id)

    def clear_tasks(self):
        self.task_store.clear_tasks()

    def get_state_counts(self) -> Dict[str, int]:
        return self.task_store.get_state_counts()

    def get_orphan_tasks(self) -> List[TaskResult]:
        return self.task_store.get_orphan_tasks()

    def get_daily_stats(self, date: Optional[str] = None, task_name: Optional[str] = None) -> List[DailyTaskStats]:
        return self.task_store.get_daily_stats(date, task_name)

    def get_task_history(self, task_name: str, days: int = 7) -> List[DailyTaskStats]:
        return self.task_store.get_task_history(task_name, days)

    def get_workers(self) -> List[WorkerInfo]:
        return self.worker_store.get_workers()

    def get_worker(self, hostname: str) -> Optional[WorkerInfo]:
        return self.worker_store.get_worker(hostname)

    def get_healthy_workers(self) -> List[WorkerInfo]:
        return self.worker_store.get_healthy_workers()

    def get_unhealthy_workers(self) -> List[WorkerInfo]:
        return self.worker_store.get_unhealthy_workers()

    async def process_event(self, event: Dict[str, Any]):
        await self.event_processor.process_event(event)

    def search_tasks(self, query: str, limit: int = 50) -> List[TaskResult]:
        task_filter = TaskFilter(search_text=query, limit=limit)
        return self.task_store.get_tasks(task_filter)

    def filter_by_date_range(self, date_from: datetime, date_to: datetime, limit: int = 100) -> List[TaskResult]:
        task_filter = TaskFilter(date_from=date_from, date_to=date_to, limit=limit)
        return self.task_store.get_tasks(task_filter)

    def filter_by_status(self, state: TaskState, limit: int = 100) -> List[TaskResult]:
        task_filter = TaskFilter(state=state, limit=limit)
        return self.task_store.get_tasks(task_filter)

    def filter_by_worker(self, worker: str, limit: int = 100) -> List[TaskResult]:
        task_filter = TaskFilter(worker=worker, limit=limit)
        return self.task_store.get_tasks(task_filter)

    def filter_by_name(self, name: str, limit: int = 100) -> List[TaskResult]:
        task_filter = TaskFilter(name=name, limit=limit)
        return self.task_store.get_tasks(task_filter)

    def get_retry_chain(self, task_id: str) -> List[TaskResult]:
        task = self.task_store.get_task(task_id)
        if not task:
            return []

        chain = [task]
        root_id = task.root_id or task_id

        all_tasks = self.task_store.get_tasks()
        related = [t for t in all_tasks if t.root_id == root_id and t.task_id != task_id]
        chain.extend(related)
        chain.sort(key=lambda t: t.created_at)
        return chain

    def get_summary(self) -> Dict[str, Any]:
        state_counts = self.get_state_counts()
        workers = self.get_workers()
        healthy_workers = self.get_healthy_workers()
        total_tasks = self.count_tasks()
        orphans = self.get_orphan_tasks()

        return {
            "total_tasks": total_tasks,
            "state_counts": state_counts,
            "total_workers": len(workers),
            "healthy_workers": len(healthy_workers),
            "unhealthy_workers": len(workers) - len(healthy_workers),
            "orphan_tasks": len(orphans),
            "timestamp": datetime.utcnow().isoformat()
        }


class MigrationManager:
    def __init__(self):
        self._migrations: List[Dict[str, Any]] = []
        self._applied: List[str] = []

    def register_migration(self, version: str, description: str, upgrade_fn, downgrade_fn=None):
        self._migrations.append({
            "version": version,
            "description": description,
            "upgrade": upgrade_fn,
            "downgrade": downgrade_fn,
            "created_at": datetime.utcnow()
        })

    def run_migrations(self):
        logger.info("Running auto-migrations...")
        for migration in self._migrations:
            version = migration["version"]
            if version not in self._applied:
                try:
                    logger.info(f"Applying migration {version}: {migration['description']}")
                    migration["upgrade"]()
                    self._applied.append(version)
                    logger.info(f"Migration {version} applied successfully")
                except Exception as e:
                    logger.error(f"Migration {version} failed: {e}")
                    raise

    def rollback(self, version: str):
        migration = next((m for m in self._migrations if m["version"] == version), None)
        if migration and migration.get("downgrade") and version in self._applied:
            migration["downgrade"]()
            self._applied.remove(version)
            logger.info(f"Migration {version} rolled back")

    def get_applied_migrations(self) -> List[str]:
        return list(self._applied)

    def get_pending_migrations(self) -> List[Dict[str, Any]]:
        return [m for m in self._migrations if m["version"] not in self._applied]


class WorkerHealthMonitor:
    def __init__(self, worker_store: WorkerStore, ws_manager: WebSocketManager,
                 check_interval: int = 10, timeout_seconds: int = 30):
        self.worker_store = worker_store
        self.ws_manager = ws_manager
        self.check_interval = check_interval
        self.timeout_seconds = timeout_seconds
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("Worker health monitor started")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Worker health monitor stopped")

    def _run(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._monitor_loop())

    async def _monitor_loop(self):
        while self._running:
            await self._check_workers()
            await asyncio.sleep(self.check_interval)

    async def _check_workers(self):
        workers = self.worker_store.get_workers()
        for worker in workers:
            if worker.state != WorkerState.OFFLINE and not worker.is_healthy(self.timeout_seconds):
                logger.warning(f"Worker {worker.hostname} appears unhealthy")
                self.worker_store.mark_offline(worker.hostname)
                message = {
                    "type": "worker-health-alert",
                    "worker": worker.to_dict(),
                    "message": f"Worker {worker.hostname} has not sent heartbeat in {self.timeout_seconds}s",
                    "timestamp": datetime.utcnow().isoformat()
                }
                await self.ws_manager.broadcast(message, channel="workers")

    def get_health_report(self) -> Dict[str, Any]:
        workers = self.worker_store.get_workers()
        healthy = self.worker_store.get_healthy_workers(self.timeout_seconds)
        unhealthy = self.worker_store.get_unhealthy_workers(self.timeout_seconds)

        return {
            "total_workers": len(workers),
            "healthy_workers": len(healthy),
            "unhealthy_workers": len(unhealthy),
            "workers": [
                {
                    **w.to_dict(),
                    "is_healthy": w.is_healthy(self.timeout_seconds)
                }
                for w in workers
            ],
            "timestamp": datetime.utcnow().isoformat()
        }


class KanchiApp:
    def __init__(self):
        self.task_store = TaskStore()
        self.worker_store = WorkerStore()
        self.ws_manager = WebSocketManager()
        self.task_manager = TaskManager(self.task_store, self.worker_store, self.ws_manager)
        self.migration_manager = MigrationManager()
        self.health_monitor = WorkerHealthMonitor(self.worker_store, self.ws_manager)
        self._setup_migrations()

    def _setup_migrations(self):
        def migration_001_initial():
            logger.info("Initial schema setup complete (in-memory)")

        def migration_002_add_indexes():
            logger.info("Index setup complete (in-memory)")

        self.migration_manager.register_migration(
            "001",
            "Initial schema",
            migration_001_initial
        )
        self.migration_manager.register_migration(
            "002",
            "Add indexes",
            migration_002_add_indexes
        )

    def startup(self):
        logger.info("Starting Kanchi...")
        self.migration_manager.run_migrations()
        self.health_monitor.start()
        logger.info("Kanchi started successfully")

    def shutdown(self):
        logger.info("Shutting down Kanchi...")
        self.health_monitor.stop()
        logger.info("Kanchi shut down")

    async def handle_websocket(self, connection_id: str) -> WebSocketConnection:
        conn = WebSocketConnection(connection_id)
        self.ws_manager.add_connection(conn)

        summary = self.task_manager.get_summary()
        await conn.send({
            "type": "connected",
            "connection_id": connection_id,
            "summary": summary,
            "timestamp": datetime.utcnow().isoformat()
        })

        return conn

    async def disconnect_websocket(self, connection_id: str):
        self.ws_manager.remove_connection(connection_id)

    async def process_event(self, event: Dict[str, Any]):
        await self.task_manager.process_event(event)

    def get_api_response(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        params = params or {}

        if endpoint == "/api/tasks":
            task_filter = TaskFilter(
                name=params.get("name"),
                state=TaskState(params["state"]) if params.get("state") else None,
                worker=params.get("worker"),
                search_text=params.get("search"),
                limit=int(params.get("limit", 100)),
                offset=int(params.get("offset", 0)),
                orphans_only=params.get("orphans_only", False)
            )
            if params.get("date_from"):
                task_filter.date_from = datetime.fromisoformat(params["date_from"])
            if params.get("date_to"):
                task_filter.date_to = datetime.fromisoformat(params["date_to"])

            tasks = self.task_manager.get_tasks(task_filter)
            total = self.task_manager.count_tasks(task_filter)
            return {
                "tasks": [t.to_dict() for t in tasks],
                "total": total,
                "limit": task_filter.limit,
                "offset": task_filter.offset
            }

        elif endpoint == "/api/tasks/summary":
            return self.task_manager.get_summary()

        elif endpoint == "/api/tasks/stats":
            stats = self.task_manager.get_daily_stats(
                date=params.get("date"),
                task_name=params.get("task_name")
            )
            return {"stats": [s.to_dict() for s in stats]}

        elif endpoint == "/api/workers":
            workers = self.task_manager.get_workers()
            return {
                "workers": [w.to_dict() for w in workers],
                "total": len(workers)
            }

        elif endpoint == "/api/workers/health":
            return self.health_monitor.get_health_report()

        elif endpoint == "/api/orphans":
            orphans = self.task_manager.get_orphan_tasks()
            return {
                "orphans": [t.to_dict() for t in orphans],
                "total": len(orphans)
            }

        else:
            return {"error": f"Unknown endpoint: {endpoint}"}


class CeleryEventSimulator:
    def __init__(self, app: KanchiApp):
        self.app = app
        self._running = False

    async def simulate_task_lifecycle(self, task_name: str = "myapp.tasks.process_data",
                                      worker: str = "celery@worker1"):
        task_id = str(uuid.uuid4())

        await self.app.process_event({
            "type": "task-sent",
            "uuid": task_id,
            "name": task_name,
            "args": "[1, 2, 3]",
            "kwargs": "{}",
            "queue": "default"
        })

        await asyncio.sleep(0.1)

        await self.app.process_event({
            "type": "task-received",
            "uuid": task_id,
            "name": task_name,
            "hostname": worker
        })

        await asyncio.sleep(0.1)

        await self.app.process_event({
            "type": "task-started",
            "uuid": task_id,
            "hostname": worker,
            "pid": 12345
        })

        await asyncio.sleep(0.2)

        import random
        if random.random() > 0.3:
            await self.app.process_event({
                "type": "task-succeeded",
                "uuid": task_id,
                "hostname": worker,
                "result": "{'status': 'ok'}",
                "runtime": random.uniform(0.1, 5.0)
            })
        else:
            await self.app.process_event({
                "type": "task-failed",
                "uuid": task_id,
                "hostname": worker,
                "exception": "ValueError: Something went wrong",
                "traceback": "Traceback (most recent call last):\n  ...\nValueError: Something went wrong"
            })

        return task_id

    async def simulate_worker_events(self, hostname: str = "celery@worker1"):
        await self.app.process_event({
            "type": "worker-online",
            "hostname": hostname,
            "pid": 12345,
            "sw_ident": "py-celery",
            "sw_ver": "5.3.0",
            "sw_sys": "Linux"
        })

        for _ in range(3):
            await asyncio.sleep(1)
            await self.app.process_event({
                "type": "worker-heartbeat",
                "hostname": hostname,
                "processed": 42,
                "active": 2,
                "loadavg": [0.5, 0.3, 0.2]
            })


async def main():
    app = KanchiApp()
    app.startup()

    simulator = CeleryEventSimulator(app)

    await simulator.simulate_worker_events("celery@worker1")

    task_names = [
        "myapp.tasks.send_email",
        "myapp.tasks.process_payment",
        "myapp.tasks.generate_report",
        "myapp.tasks.sync_data"
    ]

    task_ids = []
    for i in range(10):
        import random
        task_name = random.choice(task_names)
        task_id = await simulator.simulate_task_lifecycle(task_name, "celery@worker1")
        task_ids.append(task_id)

    print("\n=== Kanchi Task Monitor Summary ===")
    summary = app.task_manager.get_summary()
    print(json.dumps(summary, indent=2))

    print("\n=== All Tasks ===")
    tasks_response = app.get_api_response("/api/tasks", {"limit": "5"})
    print(f"Total tasks: {tasks_response['total']}")
    for task in tasks_response['tasks'][:3]:
        print(f"  - {task['task_id'][:8]}... | {task['name']} | {task['state']}")

    print("\n=== Workers ===")
    workers_response = app.get_api_response("/api/workers")
    print(json.dumps(workers_response, indent=2))

    print("\n=== Worker Health ===")
    health_response = app.get_api_response("/api/workers/health")
    print(f"Healthy: {health_response['healthy_workers']}/{health_response['total_workers']}")

    print("\n=== Daily Stats ===")
    stats_response = app.get_api_response("/api/tasks/stats")
    for stat in stats_response['stats']:
        print(f"  {stat['task_name']}: succeeded={stat['succeeded']}, failed={stat['failed']}")

    print("\n=== Search Tasks ===")
    search_results = app.task_manager.search_tasks("email")
    print(f"Found {len(search_results)} tasks matching 'email'")

    print("\n=== Filter by Status ===")
    success_tasks = app.task_manager.filter_by_status(TaskState.SUCCESS)
    failed_tasks = app.task_manager.filter_by_status(TaskState.FAILURE)
    print(f"Successful tasks: {len(success_tasks)}")
    print(f"Failed tasks: {len(failed_tasks)}")

    print("\n=== WebSocket Simulation ===")
    conn = await app.handle_websocket("test-connection-1")
    conn.subscribe("tasks")
    conn.subscribe("workers")
    print(f"WebSocket connections: {app.ws_manager.connection_count()}")

    msg = await conn.receive()
    if msg:
        print(f"Received message type: {msg.get('type')}")

    await app.disconnect_websocket("test-connection-1")
    print(f"WebSocket connections after disconnect: {app.ws_manager.connection_count()}")

    print("\n=== Migrations ===")
    applied = app.migration_manager.get_applied_migrations()
    print(f"Applied migrations: {applied}")

    app.shutdown()
    print("\nKanchi shutdown complete.")


if __name__ == "__main__":
    asyncio.run(main())