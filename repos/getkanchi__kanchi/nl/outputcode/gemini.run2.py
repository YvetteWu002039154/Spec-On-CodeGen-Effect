import datetime
from typing import List, Optional, Dict, Any

class TaskStatus:
    PENDING = "PENDING"
    STARTED = "STARTED"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    RETRY = "RETRY"
    REVOKED = "REVOKED"

class WorkerStatus:
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"

class Task:
    def __init__(self, task_id: str, name: str, worker_id: Optional[str] = None):
        self.id: str = task_id
        self.name: str = name
        self.status: str = TaskStatus.PENDING
        self.worker_id: Optional[str] = worker_id
        self.created_at: datetime.datetime = datetime.datetime.now()
        self.updated_at: datetime.datetime = self.created_at
        self.retries: int = 0
        self.is_orphan: bool = False
        self.result: Optional[str] = None
        self.traceback: Optional[str] = None

    def update_status(self, status: str, result: Optional[str] = None, traceback: Optional[str] = None) -> None:
        self.status = status
        self.updated_at = datetime.datetime.now()
        if result is not None:
            self.result = result
        if traceback is not None:
            self.traceback = traceback

class Worker:
    def __init__(self, worker_id: str, hostname: str):
        self.id: str = worker_id
        self.hostname: str = hostname
        self.status: str = WorkerStatus.ONLINE
        self.last_heartbeat: datetime.datetime = datetime.datetime.now()

    def heartbeat(self) -> None:
        self.last_heartbeat = datetime.datetime.now()
        self.status = WorkerStatus.ONLINE

class TaskStatistic:
    def __init__(self, date: datetime.date):
        self.date: datetime.date = date
        self.total_tasks: int = 0
        self.successful_tasks: int = 0
        self.failed_tasks: int = 0
        self.retried_tasks: int = 0

class MigrationManager:
    def __init__(self):
        self.migrations_run: bool = False

    def run_auto_migrations(self) -> bool:
        try:
            import alembic.config
            import alembic.command
            alembic_cfg = alembic.config.Config("alembic.ini")
            alembic.command.upgrade(alembic_cfg, "head")
            self.migrations_run = True
            return True
        except ImportError:
            self.migrations_run = True
            return False
        except Exception:
            return False

class WebSocketManager:
    def __init__(self):
        self.active_connections: List[Any] = []

    def connect(self, client: Any) -> None:
        if client not in self.active_connections:
            self.active_connections.append(client)

    def disconnect(self, client: Any) -> None:
        if client in self.active_connections:
            self.active_connections.remove(client)

    def broadcast(self, event_type: str, data: Dict[str, Any]) -> None:
        message = {
            "event": event_type,
            "data": data,
            "timestamp": datetime.datetime.now().isoformat()
        }
        for connection in self.active_connections:
            if hasattr(connection, 'send'):
                connection.send(message)

class WorkerMonitor:
    def __init__(self, timeout_seconds: int = 60):
        self.workers: Dict[str, Worker] = {}
        self.timeout_seconds: int = timeout_seconds

    def register_worker(self, worker_id: str, hostname: str) -> Worker:
        if worker_id not in self.workers:
            self.workers[worker_id] = Worker(worker_id, hostname)
        else:
            self.workers[worker_id].heartbeat()
        return self.workers[worker_id]

    def check_health(self) -> List[Worker]:
        now = datetime.datetime.now()
        offline_workers = []
        for worker in self.workers.values():
            if worker.status == WorkerStatus.ONLINE:
                delta = now - worker.last_heartbeat
                if delta.total_seconds() > self.timeout_seconds:
                    worker.status = WorkerStatus.OFFLINE
                    offline_workers.append(worker)
        return offline_workers

    def get_worker(self, worker_id: str) -> Optional[Worker]:
        return self.workers.get(worker_id)

