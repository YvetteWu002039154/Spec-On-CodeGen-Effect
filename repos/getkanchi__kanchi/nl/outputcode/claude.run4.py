import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict
import threading
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TaskStatus:
    PENDING = "PENDING"
    STARTED = "STARTED"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    RETRY = "RETRY"
    REVOKED = "REVOKED"
    RECEIVED = "RECEIVED"


class Task:
    def __init__(
        self,
        task_id: str,
        name: str,
        state: str = TaskStatus.PENDING,
        worker: Optional[str] = None,
        args: Optional[List] = None,
        kwargs: Optional[Dict] = None,
        result: Optional[Any] = None,
        traceback: Optional[str] = None,
        received: Optional[datetime] = None,
        started: Optional[datetime] = None,
        succeeded: Optional[datetime] = None,
        failed: Optional[datetime] = None,
        retried: Optional[datetime] = None,
        revoked: Optional[datetime] = None,
        runtime: Optional[float] = None,
        retries: int = 0,
        parent_id: Optional[str] = None,
        root_id: Optional[str] = None,
        eta: Optional[datetime] = None,
        expires: Optional[datetime] = None,
        hostname: Optional[str] = None,
        exchange: Optional[str] = None,
        routing_key: Optional[str] = None,
        clock: Optional[int] = None,
        client: Optional[str] = None,
    ):
        self.task_id = task_id
        self.name = name
        self.state = state
        self.worker = worker
        self.args = args or []
        self.kwargs = kwargs or {}
        self.result = result
        self.traceback = traceback
        self.received = received or datetime.utcnow()
        self.started = started
        self.succeeded = succeeded
        self.failed = failed
        self.retried = retried
        self.revoked = revoked
        self.runtime = runtime
        self.retries = retries
        self.parent_id = parent_id
        self.root_id = root_id
        self.eta = eta
        self.expires = expires
        self.hostname = hostname
        self.exchange = exchange
        self.routing_key = routing_key
        self.clock = clock
        self.client = client
        self.updated_at = datetime.utcnow()

    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "state": self.state,
            "worker": self.worker,
            "args": self.args,
            "kwargs": self.kwargs,
            "result": str(self.result) if self.result is not None else None,
            "traceback": self.traceback,
            "received": self.received.isoformat() if self.received else None,
            "started": self.started.isoformat() if self.started else None,
            "succeeded": self.succeeded.isoformat() if self.succeeded else None,
            "failed": self.failed.isoformat() if self.failed else None,
            "retried": self.retried.isoformat() if self.retried else None,
            "revoked": self.revoked.isoformat() if self.revoked else None,
            "runtime": self.runtime,
            "retries": self.retries,
            "parent_id": self.parent_id,
            "root_id": self.root_id,
            "eta": self.eta.isoformat() if self.eta else None,
            "expires": self.expires.isoformat() if self.expires else None,
            "hostname": self.hostname,
            "exchange": self.exchange,
            "routing_key": self.routing_key,
            "clock": self.clock,
            "client": self.client,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def is_orphan(self) -> bool:
        if self.state in (TaskStatus.STARTED, TaskStatus.RECEIVED):
            if self.started:
                elapsed = (datetime.utcnow() - self.started).total_seconds()
                return elapsed > 3600
            elif self.received:
                elapsed = (datetime.utcnow() - self.received).total_seconds()
                return elapsed > 3600
        return False

    def __repr__(self) -> str:
        return f"<Task id={self.task_id} name={self.name} state={self.state}>"


