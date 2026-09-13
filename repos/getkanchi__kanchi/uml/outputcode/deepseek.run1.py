import asyncio
import datetime
import json
import logging
import string
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Union

# ---------------------------------------------------------------------------
#  Forward declarations for custom types used in callbacks
# ---------------------------------------------------------------------------
class ActionResult:
    """Result returned by action handlers."""
    def __init__(self, success: bool, message: str = "", data: Dict[str, Any] = None):
        self.success = success
        self.message = message
        self.data = data or {}

class TaskProgressEvent:
    def __init__(self, task_id: str, task_name: str, progress: float, message: str = "", meta: Dict[str, Any] = None):
        self.task_id = task_id
        self.task_name = task_name
        self.progress = progress
        self.message = message
        self.meta = meta or {}

class TaskStepsEvent:
    def __init__(self, task_id: str, task_name: str, steps: List[Dict[str, Any]]):
        self.task_id = task_id
        self.task_name = task_name
        self.steps = steps

class TaskEvent:
    def __init__(self, task_id: str, task_name: str, event_type: str, worker_name: str = "", timestamp: datetime.datetime = None):
        self.task_id = task_id
        self.task_name = task_name
        self.event_type = event_type
        self.worker_name = worker_name
        self.timestamp = timestamp or datetime.datetime.utcnow()

class WorkerEvent:
    def __init__(self, hostname: str, event_type: str, status: str = "", active_tasks: int = 0, processed: int = 0, timestamp: datetime.datetime = None):
        self.hostname = hostname
        self.event_type = event_type
        self.status = status
        self.active_tasks = active_tasks
        self.processed = processed
        self.timestamp = timestamp or datetime.datetime.utcnow()

# ---------------------------------------------------------------------------
#  Database base helper (to_dict)
# ---------------------------------------------------------------------------
class BaseDB:
    """Mixin that provides a generic to_dict method based on __dict__."""
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}

# ---------------------------------------------------------------------------
#  agent.database classes
# ---------------------------------------------------------------------------
class ActionConfigDB(BaseDB):
    def __init__(self, id: int = None, name: str = "", description: str = "",
                 action_type: str = "", config: Dict[str, Any] = None,
                 usage_count: int = 0, last_used_at: Optional[datetime.datetime] = None,
                 created_by: str = "", created_at: Optional[datetime.datetime] = None,
                 updated_at: Optional[datetime.datetime] = None):
        self.id = id
        self.name = name
        self.description = description
        self.action_type = action_type
        self.config = config or {}
        self.usage_count = usage_count
        self.last_used_at = last_used_at
        self.created_by = created_by
        self.created_at = created_at or datetime.datetime.utcnow()
        self.updated_at = updated_at or datetime.datetime.utcnow()

class AppSettingDB(BaseDB):
    def __init__(self, key: str = "", value: str = "", value_type: str = "string",
                 category: str = "", label: str = "", description: str = "",
                 created_at: Optional[datetime.datetime] = None,
                 updated_at: Optional[datetime.datetime] = None):
        self.key = key
        self.value = value
        self.value_type = value_type
        self.category = category
        self.label = label
        self.description = description
        self.created_at = created_at or datetime.datetime.utcnow()
        self.updated_at = updated_at or datetime.datetime.utcnow()

class EnvironmentDB(BaseDB):
    def __init__(self, id: int = None, name: str = "", description: str = "",
                 is_active: bool = True, is_default: bool = False,
                 queue_patterns: List[str] = None, worker_patterns: List[str] = None,
                 created_at: Optional[datetime.datetime] = None,
                 updated_at: Optional[datetime.datetime] = None):
        self.id = id
        self.name = name
        self.description = description
        self.is_active = is_active
        self.is_default = is_default
        self.queue_patterns = queue_patterns or []
        self.worker_patterns = worker_patterns or []
        self.created_at = created_at or datetime.datetime.utcnow()
        self.updated_at = updated_at or datetime.datetime.utcnow()

