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


class TaskStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"


class ServerStatus(Enum):
    ONLINE = "online"
    OFFLINE = "offline"


@dataclass(frozen=True)
class SystemMetrics:
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


class PerformanceHistory:
    def __init__(self, max_samples: int = 3600) -> None:
        if max_samples <= 0:
            raise ValueError("max_samples must be > 0")
        self._max_samples = max_samples
        self._samples: List[SystemMetrics] = []
        self._lock = threading.RLock()

    @property
    def max_samples(self) -> int:
        return self._max_samples

    def add(self, metrics: SystemMetrics) -> None:
        with self._lock:
            self._samples.append(metrics)
            if len(self._samples) > self._max_samples:
                overflow = len(self._samples) - self._max_samples
                if overflow > 0:
                    del self._samples[:overflow]

    def get_all(self) -> List[SystemMetrics]:
        with self._lock:
            return list(self._samples)

    def get_latest(self) -> Optional[SystemMetrics]:
        with self._lock:
            return self._samples[-1] if self._samples else None

    def get_range(self, start: datetime, end: datetime) -> List[SystemMetrics]:
        if start > end:
            raise ValueError("start must be <= end")
        with self._lock:
            return [s for s in self._samples if start <= s.timestamp <= end]


class Task:
    def __init__(self, task_id: str, title: str, priority: Priority = Priority.MEDIUM) -> None:
        if not task_id or not isinstance(task_id, str):
            raise ValueError("task_id must be a non-empty string")
        if not title or not isinstance(title, str):
            raise ValueError("title must be a non-empty string")
        if not isinstance(priority, Priority):
            raise ValueError("priority must be a Priority")

        self._id = task_id
        self._title = title
        self._priority = priority
        self._status = TaskStatus.PENDING
        self._created_at = _utcnow()
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
            raise ValueError("priority must be a Priority")
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
                raise ValueError(f"task_id already exists: {task_id}")
            task = Task(task_id=task_id, title=title, priority=priority)
            self._tasks[task_id] = task
            return task

    def get_task(self, task_id: str) -> Task:
        with self._lock:
            if task_id not in self._tasks:
                raise KeyError(task_id)
            return self._tasks[task_id]

    def delete_task(self, task_id: str) -> None:
        with self._lock:
            if task_id not in self._tasks:
                raise KeyError(task_id)
            del self._tasks[task_id]

    def list_tasks(self, status: Optional[TaskStatus] = None, priority: Optional[Priority] = None) -> List[Task]:
        with self._lock:
            tasks = list(self._tasks.values())
        if status is not None:
            if not isinstance(status, TaskStatus):
                raise ValueError("status must be a TaskStatus")
            tasks = [t for t in tasks if t.status == status]
        if priority is not None:
            if not isinstance(priority, Priority):
                raise ValueError("priority must be a Priority")
            tasks = [t for t in tasks if t.priority == priority]
        return tasks

    def mark_completed(self, task_id: str) -> None:
        task = self.get_task(task_id)
        task.mark_completed()

    def mark_pending(self, task_id: str) -> None:
        task = self.get_task(task_id)
        task.mark_pending()

    def set_priority(self, task_id: str, priority: Priority) -> None:
        task = self.get_task(task_id)
        task.set_priority(priority)


class AgentCommandError(RuntimeError):
    pass


