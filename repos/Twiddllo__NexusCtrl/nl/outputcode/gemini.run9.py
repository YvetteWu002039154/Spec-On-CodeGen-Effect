from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
import random

class TaskPriority(Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class TaskStatus(Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"

class ServerStatus(Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"

@dataclass
class Task:
    task_id: str
    title: str
    description: str
    priority: TaskPriority
    status: TaskStatus = TaskStatus.PENDING

@dataclass
class Process:
    pid: int
    name: str
    cpu_percent: float
    memory_percent: float

@dataclass
class SystemMetrics:
    cpu_usage: float
    ram_usage: float
    network_bytes_sent: int
    network_bytes_recv: int
    timestamp: datetime = field(default_factory=datetime.now)

class Agent:
    def __init__(self, agent_id: str):
        self._agent_id = agent_id
        self._is_running = False
        self._mock_processes = {
            1: Process(1, "system", 0.1, 0.5),
            100: Process(100, "explorer.exe", 2.5, 5.0),
            200: Process(200, "chrome.exe", 15.0, 25.0)
        }

    @property
    def is_running(self) -> bool:
        return self._is_running

    def start(self) -> None:
        self._is_running = True

    def stop(self) -> None:
        self._is_running = False

    def collect_metrics(self) -> SystemMetrics:
        if not self._is_running:
            raise ConnectionError("Agent is not running.")
        return SystemMetrics(
            cpu_usage=round(random.uniform(5.0, 95.0), 2),
            ram_usage=round(random.uniform(10.0, 90.0), 2),
            network_bytes_sent=random.randint(1000, 1000000),
            network_bytes_recv=random.randint(1000, 1000000)
        )

    def capture_screen(self) -> bytes:
        if not self._is_running:
            raise ConnectionError("Agent is not running.")
        return b"mock_screen_capture_data_bytes"

    def get_processes(self) -> List[Process]:
        if not self._is_running:
            raise ConnectionError("Agent is not running.")
        return list(self._mock_processes.values())

    def kill_process(self, pid: int) -> bool:
        if not self._is_running:
            raise ConnectionError("Agent is not running.")
        if pid in self._mock_processes:
            del self._mock_processes[pid]
            return True
        return False

class Server:
    def __init__(self, server_id: str, name: str, ip_address: str, agent: Agent):
        self._server_id = server_id
        self._name = name
        self._ip_address = ip_address
        self._agent = agent
        self._status = ServerStatus.OFFLINE
        self._performance_history: List[SystemMetrics] = []
        self._tasks: Dict[str, Task] = {}
        self._max_history_records = 1000

    @property
    def server_id(self) -> str:
        return self._server_id

    @property
    def status(self) -> ServerStatus:
        return self._status

    def check_status(self) -> ServerStatus:
        if self._agent.is_running:
            self._status = ServerStatus.ONLINE
        else:
            self._status = ServerStatus.OFFLINE
        return self._status

    def update_metrics(self) -> Optional[SystemMetrics]:
        if self.check_status() == ServerStatus.ONLINE:
            try:
                metrics = self._agent.collect_metrics()
                self._performance_history.append(metrics)
                if len(self._performance_history) > self._max_history_records:
                    self._performance_history.pop(0)
                return metrics
            except ConnectionError:
                self._status = ServerStatus.OFFLINE
        return None

    def get_performance_history(self) -> List[SystemMetrics]:
        return self._performance_history.copy()

    def get_screen_capture(self) -> Optional[bytes]:
        if self.check_status() == ServerStatus.ONLINE:
            try:
                return self._agent.capture_screen()
            except ConnectionError:
                self._status = ServerStatus.OFFLINE
        return None

    def get_active_processes(self) -> List[Process]:
        if self.check_status() == ServerStatus.ONLINE:
            try:
                return self._agent.get_processes()
            except ConnectionError:
                self._status = ServerStatus.OFFLINE
        return []

    def terminate_process(self, pid: int) -> bool:
        if self.check_status() == ServerStatus.ONLINE:
            try:
                return self._agent.kill_process(pid)
            except ConnectionError:
                self._status = ServerStatus.OFFLINE
        return False

    def add_task(self, task: Task) -> None:
        if task.task_id in self._tasks:
            raise ValueError(f"Task with ID {task.task_id} already exists.")
        self._tasks[task.task_id] = task

    def update_task_status(self, task_id: str, status: TaskStatus) -> None:
        if task_id not in self._tasks:
            raise ValueError(f"Task with ID {task_id} not found.")
        self._tasks[task_id].status = status

    def get_tasks(self) -> List[Task]:
        return list(self._tasks.values())

class NexusCtrl:
    def __init__(self):
        self._servers: Dict[str, Server] = {}

    def add_server(self, server: Server) -> None:
        if server.server_id in self._servers:
            raise ValueError(f"Server with ID {server.server_id} already exists.")
        self._servers[server.server_id] = server

    def remove_server(self, server_id: str) -> None:
        if server_id not in self._servers:
            raise ValueError(f"Server with ID {server_id} not found.")
        del self._servers[server_id]

    def get_server(self, server_id: str) -> Server:
        if server_id not in self._servers:
            raise ValueError(f"Server with ID {server_id} not found.")
        return self._servers[server_id]

    def get_all_servers(self) -> List[Server]:
        return list(self._servers.values())

    def monitor_all_servers(self) -> Dict[str, Optional[SystemMetrics]]:
        metrics_report = {}
        for server_id, server in self._servers.items():
            metrics_report[server_id] = server.update_metrics()
        return metrics_report