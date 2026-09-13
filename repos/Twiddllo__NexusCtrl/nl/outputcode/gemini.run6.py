import datetime
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
        self._task_id = task_id
        self._title = title
        self._description = description
        self._priority = priority
        self._status = TaskStatus.PENDING

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
    def priority(self) -> TaskPriority:
        return self._priority

    @property
    def status(self) -> TaskStatus:
        return self._status

    def update_status(self, new_status: TaskStatus) -> None:
        self._status = new_status

    def mark_completed(self) -> None:
        self._status = TaskStatus.COMPLETED

class Process:
    def __init__(self, pid: int, name: str, cpu_percent: float, memory_percent: float):
        self._pid = pid
        self._name = name
        self._cpu_percent = cpu_percent
        self._memory_percent = memory_percent

    @property
    def pid(self) -> int:
        return self._pid

    @property
    def name(self) -> str:
        return self._name

    @property
    def cpu_percent(self) -> float:
        return self._cpu_percent

    @property
    def memory_percent(self) -> float:
        return self._memory_percent

class SystemMetrics:
    def __init__(self, cpu_usage: float, ram_usage: float, network_tx: float, network_rx: float):
        self._cpu_usage = cpu_usage
        self._ram_usage = ram_usage
        self._network_tx = network_tx
        self._network_rx = network_rx
        self._timestamp = datetime.datetime.now()

    @property
    def cpu_usage(self) -> float:
        return self._cpu_usage

    @property
    def ram_usage(self) -> float:
        return self._ram_usage

    @property
    def network_tx(self) -> float:
        return self._network_tx

    @property
    def network_rx(self) -> float:
        return self._network_rx

    @property
    def timestamp(self) -> datetime.datetime:
        return self._timestamp

class Agent:
    def __init__(self, agent_id: str, hostname: str, max_history: int = 1000):
        self._agent_id = agent_id
        self._hostname = hostname
        self._is_online = False
        self._processes: Dict[int, Process] = {}
        self._metrics_history: List[SystemMetrics] = []
        self._max_history = max_history
        self._screen_capture: bytes = b""

    @property
    def agent_id(self) -> str:
        return self._agent_id

    @property
    def hostname(self) -> str:
        return self._hostname

    @property
    def is_online(self) -> bool:
        return self._is_online

    def set_online_status(self, status: bool) -> None:
        self._is_online = status

    def collect_metrics(self, metrics: SystemMetrics) -> None:
        if not self._is_online:
            raise ValueError("Cannot collect metrics: Agent is offline.")
        self._metrics_history.append(metrics)
        if len(self._metrics_history) > self._max_history:
            self._metrics_history.pop(0)

    def get_metrics_history(self) -> List[SystemMetrics]:
        return self._metrics_history.copy()

    def get_latest_metrics(self) -> Optional[SystemMetrics]:
        if not self._metrics_history:
            return None
        return self._metrics_history[-1]

    def update_processes(self, processes: List[Process]) -> None:
        if not self._is_online:
            raise ValueError("Cannot update processes: Agent is offline.")
        self._processes = {p.pid: p for p in processes}

    def get_active_processes(self) -> List[Process]:
        return list(self._processes.values())

    def capture_screen(self, image_data: bytes) -> None:
        if not self._is_online:
            raise ValueError("Cannot capture screen: Agent is offline.")
        self._screen_capture = image_data

    def get_screen_capture(self) -> bytes:
        return self._screen_capture

    def kill_process(self, pid: int) -> bool:
        if not self._is_online:
            raise ValueError("Cannot kill process: Agent is offline.")
        if pid in self._processes:
            del self._processes[pid]
            return True
        return False

class NexusCtrl:
    def __init__(self):
        self._agents: Dict[str, Agent] = {}
        self._tasks: Dict[str, Task] = {}

    def register_agent(self, agent_id: str, hostname: str) -> Agent:
        if agent_id in self._agents:
            raise ValueError(f"Agent with ID {agent_id} is already registered.")
        new_agent = Agent(agent_id, hostname)
        self._agents[agent_id] = new_agent
        return new_agent

    def remove_agent(self, agent_id: str) -> None:
        if agent_id in self._agents:
            del self._agents[agent_id]

    def get_agent(self, agent_id: str) -> Agent:
        if agent_id not in self._agents:
            raise KeyError(f"Agent with ID {agent_id} not found.")
        return self._agents[agent_id]

    def get_all_agents(self) -> List[Agent]:
        return list(self._agents.values())

    def set_agent_status(self, agent_id: str, is_online: bool) -> None:
        agent = self.get_agent(agent_id)
        agent.set_online_status(is_online)

    def get_agent_status(self, agent_id: str) -> bool:
        return self.get_agent(agent_id).is_online

    def terminate_remote_process(self, agent_id: str, pid: int) -> bool:
        agent = self.get_agent(agent_id)
        return agent.kill_process(pid)

    def create_task(self, task_id: str, title: str, description: str, priority: TaskPriority) -> Task:
        if task_id in self._tasks:
            raise ValueError(f"Task with ID {task_id} already exists.")
        new_task = Task(task_id, title, description, priority)
        self._tasks[task_id] = new_task
        return new_task

    def get_task(self, task_id: str) -> Task:
        if task_id not in self._tasks:
            raise KeyError(f"Task with ID {task_id} not found.")
        return self._tasks[task_id]

    def get_all_tasks(self) -> List[Task]:
        return list(self._tasks.values())

    def update_task_status(self, task_id: str, status: TaskStatus) -> None:
        task = self.get_task(task_id)
        task.update_status(status)

    def mark_task_completed(self, task_id: str) -> None:
        task = self.get_task(task_id)
        task.mark_completed()