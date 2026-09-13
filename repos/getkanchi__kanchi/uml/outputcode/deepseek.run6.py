from __future__ import annotations

import abc
import asyncio
import datetime
import logging
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Callable, Tuple, Union
from string import Template

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Placeholder for WebSocket if fastapi is not available
try:
    from fastapi import WebSocket
except ImportError:
    class WebSocket:
        pass

# Placeholder for SQLAlchemy types to allow import
try:
    from sqlalchemy import create_engine, Engine
    from sqlalchemy.orm import sessionmaker, Session
except ImportError:
    Engine = object
    sessionmaker = object
    Session = object


# ---------- Event / Action data classes ----------
@dataclass
class TaskProgressEvent:
    task_id: str
    task_name: str
    progress: Optional[float] = None
    message: str = ""
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskStepsEvent:
    task_id: str
    task_name: str
    steps: Any = None
    defined_at: Optional[datetime.datetime] = None


@dataclass
class TaskEvent:
    event_type: str
    task_id: str
    task_name: str
    timestamp: datetime.datetime
    hostname: Optional[str] = None
    queue: Optional[str] = None
    # other fields can be added as needed


@dataclass
class WorkerEvent:
    event_type: str
    hostname: str
    timestamp: datetime.datetime
    status: Optional[str] = None
    active_tasks: int = 0
    processed: int = 0


@dataclass
class ActionResult:
    success: bool
    message: str = ""
    data: Optional[Any] = None


# ---------- Base DB model ----------
class BaseDBModel:
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}


