from __future__ import annotations

import base64
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Tuple


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
class MetricSample:
    timestamp: datetime
    cpu_percent: float
    ram_percent: float
    net_sent_kbps: float
    net_recv_kbps: float


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
        if not task_id or not isinstance(task_id, str):
            raise ValueError("task_id must be a non-empty string")
        if not title or not isinstance(title, str):
            raise ValueError("title must be a non-empty string")
        if not isinstance(priority, Priority):
            raise ValueError("priority must be a Priority")

        self._id: str = task_id
        self._title: str = title
        self._priority: Priority = priority
        self._status: TaskStatus = TaskStatus.PENDING
        self._created_at: datetime = datetime.now(timezone.utc)
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

    def mark_completed(self) -> None:
        if self._status == TaskStatus.COMPLETED:
            return
        self._status = TaskStatus.COMPLETED
        self._completed_at = datetime.now(timezone.utc)

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
                raise ValueError(f"task_id already exists: {task_id}")
            task = Task(task_id=task_id, title=title, priority=priority)
            self._tasks[task_id] = task
            return task

    def get_task(self, task_id: str) -> Task:
        with self._lock:
            try:
                return self._tasks[task_id]
            except KeyError as e:
                raise KeyError(f"task not found: {task_id}") from e

    def list_tasks(self) -> List[Task]:
        with self._lock:
            return list(self._tasks.values())

    def list_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        if not isinstance(status, TaskStatus):
            raise ValueError("status must be a TaskStatus")
        with self._lock:
            return [t for t in self._tasks.values() if t.status == status]

    def list_tasks_by_priority(self, priority: Priority) -> List[Task]:
        if not isinstance(priority, Priority):
            raise ValueError("priority must be a Priority")
        with self._lock:
            return [t for t in self._tasks.values() if t.priority == priority]

    def mark_task_completed(self, task_id: str) -> None:
        with self._lock:
            self.get_task(task_id).mark_completed()

    def mark_task_pending(self, task_id: str) -> None:
        with self._lock:
            self.get_task(task_id).mark_pending()


class PerformanceHistory:
    def __init__(self) -> None:
        self._samples: List[MetricSample] = []
        self._lock = threading.RLock()

    def add_sample(self, sample: MetricSample) -> None:
        if not isinstance(sample, MetricSample):
            raise ValueError("sample must be a MetricSample")
        with self._lock:
            self._samples.append(sample)

    def get_samples(self) -> List[MetricSample]:
        with self._lock:
            return list(self._samples)

    def get_latest(self) -> Optional[MetricSample]:
        with self._lock:
            return self._samples[-1] if self._samples else None


class Agent:
    def __init__(self, agent_id: str) -> None:
        if not agent_id or not isinstance(agent_id, str):
            raise ValueError("agent_id must be a non-empty string")
        self._agent_id: str = agent_id
        self._lock = threading.RLock()
        self._online: bool = False

        self._cpu_percent: float = 0.0
        self._ram_percent: float = 0.0
        self._net_sent_kbps: float = 0.0
        self._net_recv_kbps: float = 0.0

        self._processes: Dict[int, ProcessInfo] = {}
        self._last_screen: Optional[ScreenCapture] = None
        self._last_seen: Optional[datetime] = None

    @property
    def agent_id(self) -> str:
        return self._agent_id

    def set_online(self, online: bool) -> None:
        if not isinstance(online, bool):
            raise ValueError("online must be a bool")
        with self._lock:
            self._online = online
            self._last_seen = datetime.now(timezone.utc)

    def is_online(self) -> bool:
        with self._lock:
            return self._online

    def last_seen(self) -> Optional[datetime]:
        with self._lock:
            return self._last_seen

    def update_metrics(self, cpu_percent: float, ram_percent: float, net_sent_kbps: float, net_recv_kbps: float) -> None:
        for v, name in [
            (cpu_percent, "cpu_percent"),
            (ram_percent, "ram_percent"),
            (net_sent_kbps, "net_sent_kbps"),
            (net_recv_kbps, "net_recv_kbps"),
        ]:
            if not isinstance(v, (int, float)):
                raise ValueError(f"{name} must be a number")
            if v < 0:
                raise ValueError(f"{name} must be >= 0")
        if cpu_percent > 100 or ram_percent > 100:
            raise ValueError("cpu_percent and ram_percent must be <= 100")

        with self._lock:
            self._cpu_percent = float(cpu_percent)
            self._ram_percent = float(ram_percent)
            self._net_sent_kbps = float(net_sent_kbps)
            self._net_recv_kbps = float(net_recv_kbps)
            self._last_seen = datetime.now(timezone.utc)

    def get_metrics(self) -> Tuple[float, float, float, float]:
        with self._lock:
            return (self._cpu_percent, self._ram_percent, self._net_sent_kbps, self._net_recv_kbps)

    def update_processes(self, processes: List[ProcessInfo]) -> None:
        if not isinstance(processes, list):
            raise ValueError("processes must be a list of ProcessInfo")
        proc_map: Dict[int, ProcessInfo] = {}
        for p in processes:
            if not isinstance(p, ProcessInfo):
                raise ValueError("processes must be a list of ProcessInfo")
            if p.pid <= 0:
                raise ValueError("process pid must be > 0")
            if not p.name:
                raise ValueError("process name must be non-empty")
            if p.cpu_percent < 0 or p.ram_percent < 0:
                raise ValueError("process cpu_percent and ram_percent must be >= 0")
            proc_map[p.pid] = p

        with self._lock:
            self._processes = proc_map
            self._last_seen = datetime.now(timezone.utc)

    def list_processes(self) -> List[ProcessInfo]:
        with self._lock:
            return list(self._processes.values())

    def kill_process(self, pid: int) -> bool:
        if not isinstance(pid, int):
            raise ValueError("pid must be an int")
        if pid <= 0:
            raise ValueError("pid must be > 0")
        with self._lock:
            if pid in self._processes:
                del self._processes[pid]
                self._last_seen = datetime.now(timezone.utc)
                return True
            return False

    def update_screen_capture(self, image_bytes: bytes) -> ScreenCapture:
        if not isinstance(image_bytes, (bytes, bytearray)):
            raise ValueError("image_bytes must be bytes")
        encoded = base64.b64encode(bytes(image_bytes)).decode("ascii")
        capture = ScreenCapture(timestamp=datetime.now(timezone.utc), image_b64=encoded)
        with self._lock:
            self._last_screen = capture
            self._last_seen = datetime.now(timezone.utc)
        return capture

    def get_last_screen_capture(self) -> Optional[ScreenCapture]:
        with self._lock:
            return self._last_screen


