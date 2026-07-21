from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from threading import RLock
from typing import Dict, List, Optional, Tuple
import base64


class ServerStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"


class TaskPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"


@dataclass(frozen=True)
class MetricsSnapshot:
    timestamp: datetime
    cpu_percent: float
    ram_percent: float
    network_kbps: float

    def __post_init__(self) -> None:
        if not (0.0 <= self.cpu_percent <= 100.0):
            raise ValueError("cpu_percent must be between 0 and 100")
        if not (0.0 <= self.ram_percent <= 100.0):
            raise ValueError("ram_percent must be between 0 and 100")
        if self.network_kbps < 0.0:
            raise ValueError("network_kbps must be >= 0")


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


@dataclass
class Task:
    task_id: int
    title: str
    priority: TaskPriority
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = datetime.utcnow()
    completed_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if self.task_id <= 0:
            raise ValueError("task_id must be > 0")
        if not self.title:
            raise ValueError("title must be non-empty")
        if not isinstance(self.priority, TaskPriority):
            raise TypeError("priority must be a TaskPriority")
        if not isinstance(self.status, TaskStatus):
            raise TypeError("status must be a TaskStatus")
        if self.status == TaskStatus.COMPLETED and self.completed_at is None:
            self.completed_at = datetime.utcnow()
        if self.status == TaskStatus.PENDING and self.completed_at is not None:
            raise ValueError("completed_at must be None when status is pending")

    def mark_completed(self) -> None:
        if self.status != TaskStatus.COMPLETED:
            self.status = TaskStatus.COMPLETED
            self.completed_at = datetime.utcnow()

    def mark_pending(self) -> None:
        if self.status != TaskStatus.PENDING:
            self.status = TaskStatus.PENDING
            self.completed_at = None

    def set_priority(self, priority: TaskPriority) -> None:
        if not isinstance(priority, TaskPriority):
            raise TypeError("priority must be a TaskPriority")
        self.priority = priority


class PerformanceHistory:
    def __init__(self) -> None:
        self._lock = RLock()
        self._snapshots: List[MetricsSnapshot] = []

    def add_snapshot(self, snapshot: MetricsSnapshot) -> None:
        if not isinstance(snapshot, MetricsSnapshot):
            raise TypeError("snapshot must be a MetricsSnapshot")
        with self._lock:
            self._snapshots.append(snapshot)

    def get_all(self) -> List[MetricsSnapshot]:
        with self._lock:
            return list(self._snapshots)

    def latest(self) -> Optional[MetricsSnapshot]:
        with self._lock:
            return self._snapshots[-1] if self._snapshots else None

    def clear(self) -> None:
        with self._lock:
            self._snapshots.clear()


class Agent:
    def __init__(self, agent_id: str) -> None:
        if not agent_id:
            raise ValueError("agent_id must be non-empty")
        self._agent_id = agent_id
        self._lock = RLock()
        self._status: ServerStatus = ServerStatus.OFFLINE
        self._history = PerformanceHistory()
        self._processes: Dict[int, ProcessInfo] = {}
        self._last_screen: Optional[ScreenCapture] = None

    @property
    def agent_id(self) -> str:
        return self._agent_id

    def set_status(self, status: ServerStatus) -> None:
        if not isinstance(status, ServerStatus):
            raise TypeError("status must be a ServerStatus")
        with self._lock:
            self._status = status

    def get_status(self) -> ServerStatus:
        with self._lock:
            return self._status

    def report_metrics(self, cpu_percent: float, ram_percent: float, network_kbps: float, timestamp: Optional[datetime] = None) -> MetricsSnapshot:
        snap = MetricsSnapshot(
            timestamp=timestamp or datetime.utcnow(),
            cpu_percent=float(cpu_percent),
            ram_percent=float(ram_percent),
            network_kbps=float(network_kbps),
        )
        with self._lock:
            self._history.add_snapshot(snap)
        return snap

    def get_performance_history(self) -> List[MetricsSnapshot]:
        return self._history.get_all()

    def get_latest_metrics(self) -> Optional[MetricsSnapshot]:
        return self._history.latest()

    def report_processes(self, processes: List[ProcessInfo]) -> None:
        if processes is None:
            raise ValueError("processes must not be None")
        proc_map: Dict[int, ProcessInfo] = {}
        for p in processes:
            if not isinstance(p, ProcessInfo):
                raise TypeError("process list must contain ProcessInfo items")
            proc_map[p.pid] = p
        with self._lock:
            self._processes = proc_map

    def list_processes(self) -> List[ProcessInfo]:
        with self._lock:
            return list(self._processes.values())

    def kill_process(self, pid: int) -> bool:
        if pid <= 0:
            raise ValueError("pid must be > 0")
        with self._lock:
            if pid in self._processes:
                del self._processes[pid]
                return True
            return False

    def report_screen_capture(self, image_bytes: bytes, timestamp: Optional[datetime] = None) -> ScreenCapture:
        cap = ScreenCapture(timestamp=timestamp or datetime.utcnow(), image_bytes=bytes(image_bytes))
        with self._lock:
            self._last_screen = cap
        return cap

    def get_last_screen_capture(self) -> Optional[ScreenCapture]:
        with self._lock:
            return self._last_screen