class Agent:
    def __init__(self, agent_id: str) -> None:
        if not agent_id or not isinstance(agent_id, str):
            raise ValueError("agent_id must be a non-empty string")
        self._id = agent_id
        self._lock = threading.RLock()
        self._running = False

        self._processes: Dict[int, ProcessInfo] = {}
        self._latest_metrics: Optional[SystemMetrics] = None
        self._latest_screen_b64: Optional[str] = None

        self._net_sent_total = 0.0
        self._net_recv_total = 0.0
        self._last_tick = time.monotonic()

    @property
    def id(self) -> str:
        return self._id

    def start(self) -> None:
        with self._lock:
            self._running = True

    def stop(self) -> None:
        with self._lock:
            self._running = False

    def is_running(self) -> bool:
        with self._lock:
            return self._running

    def _ensure_running(self) -> None:
        if not self.is_running():
            raise AgentCommandError("agent is not running")

    def update_processes(self, processes: List[ProcessInfo]) -> None:
        self._ensure_running()
        with self._lock:
            new_map: Dict[int, ProcessInfo] = {}
            for p in processes:
                if p.pid <= 0:
                    raise ValueError("pid must be > 0")
                if not p.name:
                    raise ValueError("process name must be non-empty")
                if p.cpu_percent < 0 or p.ram_percent < 0:
                    raise ValueError("cpu_percent and ram_percent must be >= 0")
                new_map[p.pid] = p
            self._processes = new_map

    def update_metrics(self, cpu_percent: float, ram_percent: float, net_sent_bps: float, net_recv_bps: float) -> SystemMetrics:
        self._ensure_running()
        if cpu_percent < 0 or ram_percent < 0:
            raise ValueError("cpu_percent and ram_percent must be >= 0")
        if net_sent_bps < 0 or net_recv_bps < 0:
            raise ValueError("network rates must be >= 0")

        metrics = SystemMetrics(
            timestamp=_utcnow(),
            cpu_percent=float(cpu_percent),
            ram_percent=float(ram_percent),
            net_sent_bytes_per_sec=float(net_sent_bps),
            net_recv_bytes_per_sec=float(net_recv_bps),
        )
        with self._lock:
            self._latest_metrics = metrics
        return metrics

    def capture_screen(self, raw_bytes: bytes) -> str:
        self._ensure_running()
        if not isinstance(raw_bytes, (bytes, bytearray)):
            raise ValueError("raw_bytes must be bytes-like")
        b64 = base64.b64encode(bytes(raw_bytes)).decode("ascii")
        with self._lock:
            self._latest_screen_b64 = b64
        return b64

    def get_latest_metrics(self) -> Optional[SystemMetrics]:
        with self._lock:
            return self._latest_metrics

    def get_latest_screen_b64(self) -> Optional[str]:
        with self._lock:
            return self._latest_screen_b64

    def list_processes(self) -> List[ProcessInfo]:
        self._ensure_running()
        with self._lock:
            return list(self._processes.values())

    def kill_process(self, pid: int) -> bool:
        self._ensure_running()
        if pid <= 0:
            raise ValueError("pid must be > 0")
        with self._lock:
            if pid in self._processes:
                del self._processes[pid]
                return True
            return False

    def simulate_tick(
        self,
        cpu_percent: float,
        ram_percent: float,
        net_sent_increment_bytes: float,
        net_recv_increment_bytes: float,
        processes: Optional[List[ProcessInfo]] = None,
        screen_bytes: Optional[bytes] = None,
    ) -> Tuple[SystemMetrics, Optional[str]]:
        self._ensure_running()
        if net_sent_increment_bytes < 0 or net_recv_increment_bytes < 0:
            raise ValueError("network increments must be >= 0")

        now = time.monotonic()
        with self._lock:
            dt = max(1e-6, now - self._last_tick)
            self._last_tick = now
            self._net_sent_total += float(net_sent_increment_bytes)
            self._net_recv_total += float(net_recv_increment_bytes)
            sent_bps = float(net_sent_increment_bytes) / dt
            recv_bps = float(net_recv_increment_bytes) / dt

        metrics = self.update_metrics(cpu_percent=cpu_percent, ram_percent=ram_percent, net_sent_bps=sent_bps, net_recv_bps=recv_bps)

        if processes is not None:
            self.update_processes(processes)

        screen_b64: Optional[str] = None
        if screen_bytes is not None:
            screen_b64 = self.capture_screen(screen_bytes)

        return metrics, screen_b64


