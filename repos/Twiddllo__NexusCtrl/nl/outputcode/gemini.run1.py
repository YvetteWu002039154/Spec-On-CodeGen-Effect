import uuid
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional
import random

class TaskPriority(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

class ServerStatus(Enum):
    ONLINE = "online"
    OFFLINE = "offline"

@dataclass
class Task:
    title: str
    description: str
    priority: TaskPriority
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: TaskStatus = TaskStatus.PENDING

@dataclass
class Process:
    pid: int
    name: str
    cpu_usage: float
    memory_usage: float

@dataclass
class SystemMetrics:
    cpu_usage: float
    ram_usage: float
    network_upload: float
    network_download: float
    timestamp: datetime = field(default_factory=datetime.now)

class Agent:
    def __init__(self, host_id: str):
        self._host_id = host_id
        self._is_running = False
        self._active_processes: Dict[int, Process] = {}

    def start_service(self) -> None:
        self._is_running = True
        self._active_processes[1] = Process(pid=1, name="systemd", cpu_usage=0.1, memory_usage=50.0)
        self._active_processes[100] = Process(pid=100, name="rdp_server", cpu_usage=2.5, memory_usage=150.0)

    def stop_service(self) -> None:
        self._is_running = False
        self._active_processes.clear()

    def collect_metrics(self) -> SystemMetrics:
        if not self._is_running:
            raise RuntimeError("Agent service is not running on the target machine.")
        return SystemMetrics(
            cpu_usage=round(random.uniform(1.0, 100.0), 2),
            ram_usage=round(random.uniform(10.0, 100.0), 2),
            network_upload=round(random.uniform(0.0, 1000.0), 2),
            network_download=round(random.uniform(0.0, 5000.0), 2)
        )

    def capture_screen(self) -> bytes:
        if not self._is_running:
            raise RuntimeError("Agent service is not running on the target machine.")
        return b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR_mock_screen_data"

    def get_active_processes(self) -> List[Process]:
        if not self._is_running:
            raise RuntimeError("Agent service is not running on the target machine.")
        return list(self._active_processes.values())

    def kill_process(self, pid: int) -> bool:
        if not self._is_running:
            raise RuntimeError("Agent service is not running on the target machine.")
        if pid in self._active_processes:
            del self._active_processes[pid]
            return True
        return False

class Server:
    def __init__(self, server_id: str, name: str, ip_address: str):
        self._server_id = server_id
        self._name = name
        self._ip_address = ip_address
        self._status = ServerStatus.OFFLINE
        self._agent = Agent(host_id=server_id)
        self._performance_history: List[SystemMetrics] = []
        self._tasks: Dict[str, Task] = {}
        self._history_limit = 1000

    @property
    def server_id(self) -> str:
        return self._server_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def ip_address(self) -> str:
        return self._ip_address

    @property
    def status(self) -> ServerStatus:
        return self._status

    @property
    def performance_history(self) -> List[SystemMetrics]:
        return self._performance_history.copy()

    def connect(self) -> None:
        self._agent.start_service()
        self._status = ServerStatus.ONLINE

    def disconnect(self) -> None:
        self._agent.stop_service()
        self._status = ServerStatus.OFFLINE

    def update_metrics(self) -> None:
        if self._status == ServerStatus.ONLINE:
            metrics = self._agent.collect_metrics()
            self._performance_history.append(metrics)
            if len(self._performance_history) > self._history_limit:
                self._performance_history.pop(0)

    def get_latest_metrics(self) -> Optional[SystemMetrics]:
        if self._performance_history:
            return self._performance_history[-1]
        return None

    def get_screen_capture(self) -> Optional[bytes]:
        if self._status == ServerStatus.ONLINE:
            return self._agent.capture_screen()
        return None

    def get_processes(self) -> List[Process]:
        if self._status == ServerStatus.ONLINE:
            return self._agent.get_active_processes()
        return []

    def terminate_process(self, pid: int) -> bool:
        if self._status == ServerStatus.ONLINE:
            return self._agent.kill_process(pid)
        return False

    def add_task(self, task: Task) -> None:
        self._tasks[task.id] = task

    def get_tasks(self) -> List[Task]:
        return list(self._tasks.values())

    def update_task_status(self, task_id: str, status: TaskStatus) -> None:
        if task_id not in self._tasks:
            raise KeyError(f"Task with ID {task_id} not found on server {self._server_id}.")
        self._tasks[task_id].status = status

class NexusCtrl:
    def __init__(self):
        self._servers: Dict[str, Server] = {}

    def add_server(self, server: Server) -> None:
        if server.server_id in self._servers:
            raise ValueError(f"Server with ID {server.server_id} already exists.")
        self._servers[server.server_id] = server

    def remove_server(self, server_id: str) -> None:
        if server_id not in self._servers:
            raise KeyError(f"Server with ID {server_id} not found.")
        self._servers[server_id].disconnect()
        del self._servers[server_id]

    def get_server(self, server_id: str) -> Server:
        if server_id not in self._servers:
            raise KeyError(f"Server with ID {server_id} not found.")
        return self._servers[server_id]

    def get_all_servers(self) -> List[Server]:
        return list(self._servers.values())

    def monitor_servers(self) -> None:
        for server in self._servers.values():
            if server.status == ServerStatus.ONLINE:
                server.update_metrics()