class Server:
    def __init__(self, server_id: str, name: str, agent: Agent) -> None:
        if not server_id:
            raise ValueError("server_id must be non-empty")
        if not name:
            raise ValueError("name must be non-empty")
        if not isinstance(agent, Agent):
            raise TypeError("agent must be an Agent")
        self._server_id = server_id
        self._name = name
        self._agent = agent

    @property
    def server_id(self) -> str:
        return self._server_id

    @property
    def name(self) -> str:
        return self._name

    def rename(self, new_name: str) -> None:
        if not new_name:
            raise ValueError("new_name must be non-empty")
        self._name = new_name

    @property
    def agent(self) -> Agent:
        return self._agent

    def status(self) -> ServerStatus:
        return self._agent.get_status()

    def latest_metrics(self) -> Optional[MetricsSnapshot]:
        return self._agent.get_latest_metrics()

    def performance_history(self) -> List[MetricsSnapshot]:
        return self._agent.get_performance_history()

    def list_processes(self) -> List[ProcessInfo]:
        return self._agent.list_processes()

    def terminate_process(self, pid: int) -> bool:
        return self._agent.kill_process(pid)

    def last_screen_capture(self) -> Optional[ScreenCapture]:
        return self._agent.get_last_screen_capture()


class TaskManager:
    def __init__(self) -> None:
        self._lock = RLock()
        self._tasks: Dict[int, Task] = {}
        self._next_id = 1

    def create_task(self, title: str, priority: TaskPriority) -> Task:
        if not title:
            raise ValueError("title must be non-empty")
        if not isinstance(priority, TaskPriority):
            raise TypeError("priority must be a TaskPriority")
        with self._lock:
            task_id = self._next_id
            self._next_id += 1
            task = Task(task_id=task_id, title=title, priority=priority)
            self._tasks[task_id] = task
            return task

    def get_task(self, task_id: int) -> Task:
        if task_id <= 0:
            raise ValueError("task_id must be > 0")
        with self._lock:
            if task_id not in self._tasks:
                raise KeyError(f"Task {task_id} not found")
            return self._tasks[task_id]

    def list_tasks(self, status: Optional[TaskStatus] = None, priority: Optional[TaskPriority] = None) -> List[Task]:
        if status is not None and not isinstance(status, TaskStatus):
            raise TypeError("status must be a TaskStatus or None")
        if priority is not None and not isinstance(priority, TaskPriority):
            raise TypeError("priority must be a TaskPriority or None")
        with self._lock:
            tasks = list(self._tasks.values())
        if status is not None:
            tasks = [t for t in tasks if t.status == status]
        if priority is not None:
            tasks = [t for t in tasks if t.priority == priority]
        return tasks

    def complete_task(self, task_id: int) -> Task:
        task = self.get_task(task_id)
        with self._lock:
            task.mark_completed()
            return task

    def set_task_priority(self, task_id: int, priority: TaskPriority) -> Task:
        if not isinstance(priority, TaskPriority):
            raise TypeError("priority must be a TaskPriority")
        task = self.get_task(task_id)
        with self._lock:
            task.set_priority(priority)
            return task

    def delete_task(self, task_id: int) -> None:
        if task_id <= 0:
            raise ValueError("task_id must be > 0")
        with self._lock:
            if task_id not in self._tasks:
                raise KeyError(f"Task {task_id} not found")
            del self._tasks[task_id]


