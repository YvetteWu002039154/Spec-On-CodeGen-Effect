import datetime
import random
from enum import Enum
from typing import List, Dict, Optional

class TaskPriority(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

class Task:
    def __init__(self, task_id: str, title: str, description: str, priority: TaskPriority):
        self._task_id = task_id
        self._title = title
        self._description = description
        self._priority = priority
        self._status = TaskStatus.PENDING

    @property
    def task_id(self) -> str:
        return self._task_id

    @property
    def title(self) -> str:
        return self._title

    @property
    def description(self) -> str:
        return self._description

    @property
    def priority(self) -> TaskPriority:
        return self._priority

    @property
    def status(self) -> TaskStatus:
        return self._status

    def mark_completed(self) -> None:
        self._status = TaskStatus.COMPLETED

    def update_status(self, status: TaskStatus) -> None:
        self._status = status

class Process:
    def __init__(self, pid: int, name: str, cpu_usage: float, ram_usage: float):
        self._pid = pid
        self._name = name
        self._cpu_usage = cpu_usage
        self._ram_usage = ram_usage

    @property
    def pid(self) -> int:
        return self._pid

    @property
    def name(self) -> str:
        return self._name

    @property
    def cpu_usage(self) -> float:
        return self._cpu_usage

    @property
    def ram_usage(self) -> float:
        return self._ram_usage

class Metrics:
    def __init__(self, cpu_percent: float, ram_percent: float, network_tx: float, network_rx: float):
        self._timestamp = datetime.datetime.now()
        self._cpu_percent = cpu_percent
        self._ram_percent = ram_percent
        self._network_tx = network_tx
        self._network_rx = network_rx

    @property
    def timestamp(self) -> datetime.datetime:
        return self._timestamp

    @property
    def cpu_percent(self) -> float:
        return self._cpu_percent

    @property
    def ram_percent(self) -> float:
        return self._ram_percent

    @property
    def network_tx(self) -> float:
        return self._network_tx

    @property
    def network_rx(self) -> float:
        return self._network_rx

class Agent:
    def __init__(self, agent_id: str):
        self._agent_id = agent_id
        self._is_online = True
        self._metrics_history: List[Metrics] = []
        self._processes: Dict[int, Process] = {}
        self._initialize_mock_processes()

    def _initialize_mock_processes(self) -> None:
        self._processes[1] = Process(1, "system", 1.0, 5.0)
        self._processes[100] = Process(100, "explorer.exe", 2.5, 15.0)
        self._processes[250] = Process(250, "chrome.exe", 12.0, 45.0)

    @property
    def is_online(self) -> bool:
        return self._is_online

    @is_online.setter
    def is_online(self, status: bool) -> None:
        self._is_online = status

    @property
    def metrics_history(self) -> List[Metrics]:
        return self._metrics_history

    def collect_metrics(self) -> Metrics:
        if not self._is_online:
            raise ValueError("Cannot collect metrics: Agent is offline")
        
        metrics = Metrics(
            cpu_percent=random.uniform(0.0, 100.0),
            ram_percent=random.uniform(0.0, 100.0),
            network_tx=random.uniform(0.0, 1000.0),
            network_rx=random.uniform(0.0, 1000.0)
        )
        self._metrics_history.append(metrics)
        return metrics

    def capture_screen(self) -> bytes:
        if not self._is_online:
            raise ValueError("Cannot capture screen: Agent is offline")
        return b"MOCK_SCREEN_CAPTURE_DATA"

    def get_active_processes(self) -> List[Process]:
        if not self._is_online:
            raise ValueError("Cannot get processes: Agent is offline")
        return list(self._processes.values())

    def kill_process(self, pid: int) -> bool:
        if not self._is_online:
            raise ValueError("Cannot kill process: Agent is offline")
        if pid in self._processes:
            del self._processes[pid]
            return True
        return False

class Server:
    def __init__(self, server_id: str, name: str):
        self._server_id = server_id
        self._name = name
        self._agent = Agent(server_id)

    @property
    def server_id(self) -> str:
        return self._server_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_online(self) -> bool:
        return self._agent.is_online

    def set_online_status(self, status: bool) -> None:
        self._agent.is_online = status

    def get_current_metrics(self) -> Metrics:
        return self._agent.collect_metrics()

    def get_metrics_history(self) -> List[Metrics]:
        return self._agent.metrics_history

    def get_screen_capture(self) -> bytes:
        return self._agent.capture_screen()

    def get_active_processes(self) -> List[Process]:
        return self._agent.get_active_processes()

    def terminate_process(self, pid: int) -> bool:
        return self._agent.kill_process(pid)

class NexusCtrl:
    def __init__(self):
        self._servers: Dict[str, Server] = {}
        self._tasks: Dict[str, Task] = {}

    def add_server(self, server_id: str, name: str) -> Server:
        if server_id in self._servers:
            raise ValueError(f"Server with ID {server_id} already exists.")
        server = Server(server_id, name)
        self._servers[server_id] = server
        return server

    def remove_server(self, server_id: str) -> None:
        if server_id in self._servers:
            del self._servers[server_id]

    def get_server(self, server_id: str) -> Optional[Server]:
        return self._servers.get(server_id)

    def list_servers(self) -> List[Server]:
        return list(self._servers.values())

    def create_task(self, task_id: str, title: str, description: str, priority: TaskPriority) -> Task:
        if task_id in self._tasks:
            raise ValueError(f"Task with ID {task_id} already exists.")
        task = Task(task_id, title, description, priority)
        self._tasks[task_id] = task
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)

    def update_task_status(self, task_id: str, status: TaskStatus) -> None:
        task = self.get_task(task_id)
        if not task:
            raise ValueError(f"Task with ID {task_id} not found.")
        task.update_status(status)

    def list_tasks(self) -> List[Task]:
        return list(self._tasks.values())