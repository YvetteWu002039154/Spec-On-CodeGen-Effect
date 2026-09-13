import datetime
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
    def __init__(self, task_id: str, title: str, description: str, priority: Priority):
        self._task_id = task_id
        self._title = title
        self._description = description
        self._priority = priority
        self._status = TaskStatus.PENDING
        self._created_at = datetime.datetime.now()

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
    def priority(self) -> Priority:
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
        self._metrics_history: List[Metrics] = []
        self._processes: Dict[int, Process] = {}
        self._current_screen: bytes = b""
        self._is_running: bool = False

    def start_service(self) -> None:
        self._is_running = True

    def stop_service(self) -> None:
        self._is_running = False

    @property
    def is_running(self) -> bool:
        return self._is_running

    def collect_metrics(self, cpu: float, ram: float, net_tx: float, net_rx: float) -> None:
        if self._is_running:
            self._metrics_history.append(Metrics(cpu, ram, net_tx, net_rx))

    def capture_screen(self, screen_data: bytes) -> None:
        if self._is_running:
            self._current_screen = screen_data

    def get_screen(self) -> bytes:
        return self._current_screen

    def register_process(self, process: Process) -> None:
        if self._is_running:
            self._processes[process.pid] = process

    def get_active_processes(self) -> List[Process]:
        if self._is_running:
            return list(self._processes.values())
        return []

    def kill_process(self, pid: int) -> bool:
        if self._is_running and pid in self._processes:
            del self._processes[pid]
            return True
        return False

    def get_metrics_history(self) -> List[Metrics]:
        return self._metrics_history

class Server:
    def __init__(self, server_id: str, name: str, agent: Agent):
        self._server_id = server_id
        self._name = name
        self._agent = agent
        self._status = ServerStatus.OFFLINE

    @property
    def server_id(self) -> str:
        return self._server_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def status(self) -> ServerStatus:
        return self._status

    def update_status(self, status: ServerStatus) -> None:
        self._status = status
        if status == ServerStatus.ONLINE:
            self._agent.start_service()
        else:
            self._agent.stop_service()

    def get_real_time_metrics(self) -> Optional[Metrics]:
        if self._status == ServerStatus.ONLINE:
            history = self._agent.get_metrics_history()
            if history:
                return history[-1]
        return None

    def get_performance_history(self) -> List[Metrics]:
        return self._agent.get_metrics_history()

    def get_live_screen(self) -> bytes:
        if self._status == ServerStatus.ONLINE:
            return self._agent.get_screen()
        return b""

    def get_processes(self) -> List[Process]:
        if self._status == ServerStatus.ONLINE:
            return self._agent.get_active_processes()
        return []

    def terminate_process(self, pid: int) -> bool:
        if self._status == ServerStatus.ONLINE:
            return self._agent.kill_process(pid)
        return False

class NexusCtrl:
    def __init__(self):
        self._servers: Dict[str, Server] = {}
        self._tasks: Dict[str, Task] = {}

    def add_server(self, server: Server) -> None:
        self._servers[server.server_id] = server

    def remove_server(self, server_id: str) -> bool:
        if server_id in self._servers:
            del self._servers[server_id]
            return True
        return False

    def get_server(self, server_id: str) -> Optional[Server]:
        return self._servers.get(server_id)

    def get_all_servers(self) -> List[Server]:
        return list(self._servers.values())

    def create_task(self, task_id: str, title: str, description: str, priority: Priority) -> Task:
        task = Task(task_id, title, description, priority)
        self._tasks[task_id] = task
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)

    def get_all_tasks(self) -> List[Task]:
        return list(self._tasks.values())

    def update_task_status(self, task_id: str, status: TaskStatus) -> bool:
        task = self.get_task(task_id)
        if task:
            task.update_status(status)
            return True
        return False

    def delete_task(self, task_id: str) -> bool:
        if task_id in self._tasks:
            del self._tasks[task_id]
            return True
        return False