class Worker:
    def __init__(
        self,
        hostname: str,
        status: str = "online",
        active: int = 0,
        processed: int = 0,
        failed: int = 0,
        retried: int = 0,
        loadavg: Optional[List[float]] = None,
        heartbeat_expires: Optional[float] = None,
        freq: float = 2.0,
        sw_ident: Optional[str] = None,
        sw_ver: Optional[str] = None,
        sw_sys: Optional[str] = None,
        pid: Optional[int] = None,
        concurrency: Optional[int] = None,
        pool: Optional[str] = None,
        queues: Optional[List[str]] = None,
    ):
        self.hostname = hostname
        self.status = status
        self.active = active
        self.processed = processed
        self.failed = failed
        self.retried = retried
        self.loadavg = loadavg or []
        self.heartbeat_expires = heartbeat_expires or (time.time() + 10)
        self.freq = freq
        self.sw_ident = sw_ident
        self.sw_ver = sw_ver
        self.sw_sys = sw_sys
        self.pid = pid
        self.concurrency = concurrency
        self.pool = pool
        self.queues = queues or []
        self.last_heartbeat = datetime.utcnow()

    @property
    def is_alive(self) -> bool:
        return time.time() < self.heartbeat_expires

    def update_heartbeat(self, expires: Optional[float] = None):
        self.last_heartbeat = datetime.utcnow()
        self.heartbeat_expires = expires or (time.time() + 10)
        self.status = "online"

    def to_dict(self) -> Dict:
        return {
            "hostname": self.hostname,
            "status": self.status if self.is_alive else "offline",
            "active": self.active,
            "processed": self.processed,
            "failed": self.failed,
            "retried": self.retried,
            "loadavg": self.loadavg,
            "freq": self.freq,
            "sw_ident": self.sw_ident,
            "sw_ver": self.sw_ver,
            "sw_sys": self.sw_sys,
            "pid": self.pid,
            "concurrency": self.concurrency,
            "pool": self.pool,
            "queues": self.queues,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "is_alive": self.is_alive,
        }

    def __repr__(self) -> str:
        return f"<Worker hostname={self.hostname} status={self.status}>"


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
    ):
        self.state = state
        self.name = name
        self.worker = worker
        self.date_from = date_from
        self.date_to = date_to
        self.search = search
        self.task_id = task_id

    def matches(self, task: Task) -> bool:
        if self.task_id and task.task_id != self.task_id:
            return False
        if self.state and task.state != self.state:
            return False
        if self.name and self.name.lower() not in task.name.lower():
            return False
        if self.worker and task.worker and self.worker.lower() not in task.worker.lower():
            return False
        if self.date_from and task.received and task.received < self.date_from:
            return False
        if self.date_to and task.received and task.received > self.date_to:
            return False
        if self.search:
            search_lower = self.search.lower()
            searchable = " ".join([
                task.task_id or "",
                task.name or "",
                task.worker or "",
                str(task.args),
                str(task.kwargs),
                str(task.result) if task.result else "",
                task.traceback or "",
            ]).lower()
            if search_lower not in searchable:
                return False
        return True


class DailyTaskStats:
    def __init__(self, date: datetime):
        self.date = date.date() if isinstance(date, datetime) else date
        self.total = 0
        self.succeeded = 0
        self.failed = 0
        self.retried = 0
        self.task_counts: Dict[str, int] = defaultdict(int)

    def record_task(self, task: Task):
        self.total += 1
        if task.state == TaskStatus.SUCCESS:
            self.succeeded += 1
        elif task.state == TaskStatus.FAILURE:
            self.failed += 1
        elif task.state == TaskStatus.RETRY:
            self.retried += 1
        self.task_counts[task.name] += 1

    def to_dict(self) -> Dict:
        return {
            "date": self.date.isoformat(),
            "total": self.total,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "retried": self.retried,
            "task_counts": dict(self.task_counts),
        }

    def __repr__(self) -> str:
        return f"<DailyTaskStats date={self.date} total={self.total}>"


class TaskStore:
    def __init__(self, max_tasks: int = 10000):
        self._tasks: Dict[str, Task] = {}
        self._lock = threading.RLock()
        self.max_tasks = max_tasks

    def add_or_update(self, task: Task) -> Task:
        with self._lock:
            self._tasks[task.task_id] = task
            self._evict_if_needed()
            return task

    def get(self, task_id: str) -> Optional[Task]:
        with self._lock:
            return self._tasks.get(task_id)

    def delete(self, task_id: str) -> bool:
        with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
                return True
            return False

    def all(self) -> List[Task]:
        with self._lock:
            return list(self._tasks.values())

    def filter(self, task_filter: TaskFilter) -> List[Task]:
        with self._lock:
            return [t for t in self._tasks.values() if task_filter.matches(t)]

    def count(self) -> int:
        with self._lock:
            return len(self._tasks)

    def _evict_if_needed(self):
        if len(self._tasks) > self.max_tasks:
            sorted_tasks = sorted(
                self._tasks.values(),
                key=lambda t: t.received or datetime.min
            )
            to_remove = len(self._tasks) - self.max_tasks
            for task in sorted_tasks[:to_remove]:
                del self._tasks[task.task_id]

    def get_stats_by_state(self) -> Dict[str, int]:
        with self._lock:
            stats = defaultdict(int)
            for task in self._tasks.values():
                stats[task.state] += 1
            return dict(stats)

    def get_orphans(self) -> List[Task]:
        with self._lock:
            return [t for t in self._tasks.values() if t.is_orphan()]

    def clear(self):
        with self._lock:
            self._tasks.clear()


class WorkerStore:
    def __init__(self):
        self._workers: Dict[str, Worker] = {}
        self._lock = threading.RLock()

    def add_or_update(self, worker: Worker) -> Worker:
        with self._lock:
            self._workers[worker.hostname] = worker
            return worker

    def get(self, hostname: str) -> Optional[Worker]:
        with self._lock:
            return self._workers.get(hostname)

    def all(self) -> List[Worker]:
        with self._lock:
            return list(self._workers.values())

    def online(self) -> List[Worker]:
        with self._lock:
            return [w for w in self._workers.values() if w.is_alive]

    def offline(self) -> List[Worker]:
        with self._lock:
            return [w for w in self._workers.values() if not w.is_alive]

    def count(self) -> int:
        with self._lock:
            return len(self._workers)

    def remove(self, hostname: str) -> bool:
        with self._lock:
            if hostname in self._workers:
                del self._workers[hostname]
                return True
            return False

    def update_heartbeat(self, hostname: str, expires: Optional[float] = None) -> Optional[Worker]:
        with self._lock:
            worker = self._workers.get(hostname)
            if worker:
                worker.update_heartbeat(expires)
            return worker


