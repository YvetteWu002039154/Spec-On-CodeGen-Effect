from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import threading
import time
import random
import uuid
from typing import List, Optional, Tuple

# Status and priority enums
class ServerStatus(Enum):
    ONLINE = "online"
    OFFLINE = "offline"

class Priority(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

# Data classes
@dataclass
class ProcessInfo:
    pid: int
    name: str
    cpu_percent: float
    memory_mb: float

@dataclass
class PerformanceMetrics:
    cpu_percent: float
    ram_percent: float
    network_sent_bytes: int
    network_recv_bytes: int
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class Task:
    id: str
    description: str
    priority: Priority
    status: TaskStatus = TaskStatus.PENDING

    def mark_in_progress(self) -> None:
        self.status = TaskStatus.IN_PROGRESS

    def complete(self) -> None:
        self.status = TaskStatus.COMPLETED

# Agent simulates the background service on a remote server
class Agent:
    """Collects system metrics, captures screen, and handles remote commands."""
    def __init__(self, server_ip: str) -> None:
        self.server_ip = server_ip
        self.use_real = False
        try:
            import psutil
            self.psutil = psutil
            self.use_real = True
        except ImportError:
            pass

    def collect_cpu_usage(self) -> float:
        if self.use_real:
            return self.psutil.cpu_percent(interval=0.5)
        return random.uniform(10.0, 90.0)

    def collect_ram_usage(self) -> float:
        if self.use_real:
            return self.psutil.virtual_memory().percent
        return random.uniform(20.0, 80.0)

    def collect_network_usage(self) -> Tuple[int, int]:
        if self.use_real:
            net_io = self.psutil.net_io_counters()
            return net_io.bytes_sent, net_io.bytes_recv
        return random.randint(1000, 100000), random.randint(1000, 100000)

    def get_active_processes(self) -> List[ProcessInfo]:
        if self.use_real:
            processes: List[ProcessInfo] = []
            for proc in self.psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
                try:
                    info = proc.info
                    mem_mb = info['memory_info'].rss / (1024 * 1024)
                    processes.append(ProcessInfo(
                        pid=info['pid'],
                        name=info['name'] or '',
                        cpu_percent=info['cpu_percent'] or 0.0,
                        memory_mb=mem_mb
                    ))
                except (self.psutil.NoSuchProcess, self.psutil.AccessDenied):
                    pass
            return processes
        # Mock fallback
        return [
            ProcessInfo(1, "svchost.exe", 0.5, 12.3),
            ProcessInfo(2, "explorer.exe", 1.2, 45.6),
            ProcessInfo(3, "chrome.exe", 15.8, 200.5),
            ProcessInfo(4, "notepad.exe", 0.1, 5.0)
        ]

    def capture_screen(self) -> str:
        # Returns a placeholder; in practice captures and encodes screen content
        if self.use_real:
            # Real screen capture would require additional libraries (e.g., pyautogui)
            pass
        return f"Screenshot from {self.server_ip} at {datetime.now().isoformat()}"

    def kill_process(self, pid: int) -> bool:
        if self.use_real:
            try:
                proc = self.psutil.Process(pid)
                proc.terminate()
                return True
            except (self.psutil.NoSuchProcess, self.psutil.AccessDenied):
                return False
        # Mock success
        print(f"  [Mock] Process {pid} killed on {self.server_ip}")
        return True

# Server representation with live metrics, process list, and screen capture
class Server:
    def __init__(self, name: str, ip: str) -> None:
        self.name = name
        self.ip = ip
        self.status: ServerStatus = ServerStatus.OFFLINE
        self.agent = Agent(ip)
        self.current_metrics: Optional[PerformanceMetrics] = None
        self.current_processes: List[ProcessInfo] = []
        self.metrics_history: List[PerformanceMetrics] = []
        self.screen_capture: Optional[str] = None
        self._lock = threading.Lock()

    def update_metrics(self) -> PerformanceMetrics:
        cpu = self.agent.collect_cpu_usage()
        ram = self.agent.collect_ram_usage()
        sent, recv = self.agent.collect_network_usage()
        metrics = PerformanceMetrics(cpu, ram, sent, recv)
        self.current_processes = self.agent.get_active_processes()
        self.screen_capture = self.agent.capture_screen()
        with self._lock:
            self.current_metrics = metrics
            self.metrics_history.append(metrics)
        return metrics

    def get_active_processes(self) -> List[ProcessInfo]:
        return self.current_processes

    def kill_process(self, pid: int) -> bool:
        return self.agent.kill_process(pid)

    def get_performance_history(self, limit: int = 10) -> List[PerformanceMetrics]:
        with self._lock:
            return self.metrics_history[-limit:]

    def go_online(self) -> None:
        self.status = ServerStatus.ONLINE

    def go_offline(self) -> None:
        self.status = ServerStatus.OFFLINE

# Core controller: manages servers, tasks, and background monitoring
class NexusCtrl:
    def __init__(self) -> None:
        self.servers: dict[str, Server] = {}
        self.tasks: dict[str, Task] = {}
        self._monitoring_threads: dict[str, threading.Thread] = {}
        self._stop_events: dict[str, threading.Event] = {}

    def add_server(self, server: Server) -> None:
        self.servers[server.name] = server

    def remove_server(self, name: str) -> None:
        if name in self.servers:
            self.stop_monitoring(name)
            del self.servers[name]

    def start_monitoring(self, name: str, interval: float = 2.0) -> None:
        if name not in self.servers:
            raise ValueError(f"Server '{name}' not found.")
        if name in self._stop_events and not self._stop_events[name].is_set():
            return  # already monitoring
        stop_event = threading.Event()
        self._stop_events[name] = stop_event
        server = self.servers[name]

        def monitor_loop() -> None:
            while not stop_event.is_set():
                if server.status == ServerStatus.ONLINE:
                    server.update_metrics()
                time.sleep(interval)

        thread = threading.Thread(target=monitor_loop, daemon=True)
        self._monitoring_threads[name] = thread
        thread.start()

    def stop_monitoring(self, name: str) -> None:
        if name in self._stop_events:
            self._stop_events[name].set()
            if name in self._monitoring_threads:
                self._monitoring_threads[name].join(timeout=1)
            del self._stop_events[name]
            del self._monitoring_threads[name]

    def get_server_metrics(self, name: str) -> Optional[PerformanceMetrics]:
        if name not in self.servers:
            raise ValueError(f"Server '{name}' not found.")
        return self.servers[name].current_metrics

    def get_server_processes(self, name: str) -> List[ProcessInfo]:
        if name not in self.servers:
            raise ValueError(f"Server '{name}' not found.")
        return self.servers[name].get_active_processes()

    def kill_server_process(self, server_name: str, pid: int) -> bool:
        if server_name not in self.servers:
            raise ValueError(f"Server '{server_name}' not found.")
        return self.servers[server_name].kill_process(pid)

    def get_server_screen(self, name: str) -> Optional[str]:
        if name not in self.servers:
            raise ValueError(f"Server '{name}' not found.")
        return self.servers[name].screen_capture

    def create_task(self, description: str, priority: Priority) -> Task:
        task_id = str(uuid.uuid4())[:8]
        task = Task(task_id, description, priority)
        self.tasks[task_id] = task
        return task

    def list_tasks(self, status_filter: Optional[TaskStatus] = None) -> List[Task]:
        tasks = list(self.tasks.values())
        if status_filter:
            tasks = [t for t in tasks if t.status == status_filter]
        return tasks

    def update_task_status(self, task_id: str, new_status: TaskStatus) -> None:
        if task_id not in self.tasks:
            raise ValueError("Task not found.")
        task = self.tasks[task_id]
        if new_status == TaskStatus.IN_PROGRESS:
            task.mark_in_progress()
        elif new_status == TaskStatus.COMPLETED:
            task.complete()

# Demonstration / interactive shell
def main() -> None:
    ctrl = NexusCtrl()
    # Add servers
    server1 = Server("WinServer-01", "192.168.1.101")
    server1.go_online()
    server2 = Server("WinServer-02", "192.168.1.102")
    ctrl.add_server(server1)
    ctrl.add_server(server2)

    # Start monitoring
    ctrl.start_monitoring("WinServer-01", 3)

    # Give monitoring a moment to collect initial data
    time.sleep(1)

    # Create tasks
    t1 = ctrl.create_task("Update antivirus on all servers", Priority.CRITICAL)
    t2 = ctrl.create_task("Clean temp files", Priority.MEDIUM)
    ctrl.update_task_status(t1.id, TaskStatus.IN_PROGRESS)
    ctrl.update_task_status(t2.id, TaskStatus.COMPLETED)

    # Show metrics
    metrics = ctrl.get_server_metrics("WinServer-01")
    if metrics:
        print(f"Server WinServer-01: CPU={metrics.cpu_percent:.1f}%, RAM={metrics.ram_percent:.1f}%")

    # Show processes
    procs = ctrl.get_server_processes("WinServer-01")
    print("\nProcesses on WinServer-01:")
    for p in procs:
        print(f"  PID {p.pid}: {p.name} CPU {p.cpu_percent}% MEM {p.memory_mb:.1f}MB")

    # Kill a process
    if procs:
        ctrl.kill_server_process("WinServer-01", procs[0].pid)

    # Screen capture
    screen = ctrl.get_server_screen("WinServer-01")
    print(f"Screen: {screen}")

    # Show tasks
    print("\nAll Tasks:")
    for task in ctrl.list_tasks():
        print(f"  [{task.status.value}] {task.id}: {task.description} (priority {task.priority.value})")

    # Performance history
    history = ctrl.servers["WinServer-01"].get_performance_history()
    print(f"\nPerformance history entries for WinServer-01: {len(history)}")

    # Cleanup: stop monitoring
    ctrl.stop_monitoring("WinServer-01")

if __name__ == "__main__":
    main()