class NexusCtrl:
    def __init__(self) -> None:
        self._lock = RLock()
        self._agents: Dict[str, Agent] = {}
        self._servers: Dict[str, Server] = {}
        self._tasks = TaskManager()

    @property
    def tasks(self) -> TaskManager:
        return self._tasks

    def register_agent(self, agent_id: str) -> Agent:
        if not agent_id:
            raise ValueError("agent_id must be non-empty")
        with self._lock:
            if agent_id in self._agents:
                return self._agents[agent_id]
            agent = Agent(agent_id=agent_id)
            self._agents[agent_id] = agent
            return agent

    def get_agent(self, agent_id: str) -> Agent:
        if not agent_id:
            raise ValueError("agent_id must be non-empty")
        with self._lock:
            if agent_id not in self._agents:
                raise KeyError(f"Agent {agent_id} not found")
            return self._agents[agent_id]

    def register_server(self, server_id: str, name: str, agent_id: str) -> Server:
        if not server_id:
            raise ValueError("server_id must be non-empty")
        if not name:
            raise ValueError("name must be non-empty")
        if not agent_id:
            raise ValueError("agent_id must be non-empty")
        with self._lock:
            if server_id in self._servers:
                raise ValueError(f"Server {server_id} already exists")
            agent = self._agents.get(agent_id)
            if agent is None:
                agent = Agent(agent_id=agent_id)
                self._agents[agent_id] = agent
            server = Server(server_id=server_id, name=name, agent=agent)
            self._servers[server_id] = server
            return server

    def get_server(self, server_id: str) -> Server:
        if not server_id:
            raise ValueError("server_id must be non-empty")
        with self._lock:
            if server_id not in self._servers:
                raise KeyError(f"Server {server_id} not found")
            return self._servers[server_id]

    def list_servers(self) -> List[Server]:
        with self._lock:
            return list(self._servers.values())

    def server_status(self, server_id: str) -> ServerStatus:
        return self.get_server(server_id).status()

    def server_latest_metrics(self, server_id: str) -> Optional[MetricsSnapshot]:
        return self.get_server(server_id).latest_metrics()

    def server_performance_history(self, server_id: str) -> List[MetricsSnapshot]:
        return self.get_server(server_id).performance_history()

    def server_list_processes(self, server_id: str) -> List[ProcessInfo]:
        return self.get_server(server_id).list_processes()

    def server_terminate_process(self, server_id: str, pid: int) -> bool:
        return self.get_server(server_id).terminate_process(pid)

    def server_last_screen_capture(self, server_id: str) -> Optional[ScreenCapture]:
        return self.get_server(server_id).last_screen_capture()

    def agent_set_status(self, agent_id: str, status: ServerStatus) -> None:
        self.get_agent(agent_id).set_status(status)

    def agent_report_metrics(self, agent_id: str, cpu_percent: float, ram_percent: float, network_kbps: float, timestamp: Optional[datetime] = None) -> MetricsSnapshot:
        return self.get_agent(agent_id).report_metrics(cpu_percent=cpu_percent, ram_percent=ram_percent, network_kbps=network_kbps, timestamp=timestamp)

    def agent_report_processes(self, agent_id: str, processes: List[ProcessInfo]) -> None:
        self.get_agent(agent_id).report_processes(processes)

    def agent_report_screen_capture(self, agent_id: str, image_bytes: bytes, timestamp: Optional[datetime] = None) -> ScreenCapture:
        return self.get_agent(agent_id).report_screen_capture(image_bytes=image_bytes, timestamp=timestamp)

    def agent_kill_process(self, agent_id: str, pid: int) -> bool:
        return self.get_agent(agent_id).kill_process(pid)


__all__ = [
    "ServerStatus",
    "TaskPriority",
    "TaskStatus",
    "MetricsSnapshot",
    "ProcessInfo",
    "ScreenCapture",
    "Task",
    "PerformanceHistory",
    "Agent",
    "Server",
    "TaskManager",
    "NexusCtrl",
]