class StatsHistory:
    def __init__(self, max_days: int = 30):
        self._history: Dict[str, DailyTaskStats] = {}
        self._lock = threading.RLock()
        self.max_days = max_days

    def record(self, task: Task):
        with self._lock:
            date_key = (task.received or datetime.utcnow()).date().isoformat()
            if date_key not in self._history:
                self._history[date_key] = DailyTaskStats(
                    task.received or datetime.utcnow()
                )
            self._history[date_key].record_task(task)
            self._evict_old()

    def get_daily_stats(self, date: Optional[datetime] = None) -> Optional[DailyTaskStats]:
        with self._lock:
            if date is None:
                date = datetime.utcnow()
            date_key = date.date().isoformat() if isinstance(date, datetime) else date.isoformat()
            return self._history.get(date_key)

    def get_range(self, date_from: datetime, date_to: datetime) -> List[DailyTaskStats]:
        with self._lock:
            result = []
            current = date_from.date() if isinstance(date_from, datetime) else date_from
            end = date_to.date() if isinstance(date_to, datetime) else date_to
            while current <= end:
                key = current.isoformat()
                if key in self._history:
                    result.append(self._history[key])
                current += timedelta(days=1)
            return result

    def all(self) -> List[DailyTaskStats]:
        with self._lock:
            return sorted(self._history.values(), key=lambda s: s.date)

    def _evict_old(self):
        if len(self._history) > self.max_days:
            sorted_keys = sorted(self._history.keys())
            to_remove = len(self._history) - self.max_days
            for key in sorted_keys[:to_remove]:
                del self._history[key]


class WebSocketClient:
    def __init__(self, client_id: str, filters: Optional[Dict] = None):
        self.client_id = client_id
        self.filters = filters or {}
        self.connected_at = datetime.utcnow()
        self._queue: asyncio.Queue = asyncio.Queue()
        self.is_connected = True

    async def send(self, message: Dict):
        if self.is_connected:
            await self._queue.put(message)

    async def receive(self) -> Optional[Dict]:
        try:
            return await asyncio.wait_for(self._queue.get(), timeout=1.0)
        except asyncio.TimeoutError:
            return None

    def disconnect(self):
        self.is_connected = False

    def to_dict(self) -> Dict:
        return {
            "client_id": self.client_id,
            "filters": self.filters,
            "connected_at": self.connected_at.isoformat(),
            "is_connected": self.is_connected,
        }


class WebSocketManager:
    def __init__(self):
        self._clients: Dict[str, WebSocketClient] = {}
        self._lock = threading.RLock()

    def connect(self, client_id: Optional[str] = None, filters: Optional[Dict] = None) -> WebSocketClient:
        if client_id is None:
            client_id = str(uuid.uuid4())
        client = WebSocketClient(client_id=client_id, filters=filters)
        with self._lock:
            self._clients[client_id] = client
        logger.info(f"WebSocket client connected: {client_id}")
        return client

    def disconnect(self, client_id: str):
        with self._lock:
            client = self._clients.pop(client_id, None)
            if client:
                client.disconnect()
                logger.info(f"WebSocket client disconnected: {client_id}")

    def get_client(self, client_id: str) -> Optional[WebSocketClient]:
        with self._lock:
            return self._clients.get(client_id)

    def get_all_clients(self) -> List[WebSocketClient]:
        with self._lock:
            return list(self._clients.values())

    async def broadcast(self, message: Dict, event_type: str = "task_update"):
        payload = {"type": event_type, "data": message, "timestamp": datetime.utcnow().isoformat()}
        with self._lock:
            clients = list(self._clients.values())
        for client in clients:
            if client.is_connected:
                try:
                    await client.send(payload)
                except Exception as e:
                    logger.error(f"Error broadcasting to client {client.client_id}: {e}")

    async def send_to_client(self, client_id: str, message: Dict, event_type: str = "message"):
        client = self.get_client(client_id)
        if client and client.is_connected:
            payload = {"type": event_type, "data": message, "timestamp": datetime.utcnow().isoformat()}
            await client.send(payload)

    def count(self) -> int:
        with self._lock:
            return len(self._clients)


