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
        self.task_id = task_id
        self.title = title
        self.description = description
        self.priority = priority
        self.status = TaskStatus.PENDING

    def update_status(self, status: TaskStatus) -> None:
        self.status = status

class Process:
    def __init__(self, pid: int, name: str, cpu_percent: float, memory_percent: float):
        self.pid = pid
        self.name = name
        self.cpu_percent = cpu_percent
        self.memory_percent = memory_percent

class SystemMetrics:
    def __init__(self, cpu_usage: float, ram_usage: float, network_usage: float):
        self.cpu_usage = cpu_usage
        self.ram_usage = ram_usage
        self.network_usage = network_usage
        self.timestamp = datetime.datetime.now()

class Agent:
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.is_running = False
        self.metrics_history: List[SystemMetrics] = []
        self.active_processes: Dict[int, Process] = {}
        self.screen_capture: Optional[bytes] = None
        self._generate_mock_processes()

    def _generate_mock_processes(self) -> None:
        for i in range(1, 11):
            pid = 1000 + i
            self.active_processes[pid] = Process(
                pid=pid,
                name=f"process_{i}.exe",
                cpu_percent=random.uniform(0.1, 5.0),
                memory_percent=random.uniform(0.1, 10.0)
            )

    def start(self) -> None:
        self.is_running = True

    def stop(self) -> None:
        self.is_running = False

    def collect_metrics(self) -> SystemMetrics:
        if not self.is_running:
            raise ValueError("Agent is not running. Cannot collect metrics.")
        
        metrics = SystemMetrics(
            cpu_usage=random.uniform(5.0, 95.0),
            ram_usage=random.uniform(10.0, 90.0),
            network_usage=random.uniform(0.0, 100.0)
        )
        
        self.metrics_history.append(metrics)
        if len(self.metrics_history) > 1000:
            self.metrics_history.pop(0)
            
        return metrics

    def capture_screen(self) -> bytes:
        if not self.is_running:
            raise ValueError("Agent is not running. Cannot capture screen.")
        self.screen_capture = b"MOCK_SCREEN_CAPTURE_DATA_STREAM"
        return self.screen_capture

    def get_active_processes(self) -> List[Process]:
        if not self.is_running:
            raise ValueError("Agent is not running. Cannot retrieve processes.")
        return list(self.active_processes.values())

    def kill_process(self, pid: int) -> bool:
        if not self.is_running:
            raise ValueError("Agent is not running. Cannot kill process.")
        if pid in self.active_processes:
            del self.active_processes[pid]
            return True
        return False

class Server:
    def __init__(self, server_id: str, name: str, agent: Agent):
        self.server_id = server_id
        self.name = name
        self.agent = agent

    @property
    def is_online(self) -> bool:
        return self.agent.is_running

    def get_current_metrics(self) -> Optional[SystemMetrics]:
        if self.is_online:
            return self.agent.collect_metrics()
        return None

    def get_metrics_history(self) -> List[SystemMetrics]:
        return self.agent.metrics_history

    def get_screen_capture(self) -> Optional[bytes]:
        if self.is_online:
            return self.agent.capture_screen()
        return None

    def get_processes(self) -> List[Process]:
        if self.is_online:
            return self.agent.get_active_processes()
        return []

    def terminate_process(self, pid: int) -> bool:
        if self.is_online:
            return self.agent.kill_process(pid)
        return False

class TaskManager:
    def __init__(self):
        self.tasks: Dict[str, Task] = {}

    def create_task(self, task_id: str, title: str, description: str, priority: TaskPriority) -> Task:
        if task_id in self.tasks:
            raise ValueError(f"Task with ID {task_id} already exists.")
        task = Task(task_id, title, description, priority)
        self.tasks[task_id] = task
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        return self.tasks.get(task_id)

    def update_task_status(self, task_id: str, status: TaskStatus) -> bool:
        task = self.get_task(task_id)
        if task:
            task.update_status(status)
            return True
        return False

    def get_all_tasks(self) -> List[Task]:
        return list(self.tasks.values())

class NexusCtrl:
    def __init__(self):
        self.servers: Dict[str, Server] = {}
        self.task_manager = TaskManager()

    def add_server(self, server: Server) -> None:
        if server.server_id in self.servers:
            raise ValueError(f"Server with ID {server.server_id} already exists.")
        self.servers[server.server_id] = server

    def remove_server(self, server_id: str) -> None:
        if server_id in self.servers:
            del self.servers[server_id]

    def get_server(self, server_id: str) -> Optional[Server]:
        return self.servers.get(server_id)

    def get_all_servers(self) -> List[Server]:
        return list(self.servers.values())