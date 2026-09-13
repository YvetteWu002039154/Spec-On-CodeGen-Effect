import json
from datetime import datetime, timedelta, date
from enum import Enum
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
    def __init__(
        self,
        task_id: str,
        name: str,
        worker_id: str,
        args: str = "",
        kwargs: str = "",
    ):
        self.task_id: str = task_id
        self.name: str = name
        self.worker_id: str = worker_id
        self.args: str = args
        self.kwargs: str = kwargs
        self.status: TaskStatus = TaskStatus.PENDING
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = self.created_at
        self.retries: int = 0
        self.is_orphan: bool = False
        self.result: Optional[str] = None

    def update_status(self, status: TaskStatus, result: Optional[str] = None) -> None:
        self.status = status
        self.updated_at = datetime.now()
        if result is not None:
            self.result = result
        if status == TaskStatus.RETRY:
            self.retries += 1

    def mark_as_orphan(self) -> None:
        self.is_orphan = True
        self.updated_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "worker_id": self.worker_id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "retries": self.retries,
            "is_orphan": self.is_orphan,
            "result": self.result,
        }


class Worker:
    def __init__(self, worker_id: str, name: str):
        self.worker_id: str = worker_id
        self.name: str = name
        self.status: WorkerStatus = WorkerStatus.ONLINE
        self.last_heartbeat: datetime = datetime.now()

    def heartbeat(self) -> None:
        self.last_heartbeat = datetime.now()
        self.status = WorkerStatus.ONLINE

    def mark_offline(self) -> None:
        self.status = WorkerStatus.OFFLINE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "worker_id": self.worker_id,
            "name": self.name,
            "status": self.status.value,
            "last_heartbeat": self.last_heartbeat.isoformat(),
        }


class TaskFilter:
    def __init__(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status: Optional[TaskStatus] = None,
        name: Optional[str] = None,
        worker_id: Optional[str] = None,
        search_text: Optional[str] = None,
    ):
        self.start_date = start_date
        self.end_date = end_date
        self.status = status
        self.name = name
        self.worker_id = worker_id
        self.search_text = search_text

    def matches(self, task: Task) -> bool:
        if self.start_date and task.created_at < self.start_date:
            return False
        if self.end_date and task.created_at > self.end_date:
            return False
        if self.status and task.status != self.status:
            return False
        if self.name and self.name not in task.name:
            return False
        if self.worker_id and task.worker_id != self.worker_id:
            return False
        if self.search_text:
            search_lower = self.search_text.lower()
            if not (
                search_lower in task.name.lower()
                or search_lower in task.task_id.lower()
                or search_lower in str(task.args).lower()
                or search_lower in str(task.kwargs).lower()
                or search_lower in str(task.result).lower()
            ):
                return False
        return True


class TaskRepository:
    def __init__(self):
        self._tasks: Dict[str, Task] = {}

    def add_task(self, task: Task) -> None:
        self._tasks[task.task_id] = task

    def get_task(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)

    def get_all_tasks(self) -> List[Task]:
        return list(self._tasks.values())

    def filter_tasks(self, task_filter: TaskFilter) -> List[Task]:
        return [task for task in self._tasks.values() if task_filter.matches(task)]

    def detect_orphans(self, active_worker_ids: Set[str]) -> List[Task]:
        orphans = []
        for task in self._tasks.values():
            if task.status in (TaskStatus.PENDING, TaskStatus.STARTED):
                if task.worker_id not in active_worker_ids:
                    task.mark_as_orphan()
                    orphans.append(task)
        return orphans


class WorkerRepository:
    def __init__(self):
        self._workers: Dict[str, Worker] = {}

    def add_worker(self, worker: Worker) -> None:
        self._workers[worker.worker_id] = worker

    def get_worker(self, worker_id: str) -> Optional[Worker]:
        return self._workers.get(worker_id)

    def get_all_workers(self) -> List[Worker]:
        return list(self._workers.values())

    def get_active_worker_ids(self) -> Set[str]:
        return {
            w.worker_id for w in self._workers.values() if w.status == WorkerStatus.ONLINE
        }

    def check_health(self, timeout_seconds: int = 60) -> List[Worker]:
        now = datetime.now()
        offline_workers = []
        for worker in self._workers.values():
            if worker.status == WorkerStatus.ONLINE:
                if (now - worker.last_heartbeat).total_seconds() > timeout_seconds:
                    worker.mark_offline()
                    offline_workers.append(worker)
        return offline_workers