class RetryTracker:
    def __init__(self):
        self._retry_chains: Dict[str, List[str]] = defaultdict(list)
        self._lock = threading.RLock()

    def record_retry(self, original_task_id: str, new_task_id: str):
        with self._lock:
            self._retry_chains[original_task_id].append(new_task_id)

    def get_retry_chain(self, task_id: str) -> List[str]:
        with self._lock:
            return list(self._retry_chains.get(task_id, []))

    def get_retry_count(self, task_id: str) -> int:
        with self._lock:
            return len(self._retry_chains.get(task_id, []))

    def find_original(self, task_id: str) -> Optional[str]:
        with self._lock:
            for original, retries in self._retry_chains.items():
                if task_id in retries:
                    return original
            return None

    def to_dict(self) -> Dict:
        with self._lock:
            return dict(self._retry_chains)


class MigrationManager:
    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url
        self._migrations: List[Dict] = []
        self._applied: List[str] = []
        self._lock = threading.RLock()

    def register_migration(self, version: str, description: str, up_sql: str, down_sql: str):
        with self._lock:
            self._migrations.append({
                "version": version,
                "description": description,
                "up_sql": up_sql,
                "down_sql": down_sql,
                "created_at": datetime.utcnow().isoformat(),
            })

    def get_pending_migrations(self) -> List[Dict]:
        with self._lock:
            return [m for m in self._migrations if m["version"] not in self._applied]

    def apply_migration(self, version: str) -> bool:
        with self._lock:
            migration = next((m for m in self._migrations if m["version"] == version), None)
            if migration and version not in self._applied:
                self._applied.append(version)
                logger.info(f"Applied migration: {version} - {migration['description']}")
                return True
            return False

    def run_auto_migrations(self) -> int:
        pending = self.get_pending_migrations()
        count = 0
        for migration in pending:
            if self.apply_migration(migration["version"]):
                count += 1
        return count

    def get_applied_migrations(self) -> List[str]:
        with self._lock:
            return list(self._applied)

    def to_dict(self) -> Dict:
        with self._lock:
            return {
                "total": len(self._migrations),
                "applied": len(self._applied),
                "pending": len(self._migrations) - len(self._applied),
                "migrations": self._migrations,
                "applied_versions": self._applied,
            }


