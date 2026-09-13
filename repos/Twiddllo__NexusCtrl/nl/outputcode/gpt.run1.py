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
class MetricsSnapshot:
    timestamp: datetime
    cpu_percent: float
    ram_percent: float
    net_sent_bytes: int
    net_recv_bytes: int


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
    def __init__(self, title: str, priority: Priority = Priority.MEDIUM) -> None:
        title = (title or "").strip()
        if not title:
            raise ValueError("Task title must be non-empty.")
        if not isinstance(priority, Priority):
            raise TypeError("priority must be a Priority.")
        self._title: str = title
        self._priority: Priority = priority
        self._status: TaskStatus = TaskStatus.PENDING
        self._created_at: datetime = datetime.now(timezone.utc)
        self._completed_at: Optional[datetime] = None

    @property
    def title(self) -> str:
        return self._title

    @property
    def priority(self) -> Priority:
        return self._priority

    @priority.setter
    def priority(self, value: Priority) -> None:
        if not isinstance(value, Priority):
            raise TypeError("priority must be a Priority.")
        self._priority = value

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
        self._lock = threading.RLock()
        self._tasks: Dict[int, Task] = {}
        self._next_id: int = 1

    def create_task(self, title: str, priority: Priority = Priority.MEDIUM) -> int:
        with self._lock:
            task = Task(title=title, priority=priority)
            task_id = self._next_id
            self._next_id += 1
            self._tasks[task_id] = task
            return task_id

    def get_task(self, task_id: int) -> Task:
        with self._lock:
            if task_id not in self._tasks:
                raise KeyError("Task not found.")
            return self._tasks[task_id]

    def list_tasks(self) -> List[Tuple[int, Task]]:
        with self._lock:
            return list(self._tasks.items())

    def set_priority(self, task_id: int, priority: Priority) -> None:
        with self._lock:
            task = self.get_task(task_id)
            task.priority = priority

    def mark_completed(self, task_id: int) -> None:
        with self._lock:
            task = self.get_task(task_id)
            task.mark_completed()

    def mark_pending(self, task_id: int) -> None:
        with self._lock:
            task = self.get_task(task_id)
            task.mark_pending()

    def delete_task(self, task_id: int) -> None:
        with self._lock:
            if task_id not in self._tasks:
                raise KeyError("Task not found.")
            del self._tasks[task_id]


class ProcessTable:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._processes: Dict[int, ProcessInfo] = {}

    def set_processes(self, processes: List[ProcessInfo]) -> None:
        with self._lock:
            self._processes = {p.pid: p for p in processes}

    def list_processes(self) -> List[ProcessInfo]:
        with self._lock:
            return list(self._processes.values())

    def get_process(self, pid: int) -> ProcessInfo:
        with self._lock:
            if pid not in self._processes:
                raise KeyError("Process not found.")
            return self._processes[pid]

    def remove_process(self, pid: int) -> None:
        with self._lock:
            if pid not in self._processes:
                raise KeyError("Process not found.")
            del self._processes[pid]


class PerformanceHistory:
    def __init__(self, max_samples: int = 3600) -> None:
        if max_samples <= 0:
            raise ValueError("max_samples must be > 0.")
        self._lock = threading.RLock()
        self._max_samples = max_samples
        self._samples: List[MetricsSnapshot] = []

    @property
    def max_samples(self) -> int:
        return self._max_samples

    def add(self, snapshot: MetricsSnapshot) -> None:
        with self._lock:
            self._samples.append(snapshot)
            if len(self._samples) > self._max_samples:
                overflow = len(self._samples) - self._max_samples
                if overflow > 0:
                    del self._samples[:overflow]

    def list(self) -> List[MetricsSnapshot]:
        with self._lock:
            return list(self._samples)

    def latest(self) -> Optional[MetricsSnapshot]:
        with self._lock:
            return self._samples[-1] if self._samples else None


