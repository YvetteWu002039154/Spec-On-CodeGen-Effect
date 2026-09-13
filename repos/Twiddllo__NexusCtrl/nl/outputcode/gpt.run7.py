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
            raise TypeError("Priority value must be a string.")
        v = value.strip().lower()
        for p in cls:
            if p.value == v:
                return p
        raise ValueError(f"Invalid priority: {value!r}")


class TaskStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"


@dataclass(frozen=True)
class MetricSample:
    timestamp: datetime
    cpu_percent: float
    ram_percent: float
    net_sent_bytes: int
    net_recv_bytes: int

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware.")
        if not (0.0 <= self.cpu_percent <= 100.0):
            raise ValueError("cpu_percent must be between 0 and 100.")
        if not (0.0 <= self.ram_percent <= 100.0):
            raise ValueError("ram_percent must be between 0 and 100.")
        if self.net_sent_bytes < 0 or self.net_recv_bytes < 0:
            raise ValueError("Network byte counters must be non-negative.")


@dataclass(frozen=True)
class ProcessInfo:
    pid: int
    name: str
    cpu_percent: float
    ram_percent: float

    def __post_init__(self) -> None:
        if self.pid <= 0:
            raise ValueError("pid must be positive.")
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("name must be a non-empty string.")
        if not (0.0 <= self.cpu_percent <= 100.0):
            raise ValueError("cpu_percent must be between 0 and 100.")
        if not (0.0 <= self.ram_percent <= 100.0):
            raise ValueError("ram_percent must be between 0 and 100.")


@dataclass(frozen=True)
class ScreenCapture:
    timestamp: datetime
    image_bytes: bytes

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware.")
        if not isinstance(self.image_bytes, (bytes, bytearray)):
            raise TypeError("image_bytes must be bytes.")
        if len(self.image_bytes) == 0:
            raise ValueError("image_bytes must not be empty.")

    def to_base64(self) -> str:
        return base64.b64encode(self.image_bytes).decode("ascii")


class Task:
    def __init__(self, task_id: str, title: str, priority: Priority) -> None:
        if not isinstance(task_id, str) or not task_id.strip():
            raise ValueError("task_id must be a non-empty string.")
        if not isinstance(title, str) or not title.strip():
            raise ValueError("title must be a non-empty string.")
        if not isinstance(priority, Priority):
            raise TypeError("priority must be a Priority.")
        self._id: str = task_id
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
            raise TypeError("priority must be a Priority.")
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
        self._lock = threading.RLock()
        self._tasks: Dict[str, Task] = {}

    def create_task(self, task_id: str, title: str, priority: Priority) -> Task:
        with self._lock:
            if task_id in self._tasks:
                raise ValueError(f"Task with id {task_id!r} already exists.")
            task = Task(task_id=task_id, title=title, priority=priority)
            self._tasks[task_id] = task
            return task

    def get_task(self, task_id: str) -> Task:
        with self._lock:
            try:
                return self._tasks[task_id]
            except KeyError:
                raise KeyError(f"Task not found: {task_id!r}")

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


class ServerStatus(Enum):
    ONLINE = "online"
    OFFLINE = "offline"


class AgentCommandError(RuntimeError):
    pass


