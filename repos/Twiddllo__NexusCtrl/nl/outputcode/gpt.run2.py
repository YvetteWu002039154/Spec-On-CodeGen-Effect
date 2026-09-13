from __future__ import annotations

import base64
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Dict, List, Optional, Tuple


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Priority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"


class ServerStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"


@dataclass(frozen=True)
class PerformanceSample:
    timestamp: datetime
    cpu_percent: float
    ram_percent: float
    net_sent_bytes_per_sec: float
    net_recv_bytes_per_sec: float

    def __post_init__(self) -> None:
        if not (0.0 <= self.cpu_percent <= 100.0):
            raise ValueError("cpu_percent must be between 0 and 100")
        if not (0.0 <= self.ram_percent <= 100.0):
            raise ValueError("ram_percent must be between 0 and 100")
        if self.net_sent_bytes_per_sec < 0.0:
            raise ValueError("net_sent_bytes_per_sec must be >= 0")
        if self.net_recv_bytes_per_sec < 0.0:
            raise ValueError("net_recv_bytes_per_sec must be >= 0")


@dataclass(frozen=True)
class ProcessInfo:
    pid: int
    name: str
    cpu_percent: float
    ram_percent: float

    def __post_init__(self) -> None:
        if self.pid <= 0:
            raise ValueError("pid must be > 0")
        if not self.name:
            raise ValueError("name must be non-empty")
        if not (0.0 <= self.cpu_percent <= 100.0):
            raise ValueError("cpu_percent must be between 0 and 100")
        if not (0.0 <= self.ram_percent <= 100.0):
            raise ValueError("ram_percent must be between 0 and 100")


@dataclass(frozen=True)
class ScreenCapture:
    timestamp: datetime
    image_bytes: bytes

    def __post_init__(self) -> None:
        if not isinstance(self.image_bytes, (bytes, bytearray)):
            raise TypeError("image_bytes must be bytes")
        if len(self.image_bytes) == 0:
            raise ValueError("image_bytes must be non-empty")

    def to_base64(self) -> str:
        return base64.b64encode(self.image_bytes).decode("ascii")


class Task:
    def __init__(self, task_id: str, title: str, priority: Priority = Priority.MEDIUM) -> None:
        if not task_id:
            raise ValueError("task_id must be non-empty")
        if not title:
            raise ValueError("title must be non-empty")
        self._id: str = task_id
        self._title: str = title
        self._priority: Priority = priority
        self._status: TaskStatus = TaskStatus.PENDING
        self._created_at: datetime = _utcnow()
        self._completed_at: Optional[datetime] = None

    @property
    def id(self) -> str:
        return self._id

    @property
    def title(self) -> str:
        return self._title

    @property
    def priority(self) -> Priority:
        return self._priority

    @property
    def status(self) -> TaskStatus:
        return self._status

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def completed_at(self) -> Optional[datetime]:
        return self._completed_at

    def set_priority(self, priority: Priority) -> None:
        self._priority = priority

    def mark_completed(self) -> None:
        if self._status == TaskStatus.COMPLETED:
            return
        self._status = TaskStatus.COMPLETED
        self._completed_at = _utcnow()

    def mark_pending(self) -> None:
        if self._status == TaskStatus.PENDING:
            return
        self._status = TaskStatus.PENDING
        self._completed_at = None


class TaskManager:
    def __init__(self) -> None:
        self._tasks: Dict[str, Task] = {}
        self._lock = threading.RLock()

    def create_task(self, task_id: str, title: str, priority: Priority = Priority.MEDIUM) -> Task:
        with self._lock:
            if task_id in self._tasks:
                raise ValueError(f"Task with id '{task_id}' already exists")
            task = Task(task_id=task_id, title=title, priority=priority)
            self._tasks[task_id] = task
            return task

    def get_task(self, task_id: str) -> Task:
        with self._lock:
            try:
                return self._tasks[task_id]
            except KeyError as e:
                raise KeyError(f"Task with id '{task_id}' not found") from e

    def list_tasks(self) -> List[Task]:
        with self._lock:
            return list(self._tasks.values())

    def list_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        with self._lock:
            return [t for t in self._tasks.values() if t.status == status]

    def list_tasks_by_priority(self, priority: Priority) -> List[Task]:
        with self._lock:
            return [t for t in self._tasks.values() if t.priority == priority]

    def complete_task(self, task_id: str) -> None:
        with self._lock:
            self.get_task(task_id).mark_completed()

    def set_task_priority(self, task_id: str, priority: Priority) -> None:
        with self._lock:
            self.get_task(task_id).set_priority(priority)


class PerformanceHistory:
    def __init__(self, max_samples: int = 3600) -> None:
        if max_samples <= 0:
            raise ValueError("max_samples must be > 0")
        self._max_samples = max_samples
        self._samples: List[PerformanceSample] = []
        self._lock = threading.RLock()

    @property
    def max_samples(self) -> int:
        return self._max_samples

    def add_sample(self, sample: PerformanceSample) -> None:
        with self._lock:
            self._samples.append(sample)
            if len(self._samples) > self._max_samples:
                overflow = len(self._samples) - self._max_samples
                if overflow > 0:
                    del self._samples[:overflow]

    def get_samples(self, limit: Optional[int] = None) -> List[PerformanceSample]:
        with self._lock:
            if limit is None:
                return list(self._samples)
            if limit <= 0:
                return []
            return list(self._samples[-limit:])

    def latest(self) -> Optional[PerformanceSample]:
        with self._lock:
            return self._samples[-1] if self._samples else None