class Server:
    def __init__(self, server_id: str, name: str, agent: Agent) -> None:
        if not server_id or not isinstance(server_id, str):
            raise ValueError("server_id must be a non-empty string")
        if not name or not isinstance(name, str):
            raise ValueError("name must be a non-empty string")
        if not isinstance(agent, Agent):
            raise ValueError("agent must be an Agent")

        self._id: str = server_id
        self._name: str = name
        self._agent: Agent = agent
        self._history: PerformanceHistory = PerformanceHistory()
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

    def status(self) -> ServerStatus:
        return ServerStatus.ONLINE if self._agent.is_online() else ServerStatus.OFFLINE

    def record_current_metrics_to_history(self) -> MetricSample:
        cpu, ram, sent, recv = self._agent.get_metrics()
        sample = MetricSample(
            timestamp=datetime.now(timezone.utc),
            cpu_percent=cpu,
            ram_percent=ram,
            net_sent_kbps=sent,
            net_recv_kbps=recv,
        )
        self._history.add_sample(sample)
        return sample

    def list_active_processes(self) -> List[ProcessInfo]:
        return self._agent.list_processes()

    def terminate_process(self, pid: int) -> bool:
        return self._agent.kill_process(pid)

    def get_live_screen(self) -> Optional[ScreenCapture]:
        return self._agent.get_last_screen_capture()


class NexusCtrl:
    def __init__(self) -> None:
        self._servers: Dict[str, Server] = {}
        self._tasks: TaskManager = TaskManager()
        self._lock = threading.RLock()

    @property
    def tasks(self) -> TaskManager:
        return self._tasks

    def register_server(self, server_id: str, name: str, agent_id: str) -> Server:
        with self._lock:
            if server_id in self._servers:
                raise ValueError(f"server_id already exists: {server_id}")
            agent = Agent(agent_id=agent_id)
            server = Server(server_id=server_id, name=name, agent=agent)
            self._servers[server_id] = server
            return server

    def get_server(self, server_id: str) -> Server:
        with self._lock:
            try:
                return self._servers[server_id]
            except KeyError as e:
                raise KeyError(f"server not found: {server_id}") from e

    def list_servers(self) -> List[Server]:
        with self._lock:
            return list(self._servers.values())

    def server_status(self, server_id: str) -> ServerStatus:
        return self.get_server(server_id).status()

    def update_agent_online(self, server_id: str, online: bool) -> None:
        self.get_server(server_id).agent.set_online(online)

    def ingest_metrics(self, server_id: str, cpu_percent: float, ram_percent: float, net_sent_kbps: float, net_recv_kbps: float) -> MetricSample:
        server = self.get_server(server_id)
        server.agent.update_metrics(cpu_percent, ram_percent, net_sent_kbps, net_recv_kbps)
        return server.record_current_metrics_to_history()

    def ingest_processes(self, server_id: str, processes: List[ProcessInfo]) -> None:
        self.get_server(server_id).agent.update_processes(processes)

    def ingest_screen_capture(self, server_id: str, image_bytes: bytes) -> ScreenCapture:
        return self.get_server(server_id).agent.update_screen_capture(image_bytes)

    def get_performance_history(self, server_id: str) -> List[MetricSample]:
        return self.get_server(server_id).history.get_samples()

    def get_latest_metrics(self, server_id: str) -> Optional[MetricSample]:
        return self.get_server(server_id).history.get_latest()

    def list_active_processes(self, server_id: str) -> List[ProcessInfo]:
        return self.get_server(server_id).list_active_processes()

    def terminate_process(self, server_id: str, pid: int) -> bool:
        return self.get_server(server_id).terminate_process(pid)

    def get_live_screen(self, server_id: str) -> Optional[ScreenCapture]:
        return self.get_server(server_id).get_live_screen()


class MetricsPoller:
    def __init__(self, nexus: NexusCtrl, server_id: str, interval_seconds: float) -> None:
        if not isinstance(nexus, NexusCtrl):
            raise ValueError("nexus must be a NexusCtrl")
        if not server_id or not isinstance(server_id, str):
            raise ValueError("server_id must be a non-empty string")
        if not isinstance(interval_seconds, (int, float)) or interval_seconds <= 0:
            raise ValueError("interval_seconds must be > 0")

        self._nexus = nexus
        self._server_id = server_id
        self._interval = float(interval_seconds)
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self, timeout: Optional[float] = None) -> None:
        self._stop_event.set()
        t = self._thread
        if t and t.is_alive():
            t.join(timeout=timeout)

    def is_running(self) -> bool:
        t = self._thread
        return bool(t and t.is_alive())

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._nexus.get_server(self._server_id).record_current_metrics_to_history()
            except Exception:
                pass
            self._stop_event.wait(self._interval)