class RetryRelationshipDB(BaseDB):
    def __init__(self, id: int = None, task_id: str = "", original_id: str = "",
                 retry_chain: List[str] = None, total_retries: int = 0,
                 created_at: Optional[datetime.datetime] = None,
                 updated_at: Optional[datetime.datetime] = None):
        self.id = id
        self.task_id = task_id
        self.original_id = original_id
        self.retry_chain = retry_chain or []
        self.total_retries = total_retries
        self.created_at = created_at or datetime.datetime.utcnow()
        self.updated_at = updated_at or datetime.datetime.utcnow()

class TaskActionDB(BaseDB):
    def __init__(self, id: int = None, action_type: str = "", status: str = "",
                 items: List[Any] = None, selected_original_count: int = 0,
                 original_task_ids: List[str] = None, selection_size: int = 0,
                 item_total: int = 0, item_created: int = 0, item_changed: int = 0,
                 item_skipped: int = 0, item_failed: int = 0, item_noop: int = 0,
                 summary: Dict[str, Any] = None,
                 initiated_by: str = "", initiated_by_user_id: str = "", initiated_session_id: str = "",
                 started_at: Optional[datetime.datetime] = None,
                 completed_at: Optional[datetime.datetime] = None,
                 created_at: Optional[datetime.datetime] = None):
        self.id = id
        self.action_type = action_type
        self.status = status
        self.items = items or []
        self.original_task_ids = original_task_ids or []
        self.selection_size = selection_size
        self.item_total = item_total
        self.item_created = item_created
        self.item_changed = item_changed
        self.item_skipped = item_skipped
        self.item_failed = item_failed
        self.item_noop = item_noop
        self.summary = summary or {}
        self.initiated_by = initiated_by
        self.initiated_by_user_id = initiated_by_user_id
        self.initiated_session_id = initiated_session_id
        self.started_at = started_at
        self.completed_at = completed_at
        self.created_at = created_at or datetime.datetime.utcnow()

class TaskActionItemDB(BaseDB):
    def __init__(self, id: int = None, action_id: int = None,
                 original_task_id: str = "", original_task_name: str = "",
                 outcome: str = "", reason: str = "", reason_code: str = "",
                 submitted_args: List[Any] = None, submitted_kwargs: Dict[str, Any] = None,
                 rerun_kind: str = "", target_queue: str = "",
                 rerun_task_id: str = "", rerun_task_name: str = "",
                 review_fingerprint: str = "", skip_category: str = "",
                 attempted_task_id: str = "",
                 created_at: Optional[datetime.datetime] = None,
                 updated_at: Optional[datetime.datetime] = None):
        self.id = id
        self.action_id = action_id
        self.original_task_id = original_task_id
        self.original_task_name = original_task_name
        self.outcome = outcome
        self.reason = reason
        self.reason_code = reason_code
        self.submitted_args = submitted_args or []
        self.submitted_kwargs = submitted_kwargs or {}
        self.rerun_kind = rerun_kind
        self.target_queue = target_queue
        self.rerun_task_id = rerun_task_id
        self.rerun_task_name = rerun_task_name
        self.review_fingerprint = review_fingerprint
        self.skip_category = skip_category
        self.attempted_task_id = attempted_task_id
        self.created_at = created_at or datetime.datetime.utcnow()
        self.updated_at = updated_at or datetime.datetime.utcnow()

