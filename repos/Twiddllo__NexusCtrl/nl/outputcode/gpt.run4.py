from __future__ import annotations

import base64
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Tuple


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Priority(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

    @classmethod
    def from_value(cls, value: str) -> "Priority":
        if not isinstance(value, str):
            raise TypeError("priority must be a string")
        v = value.strip().lower()
        for p in cls:
            if p.value == v:
                return p
        raise ValueError("invalid priority")


class TaskStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"


@dataclass(frozen=True)
class PerformanceSample:
    timestamp: datetime
    cpu_percent: float
    ram_percent: float
    net_sent_bytes_per_sec: float
    net_recv_bytes_per_sec: float


@dataclass(frozen=True)
class ProcessInfo:
    pid: int
    name: str
    cpu_percent: float
    ram_percent: float


@dataclass(frozen=True)
class ScreenCapture:
    timestamp: datetime
    image_b64: str


class Task:
    def __init__(self, task_id: str, title: str, priority: Priority) -> None:
        if not isinstance(task_id, str) or not task_id.strip():
            raise ValueError("task_id must be a non-empty string")
        if not isinstance(title, str) or not title.strip():
            raise ValueError("title must be a non-empty string")
        if not isinstance(priority, Priority):
            raise TypeError("priority must be a Priority")

        self._id: str = task_id.strip()
        self._title: str = title.strip()
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
        if not isinstance(priority, Priority):
            raise TypeError("priority must be a Priority")
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

    def create_task(self, task_id: str, title: str, priority: Priority) -> Task:
        with self._lock:
            if task_id in self._tasks:
                raise ValueError("task_id already exists")
            task = Task(task_id=task_id, title=title, priority=priority)
            self._tasks[task.id] = task
            return task

    def get_task(self, task_id: str) -> Task:
        with self._lock:
            try:
                return self._tasks[task_id]
            except KeyError as e:
                raise KeyError("task not found") from e

    def list_tasks(self) -> List[Task]:
        with self._lock:
            return list(self._tasks.values())

    def set_task_priority(self, task_id: str, priority: Priority) -> None:
        with self._lock:
            self.get_task(task_id).set_priority(priority)

    def mark_task_completed(self, task_id: str) -> None:
        with self._lock:
            self.get_task(task_id).mark_completed()

    def mark_task_pending(self, task_id: str) -> None:
        with self._lock:
            self.get_task(task_id).mark_pending()


class PerformanceHistory:
    def __init__(self, max_samples: int = 3600) -> None:
        if not isinstance(max_samples, int) or max_samples <= 0:
            raise ValueError("max_samples must be a positive integer")
        self._max_samples = max_samples
        self._samples: List[PerformanceSample] = []
        self._lock = threading.RLock()

    @property
    def max_samples(self) -> int:
        return self._max_samples

    def add_sample(self, sample: PerformanceSample) -> None:
        if not isinstance(sample, PerformanceSample):
            raise TypeError("sample must be a PerformanceSample")
        with self._lock:
            self._samples.append(sample)
            overflow = len(self._samples) - self._max_samples
            if overflow > 0:
                del self._samples[:overflow]

    def get_samples(self) -> List[PerformanceSample]:
        with self._lock:
            return list(self._samples)

    def latest(self) -> Optional[PerformanceSample]:
        with self._lock:
            return self._samples[-1] if self._samples else None


class AgentCommandError(RuntimeError):
    pass


class Agent:
    def __init__(self, agent_id: str) -> None:
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise ValueError("agent_id must be a non-empty string")
        self._id = agent_id.strip()
        self._lock = threading.RLock()
        self._online: bool = False
        self._last_seen: Optional[datetime] = None

    @property
    def id(self) -> str:
        return self._id

    def connect(self) -> None:
        with self._lock:
            self._online = True
            self._last_seen = _utcnow()

    def disconnect(self) -> None:
        with self._lock:
            self._online = False
            self._last_seen = _utcnow()

    def heartbeat(self) -> None:
        with self._lock:
            if not self._online:
                self._online = True
            self._last_seen = _utcnow()

    def is_online(self) -> bool:
        with self._lock:
            return self._online

    def last_seen(self) -> Optional[datetime]:
        with self._lock:
            return self._last_seen

    def collect_metrics(self) -> PerformanceSample:
        raise NotImplementedError

    def list_processes(self) -> List[ProcessInfo]:
        raise NotImplementedError

    def kill_process(self, pid: int) -> None:
        raise NotImplementedError

    def capture_screen(self) -> ScreenCapture:
        raise NotImplementedError


class InMemoryAgent(Agent):
    def __init__(self, agent_id: str) -> None:
        super().__init__(agent_id)
        self._cpu: float = 0.0
        self._ram: float = 0.0
        self._net_sent_bps: float = 0.0
        self._net_recv_bps: float = 0.0
        self._processes: Dict[int, ProcessInfo] = {}
        self._screen_b64: str = base64.b64encode(b"").decode("ascii")

    def set_metrics(
        self,
        cpu_percent: float,
        ram_percent: float,
        net_sent_bytes_per_sec: float,
        net_recv_bytes_per_sec: float,
    ) -> None:
        for name, v in (
            ("cpu_percent", cpu_percent),
            ("ram_percent", ram_percent),
            ("net_sent_bytes_per_sec", net_sent_bytes_per_sec),
            ("net_recv_bytes_per_sec", net_recv_bytes_per_sec),
        ):
            if not isinstance(v, (int, float)):
                raise TypeError(f"{name} must be a number")
            if v < 0:
                raise ValueError(f"{name} must be >= 0")
        if cpu_percent > 100 or ram_percent > 100:
            raise ValueError("cpu_percent and ram_percent must be <= 100")

        with self._lock:
            self._cpu = float(cpu_percent)
            self._ram = float(ram_percent)
            self._net_sent_bps = float(net_sent_bytes_per_sec)
            self._net_recv_bps = float(net_recv_bytes_per_sec)
            self.heartbeat()

    def set_processes(self, processes: List[ProcessInfo]) -> None:
        if not isinstance(processes, list):
            raise TypeError("processes must be a list")
        proc_map: Dict[int, ProcessInfo] = {}
        for p in processes:
            if not isinstance(p, ProcessInfo):
                raise TypeError("processes must contain ProcessInfo")
            if p.pid in proc_map:
                raise ValueError("duplicate pid in processes")
            proc_map[p.pid] = p
        with self._lock:
            self._processes = proc_map
            self.heartbeat()

    def set_screen_bytes(self, image_bytes: bytes) -> None:
        if not isinstance(image_bytes, (bytes, bytearray)):
            raise TypeError("image_bytes must be bytes")
        with self._lock:
            self._screen_b64 = base64.b64encode(bytes(image_bytes)).decode("ascii")
            self.heartbeat()

    def _require_online(self) -> None:
        if not self.is_online():
            raise AgentCommandError("agent is offline")

    def collect_metrics(self) -> PerformanceSample:
        with self._lock:
            self._require_online()
            self.heartbeat()
            return PerformanceSample(
                timestamp=_utcnow(),
                cpu_percent=self._cpu,
                ram_percent=self._ram,
                net_sent_bytes_per_sec=self._net_sent_bps,
                net_recv_bytes_per_sec=self._net_recv_bps,
            )

    def list_processes(self) -> List[ProcessInfo]:
        with self._lock:
            self._require_online()
            self.heartbeat()
            return list(self._processes.values())

    def kill_process(self, pid: int) -> None:
        if not isinstance(pid, int) or pid <= 0:
            raise ValueError("pid must be a positive integer")
        with self._lock:
            self._require_online()
            if pid not in self._processes:
                raise AgentCommandError("process not found")
            del self._processes[pid]
            self.heartbeat()

    def capture_screen(self) -> ScreenCapture:
        with self._lock:
            self._require_online()
            self.heartbeat()
            return ScreenCapture(timestamp=_utcnow(), image_b64=self._screen_b64)


class Server:
    def __init__(self, server_id: str, name: str, agent: Agent, history_max_samples: int = 3600) -> None:
        if not isinstance(server_id, str) or not server_id.strip():
            raise ValueError("server_id must be a non-empty string")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("name must be a non-empty string")
        if not isinstance(agent, Agent):
            raise TypeError("agent must be an Agent")

        self._id = server_id.strip()
        self._name = name.strip()
        self._agent = agent
        self._history = PerformanceHistory(max_samples=history_max_samples)
        self._lock = threading.RLock()

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def agent(self) -> Agent:
        return self._agent

    @property
    def history(self) -> PerformanceHistory:
        return self._history

    def is_online(self) -> bool:
        return self._agent.is_online()

    def poll_metrics(self) -> PerformanceSample:
        with self._lock:
            sample = self._agent.collect_metrics()
            self._history.add_sample(sample)
            return sample

    def get_latest_metrics(self) -> Optional[PerformanceSample]:
        return self._history.latest()

    def get_performance_history(self) -> List[PerformanceSample]:
        return self._history.get_samples()

    def list_active_processes(self) -> List[ProcessInfo]:
        with self._lock:
            return self._agent.list_processes()

    def terminate_process(self, pid: int) -> None:
        with self._lock:
            self._agent.kill_process(pid)

    def get_live_screen(self) -> ScreenCapture:
        with self._lock:
            return self._agent.capture_screen()


class NexusCtrl:
    def __init__(self) -> None:
        self._servers: Dict[str, Server] = {}
        self._tasks = TaskManager()
        self._lock = threading.RLock()

    @property
    def tasks(self) -> TaskManager:
        return self._tasks

    def register_server(self, server: Server) -> None:
        if not isinstance(server, Server):
            raise TypeError("server must be a Server")
        with self._lock:
            if server.id in self._servers:
                raise ValueError("server_id already registered")
            self._servers[server.id] = server

    def get_server(self, server_id: str) -> Server:
        with self._lock:
            try:
                return self._servers[server_id]
            except KeyError as e:
                raise KeyError("server not found") from e

    def list_servers(self) -> List[Server]:
        with self._lock:
            return list(self._servers.values())

    def server_status(self, server_id: str) -> str:
        server = self.get_server(server_id)
        return "online" if server.is_online() else "offline"

    def poll_server_metrics(self, server_id: str) -> PerformanceSample:
        server = self.get_server(server_id)
        return server.poll_metrics()

    def poll_all_servers_metrics(self) -> Dict[str, PerformanceSample]:
        results: Dict[str, PerformanceSample] = {}
        for s in self.list_servers():
            results[s.id] = s.poll_metrics()
        return results

    def get_server_history(self, server_id: str) -> List[PerformanceSample]:
        server = self.get_server(server_id)
        return server.get_performance_history()

    def get_live_screen(self, server_id: str) -> ScreenCapture:
        server = self.get_server(server_id)
        return server.get_live_screen()

    def list_processes(self, server_id: str) -> List[ProcessInfo]:
        server = self.get_server(server_id)
        return server.list_active_processes()

    def kill_process(self, server_id: str, pid: int) -> None:
        server = self.get_server(server_id)
        server.terminate_process(pid)


class MetricsPoller:
    def __init__(self, controller: NexusCtrl, interval_seconds: float = 1.0) -> None:
        if not isinstance(controller, NexusCtrl):
            raise TypeError("controller must be a NexusCtrl")
        if not isinstance(interval_seconds, (int, float)) or interval_seconds <= 0:
            raise ValueError("interval_seconds must be > 0")
        self._controller = controller
        self._interval = float(interval_seconds)
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()

    @property
    def interval_seconds(self) -> float:
        return self._interval

    def start(self) -> None:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run, name="MetricsPoller", daemon=True)
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
        while not self._stop_event.is_set():
            start = time.monotonic()
            try:
                self._controller.poll_all_servers_metrics()
            except Exception:
                pass
            elapsed = time.monotonic() - start
            remaining = self._interval - elapsed
            if remaining > 0:
                self._stop_event.wait(remaining)