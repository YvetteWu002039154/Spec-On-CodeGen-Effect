import datetime
from typing import List, Dict, Optional, Any
from enum import Enum
from dataclasses import dataclass, field

class TaskStatus(Enum):
    PENDING = "PENDING"
    STARTED = "STARTED"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    RETRY = "RETRY"
    REVOKED = "REVOKED"

class WorkerStatus(Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"

@dataclass
class Task:
    task_id: str
    name: str
    status: TaskStatus = TaskStatus.PENDING
    worker_hostname: Optional[str] = None
    created_at: datetime.datetime = field(default_factory=datetime.datetime.utcnow)
    updated_at: datetime.datetime = field(default_factory=datetime.datetime.utcnow)
    retries: int = 0
    is_orphan: bool = False
    result: Optional[str] = None
    traceback: Optional[str] = None

@dataclass
class Worker:
    hostname: str
    status: WorkerStatus = WorkerStatus.ONLINE
    last_heartbeat: datetime.datetime = field(default_factory=datetime.datetime.utcnow)

@dataclass
class DailyStatistic:
    date: datetime.date
    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    retried_tasks: int = 0

class WebSocketClient:
    def send(self, message: Dict[str, Any]) -> None:
        pass

class WebSocketManager:
    def __init__(self) -> None:
        self.clients: List[WebSocketClient] = []

    def connect(self, client: WebSocketClient) -> None:
        self.clients.append(client)

    def disconnect(self, client: WebSocketClient) -> None:
        if client in self.clients:
            self.clients.remove(client)

    def broadcast(self, message: Dict[str, Any]) -> None:
        for client in self.clients:
            client.send(message)

class MigrationManager:
    @staticmethod
    def run_auto_migrations() -> None:
        pass

class KanchiSystem:
    def __init__(self, worker_timeout_seconds: int = 60) -> None:
        self.tasks: Dict[str, Task] = {}
        self.workers: Dict[str, Worker] = {}
        self.daily_statistics: Dict[datetime.date, DailyStatistic] = {}
        self.ws_manager = WebSocketManager()
        self.worker_timeout_seconds = worker_timeout_seconds
        self.migration_manager = MigrationManager()
        self.migration_manager.run_auto_migrations()

    def register_worker(self, hostname: str) -> None:
        if hostname not in self.workers:
            self.workers[hostname] = Worker(hostname=hostname)
        else:
            self.workers[hostname].status = WorkerStatus.ONLINE
            self.workers[hostname].last_heartbeat = datetime.datetime.utcnow()
        self.ws_manager.broadcast({"event": "worker_registered", "hostname": hostname})

    def heartbeat_worker(self, hostname: str) -> None:
        if hostname in self.workers:
            self.workers[hostname].last_heartbeat = datetime.datetime.utcnow()
            self.workers[hostname].status = WorkerStatus.ONLINE
        else:
            self.register_worker(hostname)

    def check_worker_health(self) -> None:
        now = datetime.datetime.utcnow()
        for worker in self.workers.values():
            if worker.status == WorkerStatus.ONLINE:
                delta = now - worker.last_heartbeat
                if delta.total_seconds() > self.worker_timeout_seconds:
                    worker.status = WorkerStatus.OFFLINE
                    self.ws_manager.broadcast({"event": "worker_offline", "hostname": worker.hostname})
        self.detect_orphans()

    def receive_task_event(self, task_id: str, event_type: str, **kwargs: Any) -> None:
        now = datetime.datetime.utcnow()
        
        if task_id not in self.tasks:
            name = kwargs.get("name", "unknown_task")
            self.tasks[task_id] = Task(task_id=task_id, name=name, created_at=now)
            
        task = self.tasks[task_id]
        task.updated_at = now
        
        if "worker_hostname" in kwargs:
            task.worker_hostname = kwargs["worker_hostname"]
            
        if event_type == "task-received":
            task.status = TaskStatus.PENDING
        elif event_type == "task-started":
            task.status = TaskStatus.STARTED
        elif event_type == "task-succeeded":
            task.status = TaskStatus.SUCCESS
            task.result = kwargs.get("result")
            self._update_statistics(now.date(), TaskStatus.SUCCESS)
        elif event_type == "task-failed":
            task.status = TaskStatus.FAILURE
            task.traceback = kwargs.get("traceback")
            self._update_statistics(now.date(), TaskStatus.FAILURE)
        elif event_type == "task-retried":
            task.status = TaskStatus.RETRY
            task.retries += 1
            self._update_statistics(now.date(), TaskStatus.RETRY)
        elif event_type == "task-revoked":
            task.status = TaskStatus.REVOKED

        self.ws_manager.broadcast({
            "event": "task_updated",
            "task_id": task.task_id,
            "status": task.status.value
        })

    def detect_orphans(self) -> None:
        for task in self.tasks.values():
            if task.status == TaskStatus.STARTED and task.worker_hostname:
                worker = self.workers.get(task.worker_hostname)
                if worker and worker.status == WorkerStatus.OFFLINE:
                    task.is_orphan = True
                    self.ws_manager.broadcast({
                        "event": "task_orphaned",
                        "task_id": task.task_id
                    })

    def filter_tasks(
        self,
        start_date: Optional[datetime.datetime] = None,
        end_date: Optional[datetime.datetime] = None,
        status: Optional[TaskStatus] = None,
        name: Optional[str] = None,
        worker_hostname: Optional[str] = None,
        search_text: Optional[str] = None
    ) -> List[Task]:
        filtered = []
        for task in self.tasks.values():
            if start_date and task.created_at < start_date:
                continue
            if end_date and task.created_at > end_date:
                continue
            if status and task.status != status:
                continue
            if name and name.lower() not in task.name.lower():
                continue
            if worker_hostname and task.worker_hostname != worker_hostname:
                continue
            if search_text:
                search_lower = search_text.lower()
                in_name = search_lower in task.name.lower()
                in_id = search_lower in task.task_id.lower()
                in_result = task.result and search_lower in task.result.lower()
                in_traceback = task.traceback and search_lower in task.traceback.lower()
                if not (in_name or in_id or in_result or in_traceback):
                    continue
            filtered.append(task)
        return filtered

    def _update_statistics(self, date: datetime.date, status: TaskStatus) -> None:
        if date not in self.daily_statistics:
            self.daily_statistics[date] = DailyStatistic(date=date)
            
        stat = self.daily_statistics[date]
        stat.total_tasks += 1
        
        if status == TaskStatus.SUCCESS:
            stat.successful_tasks += 1
        elif status == TaskStatus.FAILURE:
            stat.failed_tasks += 1
        elif status == TaskStatus.RETRY:
            stat.retried_tasks += 1

    def get_daily_statistics(self, date: datetime.date) -> DailyStatistic:
        return self.daily_statistics.get(date, DailyStatistic(date=date))

    def get_history(self, days: int = 7) -> List[DailyStatistic]:
        today = datetime.datetime.utcnow().date()
        history = []
        for i in range(days):
            target_date = today - datetime.timedelta(days=i)
            history.append(self.get_daily_statistics(target_date))
        return history