class TaskDailyStatsDB(BaseDB):
    def __init__(self, id: int = None, date: Optional[datetime.date] = None,
                 task_name: str = "", total_executions: int = 0,
                 succeeded: int = 0, failed: int = 0, retried: int = 0,
                 revoked: int = 0, pending: int = 0, orphaned: int = 0,
                 avg_runtime: float = 0.0, min_runtime: float = 0.0,
                 max_runtime: float = 0.0, p50_runtime: float = 0.0,
                 p95_runtime: float = 0.0, p99_runtime: float = 0.0,
                 first_execution: Optional[datetime.datetime] = None,
                 last_execution: Optional[datetime.datetime] = None,
                 created_at: Optional[datetime.datetime] = None,
                 updated_at: Optional[datetime.datetime] = None):
        self.id = id
        self.date = date or datetime.date.today()
        self.task_name = task_name
        self.total_executions = total_executions
        self.succeeded = succeeded
        self.failed = failed
        self.retried = retried
        self.revoked = revoked
        self.pending = pending
        self.orphaned = orphaned
        self.avg_runtime = avg_runtime
        self.min_runtime = min_runtime
        self.max_runtime = max_runtime
        self.p50_runtime = p50_runtime
        self.p95_runtime = p95_runtime
        self.p99_runtime = p99_runtime
        self.first_execution = first_execution
        self.last_execution = last_execution
        self.created_at = created_at or datetime.datetime.utcnow()
        self.updated_at = updated_at or datetime.datetime.utcnow()

class TaskEventDB(BaseDB):
    def __init__(self, id: int = None, task_id: str = "", task_name: str = "",
                 event_type: str = "", timestamp: Optional[datetime.datetime] = None,
                 worker_name: str = "", hostname: str = "", queue: str = "",
                 routing_key: str = "", exchange: str = "", args: str = "",
                 kwargs: str = "", result: str = "", exception: str = "",
                 traceback: str = "", runtime: float = 0.0, retries: int = 0,
                 eta: Optional[datetime.datetime] = None, expires: Optional[datetime.datetime] = None,
                 parent_id: str = "", root_id: str = "", retry_of: str = "",
                 retried_by: str = "", is_orphan: bool = False,
                 orphaned_at: Optional[datetime.datetime] = None,
                 is_retry: bool = False, retry_count: int = 0,
                 has_retries: bool = False):
        self.id = id
        self.task_id = task_id
        self.task_name = task_name
        self.event_type = event_type
        self.timestamp = timestamp or datetime.datetime.utcnow()
        self.worker_name = worker_name
        self.hostname = hostname
        self.queue = queue
        self.routing_key = routing_key
        self.exchange = exchange
        self.args = args
        self.kwargs = kwargs
        self.result = result
        self.exception = exception
        self.traceback = traceback
        self.runtime = runtime
        self.retries = retries
        self.eta = eta
        self.expires = expires
        self.parent_id = parent_id
        self.root_id = root_id
        self.retry_of = retry_of
        self.retried_by = retried_by
        self.is_orphan = is_orphan
        self.orphaned_at = orphaned_at
        self.is_retry = is_retry
        self.retry_count = retry_count
        self.has_retries = has_retries

class TaskLatestDB(BaseDB):
    def __init__(self, task_id: str = "", task_name: str = "",
                 event_id: int = None, event_type: str = "",
                 timestamp: Optional[datetime.datetime] = None,
                 resolved: bool = False, resolved_at: Optional[datetime.datetime] = None,
                 resolved_by: str = "",  # rest same as TaskEventDB
                 worker_name: str = "", hostname: str = "", queue: str = "",
                 routing_key: str = "", exchange: str = "", args: str = "",
                 kwargs: str = "", result: str = "", exception: str = "",
                 traceback: str = "", runtime: float = 0.0, retries: int = 0,
                 eta: Optional[datetime.datetime] = None, expires: Optional[datetime.datetime] = None,
                 parent_id: str = "", root_id: str = "", retry_of: str = "",
                 retried_by: str = "", is_orphan: bool = False,
                 orphaned_at: Optional[datetime.datetime] = None,
                 is_retry: bool = False, retry_count: int = 0,
                 has_retries: bool = False):
        self.task_id = task_id
        self.task_name = task_name
        self.event_id = event_id
        self.event_type = event_type
        self.timestamp = timestamp or datetime.datetime.utcnow()
        self.resolved = resolved
        self.resolved_at = resolved_at
        self.resolved_by = resolved_by
        self.worker_name = worker_name
        self.hostname = hostname
        self.queue = queue
        self.routing_key = routing_key
        self.exchange = exchange
        self.args = args
        self.kwargs = kwargs
        self.result = result
        self.exception = exception
        self.traceback = traceback
        self.runtime = runtime
        self.retries = retries
        self.eta = eta
        self.expires = expires
        self.parent_id = parent_id
        self.root_id = root_id
        self.retry_of = retry_of
        self.retried_by = retried_by
        self.is_orphan = is_orphan
        self.orphaned_at = orphaned_at
        self.is_retry = is_retry
        self.retry_count = retry_count
        self.has_retries = has_retries

