import time
import threading
import random
import datetime
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
import uuid

# Try to import psutil for realistic metrics, fallback to random
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

# ---------- Enums ----------
class Priority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class ServerStatus(Enum):
    ONLINE = "online"
    OFFLINE = "offline"

# ---------- Data Classes ----------
@dataclass
class ProcessInfo:
    pid: int
    name: str
    cpu_percent: float
    memory_mb: float

@dataclass
class ServerMetrics:
    cpu_percent: float
    memory_percent: float
    network_sent_mb: float
    network_recv_mb: float
    timestamp: float = field(default_factory=time.time)

@dataclass
class ScreenCapture:
    image_data: bytes
    timestamp: float = field(default_factory=time.time)

# ---------- Agent (Simulates target machine) ----------
class Agent:
    """Background agent that collects system metrics and responds to commands."""
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self._running = True
        self._metrics_lock = threading.Lock()
        self._latest_metrics: Optional[ServerMetrics] = None
        self._latest_processes: List[ProcessInfo] = []
        self._collector_thread = threading.Thread(target=self._collect_loop, daemon=True)
        self._collector_thread.start()

    def _collect_loop(self):
        """Periodically updates metrics and process list."""
        while self._running:
            if HAS_PSUTIL:
                try:
                    cpu = psutil.cpu_percent(interval=None)
                    mem = psutil.virtual_memory().percent
                    net = psutil.net_io_counters()
                    # Convert bytes to MB
                    net_sent = net.bytes_sent / (1024 * 1024)
                    net_recv = net.bytes_recv / (1024 * 1024)
                    processes = []
                    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
                        try:
                            pinfo = proc.info
                            mem_mb = pinfo['memory_info'].rss / (1024 * 1024)
                            processes.append(ProcessInfo(
                                pid=pinfo['pid'],
                                name=pinfo['name'],
                                cpu_percent=pinfo['cpu_percent'],
                                memory_mb=mem_mb
                            ))
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
                    with self._metrics_lock:
                        self._latest_metrics = ServerMetrics(
                            cpu_percent=cpu,
                            memory_percent=mem,
                            network_sent_mb=net_sent,
                            network_recv_mb=net_recv
                        )
                        self._latest_processes = processes
                except Exception:
                    self._generate_random_metrics()
            else:
                self._generate_random_metrics()
            time.sleep(2)   # Update interval

    def _generate_random_metrics(self):
        """Fallback random metrics if psutil unavailable."""
        cpu = random.uniform(10.0, 90.0)
        mem = random.uniform(30.0, 80.0)
        net_sent = random.uniform(0.0, 50.0)
        net_recv = random.uniform(0.0, 50.0)
        processes = []
        for _ in range(random.randint(20, 60)):
            processes.append(ProcessInfo(
                pid=random.randint(1000, 9999),
                name=f"process_{random.randint(1,100)}",
                cpu_percent=random.uniform(0.0, 10.0),
                memory_mb=random.uniform(1.0, 200.0)
            ))
        with self._metrics_lock:
            self._latest_metrics = ServerMetrics(
                cpu_percent=cpu,
                memory_percent=mem,
                network_sent_mb=net_sent,
                network_recv_mb=net_recv
            )
            self._latest_processes = processes

    def get_metrics(self) -> Optional[ServerMetrics]:
        with self._metrics_lock:
            return self._latest_metrics

    def get_processes(self) -> List[ProcessInfo]:
        with self._metrics_lock:
            return list(self._latest_processes)

    def kill_process(self, pid: int) -> bool:
        """Simulate killing a process. Return success."""
        with self._metrics_lock:
            before = [p for p in self._latest_processes if p.pid == pid]
            if before:
                # Remove from list (simulate termination)
                self._latest_processes = [p for p in self._latest_processes if p.pid != pid]
                return True
        return False

    def capture_screen(self) -> ScreenCapture:
        """Simulate screen capture; return dummy image bytes."""
        # In real implementation, would use libraries like mss, pyautogui, or PIL
        placeholder = b"DUMMY_SCREEN_DATA_" + str(time.time()).encode()
        return ScreenCapture(image_data=placeholder)

    def is_online(self) -> bool:
        return self._running

    def shutdown(self):
        self._running = False