class Agent:
    def __init__(self, agent_id: str, history_max_samples: int = 3600) -> None:
        agent_id = (agent_id or "").strip()
        if not agent_id:
            raise ValueError("agent_id must be non-empty.")
        self._agent_id = agent_id
        self._lock = threading.RLock()
        self._status: ServerStatus = ServerStatus.OFFLINE
        self._last_seen: Optional[datetime] = None

        self._history = PerformanceHistory(max_samples=history_max_samples)
        self._process_table = ProcessTable()
        self._latest_capture: Optional[ScreenCapture] = None

    @property
    def agent_id(self) -> str:
        return self._agent_id

    @property
    def status(self) -> ServerStatus:
        with self._lock:
            return self._status

    @property
    def last_seen(self) -> Optional[datetime]:
        with self._lock:
            return self._last_seen

    def set_online(self) -> None:
        with self._lock:
            self._status = ServerStatus.ONLINE
            self._last_seen = datetime.now(timezone.utc)

    def set_offline(self) -> None:
        with self._lock:
            self._status = ServerStatus.OFFLINE

    def update_metrics(self, cpu_percent: float, ram_percent: float, net_sent_bytes: int, net_recv_bytes: int) -> MetricsSnapshot:
        if cpu_percent < 0.0 or cpu_percent > 100.0:
            raise ValueError("cpu_percent must be between 0 and 100.")
        if ram_percent < 0.0 or ram_percent > 100.0:
            raise ValueError("ram_percent must be between 0 and 100.")
        if net_sent_bytes < 0 or net_recv_bytes < 0:
            raise ValueError("Network byte counters must be non-negative.")

        snapshot = MetricsSnapshot(
            timestamp=datetime.now(timezone.utc),
            cpu_percent=float(cpu_percent),
            ram_percent=float(ram_percent),
            net_sent_bytes=int(net_sent_bytes),
            net_recv_bytes=int(net_recv_bytes),
        )
        with self._lock:
            self._status = ServerStatus.ONLINE
            self._last_seen = snapshot.timestamp
            self._history.add(snapshot)
        return snapshot

    def update_processes(self, processes: List[ProcessInfo]) -> None:
        for p in processes:
            if p.pid <= 0:
                raise ValueError("Process pid must be > 0.")
            if not p.name:
                raise ValueError("Process name must be non-empty.")
            if p.cpu_percent < 0.0 or p.cpu_percent > 100.0:
                raise ValueError("Process cpu_percent must be between 0 and 100.")
            if p.ram_percent < 0.0 or p.ram_percent > 100.0:
                raise ValueError("Process ram_percent must be between 0 and 100.")
        with self._lock:
            self._status = ServerStatus.ONLINE
            self._last_seen = datetime.now(timezone.utc)
            self._process_table.set_processes(processes)

    def capture_screen(self, raw_bytes: bytes) -> ScreenCapture:
        if raw_bytes is None:
            raise ValueError("raw_bytes must not be None.")
        image_b64 = base64.b64encode(raw_bytes).decode("ascii")
        capture = ScreenCapture(timestamp=datetime.now(timezone.utc), image_b64=image_b64)
        with self._lock:
            self._status = ServerStatus.ONLINE
            self._last_seen = capture.timestamp
            self._latest_capture = capture
        return capture

    def get_latest_capture(self) -> Optional[ScreenCapture]:
        with self._lock:
            return self._latest_capture

    def list_processes(self) -> List[ProcessInfo]:
        return self._process_table.list_processes()

    def get_performance_history(self) -> List[MetricsSnapshot]:
        return self._history.list()

    def get_latest_metrics(self) -> Optional[MetricsSnapshot]:
        return self._history.latest()

    def kill_process(self, pid: int) -> None:
        if pid <= 0:
            raise ValueError("pid must be > 0.")
        with self._lock:
            if self._status != ServerStatus.ONLINE:
                raise RuntimeError("Cannot kill process: server is offline.")
            self._process_table.remove_process(pid)
            self._last_seen = datetime.now(timezone.utc)