class EventProcessor:
    def __init__(
        self,
        task_store: TaskStore,
        worker_store: WorkerStore,
        stats_history: StatsHistory,
        retry_tracker: RetryTracker,
        ws_manager: WebSocketManager,
    ):
        self.task_store = task_store
        self.worker_store = worker_store
        self.stats_history = stats_history
        self.retry_tracker = retry_tracker
        self.ws_manager = ws_manager
        self._event_handlers: Dict[str, Any] = {}
        self._setup_handlers()

    def _setup_handlers(self):
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

    def process_event(self, event: Dict) -> Optional[Task]:
        event_type = event.get("type", "")
        handler = self._event_handlers.get(event_type)
        if handler:
            return handler(event)
        else:
            logger.warning(f"Unknown event type: {event_type}")
            return None

    def _handle_task_received(self, event: Dict) -> Task:
        task_id = event.get("uuid", str(uuid.uuid4()))
        existing = self.task_store.get(task_id)
        if existing:
            task = existing
        else:
            task = Task(
                task_id=task_id,
                name=event.get("name", "unknown"),
                state=TaskStatus.RECEIVED,
                worker=event.get("hostname"),
                args=event.get("args", []),
                kwargs=event.get("kwargs", {}),
                received=datetime.utcfromtimestamp(event["timestamp"]) if "timestamp" in event else datetime.utcnow(),
                eta=datetime.utcfromtimestamp(event["eta"]) if event.get("eta") else None,
                expires=datetime.utcfromtimestamp(event["expires"]) if event.get("expires") else None,
                retries=event.get("retries", 0),
                parent_id=event.get("parent_id"),
                root_id=event.get("root_id"),
                hostname=event.get("hostname"),
                exchange=event.get("exchange"),
                routing_key=event.get("routing_key"),
                clock=event.get("clock"),
                client=event.get("client"),
            )
        task.state = TaskStatus.RECEIVED
        self.task_store.add_or_update(task)
        return task

    def _handle_task_started(self, event: Dict) -> Task:
        task_id = event.get("uuid", str(uuid.uuid4()))
        task = self.task_store.get(task_id)
        if not task:
            task = Task(
                task_id=task_id,
                name=event.get("name", "unknown"),
                state=TaskStatus.STARTED,
                worker=event.get("hostname"),
                hostname=event.get("hostname"),
            )
        task.state = TaskStatus.STARTED
        task.started = datetime.utcfromtimestamp(event["timestamp"]) if "timestamp" in event else datetime.utcnow()
        task.worker = event.get("hostname", task.worker)
        task.pid = event.get("pid")
        task.updated_at = datetime.utcnow()
        self.task_store.add_or_update(task)
        return task

    def _handle_task_succeeded(self, event: Dict) -> Task:
        task_id = event.get("uuid", str(uuid.uuid4()))
        task = self.task_store.get(task_id)
        if not task:
            task = Task(
                task_id=task_id,
                name=event.get("name", "unknown"),
                state=TaskStatus.SUCCESS,
                worker=event.get("hostname"),
            )
        task.state = TaskStatus.SUCCESS
        task.succeeded = datetime.utcfromtimestamp(event["timestamp"]) if "timestamp" in event else datetime.utcnow()
        task.result = event.get("result")
        task.runtime = event.get("runtime")
        task.updated_at = datetime.utcnow()
        self.task_store.add_or_update(task)
        self.stats_history.record(task)
        return task

    def _handle_task_failed(self, event: Dict) -> Task:
        task_id = event.get("uuid", str(uuid.uuid4()))
        task = self.task_store.get(task_id)
        if not task:
            task = Task(
                task_id=task_id,
                name=event.get("name", "unknown"),
                state=TaskStatus.FAILURE,
                worker=event.get("hostname"),
            )
        task.state = TaskStatus.FAILURE
        task.failed = datetime.utcfromtimestamp(event["timestamp"]) if "timestamp" in event else datetime.utcnow()
        task.result = event.get("exception")
        task.traceback = event.get("traceback")
        task.updated_at = datetime.utcnow()
        self.task_store.add_or_update(task)
        self.stats_history.record(task)
        return task

    def _handle_task_retried(self, event: Dict) -> Task:
        task_id = event.get("uuid", str(uuid.uuid4()))
        task = self.task_store.get(task_id)
        if not task:
            task = Task(
                task_id=task_id,
                name=event.get("name", "unknown"),
                state=TaskStatus.RETRY,
                worker=event.get("hostname"),
            )
        task.state = TaskStatus.RETRY
        task.retried = datetime.utcfromtimestamp(event["timestamp"]) if "timestamp" in event else datetime.utcnow()
        task.retries += 1
        task.traceback = event.get("traceback")
        task.updated_at = datetime.utcnow()

        if event.get("new_task_id"):
            self.retry_tracker.record_retry(task_id, event["new_task_id"])

        self.task_store.add_or_update(task)
        self.stats_history.record(task)
        return task

    def _handle_task_revoked(self, event: Dict) -> Task:
        task_id = event.get("uuid", str(uuid.uuid4()))
        task = self.task_store.get(task_id)
        if not task:
            task = Task(
                task_id=task_id,
                name=event.get("name", "unknown"),
                state=TaskStatus.REVOKED,
                worker=event.get("hostname"),
            )
        task.state = TaskStatus.REVOKED
        task.revoked = datetime.utcfromtimestamp(event["timestamp"]) if "timestamp" in event else datetime.utcnow()
        task.updated_at = datetime.utcnow()
        self.task_store.add_or_update(task)
        return task

    def _handle_worker_online(self, event: Dict) -> Optional[Worker]:
        hostname = event.get("hostname")
        if not hostname:
            return None
        worker = self.worker_store.get(hostname)
        if not worker:
            worker = Worker(hostname=hostname)
        worker.status = "online"
        worker.sw_ident = event.get("sw_ident")
        worker.sw_ver = event.get("sw_ver")
        worker.sw_sys = event.get("sw_sys")
        worker.pid = event.get("pid")
        worker.concurrency = event.get("concurrency")
        worker.pool = event.get("pool")
        worker.queues = event.get("queues", [])
        worker.update_heartbeat()
        self.worker_store.add_or_update(worker)
        logger.info(f"Worker online: {hostname}")
        return worker

    def _handle_worker_offline(self, event: Dict) -> Optional[Worker]:
        hostname = event.get("hostname")
        if not hostname:
            return None
        worker = self.worker_store.get(hostname)
        if worker:
            worker.status = "offline"
            worker.heartbeat_expires = 0
            self.worker_store.add_or_update(worker)
            logger.info(f"Worker offline: {hostname}")
        return worker

    def _handle_worker_heartbeat(self, event: Dict) -> Optional[Worker]:
        hostname = event.get("hostname")
        if not hostname:
            return None
        worker = self.worker_store.get(hostname)
        if not worker:
            worker = Worker(hostname=hostname)
        worker.active = event.get("active", worker.active)
        worker.processed = event.get("processed", worker.processed)
        worker.loadavg = event.get("loadavg", worker.loadavg)
        worker.freq = event.get("freq", worker.freq)
        expires = event.get("expires")
        worker.update_heartbeat(expires)
        self.worker_store.add_or_update(worker)
        return worker


