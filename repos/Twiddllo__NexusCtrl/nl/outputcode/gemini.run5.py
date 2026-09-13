import uuid
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional

class Priority(Enum):
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

class Task:
    def __init__(self, title: str, priority: Priority, description: str = ""):
        self._task_id: str = str(uuid.uuid4())
        self.title: str = title
        self.description: str = description
        self.priority: Priority = priority
        self.status: TaskStatus = TaskStatus.PENDING
        self.created_at: datetime = datetime.now()
        self.completed_at: Optional[datetime] = None

    @property
    def task_id(self) -> str:
        return self._task_id

    def update_status(self, status: TaskStatus) -> None:
        self.status = status
        if status == TaskStatus.COMPLETED:
            self.completed_at = datetime.now()

class Process:
    def __init__(self, pid: int, name: str, cpu_usage: float, ram_usage: float):
        self.pid: int = pid
        self.name: str = name
        self.cpu_usage: float = cpu_usage
        self.ram_usage: float = ram_usage

class Metrics:
    def __init__(self, cpu_usage: float, ram_usage: float, network_usage: float):
        self.timestamp: datetime = datetime.now()
        self.cpu_usage: float = cpu_usage
        self.ram_usage: float = ram_usage
        self.network_usage: float = network_usage

class Agent:
    def __init__(self, server_id: str, name: str):
        self._server_id: str = server_id
        self.name: str = name
        self.status: ServerStatus = ServerStatus.OFFLINE
        self._metrics_history: List[Metrics] = []
        self._active_processes: Dict[int, Process] = {}
        self._is_running_as_service: bool = False

    @property
    def server_id(self) -> str:
        return self._server_id

    def start_service(self) -> None:
        self._is_running_as_service = True
        self.status = ServerStatus.ONLINE

    def stop_service(self) -> None:
        self._is_running_as_service = False
        self.status = ServerStatus.OFFLINE
        self._active_processes.clear()

    def collect_metrics(self, cpu: float, ram: float, network: float) -> None:
        if self.status == ServerStatus.OFFLINE:
            raise ValueError("Cannot collect metrics while agent is offline.")
        metrics = Metrics(cpu, ram, network)
        self._metrics_history.append(metrics)

    def get_performance_history(self) -> List[Metrics]:
        return self._metrics_history.copy()

    def capture_screen(self) -> bytes:
        if self.status == ServerStatus.OFFLINE:
            raise ValueError("Cannot capture screen while agent is offline.")
        return b"SCREEN_CAPTURE_DATA_STREAM"

    def register_process(self, process: Process) -> None:
        if self.status == ServerStatus.OFFLINE:
            raise ValueError("Cannot register process while agent is offline.")
        self._active_processes[process.pid] = process

    def get_processes(self) -> List[Process]:
        return list(self._active_processes.values())

    def kill_process(self, pid: int) -> bool:
        if self.status == ServerStatus.OFFLINE:
            raise ValueError("Cannot kill process while agent is offline.")
        if pid in self._active_processes:
            del self._active_processes[pid]
            return True
        return False

class NexusCtrl:
    def __init__(self):
        self._servers: Dict[str, Agent] = {}
        self._tasks: Dict[str, Task] = {}

    def add_server(self, agent: Agent) -> None:
        if agent.server_id in self._servers:
            raise ValueError(f"Server with ID {agent.server_id} already exists.")
        self._servers[agent.server_id] = agent

    def remove_server(self, server_id: str) -> None:
        if server_id in self._servers:
            del self._servers[server_id]
        else:
            raise KeyError(f"Server with ID {server_id} not found.")

    def get_server(self, server_id: str) -> Agent:
        if server_id not in self._servers:
            raise KeyError(f"Server with ID {server_id} not found.")
        return self._servers[server_id]

    def get_server_status(self, server_id: str) -> ServerStatus:
        return self.get_server(server_id).status

    def monitor_server_metrics(self, server_id: str) -> List[Metrics]:
        server = self.get_server(server_id)
        return server.get_performance_history()

    def view_live_screen(self, server_id: str) -> bytes:
        server = self.get_server(server_id)
        return server.capture_screen()

    def view_active_processes(self, server_id: str) -> List[Process]:
        server = self.get_server(server_id)
        return server.get_processes()

    def terminate_process_remotely(self, server_id: str, pid: int) -> bool:
        server = self.get_server(server_id)
        return server.kill_process(pid)

    def create_task(self, title: str, priority: Priority, description: str = "") -> Task:
        task = Task(title, priority, description)
        self._tasks[task.task_id] = task
        return task

    def get_task(self, task_id: str) -> Task:
        if task_id not in self._tasks:
            raise KeyError(f"Task with ID {task_id} not found.")
        return self._tasks[task_id]

    def get_all_tasks(self) -> List[Task]:
        return list(self._tasks.values())

    def update_task_status(self, task_id: str, status: TaskStatus) -> None:
        task = self.get_task(task_id)
        task.update_status(status)

    def delete_task(self, task_id: str) -> None:
        if task_id in self._tasks:
            del self._tasks[task_id]
        else:
            raise KeyError(f"Task with ID {task_id} not found.")