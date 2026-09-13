from enum import Enum
from typing import List, Dict, Optional
from datetime import datetime

class TaskPriority(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class ServerStatus(Enum):
    ONLINE = "online"
    OFFLINE = "offline"

class Task:
    def __init__(self, task_id: str, description: str, priority: TaskPriority):
        self.task_id = task_id
        self.description = description
        self.priority = priority
        self.is_completed = False

    def mark_completed(self) -> None:
        self.is_completed = True

class Process:
    def __init__(self, pid: int, name: str):
        self.pid = pid
        self.name = name

class Metrics:
    def __init__(self, cpu_usage: float, ram_usage: float, network_usage: float):
        self.cpu_usage = cpu_usage
        self.ram_usage = ram_usage
        self.network_usage = network_usage
        self.timestamp = datetime.now()

class Agent:
    def __init__(self):
        self.is_running = False
        self._active_processes: Dict[int, Process] = {}

    def start(self) -> None:
        self.is_running = True

    def stop(self) -> None:
        self.is_running = False

    def collect_metrics(self) -> Optional[Metrics]:
        if not self.is_running:
            return None
        return Metrics(cpu_usage=0.0, ram_usage=0.0, network_usage=0.0)

    def capture_screen(self) -> Optional[bytes]:
        if not self.is_running:
            return None
        return b"screen_capture_data_stream"

    def get_processes(self) -> List[Process]:
        if not self.is_running:
            return []
        return list(self._active_processes.values())

    def kill_process(self, pid: int) -> bool:
        if not self.is_running:
            return False
        if pid in self._active_processes:
            del self._active_processes[pid]
            return True
        return False

    def _register_process(self, process: Process) -> None:
        self._active_processes[process.pid] = process

class Server:
    def __init__(self, server_id: str, name: str):
        self.server_id = server_id
        self.name = name
        self.status = ServerStatus.OFFLINE
        self.agent = Agent()
        self.metrics_history: List[Metrics] = []
        self.tasks: List[Task] = []

    def connect(self) -> None:
        self.status = ServerStatus.ONLINE
        self.agent.start()

    def disconnect(self) -> None:
        self.status = ServerStatus.OFFLINE
        self.agent.stop()

    def update_metrics(self) -> None:
        if self.status == ServerStatus.ONLINE:
            metrics = self.agent.collect_metrics()
            if metrics:
                self.metrics_history.append(metrics)

    def get_performance_history(self) -> List[Metrics]:
        return self.metrics_history

    def get_screen_capture(self) -> Optional[bytes]:
        if self.status == ServerStatus.ONLINE:
            return self.agent.capture_screen()
        return None

    def get_active_processes(self) -> List[Process]:
        if self.status == ServerStatus.ONLINE:
            return self.agent.get_processes()
        return []

    def terminate_process(self, pid: int) -> bool:
        if self.status == ServerStatus.ONLINE:
            return self.agent.kill_process(pid)
        return False

    def add_task(self, task: Task) -> None:
        self.tasks.append(task)

    def get_tasks(self) -> List[Task]:
        return self.tasks

class NexusCtrl:
    def __init__(self):
        self.servers: Dict[str, Server] = {}

    def add_server(self, server: Server) -> None:
        self.servers[server.server_id] = server

    def remove_server(self, server_id: str) -> None:
        if server_id in self.servers:
            del self.servers[server_id]

    def get_server(self, server_id: str) -> Optional[Server]:
        return self.servers.get(server_id)