class SearchEngine:
    def __init__(self, task_store: TaskStore):
        self.task_store = task_store

    def search(
        self,
        query: Optional[str] = None,
        state: Optional[str] = None,
        name: Optional[str] = None,
        worker: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        task_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        sort_by: str = "received",
        sort_desc: bool = True,
    ) -> Tuple[List[Task], int]:
        task_filter = TaskFilter(
            state=state,
            name=name,
            worker=worker,
            date_from=date_from,
            date_to=date_to,
            search=query,
            task_id=task_id,
        )
        tasks = self.task_store.filter(task_filter)

        def sort_key(t: Task):
            val = getattr(t, sort_by, None)
            if val is None:
                return datetime.min if sort_by in ("received", "started", "succeeded", "failed") else ""
            return val

        tasks.sort(key=sort_key, reverse=sort_desc)
        total = len(tasks)
        return tasks[offset:offset + limit], total

    def get_task_names(self) -> List[str]:
        tasks = self.task_store.all()
        return list(set(t.name for t in tasks))

    def get_worker_names(self) -> List[str]:
        tasks = self.task_store.all()
        return list(set(t.worker for t in tasks if t.worker))


class KanchiMonitor:
    def __init__(
        self,
        max_tasks: int = 10000,
        max_history_days: int = 30,
        db_url: Optional[str] = None,
    ):
        self.task_store = TaskStore(max_tasks=max_tasks)
        self.worker_store = WorkerStore()
        self.stats_history = StatsHistory(max_days=max_history_days)
        self.retry_tracker = RetryTracker()
        self.ws_manager = WebSocketManager()
        self.migration_manager = MigrationManager(db_url=db_url)
        self.event_processor = EventProcessor(
            task_store=self.task_store,
            worker_store=self.worker_store,
            stats_history=self.stats_history,
            retry_tracker=self.retry_tracker,
            ws_manager=self.ws_manager,
        )
        self.search_engine = SearchEngine(task_store=self.task_store)
        self._running = False
        self._setup_default_migrations()

    def _setup_default_migrations(self):
        self.migration_manager.register_migration(
            version="001",
            description="Create tasks table",
            up_sql="""
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
                    updated_at TIMESTAMP
                )
            """,
            down_sql="DROP TABLE IF EXISTS tasks",
        )
        self.migration_manager.register_migration(
            version="002",
            description="Create workers table",
            up_sql="""
                CREATE TABLE IF NOT EXISTS workers (
                    hostname VARCHAR(255) PRIMARY KEY,
                    status VARCHAR(50),
                    active INTEGER DEFAULT 0,
                    processed INTEGER DEFAULT 0,
                    failed INTEGER DEFAULT 0,
                    retried INTEGER DEFAULT 0,
                    loadavg TEXT,
                    heartbeat_expires FLOAT,
                    freq FLOAT,
                    sw_ident VARCHAR(255),
                    sw_ver VARCHAR(255),
                    sw_sys VARCHAR(255),
                    pid INTEGER,
                    concurrency INTEGER,
                    pool VARCHAR(255),
                    queues TEXT,
                    last_heartbeat TIMESTAMP
                )
            """,
            down_sql="DROP TABLE IF EXISTS workers",
        )
        self.migration_manager.register_migration(
            version="003",
            description="Create daily_stats table",
            up_sql="""
                CREATE TABLE IF NOT EXISTS daily_stats (
                    date DATE PRIMARY KEY,
                    total INTEGER DEFAULT 0,
                    succeeded INTEGER DEFAULT 0,
                    failed INTEGER DEFAULT 0,
                    retried INTEGER DEFAULT 0,
                    task_counts TEXT
                )
            """,
            down_sql="DROP TABLE IF EXISTS daily_stats",
        )

    def run_migrations(self) -> int:
        return self.migration_manager.run_auto_migrations()

    def process_event(self, event: Dict) -> Optional[Any]:
        result = self.event_processor.process_event(event)
        if result and isinstance(result, Task):
            asyncio.run(self._broadcast_task_update(result))
        return result

    async def process_event_async(self, event: Dict) -> Optional[Any]:
        result = self.event_processor.process_event(event)
        if result and isinstance(result, Task):
            await self._broadcast_task_update(result)
        return result

    async def _broadcast_task_update(self, task: Task):
        await self.ws_manager.broadcast(task.to_dict(), event_type="task_update")

    def get_task(self, task_id: str) -> Optional[Task]:
        return self.task_store.get(task_id)

    def get_all_tasks(self) -> List[Task]:
        return self.task_store.all()

    def search_tasks(
        self,
        query: Optional[str] = None,
        state: Optional[str] = None,
        name: Optional[str] = None,
        worker: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        task_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        sort_by: str = "received",
        sort_desc: bool = True,
    ) -> Tuple[List[Task], int]:
        return self.search_engine.search(
            query=query,
            state=state,
            name=name,
            worker=worker,
            date_from=date_from,
            date_to=date_to,
            task_id=task_id,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_desc=sort_desc,
        )

    def get_task_stats(self) -> Dict:
        state_stats = self.task_store.get_stats_by_state()
        orphans = self.task_store.get_orphans()
        workers_online = len(self.worker_store.online())
        workers_offline = len(self.worker_store.offline())
        return {
            "total_tasks": self.task_store.count(),
            "by_state": state_stats,
            "orphans": len(orphans),
            "workers_online": workers_online,
            "workers_offline": workers_offline,
            "total_workers": self.worker_store.count(),
            "ws_clients": self.ws_manager.count(),
        }

    def get_workers(self) -> List[Worker]:
        return self.worker_store.all()

    def get_worker(self, hostname: str) -> Optional[Worker]:
        return self.worker_store.get(hostname)

    def get_daily_stats(self, date: Optional[datetime] = None) -> Optional[DailyTaskStats]:
        return self.stats_history.get_daily_stats(date)

    def get_stats_history(self, days: int = 7) -> List[DailyTaskStats]:
        date_to = datetime.utcnow()
        date_from = date_to - timedelta(days=days)
        return self.stats_history.get_range(date_from, date_to)

    def get_orphans(self) -> List[Task]:
        return self.task_store.get_orphans()

    def get_retry_chain(self, task_id: str) -> List[str]:
        return self.retry_tracker.get_retry_chain(task_id)

    def connect_websocket(self, client_id: Optional[str] = None, filters: Optional[Dict] = None) -> WebSocketClient:
        return self.ws_manager.connect(client_id=client_id, filters=filters)

    def disconnect_websocket(self, client_id: str):
        self.ws_manager.disconnect(client_id)

    def get_task_names(self) -> List[str]:
        return self.search_engine.get_task_names()

    def get_worker_names(self) -> List[str]:
        return self.search_engine.get_worker_names()

    def clear_tasks(self):
        self.task_store.clear()

    def get_summary(self) -> Dict:
        stats = self.get_task_stats()
        today_stats = self.get_daily_stats()
        return {
            "stats": stats,
            "today": today_stats.to_dict() if today_stats else None,
            "workers": [w.to_dict() for w in self.get_workers()],
            "migrations": self.migration_manager.to_dict(),
        }

    def __repr__(self) -> str:
        return (
            f"<KanchiMonitor tasks={self.task_store.count()} "
            f"workers={self.worker_store.count()} "
            f"ws_clients={self.ws_manager.count()}>"
        )