class TaskProgressDB(BaseDB):
    def __init__(self, id: int = None, task_id: str = "", task_name: str = "",
                 progress: float = 0.0, message: str = "", step_key: str = "",
                 meta: Dict[str, Any] = None, timestamp: Optional[datetime.datetime] = None):
        self.id = id
        self.task_id = task_id
        self.task_name = task_name
        self.progress = progress
        self.message = message
        self.step_key = step_key
        self.meta = meta or {}
        self.timestamp = timestamp or datetime.datetime.utcnow()

class TaskProgressLatestDB(BaseDB):
    def __init__(self, task_id: str = "", task_name: str = "",
                 progress: float = 0.0, message: str = "", step_key: str = "",
                 meta: Dict[str, Any] = None, updated_at: Optional[datetime.datetime] = None):
        self.task_id = task_id
        self.task_name = task_name
        self.progress = progress
        self.message = message
        self.step_key = step_key
        self.meta = meta or {}
        self.updated_at = updated_at or datetime.datetime.utcnow()

class TaskRegistryDB(BaseDB):
    def __init__(self, id: int = None, name: str = "", human_readable_name: str = "",
                 description: str = "", tags: List[str] = None,
                 first_seen: Optional[datetime.datetime] = None,
                 last_seen: Optional[datetime.datetime] = None,
                 created_at: Optional[datetime.datetime] = None,
                 updated_at: Optional[datetime.datetime] = None):
        self.id = id
        self.name = name
        self.human_readable_name = human_readable_name
        self.description = description
        self.tags = tags or []
        self.first_seen = first_seen or datetime.datetime.utcnow()
        self.last_seen = last_seen or datetime.datetime.utcnow()
        self.created_at = created_at or datetime.datetime.utcnow()
        self.updated_at = updated_at or datetime.datetime.utcnow()

class TaskRerunRelationshipDB(BaseDB):
    def __init__(self, id: int = None, original_task_id: str = "",
                 rerun_task_id: str = "", action_id: int = None,
                 created_by: str = "", created_at: Optional[datetime.datetime] = None):
        self.id = id
        self.original_task_id = original_task_id
        self.rerun_task_id = rerun_task_id
        self.action_id = action_id
        self.created_by = created_by
        self.created_at = created_at or datetime.datetime.utcnow()

class TaskResolutionDB(BaseDB):
    def __init__(self, task_id: str = "", resolved: bool = False,
                 resolved_at: Optional[datetime.datetime] = None,
                 resolved_by: str = ""):
        self.task_id = task_id
        self.resolved = resolved
        self.resolved_at = resolved_at
        self.resolved_by = resolved_by

class TaskStepsDB(BaseDB):
    def __init__(self, task_id: str = "", task_name: str = "",
                 steps: List[Dict[str, Any]] = None,
                 defined_at: Optional[datetime.datetime] = None):
        self.task_id = task_id
        self.task_name = task_name
        self.steps = steps or []
        self.defined_at = defined_at or datetime.datetime.utcnow()

class UserDB(BaseDB):
    def __init__(self, id: int = None, name: str = "", email: str = "",
                 provider: str = "", provider_account_id: str = "",
                 avatar_url: str = "", is_active: bool = True,
                 last_login_at: Optional[datetime.datetime] = None,
                 sessions: List[Any] = None,
                 created_at: Optional[datetime.datetime] = None,
                 updated_at: Optional[datetime.datetime] = None):
        self.id = id
        self.name = name
        self.email = email
        self.provider = provider
        self.provider_account_id = provider_account_id
        self.avatar_url = avatar_url
        self.is_active = is_active
        self.last_login_at = last_login_at
        self.sessions = sessions or []
        self.created_at = created_at or datetime.datetime.utcnow()
        self.updated_at = updated_at or datetime.datetime.utcnow()

