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
        status: str = TaskStatus.PENDING,
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
        self.status = status
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
            "status": self.status,
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
            "updated_at": self.updated_at.isoformat(),
        }

    def __repr__(self) -> str:
        return f"<Task id={self.task_id} name={self.name} status={self.status}>"


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
        last_heartbeat: Optional[datetime] = None,
    ):
        self.hostname = hostname
        self.status = status
        self.active = active
        self.processed = processed
        self.failed = failed
        self.retried = retried
        self.loadavg = loadavg or []
        self.heartbeat_expires = heartbeat_expires
        self.freq = freq
        self.sw_ident = sw_ident
        self.sw_ver = sw_ver
        self.sw_sys = sw_sys
        self.pid = pid
        self.last_heartbeat = last_heartbeat or datetime.utcnow()
        self.registered_tasks: List[str] = []

    @property
    def is_alive(self) -> bool:
        if self.heartbeat_expires:
            return time.time() < self.heartbeat_expires
        threshold = datetime.utcnow() - timedelta(seconds=30)
        return self.last_heartbeat > threshold

    def to_dict(self) -> Dict:
        return {
            "hostname": self.hostname,
            "status": self.status,
            "active": self.active,
            "processed": self.processed,
            "failed": self.failed,
            "retried": self.retried,
            "loadavg": self.loadavg,
            "heartbeat_expires": self.heartbeat_expires,
            "freq": self.freq,
            "sw_ident": self.sw_ident,
            "sw_ver": self.sw_ver,
            "sw_sys": self.sw_sys,
            "pid": self.pid,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "is_alive": self.is_alive,
            "registered_tasks": self.registered_tasks,
        }

    def __repr__(self) -> str:
        return f"<Worker hostname={self.hostname} status={self.status}>"


class TaskStatistics:
    def __init__(self, date: Optional[datetime] = None):
        self.date = date or datetime.utcnow().date()
        self.total = 0
        self.succeeded = 0
        self.failed = 0
        self.retried = 0
        self.revoked = 0
        self.pending = 0
        self.started = 0
        self.avg_runtime: Optional[float] = None
        self._runtimes: List[float] = []

    def update_avg_runtime(self, runtime: float):
        self._runtimes.append(runtime)
        self.avg_runtime = sum(self._runtimes) / len(self._runtimes)

    def to_dict(self) -> Dict:
        return {
            "date": str(self.date),
            "total": self.total,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "retried": self.retried,
            "revoked": self.revoked,
            "pending": self.pending,
            "started": self.started,
            "avg_runtime": self.avg_runtime,
        }

    def __repr__(self) -> str:
        return f"<TaskStatistics date={self.date} total={self.total}>"


class TaskFilter:
    def __init__(
        self,
        status: Optional[str] = None,
        name: Optional[str] = None,
        worker: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        search: Optional[str] = None,
        task_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ):
        self.status = status
        self.name = name
        self.worker = worker
        self.date_from = date_from
        self.date_to = date_to
        self.search = search
        self.task_id = task_id
        self.page = max(1, page)
        self.page_size = min(max(1, page_size), 100)

    def matches(self, task: Task) -> bool:
        if self.task_id and task.task_id != self.task_id:
            return False
        if self.status and task.status != self.status:
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
                task.traceback or "",
            ]).lower()
            if search_lower not in searchable:
                return False
        return True