class CeleryEventReceiver:
    def __init__(self, monitor: KanchiMonitor):
        self.monitor = monitor
        self._running = False

    def _map_celery_event(self, event: Dict) -> Dict:
        mapped = dict(event)
        event_type = event.get("type", "")
        if event_type.startswith("task-"):
            mapped["uuid"] = event.get("uuid", event.get("task_id"))
        return mapped

    def process_celery_event(self, event: Dict):
        mapped = self._map_celery_event(event)
        return self.monitor.process_event(mapped)

    async def process_celery_event_async(self, event: Dict):
        mapped = self._map_celery_event(event)
        return await self.monitor.process_event_async(mapped)

    def simulate_task_lifecycle(self, task_name: str, worker: str = "worker@localhost") -> Task:
        task_id = str(uuid.uuid4())
        now = time.time()

        self.process_celery_event({
            "type": "task-received",
            "uuid": task_id,
            "name": task_name,
            "hostname": worker,
            "timestamp": now,
            "args": [],
            "kwargs": {},
            "retries": 0,
        })

        self.process_celery_event({
            "type": "task-started",
            "uuid": task_id,
            "hostname": worker,
            "timestamp": now + 0.1,
        })

        self.process_celery_event({
            "type": "task-succeeded",
            "uuid": task_id,
            "hostname": worker,
            "timestamp": now + 1.0,
            "result": "success",
            "runtime": 0.9,
        })

        return self.monitor.get_task(task_id)