class Server:
    def __init__(self, server_id: str, name: str, agent: Agent, history_max_samples: int = 3600) -> None:
        if not server_id or not isinstance(server_id, str):
            raise ValueError("server_id must be a non-empty string")
        if not name or not isinstance(name, str):
            raise ValueError("name must be a non-empty string")
        if not isinstance(agent, Agent):
            raise ValueError("agent must be an Agent")

        self._id = server_id
        self._name = name
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
    def status(self) -> ServerStatus:
        return ServerStatus.ONLINE if self._agent.is_running() else ServerStatus.OFFLINE

    @property
    def history(self) -> PerformanceHistory:
        return self._history

    def get_latest_metrics(self) -> Optional[SystemMetrics]:
        return self._agent.get_latest_metrics()

    def get_latest_screen_b64(self) -> Optional[str]:
        if self.status == ServerStatus.OFFLINE:
            return None
        return self._agent.get_latest_screen_b64()

    def list_active_processes(self) -> List[ProcessInfo]:
        if self.status == ServerStatus.OFFLINE:
            return []
        return self._agent.list_processes()

    def terminate_process(self, pid: int) -> bool:
        if self.status == ServerStatus.OFFLINE:
            raise AgentCommandError("server is offline")
        return self._agent.kill_process(pid)

    def record_latest_metrics_to_history(self) -> Optional[SystemMetrics]:
        metrics = self._agent.get_latest_metrics()
        if metrics is None:
            return None
        self._history.add(metrics)
        return metrics

    def poll_and_record(self) -> Optional[SystemMetrics]:
        if self.status == ServerStatus.OFFLINE:
            return None
        return self.record_latest_metrics_to_history()


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
            raise ValueError("server must be a Server")
        with self._lock:
            if server.id in self._servers:
                raise ValueError(f"server_id already exists: {server.id}")
            self._servers[server.id] = server

    def unregister_server(self, server_id: str) -> None:
        with self._lock:
            if server_id not in self._servers:
                raise KeyError(server_id)
            del self._servers[server_id]

    def get_server(self, server_id: str) -> Server:
        with self._lock:
            if server_id not in self._servers:
                raise KeyError(server_id)
            return self._servers[server_id]

    def list_servers(self) -> List[Server]:
        with self._lock:
            return list(self._servers.values())

    def get_server_status(self, server_id: str) -> ServerStatus:
        return self.get_server(server_id).status

    def get_server_metrics(self, server_id: str) -> Optional[SystemMetrics]:
        return self.get_server(server_id).get_latest_metrics()

    def get_server_screen_b64(self, server_id: str) -> Optional[str]:
        return self.get_server(server_id).get_latest_screen_b64()

    def list_server_processes(self, server_id: str) -> List[ProcessInfo]:
        return self.get_server(server_id).list_active_processes()

    def kill_server_process(self, server_id: str, pid: int) -> bool:
        return self.get_server(server_id).terminate_process(pid)

    def record_server_metrics(self, server_id: str) -> Optional[SystemMetrics]:
        return self.get_server(server_id).record_latest_metrics_to_history()

    def get_server_history(self, server_id: str) -> List[SystemMetrics]:
        return self.get_server(server_id).history.get_all()

    def get_server_history_range(self, server_id: str, start: datetime, end: datetime) -> List[SystemMetrics]:
        return self.get_server(server_id).history.get_range(start, end)

    def poll_all_servers(self) -> Dict[str, Optional[SystemMetrics]]:
        results: Dict[str, Optional[SystemMetrics]] = {}
        for s in self.list_servers():
            results[s.id] = s.poll_and_record()
        return results


__all__ = [
    "Agent",
    "AgentCommandError",
    "NexusCtrl",
    "PerformanceHistory",
    "Priority",
    "ProcessInfo",
    "Server",
    "ServerStatus",
    "SystemMetrics",
    "Task",
    "TaskManager",
    "TaskStatus",
]