class Agent:
    def __init__(self, agent_id: str) -> None:
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise ValueError("agent_id must be a non-empty string.")
        self._id: str = agent_id
        self._lock = threading.RLock()
        self._running: bool = False
        self._last_seen: Optional[datetime] = None

        self._latest_metrics: Optional[MetricSample] = None
        self._latest_processes: List[ProcessInfo] = []
        self._latest_screen: Optional[ScreenCapture] = None

    @property
    def id(self) -> str:
        return self._id

    @property
    def last_seen(self) -> Optional[datetime]:
        with self._lock:
            return self._last_seen

    def start(self) -> None:
        with self._lock:
            self._running = True
            self._touch()

    def stop(self) -> None:
        with self._lock:
            self._running = False
            self._touch()

    def is_running(self) -> bool:
        with self._lock:
            return self._running

    def _touch(self) -> None:
        self._last_seen = _utcnow()

    def update_metrics(self, sample: MetricSample) -> None:
        if not isinstance(sample, MetricSample):
            raise TypeError("sample must be a MetricSample.")
        with self._lock:
            self._latest_metrics = sample
            self._touch()

    def update_processes(self, processes: List[ProcessInfo]) -> None:
        if not isinstance(processes, list):
            raise TypeError("processes must be a list of ProcessInfo.")
        for p in processes:
            if not isinstance(p, ProcessInfo):
                raise TypeError("processes must be a list of ProcessInfo.")
        with self._lock:
            self._latest_processes = list(processes)
            self._touch()

    def update_screen(self, capture: ScreenCapture) -> None:
        if not isinstance(capture, ScreenCapture):
            raise TypeError("capture must be a ScreenCapture.")
        with self._lock:
            self._latest_screen = capture
            self._touch()

    def get_latest_metrics(self) -> Optional[MetricSample]:
        with self._lock:
            return self._latest_metrics

    def get_latest_processes(self) -> List[ProcessInfo]:
        with self._lock:
            return list(self._latest_processes)

    def get_latest_screen(self) -> Optional[ScreenCapture]:
        with self._lock:
            return self._latest_screen

    def kill_process(self, pid: int) -> bool:
        if not isinstance(pid, int):
            raise TypeError("pid must be an int.")
        if pid <= 0:
            raise ValueError("pid must be positive.")
        with self._lock:
            if not self._running:
                raise AgentCommandError("Agent is not running.")
            before = len(self._latest_processes)
            self._latest_processes = [p for p in self._latest_processes if p.pid != pid]
            killed = len(self._latest_processes) != before
            self._touch()
            return killed


class Server:
    def __init__(self, server_id: str, name: str, agent: Agent, history_limit: int = 3600) -> None:
        if not isinstance(server_id, str) or not server_id.strip():
            raise ValueError("server_id must be a non-empty string.")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("name must be a non-empty string.")
        if not isinstance(agent, Agent):
            raise TypeError("agent must be an Agent.")
        if not isinstance(history_limit, int):
            raise TypeError("history_limit must be an int.")
        if history_limit <= 0:
            raise ValueError("history_limit must be positive.")

        self._id: str = server_id
        self._name: str = name.strip()
        self._agent: Agent = agent
        self._history_limit: int = history_limit

        self._lock = threading.RLock()
        self._history: List[MetricSample] = []

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
    def history_limit(self) -> int:
        return self._history_limit

    def status(self, offline_after_seconds: int = 30) -> ServerStatus:
        if not isinstance(offline_after_seconds, int):
            raise TypeError("offline_after_seconds must be an int.")
        if offline_after_seconds <= 0:
            raise ValueError("offline_after_seconds must be positive.")
        last_seen = self._agent.last_seen
        if last_seen is None:
            return ServerStatus.OFFLINE
        delta = (_utcnow() - last_seen).total_seconds()
        return ServerStatus.ONLINE if delta <= offline_after_seconds else ServerStatus.OFFLINE

    def record_metrics(self, sample: MetricSample) -> None:
        if not isinstance(sample, MetricSample):
            raise TypeError("sample must be a MetricSample.")
        with self._lock:
            self._history.append(sample)
            if len(self._history) > self._history_limit:
                overflow = len(self._history) - self._history_limit
                if overflow > 0:
                    del self._history[:overflow]
        self._agent.update_metrics(sample)

    def get_performance_history(self) -> List[MetricSample]:
        with self._lock:
            return list(self._history)

    def get_latest_metrics(self) -> Optional[MetricSample]:
        return self._agent.get_latest_metrics()

    def get_active_processes(self) -> List[ProcessInfo]:
        return self._agent.get_latest_processes()

    def terminate_process(self, pid: int) -> bool:
        return self._agent.kill_process(pid)

    def get_live_screen(self) -> Optional[ScreenCapture]:
        return self._agent.get_latest_screen()


