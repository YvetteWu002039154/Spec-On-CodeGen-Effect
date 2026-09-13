import random
import time
import threading
from enum import Enum
from typing import Dict, List, Optional, Tuple
import uuid
from dataclasses import dataclass
from datetime import datetime

class Priority(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

class Task:
    def __init__(self, description: str, priority: Priority = Priority.MEDIUM):
        self.id = str(uuid.uuid4())
        self.description = description
        self.priority = priority
        self.status = TaskStatus.PENDING
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    def set_status(self, status: TaskStatus):
        self.status = status
        self.updated_at = datetime.now()
    
    def set_priority(self, priority: Priority):
        self.priority = priority
        self.updated_at = datetime.now()

class TaskManager:
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
    
    def add_task(self, description: str, priority: Priority = Priority.MEDIUM) -> Task:
        task = Task(description, priority)
        self.tasks[task.id] = task
        return task
    
    def update_status(self, task_id: str, status: TaskStatus) -> bool:
        task = self.tasks.get(task_id)
        if task:
            task.set_status(status)
            return True
        return False
    
    def set_priority(self, task_id: str, priority: Priority) -> bool:
        task = self.tasks.get(task_id)
        if task:
            task.set_priority(priority)
            return True
        return False
    
    def get_task(self, task_id: str) -> Optional[Task]:
        return self.tasks.get(task_id)
    
    def list_tasks(self, status_filter: Optional[TaskStatus] = None) -> List[Task]:
        tasks = list(self.tasks.values())
        if status_filter:
            tasks = [t for t in tasks if t.status == status_filter]
        return tasks
    
    def remove_task(self, task_id: str) -> bool:
        if task_id in self.tasks:
            del self.tasks[task_id]
            return True
        return False

@dataclass
class ProcessInfo:
    pid: int
    name: str
    cpu_percent: float
    memory_mb: float

class ServerAgent:
    def __init__(self, server_id: str, ip_address: str = "127.0.0.1"):
        self.server_id = server_id
        self.ip_address = ip_address
        self.status = "online"
        self._monitor_active = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        
        self.cpu = 0.0
        self.ram = 0.0
        self.network = 0.0
        self.history: List[Tuple[float, float, float, float]] = []
        self.processes: List[ProcessInfo] = []
        self._generate_initial_processes()
        self.screen_image: Optional[bytes] = None
        
        self.start_monitoring()
    
    def start_monitoring(self):
        if not self._monitor_active:
            self._monitor_active = True
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self._thread.start()
            self.status = "online"
    
    def stop_monitoring(self):
        if self._monitor_active:
            self._stop_event.set()
            if self._thread is not None:
                self._thread.join(timeout=2)
            self._monitor_active = False
            self.status = "offline"
    
    def _monitor_loop(self):
        while not self._stop_event.is_set():
            self._update_metrics()
            self._update_processes()
            self._capture_screen()
            time.sleep(2)
    
    def _update_metrics(self):
        with self._lock:
            cpu = max(0.0, min(100.0, self.cpu + random.uniform(-5, 5)))
            ram = max(0.0, min(100.0, self.ram + random.uniform(-3, 3)))
            network = max(0.0, min(1000.0, self.network + random.uniform(-10, 10)))
            self.cpu = round(cpu, 1)
            self.ram = round(ram, 1)
            self.network = round(network, 1)
            self.history.append((time.time(), self.cpu, self.ram, self.network))
            if len(self.history) > 100:
                self.history = self.history[-100:]
    
    def _generate_initial_processes(self):
        names = ["chrome.exe", "notepad.exe", "explorer.exe", "svchost.exe", "python.exe", "agent.exe"]
        self.processes = []
        for i, name in enumerate(names[:random.randint(2, 5)]):
            pid = random.randint(1000, 9999)
            self.processes.append(ProcessInfo(
                pid=pid,
                name=name,
                cpu_percent=round(random.uniform(0, 10), 1),
                memory_mb=round(random.uniform(10, 500), 1)
            ))
    
    def _update_processes(self):
        with self._lock:
            if random.random() < 0.3:
                if self.processes and random.random() < 0.5:
                    idx = random.randint(0, len(self.processes) - 1)
                    del self.processes[idx]
                else:
                    new_pid = random.randint(1000, 9999)
                    new_name = random.choice(["cmd.exe", "taskmgr.exe", "discord.exe", "notepad++.exe", "putty.exe"])
                    self.processes.append(ProcessInfo(
                        pid=new_pid,
                        name=new_name,
                        cpu_percent=round(random.uniform(0, 20), 1),
                        memory_mb=round(random.uniform(5, 300), 1)
                    ))
    
    def _capture_screen(self):
        with self._lock:
            self.screen_image = b'BM\x1a\x00\x00\x00\x00\x00\x00\x00\x1a\x00\x00\x00\x0c\x00\x00\x00\x01\x00\x01\x00\x01\x00\x18\x00\x00\x00\xff\x00\x00\xff\x00\x00\xff\x00\x00\x00\x00\x00\x00\x00'
    
    def get_current_metrics(self) -> Dict:
        with self._lock:
            return {
                "cpu": self.cpu,
                "ram": self.ram,
                "network": self.network,
                "status": self.status
            }
    
    def get_processes(self) -> List[ProcessInfo]:
        with self._lock:
            return list(self.processes)
    
    def kill_process(self, pid: int) -> bool:
        with self._lock:
            for proc in self.processes:
                if proc.pid == pid:
                    self.processes.remove(proc)
                    return True
            return False
    
    def get_screen_capture(self) -> Optional[bytes]:
        with self._lock:
            return self.screen_image
    
    def get_performance_history(self, limit: int = 20) -> List[Tuple[float, float, float, float]]:
        with self._lock:
            return self.history[-limit:] if len(self.history) >= limit else self.history
    
    def set_online(self):
        self.status = "online"
    
    def set_offline(self):
        self.status = "offline"

class NexusCtrl:
    def __init__(self):
        self.servers: Dict[str, ServerAgent] = {}
        self.task_manager = TaskManager()
    
    def add_server(self, server_id: str, ip_address: str = "127.0.0.1") -> bool:
        if server_id in self.servers:
            return False
        agent = ServerAgent(server_id, ip_address)
        self.servers[server_id] = agent
        return True
    
    def remove_server(self, server_id: str) -> bool:
        agent = self.servers.pop(server_id, None)
        if agent:
            agent.stop_monitoring()
            return True
        return False
    
    def get_server_status(self, server_id: str) -> Optional[Dict]:
        agent = self.servers.get(server_id)
        if agent:
            return agent.get_current_metrics()
        return None
    
    def get_server_processes(self, server_id: str) -> Optional[List[ProcessInfo]]:
        agent = self.servers.get(server_id)
        if agent:
            return agent.get_processes()
        return None
    
    def kill_process(self, server_id: str, pid: int) -> bool:
        agent = self.servers.get(server_id)
        if agent:
            return agent.kill_process(pid)
        return False
    
    def capture_server_screen(self, server_id: str) -> Optional[bytes]:
        agent = self.servers.get(server_id)
        if agent:
            return agent.get_screen_capture()
        return None
    
    def get_performance_history(self, server_id: str, limit: int = 20) -> Optional[List[Tuple[float, float, float, float]]]:
        agent = self.servers.get(server_id)
        if agent:
            return agent.get_performance_history(limit)
        return None
    
    def create_task(self, description: str, priority: Priority = Priority.MEDIUM) -> Task:
        return self.task_manager.add_task(description, priority)
    
    def update_task_status(self, task_id: str, status: TaskStatus) -> bool:
        return self.task_manager.update_status(task_id, status)
    
    def set_task_priority(self, task_id: str, priority: Priority) -> bool:
        return self.task_manager.set_priority(task_id, priority)
    
    def get_task(self, task_id: str) -> Optional[Task]:
        return self.task_manager.get_task(task_id)
    
    def list_tasks(self, status_filter: Optional[TaskStatus] = None) -> List[Task]:
        return self.task_manager.list_tasks(status_filter)
    
    def remove_task(self, task_id: str) -> bool:
        return self.task_manager.remove_task(task_id)

if __name__ == "__main__":
    pass