# ---------- Server (Connected RDP server representation) ----------
class Server:
    """Represents a managed RDP server with its Agent and monitoring history."""
    def __init__(self, server_id: str, agent: Agent):
        self.server_id = server_id
        self.agent = agent
        self.status = ServerStatus.ONLINE
        self.metrics_history: List[ServerMetrics] = []  # max size could be limited
        self._monitor_thread: Optional[threading.Thread] = None
        self._monitor_stop = threading.Event()

    def start_monitoring(self, interval: float = 2.0):
        """Continuously collect metrics into history."""
        if self._monitor_thread and self._monitor_thread.is_alive():
            return
        self._monitor_stop.clear()
        def _monitor():
            while not self._monitor_stop.is_set():
                metrics = self.agent.get_metrics()
                if metrics:
                    self.metrics_history.append(metrics)
                time.sleep(interval)
        self._monitor_thread = threading.Thread(target=_monitor, daemon=True)
        self._monitor_thread.start()

    def stop_monitoring(self):
        self._monitor_stop.set()

    def get_current_metrics(self) -> Optional[ServerMetrics]:
        return self.agent.get_metrics()

    def get_processes(self) -> List[ProcessInfo]:
        return self.agent.get_processes()

    def kill_process(self, pid: int) -> bool:
        return self.agent.kill_process(pid)

    def capture_screen(self) -> ScreenCapture:
        return self.agent.capture_screen()

    def get_history(self, limit: Optional[int] = None) -> List[ServerMetrics]:
        if limit is None:
            return list(self.metrics_history)
        return self.metrics_history[-limit:]

# ---------- Task ----------
class Task:
    def __init__(self, description: str, priority: Priority = Priority.MEDIUM):
        self.id = str(uuid.uuid4())[:8]
        self.description = description
        self.priority = priority
        self.status = TaskStatus.PENDING
        self.created_at = datetime.datetime.now()
        self.completed_at: Optional[datetime.datetime] = None

    def start(self):
        if self.status == TaskStatus.PENDING:
            self.status = TaskStatus.IN_PROGRESS

    def complete(self):
        if self.status == TaskStatus.IN_PROGRESS:
            self.status = TaskStatus.COMPLETED
            self.completed_at = datetime.datetime.now()

    def fail(self):
        if self.status == TaskStatus.IN_PROGRESS:
            self.status = TaskStatus.FAILED

    def set_priority(self, priority: Priority):
        self.priority = priority

    def __str__(self):
        return f"Task({self.id}) [{self.priority.value}] {self.description} - {self.status.value}"

# ---------- Task Manager ----------
class TaskManager:
    def __init__(self):
        self.tasks: List[Task] = []

    def add_task(self, description: str, priority: Priority = Priority.MEDIUM) -> Task:
        task = Task(description, priority)
        self.tasks.append(task)
        return task

    def get_tasks(self, status_filter: Optional[TaskStatus] = None) -> List[Task]:
        if status_filter:
            return [t for t in self.tasks if t.status == status_filter]
        return list(self.tasks)

    def get_task(self, task_id: str) -> Optional[Task]:
        for t in self.tasks:
            if t.id == task_id:
                return t
        return None

    def update_task_status(self, task_id: str, new_status: TaskStatus) -> bool:
        task = self.get_task(task_id)
        if not task:
            return False
        if new_status == TaskStatus.IN_PROGRESS:
            task.start()
        elif new_status == TaskStatus.COMPLETED:
            task.complete()
        elif new_status == TaskStatus.FAILED:
            task.fail()
        else:
            task.status = new_status
        return True

    def set_task_priority(self, task_id: str, priority: Priority) -> bool:
        task = self.get_task(task_id)
        if task:
            task.set_priority(priority)
            return True
        return False

    def remove_task(self, task_id: str) -> bool:
        task = self.get_task(task_id)
        if task:
            self.tasks.remove(task)
            return True
        return False