# ---------- Database entity classes (implemented as dataclasses for simplicity) ----------
@dataclass
class ActionConfigDB(BaseDBModel):
    action_type: Optional[str] = None
    config: Optional[Any] = None
    created_at: Optional[datetime.datetime] = None
    created_by: Optional[str] = None
    description: Optional[str] = None
    id: Optional[int] = None
    last_used_at: Optional[datetime.datetime] = None
    name: Optional[str] = None
    updated_at: Optional[datetime.datetime] = None
    usage_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AppSettingDB(BaseDBModel):
    category: Optional[str] = None
    created_at: Optional[datetime.datetime] = None
    description: Optional[str] = None
    key: Optional[str] = None
    label: Optional[str] = None
    updated_at: Optional[datetime.datetime] = None
    value: Optional[str] = None
    value_type: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EnvironmentDB(BaseDBModel):
    created_at: Optional[datetime.datetime] = None
    description: Optional[str] = None
    id: Optional[int] = None
    is_active: bool = False
    is_default: bool = False
    name: Optional[str] = None
    queue_patterns: Optional[str] = None
    updated_at: Optional[datetime.datetime] = None
    worker_patterns: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RetryRelationshipDB(BaseDBModel):
    created_at: Optional[datetime.datetime] = None
    id: Optional[int] = None
    original_id: Optional[str] = None
    retry_chain: Optional[str] = None
    task_id: Optional[str] = None
    total_retries: int = 0
    updated_at: Optional[datetime.datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TaskActionDB(BaseDBModel):
    action_type: Optional[str] = None
    completed_at: Optional[datetime.datetime] = None
    created_at: Optional[datetime.datetime] = None
    id: Optional[int] = None
    initiated_by: Optional[str] = None
    initiated_by_user_id: Optional[int] = None
    initiated_session_id: Optional[str] = None
    item_changed: int = 0
    item_created: int = 0
    item_failed: int = 0
    item_noop: int = 0
    item_skipped: int = 0
    item_total: int = 0
    items: Optional[Any] = None      # could be a JSON blob
    original_task_ids: Optional[List[str]] = field(default_factory=list)
    selection_size: int = 0
    started_at: Optional[datetime.datetime] = None
    status: Optional[str] = None
    summary: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TaskActionItemDB(BaseDBModel):
    action: Optional[str] = None
    action_id: Optional[int] = None
    attempted_task_id: Optional[str] = None
    created_at: Optional[datetime.datetime] = None
    id: Optional[int] = None
    original_task_id: Optional[str] = None
    original_task_name: Optional[str] = None
    outcome: Optional[str] = None
    reason: Optional[str] = None
    reason_code: Optional[str] = None
    rerun_kind: Optional[str] = None
    rerun_task_id: Optional[str] = None
    rerun_task_name: Optional[str] = None
    review_fingerprint: Optional[str] = None
    skip_category: Optional[str] = None
    submitted_args: Optional[Any] = None
    submitted_kwargs: Optional[Any] = None
    target_queue: Optional[str] = None
    updated_at: Optional[datetime.datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TaskDailyStatsDB(BaseDBModel):
    avg_runtime: Optional[float] = None
    created_at: Optional[datetime.datetime] = None
    date: Optional[datetime.date] = None
    failed: int = 0
    first_execution: Optional[datetime.datetime] = None
    id: Optional[int] = None
    last_execution: Optional[datetime.datetime] = None
    max_runtime: Optional[float] = None
    min_runtime: Optional[float] = None
    orphaned: int = 0
    p50_runtime: Optional[float] = None
    p95_runtime: Optional[float] = None
    p99_runtime: Optional[float] = None
    pending: int = 0
    retried: int = 0
    revoked: int = 0
    succeeded: int = 0
    task_name: Optional[str] = None
    total_executions: int = 0
    updated_at: Optional[datetime.datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TaskEventDB(BaseDBModel):
    args: Optional[Any] = None
    eta: Optional[Any] = None
    event_type: Optional[str] = None
    exception: Optional[str] = None
    exchange: Optional[str] = None
    expires: Optional[Any] = None
    has_retries: bool = False
    hostname: Optional[str] = None
    id: Optional[int] = None
    is_orphan: bool = False
    is_retry: bool = False
    kwargs: Optional[Any] = None
    orphaned_at: Optional[datetime.datetime] = None
    parent_id: Optional[str] = None
    queue: Optional[str] = None
    result: Optional[Any] = None
    retried_by: Optional[str] = None
    retries: int = 0
    retry_count: int = 0
    retry_of: Optional[str] = None
    root_id: Optional[str] = None
    routing_key: Optional[str] = None
    runtime: Optional[float] = None
    task_id: Optional[str] = None
    task_name: Optional[str] = None
    timestamp: Optional[datetime.datetime] = None
    traceback: Optional[str] = None
    worker_name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TaskLatestDB(BaseDBModel):
    args: Optional[Any] = None
    eta: Optional[Any] = None
    event_id: Optional[int] = None
    event_type: Optional[str] = None
    exception: Optional[str] = None
    exchange: Optional[str] = None
    expires: Optional[Any] = None
    has_retries: bool = False
    hostname: Optional[str] = None
    is_orphan: bool = False
    is_retry: bool = False
    kwargs: Optional[Any] = None
    orphaned_at: Optional[datetime.datetime] = None
    parent_id: Optional[str] = None
    queue: Optional[str] = None
    resolved: bool = False
    resolved_at: Optional[datetime.datetime] = None
    resolved_by: Optional[str] = None
    result: Optional[Any] = None
    retried_by: Optional[str] = None
    retries: int = 0
    retry_count: int = 0
    retry_of: Optional[str] = None
    root_id: Optional[str] = None
    routing_key: Optional[str] = None
    runtime: Optional[float] = None
    task_id: Optional[str] = None
    task_name: Optional[str] = None
    timestamp: Optional[datetime.datetime] = None
    traceback: Optional[str] = None
    worker_name: Optional[str] = None


@dataclass
class TaskProgressDB(BaseDBModel):
    id: Optional[int] = None
    message: Optional[str] = None
    meta: Optional[Any] = None
    progress: Optional[float] = None
    step_key: Optional[str] = None
    task_id: Optional[str] = None
    task_name: Optional[str] = None
    timestamp: Optional[datetime.datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TaskProgressLatestDB(BaseDBModel):
    message: Optional[str] = None
    meta: Optional[Any] = None
    progress: Optional[float] = None
    step_key: Optional[str] = None
    task_id: Optional[str] = None
    task_name: Optional[str] = None
    updated_at: Optional[datetime.datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TaskRegistryDB(BaseDBModel):
    created_at: Optional[datetime.datetime] = None
    description: Optional[str] = None
    first_seen: Optional[datetime.datetime] = None
    human_readable_name: Optional[str] = None
    id: Optional[int] = None
    last_seen: Optional[datetime.datetime] = None
    name: Optional[str] = None
    tags: Optional[Any] = None
    updated_at: Optional[datetime.datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TaskRerunRelationshipDB(BaseDBModel):
    action_id: Optional[int] = None
    created_at: Optional[datetime.datetime] = None
    created_by: Optional[str] = None
    id: Optional[int] = None
    original_task_id: Optional[str] = None
    rerun_task_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TaskResolutionDB(BaseDBModel):
    resolved: bool = False
    resolved_at: Optional[datetime.datetime] = None
    resolved_by: Optional[str] = None
    task_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TaskStepsDB(BaseDBModel):
    defined_at: Optional[datetime.datetime] = None
    steps: Optional[Any] = None
    task_id: Optional[str] = None
    task_name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class UserDB(BaseDBModel):
    avatar_url: Optional[str] = None
    created_at: Optional[datetime.datetime] = None
    email: Optional[str] = None
    id: Optional[int] = None
    is_active: bool = False
    last_login_at: Optional[datetime.datetime] = None
    name: Optional[str] = None
    provider: Optional[str] = None
    provider_account_id: Optional[str] = None
    sessions: Optional[Any] = None
    updated_at: Optional[datetime.datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class UserSessionDB(BaseDBModel):
    access_token_expires_at: Optional[datetime.datetime] = None
    access_token_hash: Optional[str] = None
    active_environment_id: Optional[int] = None
    auth_provider: Optional[str] = None
    created_at: Optional[datetime.datetime] = None
    last_active: Optional[datetime.datetime] = None
    preferences: Optional[Any] = None
    refresh_token_expires_at: Optional[datetime.datetime] = None
    refresh_token_hash: Optional[str] = None
    session_id: Optional[str] = None
    token_scopes: Optional[str] = None
    user: Optional[Any] = None
    user_id: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WorkerEventDB(BaseDBModel):
    active_tasks: int = 0
    event_type: Optional[str] = None
    hostname: Optional[str] = None
    id: Optional[int] = None
    processed: int = 0
    status: Optional[str] = None
    timestamp: Optional[datetime.datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WorkflowDB(BaseDBModel):
    actions: Optional[Any] = None
    circuit_breaker_config: Optional[Any] = None
    conditions: Optional[Any] = None
    cooldown_seconds: int = 0
    created_at: Optional[datetime.datetime] = None
    created_by: Optional[str] = None
    description: Optional[str] = None
    enabled: bool = False
    execution_count: int = 0
    failure_count: int = 0
    id: Optional[int] = None
    last_executed_at: Optional[datetime.datetime] = None
    max_executions_per_hour: int = 0
    name: Optional[str] = None
    priority: int = 0
    success_count: int = 0
    trigger_config: Optional[Any] = None
    trigger_type: Optional[str] = None
    updated_at: Optional[datetime.datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WorkflowExecutionDB(BaseDBModel):
    actions_executed: Optional[Any] = None
    circuit_breaker_key: Optional[str] = None
    completed_at: Optional[datetime.datetime] = None
    duration_ms: Optional[int] = None
    error_message: Optional[str] = None
    id: Optional[int] = None
    stack_trace: Optional[str] = None
    started_at: Optional[datetime.datetime] = None
    status: Optional[str] = None
    trigger_event: Optional[Any] = None
    trigger_type: Optional[str] = None
    triggered_at: Optional[datetime.datetime] = None
    workflow_id: Optional[int] = None
    workflow_snapshot: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------- Abstract ActionHandler ----------
class ActionHandler(abc.ABC):
    def __init__(self, db_manager: Any = None, monitor_instance: Optional[Any] = None, session: Optional[Any] = None):
        self.db_manager = db_manager
        self.monitor_instance = monitor_instance
        self.session = session

    @abc.abstractmethod
    def execute(self, context: Dict[str, Any], params: Dict[str, Any]) -> ActionResult:
        ...

    @abc.abstractmethod
    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        ...

    def render_template(self, template: str, context: Dict[str, Any]) -> str:
        return Template(template).safe_substitute(context)


# ---------- Concrete Action Handlers ----------
class RetryActionHandler(ActionHandler):
    def execute(self, context: Dict[str, Any], params: Dict[str, Any]) -> ActionResult:
        logger.info(f"Executing retry action with params: {params}")
        # Implement actual retry logic here
        return ActionResult(success=True, message="Retry initiated")

    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        required_fields = ['task_id']
        for field in required_fields:
            if field not in params:
                return False, f"Missing required parameter: {field}"
        return True, ""


class SlackActionHandler(ActionHandler):
    def execute(self, context: Dict[str, Any], params: Dict[str, Any]) -> ActionResult:
        logger.info(f"Executing slack action with params: {params}")
        # Implement Slack notification logic here
        return ActionResult(success=True, message="Slack notification sent")

    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        required_fields = ['channel', 'message']
        for field in required_fields:
            if field not in params:
                return False, f"Missing required parameter: {field}"
        return True, ""


# ---------- ConnectionManager ----------
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.client_filters: Dict[WebSocket, dict] = {}
        self.client_modes: Dict[WebSocket, str] = {}
        self.message_queue: Optional[asyncio.Queue] = None
        self._broadcast_task: Optional[asyncio.Task] = None

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)
        self.client_filters[websocket] = {}
        self.client_modes[websocket] = "default"
        logger.info(f"WebSocket connected: {websocket}")

    async def disconnect(self, websocket: WebSocket) -> None:
        self.active_connections.remove(websocket)
        self.client_filters.pop(websocket, None)
        self.client_modes.pop(websocket, None)
        logger.info(f"WebSocket disconnected: {websocket}")

    async def send_personal_message(self, message: str, websocket: WebSocket) -> None:
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Failed to send personal message: {e}")
            await self.disconnect(websocket)

    def set_client_filters(self, websocket: WebSocket, filters: dict) -> None:
        self.client_filters[websocket] = filters

    def set_client_mode(self, websocket: WebSocket, mode: str) -> None:
        self.client_modes[websocket] = mode

    def queue_broadcast(self, task_event: TaskEvent) -> None:
        if self.message_queue:
            self.message_queue.put_nowait({"type": "task_event", "data": task_event})

    def queue_progress_broadcast(self, progress_event: TaskProgressEvent) -> None:
        if self.message_queue:
            self.message_queue.put_nowait({"type": "progress_event", "data": progress_event})

    def queue_task_action_broadcast(self, action_event: Any) -> None:
        if self.message_queue:
            self.message_queue.put_nowait({"type": "task_action", "data": action_event})

    def queue_worker_broadcast(self, worker_event: WorkerEvent) -> None:
        if self.message_queue:
            self.message_queue.put_nowait({"type": "worker_event", "data": worker_event})

    async def start_background_broadcaster(self) -> None:
        if self.message_queue is None:
            self.message_queue = asyncio.Queue()
        if self._broadcast_task is None or self._broadcast_task.done():
            self._broadcast_task = asyncio.create_task(self._broadcast_loop())
        logger.info("Background broadcaster started")

    async def stop_background_broadcaster(self) -> None:
        if self._broadcast_task:
            self._broadcast_task.cancel()
            try:
                await self._broadcast_task
            except asyncio.CancelledError:
                pass
            self._broadcast_task = None
        logger.info("Background broadcaster stopped")

    async def _broadcast_loop(self) -> None:
        while True:
            try:
                msg_data = await self.message_queue.get()
                # Broadcast to all connected clients with appropriate filters / modes
                for ws in self.active_connections:
                    try:
                        # Convert data to JSON string; in production you'd apply filters
                        import json
                        payload = json.dumps(msg_data, default=str)
                        await ws.send_text(payload)
                    except Exception:
                        await self.disconnect(ws)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Error in broadcast loop: {e}")


# ---------- CeleryEventMonitor ----------
class CeleryEventMonitor:
    def __init__(
        self,
        app: Any = None,
        broker_url: str = "",
        progress_callback: Optional[Callable[[TaskProgressEvent], None]] = None,
        steps_callback: Optional[Callable[[TaskStepsEvent], None]] = None,
        task_callback: Optional[Callable[[TaskEvent], None]] = None,
        worker_callback: Optional[Callable[[WorkerEvent], None]] = None
    ):
        self.app = app
        self.broker_url = broker_url
        self.progress_callback = progress_callback
        self.steps_callback = steps_callback
        self.task_callback = task_callback
        self.worker_callback = worker_callback
        self.state = None  # could store monitoring state
        self.workers: Dict[str, Dict[str, Any]] = {}
        self._stop_flag = False

    def get_workers_info(self) -> Dict[str, Dict[str, Any]]:
        return self.workers

    def set_progress_callback(self, callback: Callable[[TaskProgressEvent], None]) -> None:
        self.progress_callback = callback

    def set_steps_callback(self, callback: Callable[[TaskStepsEvent], None]) -> None:
        self.steps_callback = callback

    def set_task_callback(self, callback: Callable[[TaskEvent], None]) -> None:
        self.task_callback = callback

    def set_worker_callback(self, callback: Callable[[WorkerEvent], None]) -> None:
        self.worker_callback = callback

    def start_monitoring(self) -> None:
        logger.info(f"Starting Celery event monitoring for broker: {self.broker_url}")
        # In a real implementation, connect to celery events and dispatch callbacks
        # self._stop_flag = False
        # asyncio.create_task(self._monitor_loop())
        pass

    def stop(self) -> None:
        logger.info("Stopping Celery event monitor")
        self._stop_flag = True


# ---------- EventHandler ----------
class EventHandler:
    def __init__(self, connection_manager: ConnectionManager, db_manager: Any = None, workflow_engine: Any = None):
        self.connection_manager = connection_manager
        self.db_manager = db_manager
        self.workflow_engine = workflow_engine

    def handle_task_event(self, task_event: TaskEvent) -> None:
        logger.info(f"Handling task event: {task_event}")
        self.connection_manager.queue_broadcast(task_event)
        # Persist to DB if needed using db_manager
        if self.db_manager:
            pass

    def handle_progress_event(self, progress_event: TaskProgressEvent) -> None:
        logger.info(f"Handling progress event: {progress_event}")
        self.connection_manager.queue_progress_broadcast(progress_event)

    def handle_steps_event(self, steps_event: TaskStepsEvent) -> None:
        logger.info(f"Handling steps event: {steps_event}")
        # Use connection_manager if it had steps broadcast; using progress for now
        # Could also persist steps
        self.connection_manager.queue_progress_broadcast(steps_event)  # placeholder

    def handle_worker_event(self, worker_event: WorkerEvent) -> None:
        logger.info(f"Handling worker event: {worker_event}")
        self.connection_manager.queue_worker_broadcast(worker_event)
        # If db_manager available, update in-memory worker list


# ---------- DatabaseManager ----------
class DatabaseManager:
    def __init__(self, database_url: str = "sqlite:///./app.db"):
        self.database_url = database_url
        self.engine: Any = None
        self.SessionLocal: Any = None
        try:
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
            self.engine = create_engine(database_url)
            self.SessionLocal = sessionmaker(bind=self.engine)
        except ImportError:
            logger.warning("SQLAlchemy not available; DatabaseManager will use mock connections")
            self.engine = None
            self.SessionLocal = None

    def get_session(self) -> Any:
        if self.SessionLocal:
            return self.SessionLocal()
        raise RuntimeError("SessionLocal not available; SQLAlchemy is required")

    def run_migrations(self) -> None:
        logger.info("Running database migrations...")
        # Placeholder: would call alembic or create tables
        try:
            if self.engine:
                # In real code, run Alembic commands
                pass
        except Exception as e:
            logger.error(f"Migrations failed: {e}")


# ---------- Example usage (not part of spec, but to illustrate it's runnable) ----------
if __name__ == "__main__":
    # Simple test
    db = DatabaseManager("sqlite:///test.db")
    cm = ConnectionManager()
    eh = EventHandler(connection_manager=cm)

    task_event = TaskEvent(event_type="task-started", task_id="abc", task_name="example_task", timestamp=datetime.datetime.now())
    eh.handle_task_event(task_event)

    worker = WorkerEvent(event_type="worker-online", hostname="worker1", timestamp=datetime.datetime.now(), status="online")
    eh.handle_worker_event(worker)

    action = RetryActionHandler()
    valid, msg = action.validate_params({"task_id": "123"})
    print(f"Validation: {valid}, {msg}")