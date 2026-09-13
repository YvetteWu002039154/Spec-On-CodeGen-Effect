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


class ServerStatus(Enum):
    ONLINE = "online"
    OFFLINE = "offline"


class TaskStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"


@dataclass(frozen=True)
class SystemMetrics:
    timestamp: float
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
    timestamp: float
    image_b64: str


class Task:
    def __init__(self, task_id: int, title: str, priority: Priority) -> None:
        if not isinstance(task_id, int) or task_id <= 0:
            raise ValueError("task_id must be a positive integer")
        if not isinstance(title, str) or not title.strip():
            raise ValueError("title must be a non-empty string")
        if not isinstance(priority, Priority):
            raise ValueError("priority must be a Priority")

        self._id: int = task_id
        self._title: str = title.strip()
        self._priority: Priority = priority
        self._status: TaskStatus = TaskStatus.PENDING
        self._created_at: float = time.time()
        self._completed_at: Optional[float] = None

    @property
    def id(self) -> int:
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
    def created_at(self) -> float:
        return self._created_at

    @property
    def completed_at(self) -> Optional[float]:
        return self._completed_at

    def set_priority(self, priority: Priority) -> None:
        if not isinstance(priority, Priority):
            raise ValueError("priority must be a Priority")
        self._priority = priority

    def mark_completed(self) -> None:
        if self._status == TaskStatus.COMPLETED:
            return
        self._status = TaskStatus.COMPLETED
        self._completed_at = time.time()

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

    def create_task(self, title: str, priority: Priority) -> Task:
        with self._lock:
            task = Task(self._next_id, title, priority)
            self._tasks[task.id] = task
            self._next_id += 1
            return task

    def get_task(self, task_id: int) -> Task:
        with self._lock:
            if task_id not in self._tasks:
                raise KeyError("task not found")
            return self._tasks[task_id]

    def list_tasks(self) -> List[Task]:
        with self._lock:
            return list(self._tasks.values())

    def list_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        if not isinstance(status, TaskStatus):
            raise ValueError("status must be a TaskStatus")
        with self._lock:
            return [t for t in self._tasks.values() if t.status == status]

    def set_task_priority(self, task_id: int, priority: Priority) -> None:
        with self._lock:
            self.get_task(task_id).set_priority(priority)

    def complete_task(self, task_id: int) -> None:
        with self._lock:
            self.get_task(task_id).mark_completed()

    def reopen_task(self, task_id: int) -> None:
        with self._lock:
            self.get_task(task_id).mark_pending()


class PerformanceHistory:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._metrics: List[SystemMetrics] = []

    def add(self, metrics: SystemMetrics) -> None:
        if not isinstance(metrics, SystemMetrics):
            raise ValueError("metrics must be a SystemMetrics")
        with self._lock:
            self._metrics.append(metrics)

    def latest(self) -> Optional[SystemMetrics]:
        with self._lock:
            return self._metrics[-1] if self._metrics else None

    def all(self) -> List[SystemMetrics]:
        with self._lock:
            return list(self._metrics)


class Agent:
    def __init__(self, agent_id: str) -> None:
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise ValueError("agent_id must be a non-empty string")
        self._id: str = agent_id.strip()
        self._lock = threading.RLock()
        self._running: bool = False
        self._status: ServerStatus = ServerStatus.OFFLINE

        self._cpu_percent: float = 0.0
        self._ram_percent: float = 0.0
        self._net_sent_bytes: int = 0
        self._net_recv_bytes: int = 0

        self._processes: Dict[int, ProcessInfo] = {}
        self._next_pid: int = 1000

        self._last_screen: Optional[ScreenCapture] = None

    @property
    def id(self) -> str:
        return self._id

    def start(self) -> None:
        with self._lock:
            self._running = True
            self._status = ServerStatus.ONLINE

    def stop(self) -> None:
        with self._lock:
            self._running = False
            self._status = ServerStatus.OFFLINE

    def status(self) -> ServerStatus:
        with self._lock:
            return self._status

    def collect_metrics(self) -> SystemMetrics:
        with self._lock:
            if not self._running:
                raise RuntimeError("agent is offline")

            cpu = float(max(0.0, min(100.0, self._cpu_percent)))
            ram = float(max(0.0, min(100.0, self._ram_percent)))
            metrics = SystemMetrics(
                timestamp=time.time(),
                cpu_percent=cpu,
                ram_percent=ram,
                net_sent_bytes=int(self._net_sent_bytes),
                net_recv_bytes=int(self._net_recv_bytes),
            )
            return metrics

    def list_processes(self) -> List[ProcessInfo]:
        with self._lock:
            if not self._running:
                raise RuntimeError("agent is offline")
            return list(self._processes.values())

    def kill_process(self, pid: int) -> None:
        with self._lock:
            if not self._running:
                raise RuntimeError("agent is offline")
            if pid not in self._processes:
                raise KeyError("process not found")
            del self._processes[pid]

    def capture_screen(self) -> ScreenCapture:
        with self._lock:
            if not self._running:
                raise RuntimeError("agent is offline")
            payload = f"screen:{self._id}:{time.time()}".encode("utf-8")
            img_b64 = base64.b64encode(payload).decode("ascii")
            cap = ScreenCapture(timestamp=time.time(), image_b64=img_b64)
            self._last_screen = cap
            return cap

    def last_screen(self) -> Optional[ScreenCapture]:
        with self._lock:
            return self._last_screen

    def _set_usage(self, cpu_percent: float, ram_percent: float, net_sent_bytes: int, net_recv_bytes: int) -> None:
        with self._lock:
            self._cpu_percent = float(cpu_percent)
            self._ram_percent = float(ram_percent)
            self._net_sent_bytes = int(net_sent_bytes)
            self._net_recv_bytes = int(net_recv_bytes)

    def _spawn_process(self, name: str, cpu_percent: float, ram_percent: float) -> ProcessInfo:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("name must be a non-empty string")
        with self._lock:
            pid = self._next_pid
            self._next_pid += 1
            p = ProcessInfo(pid=pid, name=name.strip(), cpu_percent=float(cpu_percent), ram_percent=float(ram_percent))
            self._processes[pid] = p
            return p

    def _update_process(self, pid: int, cpu_percent: float, ram_percent: float) -> None:
        with self._lock:
            if pid not in self._processes:
                raise KeyError("process not found")
            old = self._processes[pid]
            self._processes[pid] = ProcessInfo(
                pid=old.pid,
                name=old.name,
                cpu_percent=float(cpu_percent),
                ram_percent=float(ram_percent),
            )


