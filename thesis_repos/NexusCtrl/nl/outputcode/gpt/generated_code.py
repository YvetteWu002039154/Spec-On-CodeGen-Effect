from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from threading import RLock
from typing import Dict, List, Optional
import base64
import os
import platform
import socket
import subprocess
import uuid

try:
    import psutil  # type: ignore
except Exception:
    psutil = None


class Priority(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

    @classmethod
    def from_value(cls, value: str) -> "Priority":
        normalized = value.strip().lower()
        for item in cls:
            if item.value == normalized:
                return item
        raise ValueError("Invalid priority")


class TaskStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"

    @classmethod
    def from_value(cls, value: str) -> "TaskStatus":
        normalized = value.strip().lower()
        for item in cls:
            if item.value == normalized:
                return item
        raise ValueError("Invalid task status")


class ServerStatus(Enum):
    ONLINE = "online"
    OFFLINE = "offline"


@dataclass(frozen=True)
class SystemMetrics:
    cpu_percent: float
    ram_percent: float
    network_sent_bytes: int
    network_recv_bytes: int
    timestamp: datetime


@dataclass(frozen=True)
class ProcessInfo:
    pid: int
    name: str
    cpu_percent: float
    memory_percent: float


@dataclass(frozen=True)
class ScreenCapture:
    image_base64: str
    timestamp: datetime


class Task:
    def __init__(self, title: str, priority: Priority, description: str = "") -> None:
        if not title or not title.strip():
            raise ValueError("Task title cannot be empty")
        self._id: str = str(uuid.uuid4())
        self._title: str = title.strip()
        self._description: str = description.strip()
        self._priority: Priority = priority
        self._status: TaskStatus = TaskStatus.PENDING
        self._created_at: datetime = datetime.utcnow()
        self._completed_at: Optional[datetime] = None

    @property
    def id(self) -> str:
        return self._id

    @property
    def title(self) -> str:
        return self._title

    @property
    def description(self) -> str:
        return self._description

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
        self._status = TaskStatus.COMPLETED
        self._completed_at = datetime.utcnow()

    def mark_pending(self) -> None:
        self._status = TaskStatus.PENDING
        self._completed_at = None

    def set_priority(self, priority: Priority) -> None:
        self._priority = priority

    def update(self, title: Optional[str] = None, description: Optional[str] = None) -> None:
        if title is not None:
            if not title.strip():
                raise ValueError("Task title cannot be empty")
            self._title = title.strip()
        if description is not None:
            self._description = description.strip()

    def to_dict(self) -> Dict[str, Optional[str]]:
        return {
            "id": self._id,
            "title": self._title,
            "description": self._description,
            "priority": self._priority.value,
            "status": self._status.value,
            "created_at": self._created_at.isoformat(),
            "completed_at": self._completed_at.isoformat() if self._completed_at else None,
        }


class TaskManager:
    def __init__(self) -> None:
        self._tasks: Dict[str, Task] = {}
        self._lock = RLock()

    def create_task(self, title: str, priority: Priority, description: str = "") -> Task:
        with self._lock:
            task = Task(title=title, priority=priority, description=description)
            self._tasks[task.id] = task
            return task

    def get_task(self, task_id: str) -> Task:
        with self._lock:
            if task_id not in self._tasks:
                raise KeyError("Task not found")
            return self._tasks[task_id]

    def list_tasks(self) -> List[Task]:
        with self._lock:
            return list(self._tasks.values())

    def update_task(
        self,
        task_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        priority: Optional[Priority] = None,
        status: Optional[TaskStatus] = None,
    ) -> Task:
        with self._lock:
            task = self.get_task(task_id)
            task.update(title=title, description=description)
            if priority is not None:
                task.set_priority(priority)
            if status is not None:
                if status == TaskStatus.COMPLETED:
                    task.mark_completed()
                else:
                    task.mark_pending()
            return task

    def delete_task(self, task_id: str) -> None:
        with self._lock:
            if task_id not in self._tasks:
                raise KeyError("Task not found")
            del self._tasks[task_id]


class Agent:
    def __init__(self, hostname: Optional[str] = None) -> None:
        self._hostname = hostname or socket.gethostname()

    @property
    def hostname(self) -> str:
        return self._hostname

    def collect_metrics(self) -> SystemMetrics:
        timestamp = datetime.utcnow()
        if psutil is None:
            return SystemMetrics(
                cpu_percent=0.0,
                ram_percent=0.0,
                network_sent_bytes=0,
                network_recv_bytes=0,
                timestamp=timestamp,
            )
        cpu_percent = float(psutil.cpu_percent(interval=0.0))
        ram_percent = float(psutil.virtual_memory().percent)
        net = psutil.net_io_counters()
        return SystemMetrics(
            cpu_percent=cpu_percent,
            ram_percent=ram_percent,
            network_sent_bytes=int(net.bytes_sent),
            network_recv_bytes=int(net.bytes_recv),
            timestamp=timestamp,
        )

    def list_processes(self) -> List[ProcessInfo]:
        if psutil is None:
            return []
        processes: List[ProcessInfo] = []
        for proc in psutil.process_iter(attrs=["pid", "name", "cpu_percent", "memory_percent"]):
            try:
                info = proc.info
                processes.append(
                    ProcessInfo(
                        pid=int(info.get("pid", 0)),
                        name=str(info.get("name") or ""),
                        cpu_percent=float(info.get("cpu_percent") or 0.0),
                        memory_percent=float(info.get("memory_percent") or 0.0),
                    )
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return processes

    def kill_process(self, pid: int) -> bool:
        if pid <= 0:
            raise ValueError("PID must be positive")
        if psutil is not None:
            try:
                proc = psutil.Process(pid)
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except psutil.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=3)
                return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                return False
        try:
            if os.name == "nt":
                result = subprocess.run(
                    ["taskkill", "/PID", str(pid), "/F"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                return result.returncode == 0
            os.kill(pid, 15)
            return True
        except Exception:
            return False

    def capture_screen(self) -> ScreenCapture:
        timestamp = datetime.utcnow()
        image_bytes = b""
        try:
            from PIL import ImageGrab  # type: ignore

            image = ImageGrab.grab()
            from io import BytesIO

            buffer = BytesIO()
            image.save(buffer, format="PNG")
            image_bytes = buffer.getvalue()
        except Exception:
            image_bytes = b""
        return ScreenCapture(
            image_base64=base64.b64encode(image_bytes).decode("ascii"),
            timestamp=timestamp,
        )


class Server:
    def __init__(self, server_id: str, name: str, agent: Agent, history_limit: int = 100) -> None:
        if not server_id or not server_id.strip():
            raise ValueError("Server ID cannot be empty")
        if not name or not name.strip():
            raise ValueError("Server name cannot be empty")
        if history_limit <= 0:
            raise ValueError("History limit must be positive")
        self._id = server_id.strip()
        self._name = name.strip()
        self._agent = agent
        self._history_limit = history_limit
        self._metrics_history: List[SystemMetrics] = []
        self._last_screen_capture: Optional[ScreenCapture] = None
        self._status: ServerStatus = ServerStatus.OFFLINE
        self._last_seen: Optional[datetime] = None
        self._lock = RLock()

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def status(self) -> ServerStatus:
        return self._status

    @property
    def last_seen(self) -> Optional[datetime]:
        return self._last_seen

    def refresh_status(self) -> ServerStatus:
        with self._lock:
            try:
                metrics = self._agent.collect_metrics()
                self._append_metrics(metrics)
                self._status = ServerStatus.ONLINE
                self._last_seen = metrics.timestamp
            except Exception:
                self._status = ServerStatus.OFFLINE
            return self._status

    def get_current_metrics(self) -> Optional[SystemMetrics]:
        with self._lock:
            if not self._metrics_history:
                try:
                    metrics = self._agent.collect_metrics()
                    self._append_metrics(metrics)
                    self._status = ServerStatus.ONLINE
                    self._last_seen = metrics.timestamp
                except Exception:
                    self._status = ServerStatus.OFFLINE
                    return None
            return self._metrics_history[-1]

    def get_metrics_history(self) -> List[SystemMetrics]:
        with self._lock:
            return list(self._metrics_history)

    def get_processes(self) -> List[ProcessInfo]:
        with self._lock:
            try:
                processes = self._agent.list_processes()
                self._status = ServerStatus.ONLINE
                self._last_seen = datetime.utcnow()
                return processes
            except Exception:
                self._status = ServerStatus.OFFLINE
                return []

    def kill_process(self, pid: int) -> bool:
        with self._lock:
            try:
                result = self._agent.kill_process(pid)
                self._status = ServerStatus.ONLINE if result else self._status
                self._last_seen = datetime.utcnow() if result else self._last_seen
                return result
            except Exception:
                self._status = ServerStatus.OFFLINE
                return False

    def capture_screen(self) -> ScreenCapture:
        with self._lock:
            capture = self._agent.capture_screen()
            self._last_screen_capture = capture
            self._status = ServerStatus.ONLINE
            self._last_seen = capture.timestamp
            return capture

    def get_last_screen_capture(self) -> Optional[ScreenCapture]:
        with self._lock:
            return self._last_screen_capture

    def _append_metrics(self, metrics: SystemMetrics) -> None:
        self._metrics_history.append(metrics)
        if len(self._metrics_history) > self._history_limit:
            self._metrics_history = self._metrics_history[-self._history_limit :]


class NexusCtrl:
    def __init__(self) -> None:
        self._servers: Dict[str, Server] = {}
        self._task_manager = TaskManager()
        self._lock = RLock()

    @property
    def task_manager(self) -> TaskManager:
        return self._task_manager

    def register_server(self, server_id: str, name: str, agent: Optional[Agent] = None, history_limit: int = 100) -> Server:
        with self._lock:
            if server_id in self._servers:
                raise ValueError("Server already registered")
            server = Server(server_id=server_id, name=name, agent=agent or Agent(), history_limit=history_limit)
            self._servers[server_id] = server
            return server

    def get_server(self, server_id: str) -> Server:
        with self._lock:
            if server_id not in self._servers:
                raise KeyError("Server not found")
            return self._servers[server_id]

    def list_servers(self) -> List[Server]:
        with self._lock:
            return list(self._servers.values())

    def remove_server(self, server_id: str) -> None:
        with self._lock:
            if server_id not in self._servers:
                raise KeyError("Server not found")
            del self._servers[server_id]

    def monitor_server(self, server_id: str) -> Optional[SystemMetrics]:
        server = self.get_server(server_id)
        server.refresh_status()
        return server.get_current_metrics()

    def monitor_all_servers(self) -> Dict[str, Optional[SystemMetrics]]:
        result: Dict[str, Optional[SystemMetrics]] = {}
        for server in self.list_servers():
            result[server.id] = self.monitor_server(server.id)
        return result

    def get_server_status(self, server_id: str) -> ServerStatus:
        server = self.get_server(server_id)
        return server.refresh_status()

    def get_server_processes(self, server_id: str) -> List[ProcessInfo]:
        server = self.get_server(server_id)
        return server.get_processes()

    def terminate_server_process(self, server_id: str, pid: int) -> bool:
        server = self.get_server(server_id)
        return server.kill_process(pid)

    def capture_server_screen(self, server_id: str) -> ScreenCapture:
        server = self.get_server(server_id)
        return server.capture_screen()

    def get_server_history(self, server_id: str) -> List[SystemMetrics]:
        server = self.get_server(server_id)
        return server.get_metrics_history()


class LocalAgentService(Agent):
    def __init__(self) -> None:
        super().__init__(hostname=socket.gethostname())
        self._service_name = "NexusCtrlAgent"
        self._started_at = datetime.utcnow()

    @property
    def service_name(self) -> str:
        return self._service_name

    @property
    def started_at(self) -> datetime:
        return self._started_at

    def get_service_info(self) -> Dict[str, str]:
        return {
            "service_name": self._service_name,
            "hostname": self.hostname,
            "started_at": self._started_at.isoformat(),
            "platform": platform.platform(),
        }