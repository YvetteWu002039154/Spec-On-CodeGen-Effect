import datetime
from enum import Enum
from dataclasses import dataclass, field
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
    FAILED = "failed"

class ServerStatus(Enum):
    ONLINE = "online"
    OFFLINE = "offline"

@dataclass
class Task:
    id: str
    title: str
    description: str
    priority: TaskPriority
    status: TaskStatus = TaskStatus.PENDING

@dataclass
class Process:
    pid: int
    name: str
    cpu_percent: float
    memory_mb: float

@dataclass
class Metrics:
    cpu_percent: float
    ram_percent: float
    network_tx_bytes: int
    network_rx_bytes: int
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.now)

class Agent:
    def __init__(self, agent_id: str):
        self._agent_id = agent_id
        self._is_running = False
        self._mock_processes: Dict[int, Process] = {
            1001: Process(1001, "svchost.exe", 0.5, 25.0),
            1002: Process(1002, "explorer.exe", 1.2, 150.0),
            1003: Process(1003, "chrome.exe", 5.5, 500.0)
        }

    def start(self) -> None:
        self._is_running = True

    def stop(self) -> None:
        self._is_running = False

    @property
    def is_running(self) -> bool:
        return self._is_running

    def collect_metrics(self) -> Metrics:
        if not self._is_running:
            raise RuntimeError("Agent is not running on the target machine.")
        return Metrics(
            cpu_percent=14.5,
            ram_percent=42.0,
            network_tx_bytes=1048576,
            network_rx_bytes=2097152
        )

    def capture_screen(self) -> bytes:
        if not self._is_running:
            raise RuntimeError("Agent is not running on the target machine.")
        return b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR...mock_screen_data..."

    def get_processes(self) -> List[Process]:
        if not self._is_running:
            raise RuntimeError("Agent is not running on the target machine.")
        return list(self._mock_processes.values())

    def kill_process(self, pid: int) -> bool:
        if not self._is_running:
            raise RuntimeError("Agent is not running on the target machine.")
        if pid in self._mock_processes:
            del self._mock_processes[pid]
            return True
        return False

class Server:
    def __init__(self, server_id: str, name: str, agent: Agent):
        self._server_id = server_id
        self._name = name
        self._agent = agent
        self._status = ServerStatus.OFFLINE
        self._metrics_history: List[Metrics] = []
        self._tasks: Dict[str, Task] = {}
        self._max_history_records = 1000

    @property
    def server_id(self) -> str:
        return self._server_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def status(self) -> ServerStatus:
        return self._status

    def connect(self) -> None:
        self._agent.start()
        self._status = ServerStatus.ONLINE

    def disconnect(self) -> None:
        self._agent.stop()
        self._status = ServerStatus.OFFLINE

    def update_metrics(self) -> None:
        if self._status != ServerStatus.ONLINE:
            raise ConnectionError(f"Cannot update metrics. Server {self._name} is offline.")
        
        metrics = self._agent.collect_metrics()
        self._metrics_history.append(metrics)
        
        if len(self._metrics_history) > self._max_history_records:
            self._metrics_history.pop(0)

    def get_latest_metrics(self) -> Optional[Metrics]:
        if not self._metrics_history:
            return None
        return self._metrics_history[-1]

    def get_metrics_history(self) -> List[Metrics]:
        return list(self._metrics_history)

    def view_screen(self) -> bytes:
        if self._status != ServerStatus.ONLINE:
            raise ConnectionError(f"Cannot view screen. Server {self._name} is offline.")
        return self._agent.capture_screen()

    def list_processes(self) -> List[Process]:
        if self._status != ServerStatus.ONLINE:
            raise ConnectionError(f"Cannot list processes. Server {self._name} is offline.")
        return self._agent.get_processes()

    def terminate_process(self, pid: int) -> bool:
        if self._status != ServerStatus.ONLINE:
            raise ConnectionError(f"Cannot terminate process. Server {self._name} is offline.")
        return self._agent.kill_process(pid)

    def add_task(self, task: Task) -> None:
        if task.id in self._tasks:
            raise ValueError(f"Task with ID {task.id} already exists.")
        self._tasks[task.id] = task

    def update_task_status(self, task_id: str, status: TaskStatus) -> None:
        if task_id not in self._tasks:
            raise KeyError(f"Task {task_id} not found on server {self._name}.")
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
        if server_id in self._servers:
            del self._servers[server_id]
        else:
            raise KeyError(f"Server {server_id} not found.")

    def get_server(self, server_id: str) -> Server:
        if server_id not in self._servers:
            raise KeyError(f"Server {server_id} not found.")
        return self._servers[server_id]

    def get_all_servers(self) -> List[Server]:
        return list(self._servers.values())

if __name__ == "__main__":
    controller = NexusCtrl()
    
    agent1 = Agent(agent_id="agt-001")
    server1 = Server(server_id="srv-001", name="Production-DB", agent=agent1)
    
    controller.add_server(server1)
    
    server1.connect()
    
    server1.update_metrics()
    
    task1 = Task(
        id="tsk-100",
        title="Install Security Updates",
        description="Apply latest OS security patches",
        priority=TaskPriority.CRITICAL
    )
    server1.add_task(task1)
    server1.update_task_status("tsk-100", TaskStatus.IN_PROGRESS)
    
    processes = server1.list_processes()
    if processes:
        target_pid = processes[0].pid
        server1.terminate_process(target_pid)
    
    screen_data = server1.view_screen()
    
    server1.disconnect()