class KanchiAPI:
    def __init__(self, monitor: KanchiMonitor):
        self.monitor = monitor

    def get_tasks(
        self,
        page: int = 1,
        per_page: int = 20,
        state: Optional[str] = None,
        name: Optional[str] = None,
        worker: Optional[str] = None,
        search: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        sort_by: str = "received",
        sort_desc: bool = True,
    ) -> Dict:
        df = datetime.fromisoformat(date_from) if date_from else None
        dt = datetime.fromisoformat(date_to) if date_to else None
        offset = (page - 1) * per_page
        tasks, total = self.monitor.search_tasks(
            query=search,
            state=state,
            name=name,
            worker=worker,
            date_from=df,
            date_to=dt,
            limit=per_page,
            offset=offset,
            sort_by=sort_by,
            sort_desc=sort_desc,
        )
        return {
            "tasks": [t.to_dict() for t in tasks],
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page if per_page > 0 else 0,
        }

    def get_task(self, task_id: str) -> Optional[Dict]:
        task = self.monitor.get_task(task_id)
        if task:
            result = task.to_dict()
            result["retry_chain"] = self.monitor.get_retry_chain(task_id)
            result["is_orphan"] = task.is_orphan()
            return result
        return None

    def get_workers(self) -> Dict:
        workers = self.monitor.get_workers()
        return {
            "workers": [w.to_dict() for w in workers],
            "total": len(workers),
            "online": len([w for w in workers if w.is_alive]),
            "offline": len([w for w in workers if not w.is_alive]),
        }

    def get_worker(self, hostname: str) -> Optional[Dict]:
        worker = self.monitor.get_worker(hostname)
        return worker.to_dict() if worker else None

    def get_stats(self) -> Dict:
        return self.monitor.get_task_stats()

    def get_daily_stats(self, date: Optional[str] = None) -> Optional[Dict]:
        dt = datetime.fromisoformat(date) if date else None
        stats = self.monitor.get_daily_stats(dt)
        return stats.to_dict() if stats else None

    def get_history(self, days: int = 7) -> Dict:
        history = self.monitor.get_stats_history(days=days)
        return {
            "history": [s.to_dict() for s in history],
            "days": days,
        }

    def get_orphans(self) -> Dict:
        orphans = self.monitor.get_orphans()
        return {
            "orphans": [t.to_dict() for t in orphans],
            "total": len(orphans),
        }

    def get_summary(self) -> Dict:
        return self.monitor.get_summary()

    def get_task_names(self) -> List[str]:
        return self.monitor.get_task_names()

    def get_worker_names(self) -> List[str]:
        return self.monitor.get_worker_names()


def create_monitor(
    max_tasks: int = 10000,
    max_history_days: int = 30,
    db_url: Optional[str] = None,
    run_migrations: bool = True,
) -> KanchiMonitor:
    monitor = KanchiMonitor(
        max_tasks=max_tasks,
        max_history_days=max_history_days,
        db_url=db_url,
    )
    if run_migrations:
        applied = monitor.run_migrations()
        logger.info(f"Applied {applied} migrations")
    return monitor


def create_api(monitor: Optional[KanchiMonitor] = None) -> KanchiAPI:
    if monitor is None:
        monitor = create_monitor()
    return KanchiAPI(monitor=monitor)


if __name__ == "__main__":
    monitor = create_monitor()
    api = create_api(monitor)
    receiver = CeleryEventReceiver(monitor)

    receiver.process_celery_event({
        "type": "worker-online",
        "hostname": "celery@worker1",
        "sw_ident": "py-celery",
        "sw_ver": "5.3.0",
        "sw_sys": "Linux",
        "pid": 12345,
        "concurrency": 4,
        "pool": "prefork",
        "queues": ["default", "high_priority"],
    })

    for i in range(5):
        task = receiver.simulate_task_lifecycle(
            f"myapp.tasks.task_{i % 3}",
            worker="celery@worker1"
        )
        logger.info(f"Simulated task: {task}")

    receiver.process_celery_event({
        "type": "task-received",
        "uuid": "failed-task-001",
        "name": "myapp.tasks.failing_task",
        "hostname": "celery@worker1",
        "timestamp": time.time(),
    })
    receiver.process_celery_event({
        "type": "task-started",
        "uuid": "failed-task-001",
        "hostname": "celery@worker1",
        "timestamp": time.time(),
    })
    receiver.process_celery_event({
        "type": "task-failed",
        "uuid": "failed-task-001",
        "hostname": "celery@worker1",
        "timestamp": time.time(),
        "exception": "ValueError: Something went wrong",
        "traceback": "Traceback (most recent call last):\n  ...\nValueError: Something went wrong",
    })

    receiver.process_celery_event({
        "type": "task-received",
        "uuid": "retry-task-001",
        "name": "myapp.tasks.retry_task",
        "hostname": "celery@worker1",
        "timestamp": time.time(),
        "retries": 0,
    })
    receiver.process_celery_event({
        "type": "task-retried",
        "uuid": "retry-task-001",
        "hostname": "celery@worker1",
        "timestamp": time.time(),
        "new_task_id": "retry-task-002",
        "traceback": "Traceback...",
    })

    receiver.process_celery_event({
        "type": "worker-heartbeat",
        "hostname": "celery@worker1",
        "active": 2,
        "processed": 100,
        "loadavg": [0.5, 0.3, 0.2],
        "freq": 2.0,
    })

    print("\n=== Kanchi Monitor Summary ===")
    summary = api.get_summary()
    print(json.dumps(summary, indent=2, default=str))

    print("\n=== Task Search ===")
    result = api.get_tasks(state="SUCCESS", per_page=10)
    print(f"Found {result['total']} successful tasks")

    print("\n=== Workers ===")
    workers = api.get_workers()
    print(json.dumps(workers, indent=2, default=str))

    print("\n=== Orphans ===")
    orphans = api.get_orphans()
    print(f"Found {orphans['total']} orphan tasks")

    print("\n=== Stats History ===")
    history = api.get_history(days=7)
    print(json.dumps(history, indent=2, default=str))

    print(f"\n{monitor}")