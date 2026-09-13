import json
from enum import Enum
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional, Any, Set

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

class Task:
    def __init__(self, task_id: str, name: str, worker_id: Optional[str] = None, args: Optional[str] = None, kwargs: Optional[str] = None):
        self.task_id: str = task_id
        self.name: str = name
        self.status: TaskStatus = TaskStatus.PENDING
        self.worker_id: Optional[str] = worker_id
        self.args: Optional[str] = args
        self.kwargs: Optional[str] = kwargs
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = self.created_at
        self.retries: int = 0
        self.is_orphan: bool = False
        self.result: Optional[str] = None
        self.traceback: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "status": self.status.value,
            "worker_id": self.worker_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "retries": self.retries,
            "is_orphan": self.is_orphan,
            "result": self.result
        }

class Worker:
    def __init__(self, worker_id: str, hostname: str):
        self.worker_id: str = worker_id
        self.hostname: str = hostname
        self.status: WorkerStatus = WorkerStatus.ONLINE
        self.last_heartbeat: datetime = datetime.now()

class DailyStatistic:
    def __init__(self, stat_date: date):
        self.stat_date: date = stat_date
        self.total_tasks: int = 0
        self.successful_tasks: int = 0
        self.failed_tasks: int = 0
        self.retried_tasks: int = 0

class WebSocketClient:
    def __init__(self, client_id: str):
        self.client_id: str = client_id

    def send(self, message: str) -> None:
        pass

class WebSocketManager:
    def __init__(self):
        self._active_connections: Set[WebSocketClient] = set()

    def connect(self, client: WebSocketClient) -> None:
        self._active_connections.add(client)

    def disconnect(self, client: WebSocketClient) -> None:
        self._active_connections.discard(client)

    def broadcast(self, event_type: str, data: Dict[str, Any]) -> None:
        message = json.dumps({"event": event_type, "data": data})
        for connection in self._active_connections:
            connection.send(message)

class WorkerManager:
    def __init__(self, heartbeat_timeout_seconds: int = 60):
        self._workers: Dict[str, Worker] = {}
        self._heartbeat_timeout = timedelta(seconds=heartbeat_timeout_seconds)

    def register_worker(self, worker_id: str, hostname: str) -> Worker:
        if worker_id not in self._workers:
            self._workers[worker_id] = Worker(worker_id, hostname)
        return self._workers[worker_id]

    def record_heartbeat(self, worker_id: str) -> None:
        if worker_id in self._workers:
            worker = self._workers[worker_id]
            worker.last_heartbeat = datetime.now()
            worker.status = WorkerStatus.ONLINE

    def check_health(self) -> List[Worker]:
        now = datetime.now()
        offline_workers = []
        for worker in self._workers.values():
            if worker.status == WorkerStatus.ONLINE and (now - worker.last_heartbeat) > self._heartbeat_timeout:
                worker.status = WorkerStatus.OFFLINE
                offline_workers.append(worker)
        return offline_workers

    def get_online_worker_ids(self) -> Set[str]:
        return {w.worker_id for w in self._workers.values() if w.status == WorkerStatus.ONLINE}

class StatisticsManager:
    def __init__(self):
        self._daily_stats: Dict[date, DailyStatistic] = {}

    def _get_or_create_stat(self, stat_date: date) -> DailyStatistic:
        if stat_date not in self._daily_stats:
            self._daily_stats[stat_date] = DailyStatistic(stat_date)
        return self._daily_stats[stat_date]

    def record_task_created(self, task: Task) -> None:
        stat = self._get_or_create_stat(task.created_at.date())
        stat.total_tasks += 1

    def record_task_status_change(self, task: Task) -> None:
        stat = self._get_or_create_stat(task.updated_at.date())
        if task.status == TaskStatus.SUCCESS:
            stat.successful_tasks += 1
        elif task.status == TaskStatus.FAILURE:
            stat.failed_tasks += 1
        elif task.status == TaskStatus.RETRY:
            stat.retried_tasks += 1

    def get_statistics_history(self, start_date: date, end_date: date) -> List[DailyStatistic]:
        return [
            stat for d, stat in self._daily_stats.items()
            if start_date <= d <= end_date
        ]

