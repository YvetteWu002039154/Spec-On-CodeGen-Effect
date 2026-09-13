from __future__ import annotations

import base64
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple


class TaskPriority(str, Enum):
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
    image_bytes: bytes

    def to_base64(self) -> str:
        return base64.b64encode(self.image_bytes).decode("ascii")


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


class Task:
    def __init__(self, task_id: int, title: str, priority: TaskPriority) -> None:
        if not title or not title.strip():
            raise ValueError("title must be non-empty")
        self._id = task_id
        self._title = title.strip()
        self._priority = priority
        self._status = TaskStatus.PENDING
        self._created_at = time.time()
        self._completed_at: Optional[float] = None

    @property
    def id(self) -> int:
        return self._id

    @property
    def title(self) -> str:
        return self._title

    @property
    def priority(self) -> TaskPriority:
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

    def set_priority(self, priority: TaskPriority) -> None:
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
        self._tasks: Dict[int, Task] = {}
        self._next_id = 1
        self._lock = threading.RLock()

    def create_task(self, title: str, priority: TaskPriority) -> Task:
        with self._lock:
            task = Task(self._next_id, title, priority)
            self._tasks[task.id] = task
            self._next_id += 1
            return task

    def get_task(self, task_id: int) -> Task:
        with self._lock:
            if task_id not in self._tasks:
                raise KeyError(f"Task {task_id} not found")
            return self._tasks[task_id]

    def list_tasks(self, status: Optional[TaskStatus] = None) -> List[Task]:
        with self._lock:
            tasks = list(self._tasks.values())
            if status is not None:
                tasks = [t for t in tasks if t.status == status]
            priority_order = {
                TaskPriority.CRITICAL: 0,
                TaskPriority.HIGH: 1,
                TaskPriority.MEDIUM: 2,
                TaskPriority.LOW: 3,
            }
            tasks.sort(key=lambda t: (priority_order[t.priority], t.created_at, t.id))
            return tasks

    def set_task_priority(self, task_id: int, priority: TaskPriority) -> None:
        with self._lock:
            self.get_task(task_id).set_priority(priority)

    def complete_task(self, task_id: int) -> None:
        with self._lock:
            self.get_task(task_id).mark_completed()

    def reopen_task(self, task_id: int) -> None:
        with self._lock:
            self.get_task(task_id).mark_pending()


class Agent:
    def __init__(self, server_id: str) -> None:
        if not server_id or not server_id.strip():
            raise ValueError("server_id must be non-empty")
        self._server_id = server_id.strip()
        self._running = False
        self._lock = threading.RLock()

        self._cpu_percent = 0.0
        self._ram_percent = 0.0
        self._net_sent_bps = 0.0
        self._net_recv_bps = 0.0

        self._processes: Dict[int, ProcessInfo] = {}
        self._next_pid = 1000

        self._last_capture: Optional[ScreenCapture] = None
        self._thread: Optional[threading.Thread] = None

    @property
    def server_id(self) -> str:
        return self._server_id

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        with self._lock:
            self._running = False

    def is_running(self) -> bool:
        with self._lock:
            return self._running

    def _run_loop(self) -> None:
        while True:
            with self._lock:
                if not self._running:
                    break
            self._simulate_metrics_update()
            time.sleep(1.0)

    def _simulate_metrics_update(self) -> None:
        with self._lock:
            t = time.time()
            self._cpu_percent = float((t * 37.0) % 100.0)
            self._ram_percent = float((t * 19.0) % 100.0)
            self._net_sent_bps = float((t * 12345.0) % 5_000_000.0)
            self._net_recv_bps = float((t * 23456.0) % 5_000_000.0)

            if not self._processes:
                for name in ("rdpclip.exe", "explorer.exe", "svchost.exe", "chrome.exe"):
                    self._spawn_process(name)

            procs = list(self._processes.values())
            updated: Dict[int, ProcessInfo] = {}
            for p in procs:
                cpu = float(((t + p.pid) * 3.1) % 35.0)
                ram = float(((t + p.pid) * 1.7) % 25.0)
                updated[p.pid] = ProcessInfo(pid=p.pid, name=p.name, cpu_percent=cpu, ram_percent=ram)
            self._processes = updated

            self._last_capture = ScreenCapture(timestamp=t, image_bytes=self._generate_fake_screen_bytes(t))

    def _generate_fake_screen_bytes(self, t: float) -> bytes:
        payload = f"NexusCtrl Screen {self._server_id} {t}".encode("utf-8")
        return payload

    def _spawn_process(self, name: str) -> ProcessInfo:
        pid = self._next_pid
        self._next_pid += 1
        p = ProcessInfo(pid=pid, name=name, cpu_percent=0.0, ram_percent=0.0)
        self._processes[pid] = p
        return p

    def collect_metrics(self) -> Tuple[float, float, float, float]:
        with self._lock:
            return self._cpu_percent, self._ram_percent, self._net_sent_bps, self._net_recv_bps

    def list_processes(self) -> List[ProcessInfo]:
        with self._lock:
            return sorted(self._processes.values(), key=lambda p: p.pid)

    def kill_process(self, pid: int) -> bool:
        with self._lock:
            if pid in self._processes:
                del self._processes[pid]
                return True
            return False

    def capture_screen(self) -> Optional[ScreenCapture]:
        with self._lock:
            return self._last_capture