class Server:
    def __init__(self, server_id: str, agent: Agent) -> None:
        if not isinstance(server_id, str) or not server_id.strip():
            raise ValueError("server_id must be a non-empty string")
        if not isinstance(agent, Agent):
            raise ValueError("agent must be an Agent")

        self._id: str = server_id.strip()
        self._agent: Agent = agent
        self._history: PerformanceHistory = PerformanceHistory()

    @property
    def id(self) -> str:
        return self._id

    def status(self) -> ServerStatus:
        return self._agent.status()

    def poll_metrics(self) -> SystemMetrics:
        metrics = self._agent.collect_metrics()
        self._history.add(metrics)
        return metrics

    def performance_history(self) -> List[SystemMetrics]:
        return self._history.all()

    def latest_metrics(self) -> Optional[SystemMetrics]:
        return self._history.latest()

    def list_active_processes(self) -> List[ProcessInfo]:
        return self._agent.list_processes()

    def terminate_process(self, pid: int) -> None:
        self._agent.kill_process(pid)

    def live_screen(self) -> ScreenCapture:
        return self._agent.capture_screen()

    def last_screen(self) -> Optional[ScreenCapture]:
        return self._agent.last_screen()


class NexusCtrl:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._servers: Dict[str, Server] = {}
        self._tasks: TaskManager = TaskManager()

    @property
    def tasks(self) -> TaskManager:
        return self._tasks

    def register_server(self, server: Server) -> None:
        if not isinstance(server, Server):
            raise ValueError("server must be a Server")
        with self._lock:
            if server.id in self._servers:
                raise ValueError("server already registered")
            self._servers[server.id] = server

    def unregister_server(self, server_id: str) -> None:
        if not isinstance(server_id, str) or not server_id.strip():
            raise ValueError("server_id must be a non-empty string")
        with self._lock:
            if server_id not in self._servers:
                raise KeyError("server not found")
            del self._servers[server_id]

    def get_server(self, server_id: str) -> Server:
        if not isinstance(server_id, str) or not server_id.strip():
            raise ValueError("server_id must be a non-empty string")
        with self._lock:
            if server_id not in self._servers:
                raise KeyError("server not found")
            return self._servers[server_id]

    def list_servers(self) -> List[Server]:
        with self._lock:
            return list(self._servers.values())

    def server_status(self, server_id: str) -> ServerStatus:
        return self.get_server(server_id).status()

    def poll_server_metrics(self, server_id: str) -> SystemMetrics:
        return self.get_server(server_id).poll_metrics()

    def get_server_history(self, server_id: str) -> List[SystemMetrics]:
        return self.get_server(server_id).performance_history()

    def get_live_screen(self, server_id: str) -> ScreenCapture:
        return self.get_server(server_id).live_screen()

    def list_server_processes(self, server_id: str) -> List[ProcessInfo]:
        return self.get_server(server_id).list_active_processes()

    def kill_server_process(self, server_id: str, pid: int) -> None:
        self.get_server(server_id).terminate_process(pid)


class InMemoryAgent(Agent):
    def __init__(self, agent_id: str) -> None:
        super().__init__(agent_id)

    def set_usage(self, cpu_percent: float, ram_percent: float, net_sent_bytes: int, net_recv_bytes: int) -> None:
        self._set_usage(cpu_percent, ram_percent, net_sent_bytes, net_recv_bytes)

    def spawn_process(self, name: str, cpu_percent: float = 0.0, ram_percent: float = 0.0) -> ProcessInfo:
        return self._spawn_process(name, cpu_percent, ram_percent)

    def update_process(self, pid: int, cpu_percent: float, ram_percent: float) -> None:
        self._update_process(pid, cpu_percent, ram_percent)


def build_demo_controller() -> Tuple[NexusCtrl, InMemoryAgent, Server]:
    ctrl = NexusCtrl()
    agent = InMemoryAgent("agent-1")
    server = Server("server-1", agent)
    ctrl.register_server(server)
    agent.start()
    agent.set_usage(cpu_percent=12.5, ram_percent=43.2, net_sent_bytes=1024, net_recv_bytes=2048)
    agent.spawn_process("rdpclip.exe", cpu_percent=0.1, ram_percent=0.5)
    agent.spawn_process("explorer.exe", cpu_percent=1.2, ram_percent=2.3)
    return ctrl, agent, server


if __name__ == "__main__":
    ctrl, agent, server = build_demo_controller()
    ctrl.tasks.create_task("Review server health", Priority.HIGH)
    ctrl.tasks.create_task("Kill suspicious process", Priority.CRITICAL)
    m = ctrl.poll_server_metrics(server.id)
    _ = ctrl.get_live_screen(server.id)
    procs = ctrl.list_server_processes(server.id)
    if procs:
        ctrl.kill_server_process(server.id, procs[0].pid)
    _ = ctrl.poll_server_metrics(server.id)