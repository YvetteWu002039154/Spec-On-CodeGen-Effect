import datetime
import random
from enum import Enum
from typing import List, Dict, Optional

class TaskPriority(Enum):
    CRITICAL = 4
    HIGH = 3
    MEDIUM = 2
    LOW = 1

class TaskStatus(Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"

class Task:
    def __init__(self, task_id: str, title: str, description: str, priority: TaskPriority):
        self.task_id = task_id
        self.title = title
        self.description = description
        self.priority = priority
        self.status = TaskStatus.PENDING
        self.created_at = datetime.datetime.now()
        self.updated_at = self.created_at

    def update_status(self, new_status: TaskStatus) -> None:
        self.status = new_status
        self.updated_at = datetime.datetime.now()

class Process:
    def __init__(self, pid: int, name: str, cpu_usage: float, memory_usage: float):
        self.pid = pid
        self.name = name
        self.cpu_usage = cpu_usage
        self.memory_usage = memory_usage

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
        self._active_processes: Dict[int, Process] = {}

    def start_service(self) -> None:
        self.is_running = True
        self._seed_mock_processes()

    def stop_service(self) -> None:
        self.is_running = False
        self._active_processes.clear()

    def collect_metrics(self) -> Optional[SystemMetrics]:
        if not self.is_running:
            return None
        return SystemMetrics(
            cpu_usage=round(random.uniform(5.0, 95.0), 2),
            ram_usage=round(random.uniform(10.0, 99.0), 2),
            network_usage=round(random.uniform(0.1, 500.0), 2)
        )

    def capture_screen(self) -> Optional[bytes]:
        if not self.is_running:
            return None
        return b"mock_screen_capture_byte_data_stream"

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

    def _seed_mock_processes(self) -> None:
        mock_procs = [
            Process(1024, "svchost.exe", 1.2, 45.0),
            Process(2048, "explorer.exe", 2.5, 120.5),
            Process(3306, "mysqld.exe", 15.0, 512.0),
            Process(8080, "nginx.exe", 0.5, 25.0)
        ]
        for proc in mock_procs:
            self._active_processes[proc.pid] = proc

class Server:
    def __init__(self, server_id: str, hostname: str, ip_address: str):
        self.server_id = server_id
        self.hostname = hostname
        self.ip_address = ip_address
        self.agent = Agent(agent_id=f"agent_{server_id}")
        self.is_online = False
        self.performance_history: List[SystemMetrics] = []
        self.history_limit = 1000

    def connect(self) -> None:
        self.agent.start_service()
        self.is_online = True

    def disconnect(self) -> None:
        self.agent.stop_service()
        self.is_online = False

    def update_monitoring_data(self) -> None:
        if not self.is_online:
            return
        metrics = self.agent.collect_metrics()
        if metrics:
            self.performance_history.append(metrics)
            if len(self.performance_history) > self.history_limit:
                self.performance_history.pop(0)

    def get_active_processes(self) -> List[Process]:
        if not self.is_online:
            return []
        return self.agent.get_processes()

    def terminate_process(self, pid: int) -> bool:
        if not self.is_online:
            return False
        return self.agent.kill_process(pid)

    def get_live_screen(self) -> Optional[bytes]:
        if not self.is_online:
            return None
        return self.agent.capture_screen()

class NexusCtrl:
    def __init__(self):
        self.servers: Dict[str, Server] = {}
        self.tasks: Dict[str, Task] = {}

    def add_server(self, server: Server) -> None:
        self.servers[server.server_id] = server

    def remove_server(self, server_id: str) -> None:
        if server_id in self.servers:
            self.servers[server_id].disconnect()
            del self.servers[server_id]

    def get_server(self, server_id: str) -> Optional[Server]:
        return self.servers.get(server_id)

    def monitor_servers(self) -> None:
        for server in self.servers.values():
            server.update_monitoring_data()

    def create_task(self, task_id: str, title: str, description: str, priority: TaskPriority) -> Task:
        task = Task(task_id, title, description, priority)
        self.tasks[task_id] = task
        return task

    def update_task_status(self, task_id: str, status: TaskStatus) -> bool:
        task = self.tasks.get(task_id)
        if task:
            task.update_status(status)
            return True
        return False

    def get_all_tasks(self) -> List[Task]:
        return list(self.tasks.values())

    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        return [task for task in self.tasks.values() if task.status == status]

if __name__ == "__main__":
    nexus = NexusCtrl()

    server1 = Server("srv_01", "db-primary", "192.168.1.10")
    server2 = Server("srv_02", "web-node-1", "192.168.1.11")
    
    nexus.add_server(server1)
    nexus.add_server(server2)

    server1.connect()
    
    nexus.monitor_servers()

    processes = server1.get_active_processes()
    if processes:
        target_pid = processes[0].pid
        success = server1.terminate_process(target_pid)

    screen_data = server1.get_live_screen()

    nexus.create_task("t_01", "Update DB credentials", "Rotate passwords for primary DB", TaskPriority.CRITICAL)
    nexus.create_task("t_02", "Check web logs", "Review nginx error logs", TaskPriority.MEDIUM)

    nexus.update_task_status("t_01", TaskStatus.IN_PROGRESS)
    nexus.update_task_status("t_01", TaskStatus.COMPLETED)