class DailyTaskStatistics:
    def __init__(self, stat_date: date):
        self.stat_date: date = stat_date
        self.total_tasks: int = 0
        self.status_counts: Dict[TaskStatus, int] = {status: 0 for status in TaskStatus}
        self.total_retries: int = 0
        self.total_orphans: int = 0

    def record_task(self, task: Task) -> None:
        self.total_tasks += 1
        self.status_counts[task.status] += 1
        self.total_retries += task.retries
        if task.is_orphan:
            self.total_orphans += 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.stat_date.isoformat(),
            "total_tasks": self.total_tasks,
            "status_counts": {k.value: v for k, v in self.status_counts.items()},
            "total_retries": self.total_retries,
            "total_orphans": self.total_orphans,
        }


class StatisticsManager:
    def __init__(self, task_repository: TaskRepository):
        self.task_repository = task_repository

    def get_daily_statistics(self, target_date: date) -> DailyTaskStatistics:
        stats = DailyTaskStatistics(target_date)
        for task in self.task_repository.get_all_tasks():
            if task.created_at.date() == target_date:
                stats.record_task(task)
        return stats

    def get_history(self, start_date: date, end_date: date) -> List[DailyTaskStatistics]:
        history = []
        current_date = start_date
        while current_date <= end_date:
            history.append(self.get_daily_statistics(current_date))
            current_date += timedelta(days=1)
        return history


class WebSocketClient:
    def __init__(self, client_id: str):
        self.client_id = client_id

    def send(self, message: str) -> None:
        pass


class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocketClient] = []

    def connect(self, client: WebSocketClient) -> None:
        self.active_connections.append(client)

    def disconnect(self, client: WebSocketClient) -> None:
        if client in self.active_connections:
            self.active_connections.remove(client)

    def broadcast(self, event_type: str, data: Dict[str, Any]) -> None:
        message = json.dumps({"event": event_type, "data": data})
        for connection in self.active_connections:
            connection.send(message)


class AlembicMigrator:
    def __init__(self, database_url: str):
        self.database_url = database_url

    def run_auto_migrations(self) -> None:
        pass


class KanchiSystem:
    def __init__(self, database_url: str):
        self.task_repository = TaskRepository()
        self.worker_repository = WorkerRepository()
        self.statistics_manager = StatisticsManager(self.task_repository)
        self.websocket_manager = WebSocketManager()
        self.migrator = AlembicMigrator(database_url)
        self.worker_health_timeout_seconds = 60

    def initialize(self) -> None:
        self.migrator.run_auto_migrations()

    def register_worker(self, worker_id: str, name: str) -> Worker:
        worker = Worker(worker_id, name)
        self.worker_repository.add_worker(worker)
        self.websocket_manager.broadcast("worker_registered", worker.to_dict())
        return worker

    def process_worker_heartbeat(self, worker_id: str) -> None:
        worker = self.worker_repository.get_worker(worker_id)
        if worker:
            worker.heartbeat()
            self.websocket_manager.broadcast("worker_heartbeat", worker.to_dict())

    def monitor_worker_health(self) -> None:
        offline_workers = self.worker_repository.check_health(
            self.worker_health_timeout_seconds
        )
        for worker in offline_workers:
            self.websocket_manager.broadcast("worker_offline", worker.to_dict())
        
        active_worker_ids = self.worker_repository.get_active_worker_ids()
        orphaned_tasks = self.task_repository.detect_orphans(active_worker_ids)
        for task in orphaned_tasks:
            self.websocket_manager.broadcast("task_orphaned", task.to_dict())

    def receive_task_event(
        self,
        task_id: str,
        name: str,
        worker_id: str,
        status: TaskStatus,
        args: str = "",
        kwargs: str = "",
        result: Optional[str] = None,
    ) -> Task:
        task = self.task_repository.get_task(task_id)
        if not task:
            task = Task(task_id, name, worker_id, args, kwargs)
            self.task_repository.add_task(task)
            self.websocket_manager.broadcast("task_created", task.to_dict())

        task.update_status(status, result)
        self.websocket_manager.broadcast("task_updated", task.to_dict())
        return task

    def search_tasks(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status: Optional[TaskStatus] = None,
        name: Optional[str] = None,
        worker_id: Optional[str] = None,
        search_text: Optional[str] = None,
    ) -> List[Task]:
        task_filter = TaskFilter(
            start_date=start_date,
            end_date=end_date,
            status=status,
            name=name,
            worker_id=worker_id,
            search_text=search_text,
        )
        return self.task_repository.filter_tasks(task_filter)

    def get_daily_statistics(self, target_date: date) -> Dict[str, Any]:
        stats = self.statistics_manager.get_daily_statistics(target_date)
        return stats.to_dict()

    def get_statistics_history(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        history = self.statistics_manager.get_history(start_date, end_date)
        return [stats.to_dict() for stats in history]