# ---------- NexusCtrl Main Controller ----------
class NexusCtrl:
    """Central controller managing servers and tasks."""
    def __init__(self):
        self.servers: Dict[str, Server] = {}
        self.task_manager = TaskManager()

    def register_server(self, server_id: str, agent: Agent) -> Server:
        server = Server(server_id, agent)
        self.servers[server_id] = server
        return server

    def remove_server(self, server_id: str) -> bool:
        if server_id in self.servers:
            server = self.servers.pop(server_id)
            server.stop_monitoring()
            server.agent.shutdown()
            return True
        return False

    def get_server(self, server_id: str) -> Optional[Server]:
        return self.servers.get(server_id)

    def list_servers(self) -> List[str]:
        return list(self.servers.keys())

    def monitor_all(self, interval: float = 2.0):
        """Start continuous monitoring for all servers."""
        for server in self.servers.values():
            server.start_monitoring(interval)

    def stop_all_monitoring(self):
        for server in self.servers.values():
            server.stop_monitoring()

    def get_server_status(self, server_id: str) -> Optional[ServerStatus]:
        server = self.get_server(server_id)
        if server:
            return server.status
        return None

    def get_metrics(self, server_id: str) -> Optional[ServerMetrics]:
        server = self.get_server(server_id)
        if server:
            return server.get_current_metrics()
        return None

    def get_processes(self, server_id: str) -> List[ProcessInfo]:
        server = self.get_server(server_id)
        if server:
            return server.get_processes()
        return []

    def kill_process(self, server_id: str, pid: int) -> bool:
        server = self.get_server(server_id)
        if server:
            return server.kill_process(pid)
        return False

    def capture_screen(self, server_id: str) -> Optional[ScreenCapture]:
        server = self.get_server(server_id)
        if server:
            return server.capture_screen()
        return None

    def get_metric_history(self, server_id: str, limit: int = None) -> List[ServerMetrics]:
        server = self.get_server(server_id)
        if server:
            return server.get_history(limit)
        return []

# ---------- Simple CLI Interface ----------
def print_metrics(metrics: ServerMetrics, server_id: str):
    print(f"\n--- {server_id} Metrics at {datetime.datetime.fromtimestamp(metrics.timestamp).isoformat()} ---")
    print(f"CPU: {metrics.cpu_percent:.1f}%")
    print(f"Memory: {metrics.memory_percent:.1f}%")
    print(f"Network: Sent {metrics.network_sent_mb:.2f} MB, Recv {metrics.network_recv_mb:.2f} MB")

def print_processes(processes: List[ProcessInfo]):
    print("\n--- Processes ---")
    print(f"{'PID':>8} {'Name':<20} {'CPU%':>6} {'Mem(MB)':>8}")
    for proc in processes[:20]:  # Show top 20
        print(f"{proc.pid:>8} {proc.name:<20} {proc.cpu_percent:>6.1f} {proc.memory_mb:>8.1f}")
    if len(processes) > 20:
        print(f"... and {len(processes)-20} more")

def print_tasks(tasks: List[Task]):
    print("\n--- Tasks ---")
    for task in tasks:
        print(f"ID: {task.id} | Priority: {task.priority.value:8} | Status: {task.status.value:12} | {task.description}")

