import enum
import threading
import time
import random
import uuid
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime


class TaskPriority(enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskStatus(enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class ServerStatus(enum.Enum):
    ONLINE = "online"
    OFFLINE = "offline"


@dataclass
class ProcessInfo:
    pid: int
    name: str
    cpu_percent: float
    memory_percent: float


@dataclass(frozen=True)
class MetricSnapshot:
    timestamp: datetime
    cpu_percent: float
    ram_percent: float
    network_rx_bytes: int
    network_tx_bytes: int


class PerformanceHistory:
    def __init__(self, max_entries: int = 1000) -> None:
        self._history: List[MetricSnapshot] = []
        self._max_entries = max_entries
        self._lock = threading.Lock()

    def add(self, snapshot: MetricSnapshot) -> None:
        with self._lock:
            self._history.append(snapshot)
            if len(self._history) > self._max_entries:
                self._history.pop(0)

    def get_all(self) -> List[MetricSnapshot]:
        with self._lock:
            return list(self._history)

    def get_recent(self, count: int = 10) -> List[MetricSnapshot]:
        with self._lock:
            return self._history[-count:]


class Task:
    def __init__(self, description: str, priority: TaskPriority = TaskPriority.MEDIUM) -> None:
        self.id: str = str(uuid.uuid4())
        self.description: str = description
        self.priority: TaskPriority = priority
        self.status: TaskStatus = TaskStatus.PENDING
        self.created_at: datetime = datetime.now()
        self.completed_at: Optional[datetime] = None
        self.assigned_server_id: Optional[str] = None

    def start(self) -> None:
        if self.status != TaskStatus.PENDING:
            raise RuntimeError("Task can only be started when pending")
        self.status = TaskStatus.IN_PROGRESS

    def complete(self) -> None:
        if self.status != TaskStatus.IN_PROGRESS:
            raise RuntimeError("Task must be in progress to complete")
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now()

    def assign_to_server(self, server_id: str) -> None:
        self.assigned_server_id = server_id


class Agent:
    """Simulates the agent running on a remote machine."""
    def __init__(self, server_id: str) -> None:
        self._server_id = server_id
        self._running = False
        self._metrics_thread: Optional[threading.Thread] = None
        self._processes: List[ProcessInfo] = self._generate_fake_processes()
        self._last_metrics: MetricSnapshot = MetricSnapshot(
            timestamp=datetime.now(),
            cpu_percent=0.0,
            ram_percent=0.0,
            network_rx_bytes=0,
            network_tx_bytes=0
        )
        self.history = PerformanceHistory()

    def _generate_fake_processes(self) -> List[ProcessInfo]:
        fake_names = ["svchost.exe", "chrome.exe", "explorer.exe", "notepad.exe",
                      "python.exe", "node.exe", "sqlserver.exe"]
        processes = []
        for i, name in enumerate(random.sample(fake_names, random.randint(3, 5)), start=1000):
            processes.append(ProcessInfo(
                pid=i,
                name=name,
                cpu_percent=round(random.uniform(0.1, 30.0), 2),
                memory_percent=round(random.uniform(0.5, 15.0), 2)
            ))
        return processes

    def _collect_metrics(self) -> MetricSnapshot:
        cpu = round(random.uniform(5.0, 95.0), 2)
        ram = round(random.uniform(20.0, 90.0), 2)
        rx = random.randint(1000, 100000)
        tx = random.randint(1000, 100000)
        snapshot = MetricSnapshot(
            timestamp=datetime.now(),
            cpu_percent=cpu,
            ram_percent=ram,
            network_rx_bytes=rx,
            network_tx_bytes=tx
        )
        self.history.add(snapshot)
        self._last_metrics = snapshot
        return snapshot

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._metrics_thread = threading.Thread(target=self._metrics_loop, daemon=True)
        self._metrics_thread.start()

    def stop(self) -> None:
        self._running = False
        if self._metrics_thread:
            self._metrics_thread.join(timeout=2)

    def _metrics_loop(self) -> None:
        while self._running:
            self._collect_metrics()
            time.sleep(2)  # 2 second interval

    def get_current_metrics(self) -> MetricSnapshot:
        return self._last_metrics

    def get_processes(self) -> List[ProcessInfo]:
        # Simulate changing process list occasionally
        if random.random() < 0.1:  # 10% chance to refresh
            self._processes = self._generate_fake_processes()
        return self._processes

    def kill_process(self, pid: int) -> bool:
        for proc in self._processes:
            if proc.pid == pid:
                self._processes.remove(proc)
                return True
        return False

    def capture_screen(self) -> bytes:
        # Simulate a screen capture, returning a placeholder (e.g., a tiny black PNG)
        # Real implementation would use pyautogui or PIL
        png_header = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
        return png_header


class Server:
    def __init__(self, name: str, host: str) -> None:
        self.id: str = str(uuid.uuid4())
        self.name: str = name
        self.host: str = host
        self.status: ServerStatus = ServerStatus.OFFLINE
        self.agent: Agent = Agent(self.id)
        self.tasks: List[Task] = []
        self._lock = threading.Lock()

    def connect(self) -> None:
        self.agent.start()
        self.status = ServerStatus.ONLINE

    def disconnect(self) -> None:
        self.agent.stop()
        self.status = ServerStatus.OFFLINE

    def get_metrics(self) -> MetricSnapshot:
        return self.agent.get_current_metrics()

    def get_processes(self) -> List[ProcessInfo]:
        return self.agent.get_processes()

    def kill_process(self, pid: int) -> bool:
        return self.agent.kill_process(pid)

    def capture_screen(self) -> bytes:
        return self.agent.capture_screen()

    def get_performance_history(self) -> List[MetricSnapshot]:
        return self.agent.history.get_all()

    def add_task(self, task: Task) -> None:
        with self._lock:
            task.assign_to_server(self.id)
            self.tasks.append(task)

    def remove_task(self, task_id: str) -> bool:
        with self._lock:
            for i, t in enumerate(self.tasks):
                if t.id == task_id:
                    self.tasks.pop(i)
                    return True
        return False

    def get_tasks(self) -> List[Task]:
        with self._lock:
            return list(self.tasks)


class NexusCtrl:
    def __init__(self) -> None:
        self._servers: Dict[str, Server] = {}
        self._global_tasks: List[Task] = []
        self._lock = threading.Lock()

    def add_server(self, name: str, host: str) -> Server:
        server = Server(name, host)
        with self._lock:
            self._servers[server.id] = server
        return server

    def remove_server(self, server_id: str) -> bool:
        with self._lock:
            if server_id in self._servers:
                del self._servers[server_id]
                return True
        return False

    def get_server(self, server_id: str) -> Optional[Server]:
        with self._lock:
            return self._servers.get(server_id)

    def list_servers(self) -> List[Server]:
        with self._lock:
            return list(self._servers.values())

    def create_task(self, description: str, priority: TaskPriority = TaskPriority.MEDIUM) -> Task:
        task = Task(description, priority)
        with self._lock:
            self._global_tasks.append(task)
        return task

    def assign_task_to_server(self, task_id: str, server_id: str) -> bool:
        server = self.get_server(server_id)
        if not server:
            return False
        task = self.find_task(task_id, global_only=True)
        if not task:
            return False
        server.add_task(task)
        return True

    def find_task(self, task_id: str, global_only: bool = False) -> Optional[Task]:
        if not global_only:
            for server in self.list_servers():
                for task in server.get_tasks():
                    if task.id == task_id:
                        return task
        with self._lock:
            for task in self._global_tasks:
                if task.id == task_id:
                    return task
        return None

    def list_global_tasks(self) -> List[Task]:
        with self._lock:
            return list(self._global_tasks)


if __name__ == "__main__":
    # Simple demonstration
    print("NexusCtrl - Starting demo")
    controller = NexusCtrl()

    # Add servers
    server1 = controller.add_server("Dev RDP", "192.168.1.10")
    server2 = controller.add_server("Test Server", "192.168.1.20")
    server1.connect()
    server2.connect()

    # Create tasks
    task1 = controller.create_task("Update all packages", TaskPriority.HIGH)
    task2 = controller.create_task("Run security scan", TaskPriority.CRITICAL)
    controller.assign_task_to_server(task1.id, server1.id)
    controller.assign_task_to_server(task2.id, server2.id)

    task1.start()
    task1.complete()

    # Monitor metrics
    time.sleep(3)  # wait for some data
    print(f"Server1 metrics: CPU={server1.get_metrics().cpu_percent}%, RAM={server1.get_metrics().ram_percent}%")
    print(f"Server1 processes: {len(server1.get_processes())} running")
    # Kill a process
    if server1.get_processes():
        proc = server1.get_processes()[0]
        print(f"Killing process {proc.name} (PID {proc.pid})")
        server1.kill_process(proc.pid)

    # Screen capture (placeholder)
    img = server2.capture_screen()
    print(f"Screen capture size: {len(img)} bytes")

    # Show history
    history = server1.get_performance_history()
    print(f"Performance history entries: {len(history)}")

    # Tasks listing
    global_tasks = controller.list_global_tasks()
    for t in global_tasks:
        print(f"Task: {t.description} [{t.priority.value}] - {t.status.value}")

    # Disconnect
    server1.disconnect()
    server2.disconnect()
    print("Demo finished.")