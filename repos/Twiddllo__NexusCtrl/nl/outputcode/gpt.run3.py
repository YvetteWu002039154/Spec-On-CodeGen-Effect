from __future__ import annotations

import base64
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple


class Priority(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

    @classmethod
    def from_value(cls, value: str) -> "Priority":
        if not isinstance(value, str):
            raise TypeError("Priority value must be a string.")
        normalized = value.strip().lower()
        for p in cls:
            if p.value == normalized:
                return p
        raise ValueError(f"Invalid priority: {value!r}")


class ServerStatus(Enum):
    ONLINE = "online"
    OFFLINE = "offline"


@dataclass(frozen=True)
class MetricsSnapshot:
    timestamp: float
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
    timestamp: float
    image_b64: str


class Task:
    def __init__(self, task_id: str, title: str, priority: Priority) -> None:
        if not isinstance(task_id, str) or not task_id.strip():
            raise ValueError("task_id must be a non-empty string.")
        if not isinstance(title, str) or not title.strip():
            raise ValueError("title must be a non-empty string.")
        if not isinstance(priority, Priority):
            raise TypeError("priority must be a Priority.")
        self._id: str = task_id.strip()
        self._title: str = title.strip()
        self._priority: Priority = priority
        self._completed: bool = False
        self._created_at: float = time.time()
        self._completed_at: Optional[float] = None

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
    def completed(self) -> bool:
        return self._completed

    @property
    def created_at(self) -> float:
        return self._created_at

    @property
    def completed_at(self) -> Optional[float]:
        return self._completed_at

    def set_priority(self, priority: Priority) -> None:
        if not isinstance(priority, Priority):
            raise TypeError("priority must be a Priority.")
        self._priority = priority

    def mark_completed(self) -> None:
        if not self._completed:
            self._completed = True
            self._completed_at = time.time()

    def mark_incomplete(self) -> None:
        if self._completed:
            self._completed = False
            self._completed_at = None


class TaskManager:
    def __init__(self) -> None:
        self._tasks: Dict[str, Task] = {}
        self._lock = threading.RLock()

    def create_task(self, task_id: str, title: str, priority: Priority) -> Task:
        with self._lock:
            if task_id in self._tasks:
                raise ValueError(f"Task with id {task_id!r} already exists.")
            task = Task(task_id=task_id, title=title, priority=priority)
            self._tasks[task.id] = task
            return task

    def get_task(self, task_id: str) -> Task:
        with self._lock:
            try:
                return self._tasks[task_id]
            except KeyError as e:
                raise KeyError(f"Task not found: {task_id!r}") from e

    def list_tasks(self) -> List[Task]:
        with self._lock:
            return list(self._tasks.values())

    def list_tasks_by_completion(self, completed: bool) -> List[Task]:
        with self._lock:
            return [t for t in self._tasks.values() if t.completed == completed]

    def set_task_priority(self, task_id: str, priority: Priority) -> None:
        with self._lock:
            self.get_task(task_id).set_priority(priority)

    def mark_task_completed(self, task_id: str) -> None:
        with self._lock:
            self.get_task(task_id).mark_completed()

    def mark_task_incomplete(self, task_id: str) -> None:
        with self._lock:
            self.get_task(task_id).mark_incomplete()


class PerformanceHistory:
    def __init__(self, max_snapshots: int = 3600) -> None:
        if not isinstance(max_snapshots, int) or max_snapshots <= 0:
            raise ValueError("max_snapshots must be a positive integer.")
        self._max_snapshots = max_snapshots
        self._snapshots: List[MetricsSnapshot] = []
        self._lock = threading.RLock()

    @property
    def max_snapshots(self) -> int:
        return self._max_snapshots

    def add_snapshot(self, snapshot: MetricsSnapshot) -> None:
        if not isinstance(snapshot, MetricsSnapshot):
            raise TypeError("snapshot must be a MetricsSnapshot.")
        with self._lock:
            self._snapshots.append(snapshot)
            overflow = len(self._snapshots) - self._max_snapshots
            if overflow > 0:
                del self._snapshots[:overflow]

    def get_snapshots(self) -> List[MetricsSnapshot]:
        with self._lock:
            return list(self._snapshots)

    def latest(self) -> Optional[MetricsSnapshot]:
        with self._lock:
            return self._snapshots[-1] if self._snapshots else None


class Agent:
    def __init__(self, agent_id: str, server_name: str) -> None:
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise ValueError("agent_id must be a non-empty string.")
        if not isinstance(server_name, str) or not server_name.strip():
            raise ValueError("server_name must be a non-empty string.")
        self._agent_id = agent_id.strip()
        self._server_name = server_name.strip()
        self._online = False
        self._lock = threading.RLock()

        self._processes: Dict[int, ProcessInfo] = {}
        self._last_metrics: Optional[MetricsSnapshot] = None
        self._last_screen: Optional[ScreenCapture] = None

    @property
    def agent_id(self) -> str:
        return self._agent_id

    @property
    def server_name(self) -> str:
        return self._server_name

    def connect(self) -> None:
        with self._lock:
            self._online = True

    def disconnect(self) -> None:
        with self._lock:
            self._online = False

    def is_online(self) -> bool:
        with self._lock:
            return self._online

    def update_metrics(self, cpu_percent: float, ram_percent: float, net_sent_bps: float, net_recv_bps: float) -> MetricsSnapshot:
        for name, v in (
            ("cpu_percent", cpu_percent),
            ("ram_percent", ram_percent),
            ("net_sent_bps", net_sent_bps),
            ("net_recv_bps", net_recv_bps),
        ):
            if not isinstance(v, (int, float)):
                raise TypeError(f"{name} must be a number.")
            if v < 0:
                raise ValueError(f"{name} must be >= 0.")
        if cpu_percent > 100 or ram_percent > 100:
            raise ValueError("cpu_percent and ram_percent must be <= 100.")

        snapshot = MetricsSnapshot(
            timestamp=time.time(),
            cpu_percent=float(cpu_percent),
            ram_percent=float(ram_percent),
            net_sent_bytes_per_sec=float(net_sent_bps),
            net_recv_bytes_per_sec=float(net_recv_bps),
        )
        with self._lock:
            self._last_metrics = snapshot
        return snapshot

    def set_processes(self, processes: List[ProcessInfo]) -> None:
        if not isinstance(processes, list):
            raise TypeError("processes must be a list of ProcessInfo.")
        proc_map: Dict[int, ProcessInfo] = {}
        for p in processes:
            if not isinstance(p, ProcessInfo):
                raise TypeError("processes must contain ProcessInfo items.")
            if p.pid in proc_map:
                raise ValueError(f"Duplicate pid in process list: {p.pid}")
            proc_map[p.pid] = p
        with self._lock:
            self._processes = proc_map

    def list_processes(self) -> List[ProcessInfo]:
        with self._lock:
            return list(self._processes.values())

    def kill_process(self, pid: int) -> bool:
        if not isinstance(pid, int) or pid <= 0:
            raise ValueError("pid must be a positive integer.")
        with self._lock:
            if not self._online:
                raise RuntimeError("Agent is offline.")
            if pid in self._processes:
                del self._processes[pid]
                return True
            return False

    def update_screen_capture(self, image_bytes: bytes) -> ScreenCapture:
        if not isinstance(image_bytes, (bytes, bytearray)):
            raise TypeError("image_bytes must be bytes.")
        encoded = base64.b64encode(bytes(image_bytes)).decode("ascii")
        capture = ScreenCapture(timestamp=time.time(), image_b64=encoded)
        with self._lock:
            self._last_screen = capture
        return capture

    def get_last_metrics(self) -> Optional[MetricsSnapshot]:
        with self._lock:
            return self._last_metrics

    def get_last_screen_capture(self) -> Optional[ScreenCapture]:
        with self._lock:
            return self._last_screen


class Server:
    def __init__(self, server_id: str, name: str, agent: Agent, history_max_snapshots: int = 3600) -> None:
        if not isinstance(server_id, str) or not server_id.strip():
            raise ValueError("server_id must be a non-empty string.")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("name must be a non-empty string.")
        if not isinstance(agent, Agent):
            raise TypeError("agent must be an Agent.")
        self._id = server_id.strip()
        self._name = name.strip()
        self._agent = agent
        self._history = PerformanceHistory(max_snapshots=history_max_snapshots)
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

    def get_live_metrics(self) -> Optional[MetricsSnapshot]:
        return self._agent.get_last_metrics()

    def record_metrics_to_history(self) -> Optional[MetricsSnapshot]:
        snapshot = self._agent.get_last_metrics()
        if snapshot is None:
            return None
        self._history.add_snapshot(snapshot)
        return snapshot

    def get_live_screen_capture(self) -> Optional[ScreenCapture]:
        return self._agent.get_last_screen_capture()

    def list_active_processes(self) -> List[ProcessInfo]:
        return self._agent.list_processes()

    def terminate_process(self, pid: int) -> bool:
        return self._agent.kill_process(pid)


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
            raise TypeError("server must be a Server.")
        with self._lock:
            if server.id in self._servers:
                raise ValueError(f"Server with id {server.id!r} already registered.")
            self._servers[server.id] = server

    def get_server(self, server_id: str) -> Server:
        with self._lock:
            try:
                return self._servers[server_id]
            except KeyError as e:
                raise KeyError(f"Server not found: {server_id!r}") from e

    def list_servers(self) -> List[Server]:
        with self._lock:
            return list(self._servers.values())

    def get_server_status(self, server_id: str) -> ServerStatus:
        return self.get_server(server_id).status

    def get_server_live_metrics(self, server_id: str) -> Optional[MetricsSnapshot]:
        return self.get_server(server_id).get_live_metrics()

    def get_server_performance_history(self, server_id: str) -> List[MetricsSnapshot]:
        return self.get_server(server_id).history.get_snapshots()

    def record_server_metrics_to_history(self, server_id: str) -> Optional[MetricsSnapshot]:
        return self.get_server(server_id).record_metrics_to_history()

    def get_server_live_screen_capture(self, server_id: str) -> Optional[ScreenCapture]:
        return self.get_server(server_id).get_live_screen_capture()

    def list_server_processes(self, server_id: str) -> List[ProcessInfo]:
        return self.get_server(server_id).list_active_processes()

    def terminate_server_process(self, server_id: str, pid: int) -> bool:
        return self.get_server(server_id).terminate_process(pid)


class MetricsPoller:
    def __init__(self, nexus: NexusCtrl, interval_seconds: float = 1.0) -> None:
        if not isinstance(nexus, NexusCtrl):
            raise TypeError("nexus must be a NexusCtrl.")
        if not isinstance(interval_seconds, (int, float)) or interval_seconds <= 0:
            raise ValueError("interval_seconds must be > 0.")
        self._nexus = nexus
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
            servers = self._nexus.list_servers()
            for s in servers:
                s.record_metrics_to_history()
            self._stop_event.wait(self._interval)


def create_process(pid: int, name: str, cpu_percent: float, ram_percent: float) -> ProcessInfo:
    if not isinstance(pid, int) or pid <= 0:
        raise ValueError("pid must be a positive integer.")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("name must be a non-empty string.")
    for n, v in (("cpu_percent", cpu_percent), ("ram_percent", ram_percent)):
        if not isinstance(v, (int, float)):
            raise TypeError(f"{n} must be a number.")
        if v < 0:
            raise ValueError(f"{n} must be >= 0.")
        if v > 100:
            raise ValueError(f"{n} must be <= 100.")
    return ProcessInfo(pid=pid, name=name.strip(), cpu_percent=float(cpu_percent), ram_percent=float(ram_percent))


def decode_screen_capture_b64(image_b64: str) -> bytes:
    if not isinstance(image_b64, str):
        raise TypeError("image_b64 must be a string.")
    return base64.b64decode(image_b64.encode("ascii"), validate=True)


__all__ = [
    "Priority",
    "ServerStatus",
    "MetricsSnapshot",
    "ProcessInfo",
    "ScreenCapture",
    "Task",
    "TaskManager",
    "PerformanceHistory",
    "Agent",
    "Server",
    "NexusCtrl",
    "MetricsPoller",
    "create_process",
    "decode_screen_capture_b64",
]