class Server:
    def __init__(self, server_id: str, name: str, agent: Optional[Agent] = None, history_max_samples: int = 3600) -> None:
        if not server_id or not server_id.strip():
            raise ValueError("server_id must be non-empty")
        if not name or not name.strip():
            raise ValueError("name must be non-empty")
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
    def status(self) -> ServerStatus:
        with self._lock:
            if self._agent is None:
                return ServerStatus.OFFLINE
            return ServerStatus.ONLINE if self._agent.is_running() else ServerStatus.OFFLINE

    def attach_agent(self, agent: Agent) -> None:
        if agent.server_id != self._id:
            raise ValueError("agent.server_id must match server.id")
        with self._lock:
            self._agent = agent

    def detach_agent(self) -> None:
        with self._lock:
            self._agent = None

    def poll(self) -> None:
        with self._lock:
            agent = self._agent
        if agent is None or not agent.is_running():
            return
        cpu, ram, sent, recv = agent.collect_metrics()
        sample = PerformanceSample(
            timestamp=time.time(),
            cpu_percent=cpu,
            ram_percent=ram,
            net_sent_bytes_per_sec=sent,
            net_recv_bytes_per_sec=recv,
        )
        self._history.add_sample(sample)

    def get_performance_history(self, limit: Optional[int] = None) -> List[PerformanceSample]:
        return self._history.get_samples(limit=limit)

    def latest_performance(self) -> Optional[PerformanceSample]:
        return self._history.latest()

    def list_processes(self) -> List[ProcessInfo]:
        with self._lock:
            agent = self._agent
        if agent is None or not agent.is_running():
            return []
        return agent.list_processes()

    def terminate_process(self, pid: int) -> bool:
        with self._lock:
            agent = self._agent
        if agent is None or not agent.is_running():
            return False
        return agent.kill_process(pid)

    def get_screen_capture(self) -> Optional[ScreenCapture]:
        with self._lock:
            agent = self._agent
        if agent is None or not agent.is_running():
            return None
        return agent.capture_screen()


class NexusCtrl:
    def __init__(self) -> None:
        self._servers: Dict[str, Server] = {}
        self._tasks = TaskManager()
        self._lock = threading.RLock()

    @property
    def tasks(self) -> TaskManager:
        return self._tasks

    def add_server(self, server: Server) -> None:
        with self._lock:
            if server.id in self._servers:
                raise ValueError(f"Server {server.id} already exists")
            self._servers[server.id] = server

    def get_server(self, server_id: str) -> Server:
        with self._lock:
            if server_id not in self._servers:
                raise KeyError(f"Server {server_id} not found")
            return self._servers[server_id]

    def list_servers(self) -> List[Server]:
        with self._lock:
            return sorted(self._servers.values(), key=lambda s: s.id)

    def server_status(self, server_id: str) -> ServerStatus:
        return self.get_server(server_id).status

    def poll_server(self, server_id: str) -> None:
        self.get_server(server_id).poll()

    def poll_all_servers(self) -> None:
        for s in self.list_servers():
            s.poll()

    def list_server_processes(self, server_id: str) -> List[ProcessInfo]:
        return self.get_server(server_id).list_processes()

    def terminate_server_process(self, server_id: str, pid: int) -> bool:
        return self.get_server(server_id).terminate_process(pid)

    def get_server_screen(self, server_id: str) -> Optional[ScreenCapture]:
        return self.get_server(server_id).get_screen_capture()

    def get_server_history(self, server_id: str, limit: Optional[int] = None) -> List[PerformanceSample]:
        return self.get_server(server_id).get_performance_history(limit=limit)


__all__ = [
    "TaskPriority",
    "TaskStatus",
    "ServerStatus",
    "PerformanceSample",
    "ProcessInfo",
    "ScreenCapture",
    "PerformanceHistory",
    "Task",
    "TaskManager",
    "Agent",
    "Server",
    "NexusCtrl",
]