class StatisticsManager:
    def __init__(self):
        self.daily_stats: Dict[datetime.date, TaskStatistic] = {}

    def _get_or_create_stat(self, date: datetime.date) -> TaskStatistic:
        if date not in self.daily_stats:
            self.daily_stats[date] = TaskStatistic(date)
        return self.daily_stats[date]

    def record_task_event(self, task: Task) -> None:
        stat = self._get_or_create_stat(task.updated_at.date())
        stat.total_tasks += 1
        if task.status == TaskStatus.SUCCESS:
            stat.successful_tasks += 1
        elif task.status == TaskStatus.FAILURE:
            stat.failed_tasks += 1
        elif task.status == TaskStatus.RETRY:
            stat.retried_tasks += 1

    def get_history(self) -> List[TaskStatistic]:
        return sorted(self.daily_stats.values(), key=lambda x: x.date)

class TaskFilter:
    def __init__(self, tasks: List[Task]):
        self.tasks: List[Task] = tasks

    def search(self,
               start_date: Optional[datetime.datetime] = None,
               end_date: Optional[datetime.datetime] = None,
               status: Optional[str] = None,
               name: Optional[str] = None,
               worker_id: Optional[str] = None,
               full_text: Optional[str] = None) -> List[Task]:
        
        filtered = self.tasks

        if start_date:
            filtered = [t for t in filtered if t.created_at >= start_date]
        if end_date:
            filtered = [t for t in filtered if t.created_at <= end_date]
        if status:
            filtered = [t for t in filtered if t.status == status]
        if name:
            filtered = [t for t in filtered if name.lower() in t.name.lower()]
        if worker_id:
            filtered = [t for t in filtered if t.worker_id == worker_id]
        if full_text:
            ft_lower = full_text.lower()
            filtered = [
                t for t in filtered 
                if ft_lower in t.name.lower() 
                or (t.result and ft_lower in t.result.lower())
                or (t.traceback and ft_lower in t.traceback.lower())
            ]

        return filtered

class KanchiSystem:
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.websocket_manager: WebSocketManager = WebSocketManager()
        self.worker_monitor: WorkerMonitor = WorkerMonitor()
        self.statistics_manager: StatisticsManager = StatisticsManager()
        self.migration_manager: MigrationManager = MigrationManager()
        
        self.migration_manager.run_auto_migrations()

    def add_task(self, task_id: str, name: str, worker_id: Optional[str] = None) -> Task:
        task = Task(task_id, name, worker_id)
        self.tasks[task_id] = task
        self.websocket_manager.broadcast("task_created", {"task_id": task.id, "name": task.name})
        return task

    def update_task_status(self, task_id: str, status: str, result: Optional[str] = None, traceback: Optional[str] = None) -> None:
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        task.update_status(status, result, traceback)
        self.statistics_manager.record_task_event(task)
        self.websocket_manager.broadcast("task_updated", {"task_id": task.id, "status": task.status})

    def track_retry(self, task_id: str) -> None:
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        task.retries += 1
        self.update_task_status(task_id, TaskStatus.RETRY)
        self.websocket_manager.broadcast("task_retried", {"task_id": task.id, "retries": task.retries})

    def detect_orphans(self) -> List[Task]:
        self.worker_monitor.check_health()
        orphans = []
        for task in self.tasks.values():
            if task.status == TaskStatus.STARTED and task.worker_id:
                worker = self.worker_monitor.get_worker(task.worker_id)
                if not worker or worker.status == WorkerStatus.OFFLINE:
                    task.is_orphan = True
                    orphans.append(task)
                    self.websocket_manager.broadcast("task_orphaned", {"task_id": task.id})
        return orphans

    def filter_tasks(self, 
                     start_date: Optional[datetime.datetime] = None,
                     end_date: Optional[datetime.datetime] = None,
                     status: Optional[str] = None,
                     name: Optional[str] = None,
                     worker_id: Optional[str] = None,
                     full_text: Optional[str] = None) -> List[Task]:
        task_filter = TaskFilter(list(self.tasks.values()))
        return task_filter.search(
            start_date=start_date,
            end_date=end_date,
            status=status,
            name=name,
            worker_id=worker_id,
            full_text=full_text
        )

    def register_worker_heartbeat(self, worker_id: str, hostname: str) -> None:
        worker = self.worker_monitor.register_worker(worker_id, hostname)
        self.websocket_manager.broadcast("worker_heartbeat", {"worker_id": worker.id, "status": worker.status})

    def get_daily_statistics(self) -> List[TaskStatistic]:
        return self.statistics_manager.get_history()