class Server:
    def __init__(self, server_id: str, agent: Agent) -> None:
        server_id = (server_id or "").strip()
        if not server_id:
            raise ValueError("server_id must be non-empty.")
        if not isinstance(agent, Agent):
            raise TypeError("agent must be an Agent.")
        self._server_id = server_id
        self._agent = agent

    @property
    def server_id(self) -> str:
        return self._server_id

    @property
    def status(self) -> ServerStatus:
        return self._agent.status

    @property
    def last_seen(self) -> Optional[datetime]:
        return self._agent.last_seen

    def get_latest_metrics(self) -> Optional[MetricsSnapshot]:
        return self._agent.get_latest_metrics()

    def get_performance_history(self) -> List[MetricsSnapshot]:
        return self._agent.get_performance_history()

    def list_processes(self) -> List[ProcessInfo]:
        return self._agent.list_processes()

    def kill_process(self, pid: int) -> None:
        self._agent.kill_process(pid)

    def get_latest_screen(self) -> Optional[ScreenCapture]:
        return self._agent.get_latest_capture()


class NexusCtrl:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._servers: Dict[str, Server] = {}
        self._agents: Dict[str, Agent] = {}
        self._tasks = TaskManager()

    @property
    def tasks(self) -> TaskManager:
        return self._tasks

    def register_server(self, server_id: str, agent_id: str, history_max_samples: int = 3600) -> None:
        server_id = (server_id or "").strip()
        agent_id = (agent_id or "").strip()
        if not server_id:
            raise ValueError("server_id must be non-empty.")
        if not agent_id:
            raise ValueError("agent_id must be non-empty.")
        with self._lock:
            if server_id in self._servers:
                raise ValueError("server_id already registered.")
            if agent_id in self._agents:
                agent = self._agents[agent_id]
            else:
                agent = Agent(agent_id=agent_id, history_max_samples=history_max_samples)
                self._agents[agent_id] = agent
            self._servers[server_id] = Server(server_id=server_id, agent=agent)

    def unregister_server(self, server_id: str) -> None:
        server_id = (server_id or "").strip()
        if not server_id:
            raise ValueError("server_id must be non-empty.")
        with self._lock:
            if server_id not in self._servers:
                raise KeyError("Server not found.")
            del self._servers[server_id]

    def list_servers(self) -> List[Server]:
        with self._lock:
            return list(self._servers.values())

    def get_server(self, server_id: str) -> Server:
        server_id = (server_id or "").strip()
        if not server_id:
            raise ValueError("server_id must be non-empty.")
        with self._lock:
            if server_id not in self._servers:
                raise KeyError("Server not found.")
            return self._servers[server_id]

    def get_agent(self, agent_id: str) -> Agent:
        agent_id = (agent_id or "").strip()
        if not agent_id:
            raise ValueError("agent_id must be non-empty.")
        with self._lock:
            if agent_id not in self._agents:
                raise KeyError("Agent not found.")
            return self._agents[agent_id]

    def update_agent_metrics(self, agent_id: str, cpu_percent: float, ram_percent: float, net_sent_bytes: int, net_recv_bytes: int) -> MetricsSnapshot:
        agent = self.get_agent(agent_id)
        return agent.update_metrics(cpu_percent=cpu_percent, ram_percent=ram_percent, net_sent_bytes=net_sent_bytes, net_recv_bytes=net_recv_bytes)

    def update_agent_processes(self, agent_id: str, processes: List[ProcessInfo]) -> None:
        agent = self.get_agent(agent_id)
        agent.update_processes(processes)

    def update_agent_screen(self, agent_id: str, raw_bytes: bytes) -> ScreenCapture:
        agent = self.get_agent(agent_id)
        return agent.capture_screen(raw_bytes)

    def kill_server_process(self, server_id: str, pid: int) -> None:
        server = self.get_server(server_id)
        server.kill_process(pid)

    def get_server_status(self, server_id: str) -> ServerStatus:
        return self.get_server(server_id).status

    def set_agent_offline(self, agent_id: str) -> None:
        agent = self.get_agent(agent_id)
        agent.set_offline()

    def set_agent_online(self, agent_id: str) -> None:
        agent = self.get_agent(agent_id)
        agent.set_online()