class TaskStore:
    def __init__(self, max_tasks: int = 10000):
        self._tasks: Dict[str, Task] = {}
        self._lock = threading.RLock()
        self.max_tasks = max_tasks

    def add_task(self, task: Task) -> None:
        with self._lock:
            if len(self._tasks) >= self.max_tasks:
                oldest_key = min(
                    self._tasks.keys(),
                    key=lambda k: self._tasks[k].received or datetime.min
                )
                del self._tasks[oldest_key]
            self._tasks[task.task_id] = task

    def get_task(self, task_id: str) -> Optional[Task]:
        with self._lock:
            return self._tasks.get(task_id)

    def update_task(self, task_id: str, **kwargs) -> Optional[Task]:
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                for key, value in kwargs.items():
                    if hasattr(task, key):
                        setattr(task, key, value)
                task.updated_at = datetime.utcnow()
            return task

    def delete_task(self, task_id: str) -> bool:
        with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
                return True
            return False

    def get_all_tasks(self) -> List[Task]:
        with self._lock:
            return list(self._tasks.values())

    def filter_tasks(self, task_filter: TaskFilter) -> Tuple[List[Task], int]:
        with self._lock:
            all_tasks = list(self._tasks.values())

        filtered = [t for t in all_tasks if task_filter.matches(t)]
        filtered.sort(key=lambda t: t.received or datetime.min, reverse=True)

        total = len(filtered)
        start = (task_filter.page - 1) * task_filter.page_size
        end = start + task_filter.page_size
        return filtered[start:end], total

    def get_orphan_tasks(self) -> List[Task]:
        with self._lock:
            tasks = list(self._tasks.values())
        orphans = []
        for task in tasks:
            if task.parent_id and task.parent_id not in self._tasks:
                orphans.append(task)
        return orphans

    def get_retry_chain(self, task_id: str) -> List[Task]:
        with self._lock:
            tasks = list(self._tasks.values())
        chain = []
        current_id = task_id
        visited = set()
        while current_id and current_id not in visited:
            visited.add(current_id)
            task = self._tasks.get(current_id)
            if task:
                chain.append(task)
                current_id = task.parent_id
            else:
                break
        return chain

    def count(self) -> int:
        with self._lock:
            return len(self._tasks)

    def clear(self) -> None:
        with self._lock:
            self._tasks.clear()


class WorkerStore:
    def __init__(self):
        self._workers: Dict[str, Worker] = {}
        self._lock = threading.RLock()

    def add_worker(self, worker: Worker) -> None:
        with self._lock:
            self._workers[worker.hostname] = worker

    def get_worker(self, hostname: str) -> Optional[Worker]:
        with self._lock:
            return self._workers.get(hostname)

    def update_worker(self, hostname: str, **kwargs) -> Optional[Worker]:
        with self._lock:
            worker = self._workers.get(hostname)
            if worker:
                for key, value in kwargs.items():
                    if hasattr(worker, key):
                        setattr(worker, key, value)
            return worker

    def get_all_workers(self) -> List[Worker]:
        with self._lock:
            return list(self._workers.values())

    def get_online_workers(self) -> List[Worker]:
        with self._lock:
            return [w for w in self._workers.values() if w.is_alive]

    def remove_worker(self, hostname: str) -> bool:
        with self._lock:
            if hostname in self._workers:
                del self._workers[hostname]
                return True
            return False

    def count(self) -> int:
        with self._lock:
            return len(self._workers)


class StatisticsStore:
    def __init__(self):
        self._daily_stats: Dict[str, TaskStatistics] = {}
        self._task_name_stats: Dict[str, Dict] = defaultdict(lambda: {
            "total": 0, "succeeded": 0, "failed": 0, "retried": 0,
            "avg_runtime": None, "_runtimes": []
        })
        self._lock = threading.RLock()

    def _get_date_key(self, dt: Optional[datetime] = None) -> str:
        if dt is None:
            dt = datetime.utcnow()
        return str(dt.date())

    def get_daily_stats(self, date: Optional[datetime] = None) -> TaskStatistics:
        key = self._get_date_key(date)
        with self._lock:
            if key not in self._daily_stats:
                self._daily_stats[key] = TaskStatistics(
                    datetime.strptime(key, "%Y-%m-%d") if date is None else date
                )
            return self._daily_stats[key]

    def get_history(self, days: int = 7) -> List[TaskStatistics]:
        result = []
        for i in range(days):
            date = datetime.utcnow() - timedelta(days=i)
            key = self._get_date_key(date)
            with self._lock:
                if key in self._daily_stats:
                    result.append(self._daily_stats[key])
                else:
                    result.append(TaskStatistics(date))
        return result

    def record_task_event(self, task: Task, event_type: str) -> None:
        with self._lock:
            stats = self.get_daily_stats(task.received)
            name_stats = self._task_name_stats[task.name]

            if event_type == "task-received":
                stats.total += 1
                stats.pending += 1
                name_stats["total"] += 1
            elif event_type == "task-started":
                stats.started += 1
                if stats.pending > 0:
                    stats.pending -= 1
            elif event_type == "task-succeeded":
                stats.succeeded += 1
                if stats.started > 0:
                    stats.started -= 1
                name_stats["succeeded"] += 1
                if task.runtime:
                    stats.update_avg_runtime(task.runtime)
                    name_stats["_runtimes"].append(task.runtime)
                    name_stats["avg_runtime"] = sum(name_stats["_runtimes"]) / len(name_stats["_runtimes"])
            elif event_type == "task-failed":
                stats.failed += 1
                if stats.started > 0:
                    stats.started -= 1
                name_stats["failed"] += 1
            elif event_type == "task-retried":
                stats.retried += 1
                name_stats["retried"] += 1
            elif event_type == "task-revoked":
                stats.revoked += 1
                if stats.pending > 0:
                    stats.pending -= 1

    def get_task_name_stats(self) -> Dict[str, Dict]:
        with self._lock:
            result = {}
            for name, stats in self._task_name_stats.items():
                result[name] = {k: v for k, v in stats.items() if not k.startswith("_")}
            return result

    def get_all_daily_stats(self) -> List[TaskStatistics]:
        with self._lock:
            return sorted(self._daily_stats.values(), key=lambda s: s.date, reverse=True)