class Agent:
    def __init__(
        self,
        agent_id: str,
        metrics_provider: Callable[[], Tuple[float, float, float, float]],
        process_provider: Callable[[], List[ProcessInfo]],
        screen_provider: Callable[[], bytes],
    ) -> None:
        if not agent_id:
            raise ValueError("agent_id must be non-empty")
        self._id = agent_id
        self._metrics_provider = metrics_provider
        self._process_provider = process_provider
        self._screen_provider = screen_provider

        self._online = False
        self._lock = threading.RLock()

    @property
    def id(self) -> str:
        return self._id

    def start(self) -> None:
        with self._lock:
            self._online = True

    def stop(self) -> None:
        with self._lock:
            self._online = False

    def is_online(self) -> bool:
        with self._lock:
            return self._online

    def collect_metrics(self) -> PerformanceSample:
        with self._lock:
            if not self._online:
                raise RuntimeError("Agent is offline")
        cpu, ram, sent_bps, recv_bps = self._metrics_provider()
        return PerformanceSample(
            timestamp=_utcnow(),
            cpu_percent=float(cpu),
            ram_percent=float(ram),
            net_sent_bytes_per_sec=float(sent_bps),
            net_recv_bytes_per_sec=float(recv_bps),
        )

    def list_processes(self) -> List[ProcessInfo]:
        with self._lock:
            if not self._online:
                raise RuntimeError("Agent is offline")
        procs = self._process_provider()
        return list(procs)

    def capture_screen(self) -> ScreenCapture:
        with self._lock:
            if not self._online:
                raise RuntimeError("Agent is offline")
        img = self._screen_provider()
        return ScreenCapture(timestamp=_utcnow(), image_bytes=bytes(img))

    def kill_process(self, pid: int) -> bool:
        with self._lock:
            if not self._online:
                raise RuntimeError("Agent is offline")
        if pid <= 0:
            raise ValueError("pid must be > 0")
        processes = self._process_provider()
        for p in processes:
            if p.pid == pid:
                return True
        return False


class Server:
    def __init__(self, server_id: str, name: str, agent: Agent, history_max_samples: int = 3600) -> None:
        if not server_id:
            raise ValueError("server_id must be non-empty")
        if not name:
            raise ValueError("name must be non-empty")
        self._id = server_id
        self._name = name
        self._agent = agent
        self._history = PerformanceHistory(max_samples=history_max_samples)
        self._last_screen: Optional[ScreenCapture] = None
        self._lock = threading.RLock()

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def status(self) -> ServerStatus:
        return ServerStatus.ONLINE if self._agent.is_online() else ServerStatus.OFFLINE

    @property
    def history(self) -> PerformanceHistory:
        return self._history

    def poll_metrics(self) -> PerformanceSample:
        sample = self._agent.collect_metrics()
        self._history.add_sample(sample)
        return sample

    def get_latest_metrics(self) -> Optional[PerformanceSample]:
        return self._history.latest()

    def get_performance_history(self, limit: Optional[int] = None) -> List[PerformanceSample]:
        return self._history.get_samples(limit=limit)

    def list_active_processes(self) -> List[ProcessInfo]:
        return self._agent.list_processes()

    def terminate_process(self, pid: int) -> bool:
        return self._agent.kill_process(pid)

    def capture_live_screen(self) -> ScreenCapture:
        cap = self._agent.capture_screen()
        with self._lock:
            self._last_screen = cap
        return cap

    def get_last_screen(self) -> Optional[ScreenCapture]:
        with self._lock:
            return self._last_screen


class NexusCtrl:
    def __init__(self) -> None:
        self._servers: Dict[str, Server] = {}
        self._tasks = TaskManager()
        self._lock = threading.RLock()

    @property
    def tasks(self) -> TaskManager:
        return self._tasks

    def register_server(self, server: Server) -> None:
        with self._lock:
            if server.id in self._servers:
                raise ValueError(f"Server with id '{server.id}' already registered")
            self._servers[server.id] = server

    def get_server(self, server_id: str) -> Server:
        with self._lock:
            try:
                return self._servers[server_id]
            except KeyError as e:
                raise KeyError(f"Server with id '{server_id}' not found") from e

    def list_servers(self) -> List[Server]:
        with self._lock:
            return list(self._servers.values())

    def list_server_statuses(self) -> Dict[str, ServerStatus]:
        with self._lock:
            return {sid: srv.status for sid, srv in self._servers.items()}

    def poll_all_servers(self) -> Dict[str, PerformanceSample]:
        results: Dict[str, PerformanceSample] = {}
        with self._lock:
            servers = list(self._servers.values())
        for srv in servers:
            if srv.status == ServerStatus.ONLINE:
                results[srv.id] = srv.poll_metrics()
        return results


class PollingService:
    def __init__(self, controller: NexusCtrl, interval_seconds: float = 1.0) -> None:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be > 0")
        self._controller = controller
        self._interval = float(interval_seconds)
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.RLock()

    @property
    def interval_seconds(self) -> float:
        return self._interval

    def start(self) -> None:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

    def stop(self, timeout: Optional[float] = None) -> None:
        with self._lock:
            self._stop_event.set()
            t = self._thread
        if t is not None:
            t.join(timeout=timeout)

    def is_running(self) -> bool:
        with self._lock:
            return self._thread is not None and self._thread.is_alive()

    def _run(self) -> None:
        next_time = time.monotonic()
        while not self._stop_event.is_set():
            now = time.monotonic()
            if now >= next_time:
                try:
                    self._controller.poll_all_servers()
                finally:
                    next_time = now + self._interval
            remaining = max(0.0, next_time - time.monotonic())
            self._stop_event.wait(timeout=remaining)