class TaskManager:
    def __init__(self, ws_manager: WebSocketManager, stats_manager: StatisticsManager):
        self._tasks: Dict[str, Task] = {}
        self._ws_manager: WebSocketManager = ws_manager
        self._stats_manager: StatisticsManager = stats_manager

    def add_task(self, task_id: str, name: str, worker_id: Optional[str] = None) -> Task:
        task = Task(task_id=task_id, name=name, worker_id=worker_id)
        self._tasks[task_id] = task
        self._stats_manager.record_task_created(task)
        self._ws_manager.broadcast("task_created", task.to_dict())
        return task

    def update_task(self, task_id: str, status: TaskStatus, worker_id: Optional[str] = None, result: Optional[str] = None, traceback: Optional[str] = None) -> Optional[Task]:
        if task_id not in self._tasks:
            return None
        
        task = self._tasks[task_id]
        task.status = status
        task.updated_at = datetime.now()
        
        if worker_id:
            task.worker_id = worker_id
        if result:
            task.result = result
        if traceback:
            task.traceback = traceback
            
        if status == TaskStatus.RETRY:
            task.retries += 1
            
        self._stats_manager.record_task_status_change(task)
        self._ws_manager.broadcast("task_updated", task.to_dict())
        return task

    def detect_orphans(self, online_worker_ids: Set[str]) -> List[Task]:
        orphans = []
        for task in self._tasks.values():
            if task.status == TaskStatus.STARTED and task.worker_id not in online_worker_ids:
                if not task.is_orphan:
                    task.is_orphan = True
                    task.updated_at = datetime.now()
                    orphans.append(task)
                    self._ws_manager.broadcast("task_orphaned", task.to_dict())
        return orphans

    def filter_tasks(
        self, 
        start_date: Optional[datetime] = None, 
        end_date: Optional[datetime] = None, 
        status: Optional[TaskStatus] = None, 
        name: Optional[str] = None, 
        worker_id: Optional[str] = None, 
        search_text: Optional[str] = None
    ) -> List[Task]:
        filtered = []
        for task in self._tasks.values():
            if start_date and task.created_at < start_date:
                continue
            if end_date and task.created_at > end_date:
                continue
            if status and task.status != status:
                continue
            if name and task.name != name:
                continue
            if worker_id and task.worker_id != worker_id:
                continue
            if search_text:
                search_lower = search_text.lower()
                name_match = search_lower in task.name.lower()
                result_match = task.result and search_lower in task.result.lower()
                traceback_match = task.traceback and search_lower in task.traceback.lower()
                if not (name_match or result_match or traceback_match):
                    continue
            filtered.append(task)
        return filtered

class MigrationManager:
    def __init__(self):
        self.current_revision: Optional[str] = None

    def run_auto_migrations(self) -> None:
        self.current_revision = "head"

class KanchiSystem:
    def __init__(self):
        self.ws_manager = WebSocketManager()
        self.stats_manager = StatisticsManager()
        self.worker_manager = WorkerManager()
        self.task_manager = TaskManager(self.ws_manager, self.stats_manager)
        self.migration_manager = MigrationManager()

    def startup(self) -> None:
        self.migration_manager.run_auto_migrations()

    def monitor_system_health(self) -> None:
        offline_workers = self.worker_manager.check_health()
        for worker in offline_workers:
            self.ws_manager.broadcast("worker_offline", {"worker_id": worker.worker_id})
        
        online_worker_ids = self.worker_manager.get_online_worker_ids()
        self.task_manager.detect_orphans(online_worker_ids)

if __name__ == "__main__":
    kanchi = KanchiSystem()
    kanchi.startup()
    
    client = WebSocketClient("client_1")
    kanchi.ws_manager.connect(client)
    
    kanchi.worker_manager.register_worker("worker_1", "host_a")
    kanchi.worker_manager.record_heartbeat("worker_1")
    
    kanchi.task_manager.add_task("task_1", "process_data", "worker_1")
    kanchi.task_manager.update_task("task_1", TaskStatus.STARTED, "worker_1")
    kanchi.task_manager.update_task("task_1", TaskStatus.RETRY, "worker_1", traceback="Connection timeout")
    
    kanchi.monitor_system_health()
    
    tasks = kanchi.task_manager.filter_tasks(status=TaskStatus.RETRY, search_text="timeout")
    
    kanchi.ws_manager.disconnect(client)