class WebSocketConnection:
    def __init__(self, connection_id: str):
        self.connection_id = connection_id
        self.connected_at = datetime.utcnow()
        self._queue: asyncio.Queue = asyncio.Queue()
        self._closed = False
        self.subscriptions: List[str] = []

    async def send(self, message: Dict) -> None:
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

    def subscribe(self, channel: str) -> None:
        if channel not in self.subscriptions:
            self.subscriptions.append(channel)

    def unsubscribe(self, channel: str) -> None:
        if channel in self.subscriptions:
            self.subscriptions.remove(channel)


class WebSocketManager:
    def __init__(self):
        self._connections: Dict[str, WebSocketConnection] = {}
        self._lock = threading.RLock()

    def connect(self, connection_id: Optional[str] = None) -> WebSocketConnection:
        if connection_id is None:
            connection_id = str(uuid.uuid4())
        conn = WebSocketConnection(connection_id)
        with self._lock:
            self._connections[connection_id] = conn
        logger.info(f"WebSocket connected: {connection_id}")
        return conn

    def disconnect(self, connection_id: str) -> None:
        with self._lock:
            conn = self._connections.pop(connection_id, None)
            if conn:
                conn.close()
        logger.info(f"WebSocket disconnected: {connection_id}")

    async def broadcast(self, message: Dict, channel: Optional[str] = None) -> None:
        with self._lock:
            connections = list(self._connections.values())

        for conn in connections:
            if conn.is_closed:
                continue
            if channel is None or channel in conn.subscriptions:
                try:
                    await conn.send(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to {conn.connection_id}: {e}")

    async def send_to(self, connection_id: str, message: Dict) -> bool:
        with self._lock:
            conn = self._connections.get(connection_id)
        if conn and not conn.is_closed:
            await conn.send(message)
            return True
        return False

    def get_connection(self, connection_id: str) -> Optional[WebSocketConnection]:
        with self._lock:
            return self._connections.get(connection_id)

    def count(self) -> int:
        with self._lock:
            return len(self._connections)

    def get_all_connections(self) -> List[WebSocketConnection]:
        with self._lock:
            return list(self._connections.values())


class EventProcessor:
    def __init__(
        self,
        task_store: TaskStore,
        worker_store: WorkerStore,
        stats_store: StatisticsStore,
        ws_manager: WebSocketManager,
    ):
        self.task_store = task_store
        self.worker_store = worker_store
        self.stats_store = stats_store
        self.ws_manager = ws_manager
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

    async def process_event(self, event: Dict) -> None:
        event_type = event.get("type")
        if not event_type:
            logger.warning(f"Event missing type: {event}")
            return

        handler = self._event_handlers.get(event_type)
        if handler:
            try:
                await handler(event)
            except Exception as e:
                logger.error(f"Error processing event {event_type}: {e}")
        else:
            logger.debug(f"No handler for event type: {event_type}")

    async def _handle_task_received(self, event: Dict) -> None:
        task_id = event.get("uuid") or event.get("task_id")
        if not task_id:
            return

        task = Task(
            task_id=task_id,
            name=event.get("name", "unknown"),
            status=TaskStatus.RECEIVED,
            worker=event.get("hostname"),
            args=event.get("args", []),
            kwargs=event.get("kwargs", {}),
            received=self._parse_datetime(event.get("timestamp")),
            eta=self._parse_datetime(event.get("eta")),
            expires=self._parse_datetime(event.get("expires")),
            hostname=event.get("hostname"),
            exchange=event.get("exchange"),
            routing_key=event.get("routing_key"),
            clock=event.get("clock"),
            client=event.get("client"),
            parent_id=event.get("parent_id"),
            root_id=event.get("root_id"),
            retries=event.get("retries", 0),
        )

        self.task_store.add_task(task)
        self.stats_store.record_task_event(task, "task-received")

        await self.ws_manager.broadcast({
            "type": "task-received",
            "task": task.to_dict(),
        })

    async def _handle_task_started(self, event: Dict) -> None:
        task_id = event.get("uuid") or event.get("task_id")
        if not task_id:
            return

        task = self.task_store.get_task(task_id)
        if not task:
            task = Task(
                task_id=task_id,
                name=event.get("name", "unknown"),
                status=TaskStatus.STARTED,
                worker=event.get("hostname"),
                hostname=event.get("hostname"),
            )
            self.task_store.add_task(task)
        else:
            task.status = TaskStatus.STARTED
            task.started = self._parse_datetime(event.get("timestamp"))
            task.worker = event.get("hostname", task.worker)
            task.hostname = event.get("hostname", task.hostname)
            task.pid = event.get("pid", task.pid)
            task.updated_at = datetime.utcnow()

        self.stats_store.record_task_event(task, "task-started")

        worker = self.worker_store.get_worker(task.worker or "")
        if worker:
            worker.active += 1

        await self.ws_manager.broadcast({
            "type": "task-started",
            "task": task.to_dict(),
        })

    async def _handle_task_succeeded(self, event: Dict) -> None:
        task_id = event.get("uuid") or event.get("task_id")
        if not task_id:
            return

        task = self.task_store.get_task(task_id)
        if not task:
            task = Task(
                task_id=task_id,
                name=event.get("name", "unknown"),
                status=TaskStatus.SUCCESS,
                worker=event.get("hostname"),
            )
            self.task_store.add_task(task)

        task.status = TaskStatus.SUCCESS
        task.succeeded = self._parse_datetime(event.get("timestamp"))
        task.result = event.get("result")
        task.runtime = event.get("runtime")
        task.updated_at = datetime.utcnow()

        self.stats_store.record_task_event(task, "task-succeeded")

        worker = self.worker_store.get_worker(task.worker or "")
        if worker:
            if worker.active > 0:
                worker.active -= 1
            worker.processed += 1

        await self.ws_manager.broadcast({
            "type": "task-succeeded",
            "task": task.to_dict(),
        })

    async def _handle_task_failed(self, event: Dict) -> None:
        task_id = event.get("uuid") or event.get("task_id")
        if not task_id:
            return

        task = self.task_store.get_task(task_id)
        if not task:
            task = Task(
                task_id=task_id,
                name=event.get("name", "unknown"),
                status=TaskStatus.FAILURE,
                worker=event.get("hostname"),
            )
            self.task_store.add_task(task)

        task.status = TaskStatus.FAILURE
        task.failed = self._parse_datetime(event.get("timestamp"))
        task.traceback = event.get("traceback")
        task.result = event.get("exception")
        task.updated_at = datetime.utcnow()

        self.stats_store.record_task_event(task, "task-failed")

        worker = self.worker_store.get_worker(task.worker or "")
        if worker:
            if worker.active > 0:
                worker.active -= 1
            worker.failed += 1

        await self.ws_manager.broadcast({
            "type": "task-failed",
            "task": task.to_dict(),
        })

    async def _handle_task_retried(self, event: Dict) -> None:
        task_id = event.get("uuid") or event.get("task_id")
        if not task_id:
            return

        task = self.task_store.get_task(task_id)
        if not task:
            task = Task(
                task_id=task_id,
                name=event.get("name", "unknown"),
                status=TaskStatus.RETRY,
                worker=event.get("hostname"),
            )
            self.task_store.add_task(task)

        task.status = TaskStatus.RETRY
        task.retried = self._parse_datetime(event.get("timestamp"))
        task.retries += 1
        task.traceback = event.get("traceback")
        task.updated_at = datetime.utcnow()

        self.stats_store.record_task_event(task, "task-retried")

        worker = self.worker_store.get_worker(task.worker or "")
        if worker:
            worker.retried += 1

        await self.ws_manager.broadcast({
            "type": "task-retried",
            "task": task.to_dict(),
        })

    async def _handle_task_revoked(self, event: Dict) -> None:
        task_id = event.get("uuid") or event.get("task_id")
        if not task_id:
            return

        task = self.task_store.get_task(task_id)
        if not task:
            task = Task(
                task_id=task_id,
                name=event.get("name", "unknown"),
                status=TaskStatus.REVOKED,
                worker=event.get("hostname"),
            )
            self.task_store.add_task(task)

        task.status = TaskStatus.REVOKED
        task.revoked = self._parse_datetime(event.get("timestamp"))
        task.updated_at = datetime.utcnow()

        self.stats_store.record_task_event(task, "task-revoked")

        await self.ws_manager.broadcast({
            "type": "task-revoked",
            "task": task.to_dict(),
        })

    async def _handle_worker_online(self, event: Dict) -> None:
        hostname = event.get("hostname")
        if not hostname:
            return

        worker = self.worker_store.get_worker(hostname)
        if not worker:
            worker = Worker(
                hostname=hostname,
                status="online",
                sw_ident=event.get("sw_ident"),
                sw_ver=event.get("sw_ver"),
                sw_sys=event.get("sw_sys"),
                pid=event.get("pid"),
            )
            self.worker_store.add_worker(worker)
        else:
            worker.status = "online"
            worker.last_heartbeat = datetime.utcnow()

        await self.ws_manager.broadcast({
            "type": "worker-online",
            "worker": worker.to_dict(),
        })

    async def _handle_worker_offline(self, event: Dict) -> None:
        hostname = event.get("hostname")
        if not hostname:
            return

        worker = self.worker_store.get_worker(hostname)
        if worker:
            worker.status = "offline"
            worker.active = 0

        await self.ws_manager.broadcast({
            "type": "worker-offline",
            "worker": worker.to_dict() if worker else {"hostname": hostname},
        })

    async def _handle_worker_heartbeat(self, event: Dict) -> None:
        hostname = event.get("hostname")
        if not hostname:
            return

        worker = self.worker_store.get_worker(hostname)
        if not worker:
            worker = Worker(hostname=hostname, status="online")
            self.worker_store.add_worker(worker)

        worker.last_heartbeat = datetime.utcnow()
        worker.status = "online"
        worker.active = event.get("active", worker.active)
        worker.processed = event.get("processed", worker.processed)
        worker.loadavg = event.get("loadavg", worker.loadavg)
        worker.heartbeat_expires = event.get("expires", worker.heartbeat_expires)
        worker.freq = event.get("freq", worker.freq)
        worker.sw_ident = event.get("sw_ident", worker.sw_ident)
        worker.sw_ver = event.get("sw_ver", worker.sw_ver)
        worker.sw_sys = event.get("sw_sys", worker.sw_sys)
        worker.pid = event.get("pid", worker.pid)

        await self.ws_manager.broadcast({
            "type": "worker-heartbeat",
            "worker": worker.to_dict(),
        })

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
                try:
                    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%f")
                except ValueError:
                    try:
                        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")
                    except ValueError:
                        return None
        return None


class MigrationManager:
    def __init__(self):
        self._migrations: List[Dict] = []
        self._applied: List[str] = []
        self._lock = threading.Lock()

    def register_migration(self, version: str, description: str, up_fn, down_fn=None) -> None:
        with self._lock:
            self._migrations.append({
                "version": version,
                "description": description,
                "up": up_fn,
                "down": down_fn,
                "applied": False,
            })
            self._migrations.sort(key=lambda m: m["version"])

    def run_migrations(self) -> List[str]:
        applied = []
        with self._lock:
            for migration in self._migrations:
                if migration["version"] not in self._applied:
                    try:
                        migration["up"]()
                        self._applied.append(migration["version"])
                        migration["applied"] = True
                        applied.append(migration["version"])
                        logger.info(f"Applied migration: {migration['version']} - {migration['description']}")
                    except Exception as e:
                        logger.error(f"Failed to apply migration {migration['version']}: {e}")
                        raise
        return applied

    def rollback_migration(self, version: str) -> bool:
        with self._lock:
            for migration in reversed(self._migrations):
                if migration["version"] == version and version in self._applied:
                    if migration["down"]:
                        try:
                            migration["down"]()
                            self._applied.remove(version)
                            migration["applied"] = False
                            logger.info(f"Rolled back migration: {version}")
                            return True
                        except Exception as e:
                            logger.error(f"Failed to rollback migration {version}: {e}")
                            raise
        return False

    def get_status(self) -> List[Dict]:
        with self._lock:
            return [
                {
                    "version": m["version"],
                    "description": m["description"],
                    "applied": m["version"] in self._applied,
                }
                for m in self._migrations
            ]

    def get_applied_versions(self) -> List[str]:
        with self._lock:
            return list(self._applied)


class TaskManager:
    def __init__(
        self,
        task_store: TaskStore,
        worker_store: WorkerStore,
        stats_store: StatisticsStore,
        ws_manager: WebSocketManager,
        event_processor: EventProcessor,
    ):
        self.task_store = task_store
        self.worker_store = worker_store
        self.stats_store = stats_store
        self.ws_manager = ws_manager
        self.event_processor = event_processor

    def get_task(self, task_id: str) -> Optional[Task]:
        return self.task_store.get_task(task_id)

    def get_tasks(self, task_filter: Optional[TaskFilter] = None) -> Tuple[List[Task], int]:
        if task_filter is None:
            task_filter = TaskFilter()
        return self.task_store.filter_tasks(task_filter)

    def get_all_tasks(self) -> List[Task]:
        return self.task_store.get_all_tasks()

    def delete_task(self, task_id: str) -> bool:
        return self.task_store.delete_task(task_id)

    def get_orphan_tasks(self) -> List[Task]:
        return self.task_store.get_orphan_tasks()

    def get_retry_chain(self, task_id: str) -> List[Task]:
        return self.task_store.get_retry_chain(task_id)

    def get_workers(self) -> List[Worker]:
        return self.worker_store.get_all_workers()

    def get_worker(self, hostname: str) -> Optional[Worker]:
        return self.worker_store.get_worker(hostname)

    def get_online_workers(self) -> List[Worker]:
        return self.worker_store.get_online_workers()

    def get_daily_stats(self, date: Optional[datetime] = None) -> TaskStatistics:
        return self.stats_store.get_daily_stats(date)

    def get_stats_history(self, days: int = 7) -> List[TaskStatistics]:
        return self.stats_store.get_history(days)

    def get_task_name_stats(self) -> Dict[str, Dict]:
        return self.stats_store.get_task_name_stats()

    def get_overview(self) -> Dict:
        all_tasks = self.task_store.get_all_tasks()
        status_counts = defaultdict(int)
        for task in all_tasks:
            status_counts[task.status] += 1

        workers = self.worker_store.get_all_workers()
        online_workers = [w for w in workers if w.is_alive]

        today_stats = self.stats_store.get_daily_stats()

        return {
            "tasks": {
                "total": len(all_tasks),
                "by_status": dict(status_counts),
            },
            "workers": {
                "total": len(workers),
                "online": len(online_workers),
                "offline": len(workers) - len(online_workers),
            },
            "today": today_stats.to_dict(),
            "orphans": len(self.task_store.get_orphan_tasks()),
        }

    async def process_event(self, event: Dict) -> None:
        await self.event_processor.process_event(event)

    def search_tasks(self, query: str, page: int = 1, page_size: int = 20) -> Tuple[List[Task], int]:
        task_filter = TaskFilter(search=query, page=page, page_size=page_size)
        return self.task_store.filter_tasks(task_filter)

    def get_task_history(self, task_name: str) -> List[Task]:
        all_tasks = self.task_store.get_all_tasks()
        return [t for t in all_tasks if t.name == task_name]

    def purge_tasks(self, status: Optional[str] = None, before: Optional[datetime] = None) -> int:
        all_tasks = self.task_store.get_all_tasks()
        purged = 0
        for task in all_tasks:
            should_purge = True
            if status and task.status != status:
                should_purge = False
            if before and task.received and task.received >= before:
                should_purge = False
            if should_purge:
                self.task_store.delete_task(task.task_id)
                purged += 1
        return purged


class KanchiMonitor:
    def __init__(self, max_tasks: int = 10000):
        self.task_store = TaskStore(max_tasks=max_tasks)
        self.worker_store = WorkerStore()
        self.stats_store = StatisticsStore()
        self.ws_manager = WebSocketManager()
        self.migration_manager = MigrationManager()

        self.event_processor = EventProcessor(
            task_store=self.task_store,
            worker_store=self.worker_store,
            stats_store=self.stats_store,
            ws_manager=self.ws_manager,
        )

        self.task_manager = TaskManager(
            task_store=self.task_store,
            worker_store=self.worker_store,
            stats_store=self.stats_store,
            ws_manager=self.ws_manager,
            event_processor=self.event_processor,
        )

        self._running = False
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._setup_default_migrations()

    def _setup_default_migrations(self) -> None:
        def migration_001_up():
            logger.info("Migration 001: Initialize task store")

        def migration_002_up():
            logger.info("Migration 002: Initialize worker store")

        def migration_003_up():
            logger.info("Migration 003: Initialize statistics store")

        self.migration_manager.register_migration(
            "001", "Initialize task store", migration_001_up
        )
        self.migration_manager.register_migration(
            "002", "Initialize worker store", migration_002_up
        )
        self.migration_manager.register_migration(
            "003", "Initialize statistics store", migration_003_up
        )

    def run_migrations(self) -> List[str]:
        return self.migration_manager.run_migrations()

    async def start(self) -> None:
        self._running = True
        self.run_migrations()
        logger.info("KanchiMonitor started")
        await self._process_events()

    async def stop(self) -> None:
        self._running = False
        logger.info("KanchiMonitor stopped")

    async def _process_events(self) -> None:
        while self._running:
            try:
                event = await asyncio.wait_for(self._event_queue.get(), timeout=1.0)
                await self.event_processor.process_event(event)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing event: {e}")

    async def send_event(self, event: Dict) -> None:
        await self._event_queue.put(event)

    async def process_event(self, event: Dict) -> None:
        await self.event_processor.process_event(event)

    def connect_websocket(self, connection_id: Optional[str] = None) -> WebSocketConnection:
        return self.ws_manager.connect(connection_id)

    def disconnect_websocket(self, connection_id: str) -> None:
        self.ws_manager.disconnect(connection_id)

    def get_overview(self) -> Dict:
        return self.task_manager.get_overview()

    def get_tasks(self, task_filter: Optional[TaskFilter] = None) -> Tuple[List[Task], int]:
        return self.task_manager.get_tasks(task_filter)

    def get_task(self, task_id: str) -> Optional[Task]:
        return self.task_manager.get_task(task_id)

    def get_workers(self) -> List[Worker]:
        return self.task_manager.get_workers()

    def get_worker(self, hostname: str) -> Optional[Worker]:
        return self.task_manager.get_worker(hostname)

    def get_stats(self, days: int = 7) -> List[TaskStatistics]:
        return self.task_manager.get_stats_history(days)

    def get_daily_stats(self, date: Optional[datetime] = None) -> TaskStatistics:
        return self.task_manager.get_daily_stats(date)

    def get_task_name_stats(self) -> Dict[str, Dict]:
        return self.task_manager.get_task_name_stats()

    def search_tasks(self, query: str, page: int = 1, page_size: int = 20) -> Tuple[List[Task], int]:
        return self.task_manager.search_tasks(query, page, page_size)

    def get_orphan_tasks(self) -> List[Task]:
        return self.task_manager.get_orphan_tasks()

    def get_retry_chain(self, task_id: str) -> List[Task]:
        return self.task_manager.get_retry_chain(task_id)

    def purge_tasks(self, status: Optional[str] = None, before: Optional[datetime] = None) -> int:
        return self.task_manager.purge_tasks(status, before)

    def delete_task(self, task_id: str) -> bool:
        return self.task_manager.delete_task(task_id)

    def get_migration_status(self) -> List[Dict]:
        return self.migration_manager.get_status()

    def __repr__(self) -> str:
        return (
            f"<KanchiMonitor tasks={self.task_store.count()} "
            f"workers={self.worker_store.count()} "
            f"connections={self.ws_manager.count()}>"
        )


async def demo():
    monitor = KanchiMonitor(max_tasks=1000)

    migrations = monitor.run_migrations()
    print(f"Applied migrations: {migrations}")

    ws_conn = monitor.connect_websocket("client-1")
    ws_conn.subscribe("tasks")

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
            "type": "task-received",
            "uuid": "task-001",
            "name": "myapp.tasks.send_email",
            "hostname": "celery@worker1",
            "args": ["user@example.com"],
            "kwargs": {"subject": "Hello"},
            "timestamp": datetime.utcnow().timestamp(),
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
            "result": "Email sent successfully",
            "runtime": 0.5,
            "timestamp": datetime.utcnow().timestamp(),
        },
        {
            "type": "task-received",
            "uuid": "task-002",
            "name": "myapp.tasks.process_data",
            "hostname": "celery@worker1",
            "args": [42],
            "kwargs": {},
            "timestamp": datetime.utcnow().timestamp(),
        },
        {
            "type": "task-started",
            "uuid": "task-002",
            "hostname": "celery@worker1",
            "timestamp": datetime.utcnow().timestamp(),
        },
        {
            "type": "task-failed",
            "uuid": "task-002",
            "hostname": "celery@worker1",
            "exception": "ValueError: Invalid data",
            "traceback": "Traceback (most recent call last):\n  ...\nValueError: Invalid data",
            "timestamp": datetime.utcnow().timestamp(),
        },
        {
            "type": "task-received",
            "uuid": "task-003",
            "name": "myapp.tasks.process_data",
            "hostname": "celery@worker1",
            "args": [42],
            "kwargs": {},
            "parent_id": "task-002",
            "retries": 1,
            "timestamp": datetime.utcnow().timestamp(),
        },
        {
            "type": "worker-heartbeat",
            "hostname": "celery@worker1",
            "active": 1,
            "processed": 1,
            "loadavg": [0.1, 0.2, 0.3],
            "freq": 2.0,
        },
    ]

    for event in events:
        await monitor.process_event(event)

    print("\n=== Overview ===")
    overview = monitor.get_overview()
    print(json.dumps(overview, indent=2))

    print("\n=== All Tasks ===")
    tasks, total = monitor.get_tasks()
    print(f"Total tasks: {total}")
    for task in tasks:
        print(f"  {task}")

    print("\n=== Workers ===")
    workers = monitor.get_workers()
    for worker in workers:
        print(f"  {worker}")

    print("\n=== Daily Stats ===")
    stats = monitor.get_daily_stats()
    print(json.dumps(stats.to_dict(), indent=2))

    print("\n=== Task Name Stats ===")
    name_stats = monitor.get_task_name_stats()
    print(json.dumps(name_stats, indent=2))

    print("\n=== Filter by Status (FAILURE) ===")
    task_filter = TaskFilter(status=TaskStatus.FAILURE)
    failed_tasks, total = monitor.get_tasks(task_filter)
    print(f"Failed tasks: {total}")
    for task in failed_tasks:
        print(f"  {task}")

    print("\n=== Search Tasks ===")
    search_results, total = monitor.search_tasks("process_data")
    print(f"Search results for 'process_data': {total}")
    for task in search_results:
        print(f"  {task}")

    print("\n=== Orphan Tasks ===")
    orphans = monitor.get_orphan_tasks()
    print(f"Orphan tasks: {len(orphans)}")
    for task in orphans:
        print(f"  {task} (parent_id={task.parent_id})")

    print("\n=== Retry Chain for task-003 ===")
    chain = monitor.get_retry_chain("task-003")
    print(f"Retry chain length: {len(chain)}")
    for task in chain:
        print(f"  {task}")

    print("\n=== Stats History (7 days) ===")
    history = monitor.get_stats(days=7)
    for stat in history:
        if stat.total > 0:
            print(f"  {stat}")

    print("\n=== Migration Status ===")
    migration_status = monitor.get_migration_status()
    for m in migration_status:
        print(f"  {m['version']}: {m['description']} - Applied: {m['applied']}")

    print("\n=== WebSocket Messages ===")
    messages = []
    while True:
        msg = await ws_conn.receive()
        if msg is None:
            break
        messages.append(json.loads(msg))

    print(f"Received {len(messages)} WebSocket messages")
    for msg in messages[:3]:
        print(f"  Type: {msg['type']}")

    monitor.disconnect_websocket("client-1")

    print(f"\n{monitor}")


if __name__ == "__main__":
    asyncio.run(demo())