class UserSessionDB(BaseDB):
    def __init__(self, session_id: str = "", user_id: int = None,
                 auth_provider: str = "", access_token_hash: str = "",
                 refresh_token_hash: str = "",
                 token_scopes: str = "",
                 access_token_expires_at: Optional[datetime.datetime] = None,
                 refresh_token_expires_at: Optional[datetime.datetime] = None,
                 preferences: Dict[str, Any] = None,
                 active_environment_id: int = None,
                 last_active: Optional[datetime.datetime] = None,
                 created_at: Optional[datetime.datetime] = None,
                 user: Optional[Any] = None):
        self.session_id = session_id
        self.user_id = user_id
        self.auth_provider = auth_provider
        self.access_token_hash = access_token_hash
        self.refresh_token_hash = refresh_token_hash
        self.token_scopes = token_scopes
        self.access_token_expires_at = access_token_expires_at
        self.refresh_token_expires_at = refresh_token_expires_at
        self.preferences = preferences or {}
        self.active_environment_id = active_environment_id
        self.last_active = last_active or datetime.datetime.utcnow()
        self.created_at = created_at or datetime.datetime.utcnow()
        self.user = user

class WorkerEventDB(BaseDB):
    def __init__(self, id: int = None, hostname: str = "", event_type: str = "",
                 status: str = "", active_tasks: int = 0, processed: int = 0,
                 timestamp: Optional[datetime.datetime] = None):
        self.id = id
        self.hostname = hostname
        self.event_type = event_type
        self.status = status
        self.active_tasks = active_tasks
        self.processed = processed
        self.timestamp = timestamp or datetime.datetime.utcnow()

class WorkflowDB(BaseDB):
    def __init__(self, id: int = None, name: str = "", description: str = "",
                 trigger_type: str = "", trigger_config: Dict[str, Any] = None,
                 conditions: Dict[str, Any] = None, actions: List[Dict[str, Any]] = None,
                 enabled: bool = True, priority: int = 0,
                 cooldown_seconds: int = 0, max_executions_per_hour: int = 0,
                 circuit_breaker_config: Dict[str, Any] = None,
                 execution_count: int = 0, success_count: int = 0, failure_count: int = 0,
                 last_executed_at: Optional[datetime.datetime] = None,
                 created_at: Optional[datetime.datetime] = None,
                 updated_at: Optional[datetime.datetime] = None,
                 created_by: str = ""):
        self.id = id
        self.name = name
        self.description = description
        self.trigger_type = trigger_type
        self.trigger_config = trigger_config or {}
        self.conditions = conditions or {}
        self.actions = actions or []
        self.enabled = enabled
        self.priority = priority
        self.cooldown_seconds = cooldown_seconds
        self.max_executions_per_hour = max_executions_per_hour
        self.circuit_breaker_config = circuit_breaker_config or {}
        self.execution_count = execution_count
        self.success_count = success_count
        self.failure_count = failure_count
        self.last_executed_at = last_executed_at
        self.created_at = created_at or datetime.datetime.utcnow()
        self.updated_at = updated_at or datetime.datetime.utcnow()
        self.created_by = created_by

class WorkflowExecutionDB(BaseDB):
    def __init__(self, id: int = None, workflow_id: int = None,
                 status: str = "", trigger_type: str = "",
                 trigger_event: Dict[str, Any] = None,
                 actions_executed: List[str] = None,
                 duration_ms: float = 0.0, error_message: str = "",
                 stack_trace: str = "", circuit_breaker_key: str = "",
                 workflow_snapshot: Dict[str, Any] = None,
                 triggered_at: Optional[datetime.datetime] = None,
                 started_at: Optional[datetime.datetime] = None,
                 completed_at: Optional[datetime.datetime] = None):
        self.id = id
        self.workflow_id = workflow_id
        self.status = status
        self.trigger_type = trigger_type
        self.trigger_event = trigger_event or {}
        self.actions_executed = actions_executed or []
        self.duration_ms = duration_ms
        self.error_message = error_message
        self.stack_trace = stack_trace
        self.circuit_breaker_key = circuit_breaker_key
        self.workflow_snapshot = workflow_snapshot or {}
        self.triggered_at = triggered_at
        self.started_at = started_at
        self.completed_at = completed_at