class NexusCtrl:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._servers: Dict[str, Server] = {}
        self._tasks = TaskManager()

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
            except KeyError:
                raise KeyError(f"Server not found: {server_id!r}")

    def list_servers(self) -> List[Server]:
        with self._lock:
            return list(self._servers.values())

    def server_status(self, server_id: str, offline_after_seconds: int = 30) -> ServerStatus:
        return self.get_server(server_id).status(offline_after_seconds=offline_after_seconds)

    def update_server_metrics(
        self,
        server_id: str,
        cpu_percent: float,
        ram_percent: float,
        net_sent_bytes: int,
        net_recv_bytes: int,
        timestamp: Optional[datetime] = None,
    ) -> MetricSample:
        if timestamp is None:
            timestamp = _utcnow()
        sample = MetricSample(
            timestamp=timestamp,
            cpu_percent=float(cpu_percent),
            ram_percent=float(ram_percent),
            net_sent_bytes=int(net_sent_bytes),
            net_recv_bytes=int(net_recv_bytes),
        )
        server = self.get_server(server_id)
        server.record_metrics(sample)
        return sample

    def update_server_processes(self, server_id: str, processes: List[ProcessInfo]) -> None:
        server = self.get_server(server_id)
        server.agent.update_processes(processes)

    def update_server_screen(self, server_id: str, image_bytes: bytes, timestamp: Optional[datetime] = None) -> ScreenCapture:
        if timestamp is None:
            timestamp = _utcnow()
        capture = ScreenCapture(timestamp=timestamp, image_bytes=bytes(image_bytes))
        server = self.get_server(server_id)
        server.agent.update_screen(capture)
        return capture

    def get_server_live_screen(self, server_id: str) -> Optional[ScreenCapture]:
        return self.get_server(server_id).get_live_screen()

    def get_server_active_processes(self, server_id: str) -> List[ProcessInfo]:
        return self.get_server(server_id).get_active_processes()

    def kill_server_process(self, server_id: str, pid: int) -> bool:
        return self.get_server(server_id).terminate_process(pid)

    def get_server_performance_history(self, server_id: str) -> List[MetricSample]:
        return self.get_server(server_id).get_performance_history()


class InMemoryAgent(Agent):
    def __init__(self, agent_id: str) -> None:
        super().__init__(agent_id=agent_id)
        self.start()


class SimulatedAgent(Agent):
    def __init__(
        self,
        agent_id: str,
        update_interval_seconds: float = 1.0,
        history_process_count: int = 25,
    ) -> None:
        super().__init__(agent_id=agent_id)
        if update_interval_seconds <= 0:
            raise ValueError("update_interval_seconds must be positive.")
        if history_process_count <= 0:
            raise ValueError("history_process_count must be positive.")
        self._interval = float(update_interval_seconds)
        self._process_count = int(history_process_count)
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self.start()

    def start(self) -> None:
        super().start()
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        super().stop()

    def _run(self) -> None:
        t = 0
        sent = 0
        recv = 0
        while not self._stop_event.is_set():
            t += 1
            cpu = float((t * 7) % 101)
            ram = float((t * 5) % 101)
            sent += 1024 * (1 + (t % 5))
            recv += 2048 * (1 + (t % 3))

            sample = MetricSample(
                timestamp=_utcnow(),
                cpu_percent=cpu,
                ram_percent=ram,
                net_sent_bytes=sent,
                net_recv_bytes=recv,
            )
            self.update_metrics(sample)

            procs: List[ProcessInfo] = []
            for i in range(1, self._process_count + 1):
                pid = 1000 + i
                p_cpu = float((cpu + i * 3) % 101)
                p_ram = float((ram + i * 2) % 101)
                procs.append(ProcessInfo(pid=pid, name=f"proc_{i}", cpu_percent=p_cpu, ram_percent=p_ram))
            self.update_processes(procs)

            img = (f"SIM_SCREEN_{self.id}_{t}".encode("utf-8")) * 10
            self.update_screen(ScreenCapture(timestamp=_utcnow(), image_bytes=img))

            time.sleep(self._interval)


__all__ = [
    "NexusCtrl",
    "Server",
    "Agent",
    "InMemoryAgent",
    "SimulatedAgent",
    "MetricSample",
    "ProcessInfo",
    "ScreenCapture",
    "Task",
    "TaskManager",
    "Priority",
    "TaskStatus",
    "ServerStatus",
    "AgentCommandError",
]