class AgentService:
    def __init__(self, nexus: NexusCtrl, agent_id: str) -> None:
        if not isinstance(nexus, NexusCtrl):
            raise TypeError("nexus must be a NexusCtrl.")
        agent_id = (agent_id or "").strip()
        if not agent_id:
            raise ValueError("agent_id must be non-empty.")
        self._nexus = nexus
        self._agent_id = agent_id
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()

        self._cpu_percent: float = 0.0
        self._ram_percent: float = 0.0
        self._net_sent: int = 0
        self._net_recv: int = 0
        self._processes: Dict[int, ProcessInfo] = {}
        self._next_pid: int = 1000

    @property
    def agent_id(self) -> str:
        return self._agent_id

    def start(self, interval_seconds: float = 1.0) -> None:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be > 0.")
        with self._lock:
            if self._running:
                return
            self._running = True
            self._nexus.set_agent_online(self._agent_id)
            self._thread = threading.Thread(target=self._run_loop, args=(interval_seconds,), daemon=True)
            self._thread.start()

    def stop(self) -> None:
        with self._lock:
            if not self._running:
                return
            self._running = False
        self._nexus.set_agent_offline(self._agent_id)

    def _run_loop(self, interval_seconds: float) -> None:
        while True:
            with self._lock:
                if not self._running:
                    break
                cpu = self._cpu_percent
                ram = self._ram_percent
                sent = self._net_sent
                recv = self._net_recv
                processes = list(self._processes.values())
            try:
                self._nexus.update_agent_metrics(self._agent_id, cpu, ram, sent, recv)
                self._nexus.update_agent_processes(self._agent_id, processes)
            except KeyError:
                with self._lock:
                    self._running = False
                break
            time.sleep(interval_seconds)

    def set_metrics(self, cpu_percent: float, ram_percent: float, net_sent_bytes: int, net_recv_bytes: int) -> None:
        if cpu_percent < 0.0 or cpu_percent > 100.0:
            raise ValueError("cpu_percent must be between 0 and 100.")
        if ram_percent < 0.0 or ram_percent > 100.0:
            raise ValueError("ram_percent must be between 0 and 100.")
        if net_sent_bytes < 0 or net_recv_bytes < 0:
            raise ValueError("Network byte counters must be non-negative.")
        with self._lock:
            self._cpu_percent = float(cpu_percent)
            self._ram_percent = float(ram_percent)
            self._net_sent = int(net_sent_bytes)
            self._net_recv = int(net_recv_bytes)

    def spawn_process(self, name: str, cpu_percent: float = 0.0, ram_percent: float = 0.0) -> int:
        name = (name or "").strip()
        if not name:
            raise ValueError("Process name must be non-empty.")
        if cpu_percent < 0.0 or cpu_percent > 100.0:
            raise ValueError("cpu_percent must be between 0 and 100.")
        if ram_percent < 0.0 or ram_percent > 100.0:
            raise ValueError("ram_percent must be between 0 and 100.")
        with self._lock:
            pid = self._next_pid
            self._next_pid += 1
            self._processes[pid] = ProcessInfo(pid=pid, name=name, cpu_percent=float(cpu_percent), ram_percent=float(ram_percent))
            return pid

    def update_process(self, pid: int, cpu_percent: float, ram_percent: float) -> None:
        if pid <= 0:
            raise ValueError("pid must be > 0.")
        if cpu_percent < 0.0 or cpu_percent > 100.0:
            raise ValueError("cpu_percent must be between 0 and 100.")
        if ram_percent < 0.0 or ram_percent > 100.0:
            raise ValueError("ram_percent must be between 0 and 100.")
        with self._lock:
            if pid not in self._processes:
                raise KeyError("Process not found.")
            p = self._processes[pid]
            self._processes[pid] = ProcessInfo(pid=pid, name=p.name, cpu_percent=float(cpu_percent), ram_percent=float(ram_percent))

    def kill_process(self, pid: int) -> None:
        if pid <= 0:
            raise ValueError("pid must be > 0.")
        with self._lock:
            if pid not in self._processes:
                raise KeyError("Process not found.")
            del self._processes[pid]

    def capture_screen(self, raw_bytes: bytes) -> ScreenCapture:
        return self._nexus.update_agent_screen(self._agent_id, raw_bytes)