# ---------------------------------------------------------------------------
#  DatabaseManager (agent.database.DatabaseManager)
# ---------------------------------------------------------------------------
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

class DatabaseManager:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def get_session(self) -> Session:
        return self.SessionLocal()

    def run_migrations(self):
        # Stub: in a real app run alembic or SQLAlchemy metadata.create_all(engine)
        # For now, simply print
        print("Running migrations (if any)")

# ---------------------------------------------------------------------------
#  agent.monitor.CeleryEventMonitor
# ---------------------------------------------------------------------------
import celery

class CeleryEventMonitor:
    def __init__(self, app: celery.Celery = None, broker_url: str = ""):
        self.app = app
        self.broker_url = broker_url
        self.state = None
        self.workers: Dict[str, Dict[str, Any]] = {}
        self.progress_callback: Optional[Callable[[TaskProgressEvent], None]] = None
        self.steps_callback: Optional[Callable[[TaskStepsEvent], None]] = None
        self.task_callback: Optional[Callable[[TaskEvent], None]] = None
        self.worker_callback: Optional[Callable[[WorkerEvent], None]] = None

    def get_workers_info(self) -> Dict[str, Dict[str, Any]]:
        return self.workers

    def set_progress_callback(self, callback: Callable[[TaskProgressEvent], None]):
        self.progress_callback = callback

    def set_steps_callback(self, callback: Callable[[TaskStepsEvent], None]):
        self.steps_callback = callback

    def set_task_callback(self, callback: Callable[[TaskEvent], None]):
        self.task_callback = callback

    def set_worker_callback(self, callback: Callable[[WorkerEvent], None]):
        self.worker_callback = callback

    def start_monitoring(self):
        logging.info("Celery event monitoring started (stub)")

    def stop(self):
        logging.info("Celery event monitoring stopped (stub)")