def main():
    print("=== NexusCtrl - RDP Server Management Tool ===")
    nexus = NexusCtrl()

    # Create two simulated agents and register servers
    agent1 = Agent("agent_1")
    agent2 = Agent("agent_2")
    nexus.register_server("server-001", agent1)
    nexus.register_server("server-002", agent2)

    # Start monitoring history for both servers
    nexus.monitor_all(interval=3.0)

    # Add some tasks
    tm = nexus.task_manager
    tm.add_task("Check disk space on server-001", Priority.HIGH)
    tm.add_task("Update DNS records", Priority.MEDIUM)
    tm.add_task("Run security audit", Priority.CRITICAL)

    help_text = """
Commands:
  list                  - list all servers
  status <server_id>    - show server status
  metrics <server_id>   - current metrics
  processes <server_id> - show active processes
  kill <server_id> <pid>- kill a process
  screen <server_id>    - capture screen (simulated)
  history <server_id>   - show recent metric history
  tasks                 - list all tasks
  addtask <desc> [priority] - add task (priority: low/medium/high/critical)
  starttask <id>        - move task to in_progress
  completetask <id>     - mark task completed
  failtask <id>         - mark task failed
  removetask <id>       - delete task
  setpriority <id> <prio> - change task priority
  help                  - show this list
  quit                  - exit
    """
    print(help_text)

    # Wait a bit for initial metric collection
    time.sleep(2)

    try:
        while True:
            cmd = input("\nnexus> ").strip().split()
            if not cmd:
                continue
            action = cmd[0].lower()
            if action == "quit":
                break
            elif action == "list":
                servers = nexus.list_servers()
                print("Servers:", servers if servers else "none")
            elif action == "status":
                if len(cmd) < 2:
                    print("Usage: status <server_id>")
                    continue
                sid = cmd[1]
                status = nexus.get_server_status(sid)
                print(f"Status of {sid}: {status.value if status else 'not found'}")
            elif action == "metrics":
                if len(cmd) < 2:
                    print("Usage: metrics <server_id>")
                    continue
                sid = cmd[1]
                m = nexus.get_metrics(sid)
                if m:
                    print_metrics(m, sid)
                else:
                    print("No metrics available.")
            elif action == "processes":
                if len(cmd) < 2:
                    print("Usage: processes <server_id>")
                    continue
                sid = cmd[1]
                procs = nexus.get_processes(sid)
                if procs is not None:
                    print_processes(procs)
                else:
                    print("Server not found.")
            elif action == "kill":
                if len(cmd) < 3:
                    print("Usage: kill <server_id> <pid>")
                    continue
                sid = cmd[1]
                try:
                    pid = int(cmd[2])
                except ValueError:
                    print("Invalid PID")
                    continue
                if nexus.kill_process(sid, pid):
                    print(f"Process {pid} terminated on {sid}.")
                else:
                    print(f"Failed to kill process {pid} on {sid}.")
            elif action == "screen":
                if len(cmd) < 2:
                    print("Usage: screen <server_id>")
                    continue
                sid = cmd[1]
                capture = nexus.capture_screen(sid)
                if capture:
                    print(f"Screen capture from {sid}: {capture.image_data[:30]}...")
                else:
                    print("Server not found.")
            elif action == "history":
                if len(cmd) < 2:
                    print("Usage: history <server_id> [limit]")
                    continue
                sid = cmd[1]
                limit = None
                if len(cmd) >= 3:
                    try:
                        limit = int(cmd[2])
                    except ValueError:
                        print("Invalid limit")
                        continue
                history = nexus.get_metric_history(sid, limit)
                if history:
                    for i, m in enumerate(history[-10:]):  # show last 10 if no limit
                        print(f"#{i}: CPU {m.cpu_percent:.1f}% Mem {m.memory_percent:.1f}% at {datetime.datetime.fromtimestamp(m.timestamp).strftime('%H:%M:%S')}")
                else:
                    print("No history for that server.")
            elif action == "tasks":
                tasks = tm.get_tasks()
                print_tasks(tasks)
            elif action == "addtask":
                if len(cmd) < 2:
                    print("Usage: addtask <description> [priority]")
                    continue
                desc = cmd[1]
                prio_str = cmd[2].lower() if len(cmd) > 2 else "medium"
                try:
                    prio = Priority(prio_str)
                except ValueError:
                    print("Invalid priority. Use low/medium/high/critical")
                    continue
                task = tm.add_task(desc, prio)
                print(f"Task added with ID: {task.id}")
            elif action == "starttask":
                if len(cmd) < 2:
                    print("Usage: starttask <task_id>")
                    continue
                tid = cmd[1]
                if tm.update_task_status(tid, TaskStatus.IN_PROGRESS):
                    print("Task started.")
                else:
                    print("Task not found or cannot be started.")
            elif action == "completetask":
                if len(cmd) < 2:
                    print("Usage: completetask <task_id>")
                    continue
                tid = cmd[1]
                if tm.update_task_status(tid, TaskStatus.COMPLETED):
                    print("Task completed.")
                else:
                    print("Task not found or cannot be completed.")
            elif action == "failtask":
                if len(cmd) < 2:
                    print("Usage: failtask <task_id>")
                    continue
                tid = cmd[1]
                if tm.update_task_status(tid, TaskStatus.FAILED):
                    print("Task marked as failed.")
                else:
                    print("Task not found or cannot be failed.")
            elif action == "removetask":
                if len(cmd) < 2:
                    print("Usage: removetask <task_id>")
                    continue
                tid = cmd[1]
                if tm.remove_task(tid):
                    print("Task removed.")
                else:
                    print("Task not found.")
            elif action == "setpriority":
                if len(cmd) < 3:
                    print("Usage: setpriority <task_id> <priority>")
                    continue
                tid = cmd[1]
                try:
                    prio = Priority(cmd[2].lower())
                except ValueError:
                    print("Invalid priority")
                    continue
                if tm.set_task_priority(tid, prio):
                    print("Priority updated.")
                else:
                    print("Task not found.")
            elif action == "help":
                print(help_text)
            else:
                print("Unknown command. Type 'help'.")
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        nexus.stop_all_monitoring()
        for sid in list(nexus.servers.keys()):
            nexus.remove_server(sid)
        print("All agents stopped. Goodbye.")

if __name__ == "__main__":
    main()