# ---------------------------------------------------------------------------
#  agent.connection_manager.ConnectionManager
# ---------------------------------------------------------------------------
from starlette.websockets import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.client_filters: Dict[WebSocket, dict] = {}
        self.client_modes: Dict[WebSocket, str] = {}
        self.message_queue: Optional[asyncio.Queue] = None
        self._broadcast_task = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        self.client_filters.pop(websocket, None)
        self.client_modes.pop(websocket, None)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        if websocket in self.active_connections:
            await websocket.send_text(message)

    def set_client_filters(self, websocket: WebSocket, filters: dict):
        self.client_filters[websocket] = filters

    def set_client_mode(self, websocket: WebSocket, mode: str):
        self.client_modes[websocket] = mode

    def queue_broadcast(self, task_event: TaskEvent):
        if self.message_queue:
            self.message_queue.put_nowait(("task", task_event))

    def queue_progress_broadcast(self, progress_event):
        if self.message_queue:
            self.message_queue.put_nowait(("progress", progress_event))

    def queue_task_action_broadcast(self, action_event):
        if self.message_queue:
            self.message_queue.put_nowait(("action", action_event))

    def queue_worker_broadcast(self, worker_event: WorkerEvent):
        if self.message_queue:
            self.message_queue.put_nowait(("worker", worker_event))

    async def _broadcaster(self):
        while True:
            if self.message_queue is None:
                break
            try:
                msg_type, payload = await asyncio.wait_for(self.message_queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            # Broadcast to all active connections (simple version)
            for ws in self.active_connections:
                try:
                    if msg_type == "task":
                        await ws.send_text(json.dumps({"type": "task_event", "data": payload.__dict__}))
                    elif msg_type == "progress":
                        await ws.send_text(json.dumps({"type": "progress_event", "data": payload.__dict__}))
                    elif msg_type == "action":
                        await ws.send_text(json.dumps({"type": "action_event", "data": payload.__dict__}))
                    elif msg_type == "worker":
                        await ws.send_text(json.dumps({"type": "worker_event", "data": payload.__dict__}))
                except Exception:
                    self.disconnect(ws)
            self.message_queue.task_done()

    def start_background_broadcaster(self):
        if self._broadcast_task is None:
            self.message_queue = asyncio.Queue()
            self._broadcast_task = asyncio.create_task(self._broadcaster())

    def stop_background_broadcaster(self):
        if self._broadcast_task:
            self._broadcast_task.cancel()
            self._broadcast_task = None
            self.message_queue = None

# ---------------------------------------------------------------------------
#  agent.event_handler.EventHandler
# ---------------------------------------------------------------------------
class EventHandler:
    def __init__(self, connection_manager: ConnectionManager, db_manager: DatabaseManager):
        self.connection_manager = connection_manager
        self.db_manager = db_manager
        self.workflow_engine = None  # placeholder

    async def handle_task_event(self, task_event: TaskEvent):
        # Store in DB, broadcast via websockets
        self.connection_manager.queue_broadcast(task_event)

    async def handle_worker_event(self, worker_event: WorkerEvent):
        self.connection_manager.queue_worker_broadcast(worker_event)

    async def handle_progress_event(self, progress_event):
        self.connection_manager.queue_progress_broadcast(progress_event)

    async def handle_steps_event(self, steps_event):
        self.connection_manager.queue_task_action_broadcast(steps_event)

# ---------------------------------------------------------------------------
#  agent.services.actions.base.ActionHandler (abstract)
# ---------------------------------------------------------------------------
class ActionHandler(ABC):
    def __init__(self, db_manager: DatabaseManager, session: Optional[Session] = None,
                 monitor_instance: Optional[CeleryEventMonitor] = None):
        self.db_manager = db_manager
        self.session = session
        self.monitor_instance = monitor_instance

    @abstractmethod
    def execute(self, context: Dict[str, Any], params: Dict[str, Any]) -> ActionResult:
        raise NotImplementedError

    @abstractmethod
    def validate_params(self, params: Dict[str, Any]) -> tuple[bool, str]:
        raise NotImplementedError

    def render_template(self, template: str, context: Dict[str, Any]) -> str:
        # Simple string.Template substitution
        return string.Template(template).safe_substitute(context)

# ---------------------------------------------------------------------------
#  agent.services.actions.retry_action.RetryActionHandler
# ---------------------------------------------------------------------------
class RetryActionHandler(ActionHandler):
    def validate_params(self, params: Dict[str, Any]) -> tuple[bool, str]:
        required = ["task_id"]
        for key in required:
            if key not in params:
                return False, f"Missing required parameter: {key}"
        return True, ""

    def execute(self, context: Dict[str, Any], params: Dict[str, Any]) -> ActionResult:
        # Simulate retry logic
        task_id = params.get("task_id", "")
        # Here we would actually reschedule the task via Celery
        return ActionResult(success=True, message=f"Task {task_id} scheduled for retry")

# ---------------------------------------------------------------------------
#  agent.services.actions.slack_action.SlackActionHandler
# ---------------------------------------------------------------------------
class SlackActionHandler(ActionHandler):
    def validate_params(self, params: Dict[str, Any]) -> tuple[bool, str]:
        required = ["channel", "message"]
        for key in required:
            if key not in params:
                return False, f"Missing required parameter: {key}"
        return True, ""

    def execute(self, context: Dict[str, Any], params: Dict[str, Any]) -> ActionResult:
        # Simulate sending a Slack message
        channel = params["channel"]
        message = params["message"]
        rendered = self.render_template(message, context)
        # Here we'd call Slack API with rendered message
        return ActionResult(success=True, message=f"Message sent to {channel}", data={"rendered": rendered})

# ---------------------------------------------------------------------------
#  If run as main, do nothing
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("All classes defined. No execution.")